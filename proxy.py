import socket
import threading
import time
import signal
import sys
import numpy as np
import requests
from flask import Flask, request, jsonify, render_template, Response
from collections import deque
from sklearn.ensemble import IsolationForest
import logging

SHIELD_ACTIVE = True
MAX_RPS_PER_IP = 15.0
MIN_IAT_MS = 100
ANOMALY_TRAINING_SIZE = 100
CONTAMINATION = 0.05

app = Flask(__name__)

# FIX: Enable logging instead of disabling it
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Only reduce werkzeug verbosity, but don't silence it completely
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

global_traffic_history = deque(maxlen=500)
isolation_model = IsolationForest(contamination=CONTAMINATION, random_state=42)
is_model_trained = False

ip_stats = {}
blacklist = set()
stats_lock = threading.Lock()

system_stats = {
    "total_requests": 0,
    "blocked_requests": 0,
    "safe_requests": 0,
    "attack_allowed_requests": 0,
    "shield_active": True,
    "current_anomaly_score": 0.0,
    "defense_layer": "Idle",
    "uptime": 0,
    "current_rps": 0.0
}

TARGET_URL = 'http://localhost:5001'

# Global Stats Tracking
start_time = time.time()
last_rps_check = time.time()
request_counter_window = 0
global_rps = 0.0

def get_client_features(ip, current_time):
    if ip not in ip_stats:
        ip_stats[ip] = {
            "timestamps": deque(maxlen=20),
            "banned": False
        }
    
    stats = ip_stats[ip]
    stats["timestamps"].append(current_time)
    
    timestamps = list(stats["timestamps"])
    
    if len(timestamps) > 1:
        duration = timestamps[-1] - timestamps[0]
        rps = len(timestamps) / duration if duration > 0 else 0
    else:
        rps = 0
        
    if len(timestamps) > 1:
        iats = [t2 - t1 for t1, t2 in zip(timestamps[:-1], timestamps[1:])]
        mean_iat = np.mean(iats) * 1000
    else:
        mean_iat = 1000
        
    return rps, mean_iat

def train_isolation_forest():
    global is_model_trained, isolation_model
    if len(global_traffic_history) < ANOMALY_TRAINING_SIZE:
        return

    try:
        data = np.array(global_traffic_history)
        isolation_model.fit(data)
        is_model_trained = True
        logger.info("🤖 Isolation Forest model trained successfully")
    except Exception as e:
        logger.error(f"Error training model: {e}")

@app.route('/api/toggle_shield', methods=['POST'])
def toggle_shield():
    global SHIELD_ACTIVE
    SHIELD_ACTIVE = not SHIELD_ACTIVE
    system_stats["shield_active"] = SHIELD_ACTIVE
    logger.info(f"🛡️ SHIELD {'ACTIVATED' if SHIELD_ACTIVE else 'DEACTIVATED'}")
    print(f"🛡️ SHIELD {'ACTIVATED' if SHIELD_ACTIVE else 'DEACTIVATED'}", flush=True)
    return jsonify({"status": "success", "shield_active": SHIELD_ACTIVE})

@app.route('/api/reset_stats', methods=['POST'])
def reset_stats():
    global system_stats, ip_stats, blacklist, global_traffic_history
    
    with stats_lock:
        system_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "safe_requests": 0,
            "attack_allowed_requests": 0,
            "shield_active": SHIELD_ACTIVE,
            "current_anomaly_score": 0.0,
            "defense_layer": "Idle"
        }
        ip_stats = {}
        blacklist = set()
        global_traffic_history.clear()
        
    logger.info("🔄 SYSTEM RESET: All stats and bans cleared.")
    print("🔄 SYSTEM RESET: All stats and bans cleared.", flush=True)
    
    # Reset Timers
    global start_time, last_rps_check, request_counter_window, global_rps
    start_time = time.time()
    last_rps_check = time.time()
    request_counter_window = 0
    global_rps = 0.0
    
    return jsonify({"status": "success"})

@app.route('/api/stats')
def stats():
    return jsonify(system_stats)

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    global system_stats, is_model_trained
    
    current_time = time.time()
    client_ip = request.headers.get('X-Simulation-ID', request.remote_addr)
    
    system_stats["total_requests"] += 1
    
    # FIX: Add request logging - DISABLED FOR PERFORMANCE
    # logger.debug(f"📥 Request from {client_ip} to /{path}")

    # --- GLOBAL RPS CALCULATION ---
    with stats_lock:
        global request_counter_window, last_rps_check, global_rps
        request_counter_window += 1
        now = time.time()
        time_diff = now - last_rps_check
        
        if time_diff >= 1.0:
            global_rps = request_counter_window / time_diff
            request_counter_window = 0
            last_rps_check = now
            
        system_stats["current_rps"] = round(global_rps, 1)
        system_stats["uptime"] = int(now - start_time)
    # ------------------------------

    if client_ip in blacklist:
        system_stats["blocked_requests"] += 1
        logger.warning(f"🚫 Blacklisted IP attempted access: {client_ip}")
        return jsonify({"error": "Banned", "layer": "L0_Blacklist"}), 403

    with stats_lock:
        rps, mean_iat = get_client_features(client_ip, current_time)
        
        global_traffic_history.append([rps, mean_iat])
        
        if len(global_traffic_history) % 50 == 0:
            threading.Thread(target=train_isolation_forest).start()

    decision = "SAFE"
    violation_reason = ""
    
    if rps > MAX_RPS_PER_IP:
        decision = "ATTACK"
        violation_reason = f"L7_RateLimit ({rps:.1f} rps)"
    elif mean_iat < MIN_IAT_MS:
         decision = "ATTACK"
         violation_reason = f"L7_FastFlood ({mean_iat:.0f}ms IAT)"

    if decision == "SAFE" and is_model_trained:
        vector = np.array([[rps, mean_iat]])
        anomaly = isolation_model.predict(vector)[0]
        if anomaly == -1:
             decision = "ATTACK"
             violation_reason = "L4_Anomaly_Detection"
             system_stats["current_anomaly_score"] = 1.0
        else:
             system_stats["current_anomaly_score"] = 0.0

    if decision == "ATTACK":
        system_stats["defense_layer"] = violation_reason.split('_')[0] if violation_reason else "Unknown"
        
        if SHIELD_ACTIVE:
            if client_ip in ["127.0.0.1", "::1"]:
                logger.warning(f"⚠️ [Admin] Violating Rules: {violation_reason} (Allowed)")
                print(f"⚠️ [Admin] Violating Rules: {violation_reason} (Allowed)", flush=True)
            else:
                # logger.warning(f"🛡️ BLOCK [{client_ip}]: {violation_reason}")
                # print(f"🛡️ BLOCK [{client_ip}]: {violation_reason}", flush=True)
                pass
                blacklist.add(client_ip)
                system_stats["blocked_requests"] += 1
                return jsonify({"error": "Request Blocked", "reason": violation_reason}), 403
        else:
            system_stats["attack_allowed_requests"] += 1
            logger.info(f"⚠️ Attack detected but shield OFF: {client_ip} - {violation_reason}")
    else:
        system_stats["safe_requests"] += 1
        system_stats["defense_layer"] = "Monitoring"

    try:
        if request.method == 'GET':
            resp = requests.get(f"{TARGET_URL}/{path}", headers={key: value for (key, value) in request.headers if key != 'Host'}, allow_redirects=False)
        elif request.method == 'POST':
            resp = requests.post(f"{TARGET_URL}/{path}", headers={key: value for (key, value) in request.headers if key != 'Host'}, data=request.get_data(), allow_redirects=False)
        else:
             resp = requests.request(request.method, f"{TARGET_URL}/{path}", headers={key: value for (key, value) in request.headers if key != 'Host'}, data=request.get_data(), allow_redirects=False)
            
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        
        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        logger.error(f"❌ Origin connection failed: {e}")
        return jsonify({"error": "Origin Down"}), 502

if __name__ == '__main__':
    print("🛡️ STARTING HYBRID DEFENSE SYSTEM", flush=True)
    print(f"   - L7 Rules: Max {MAX_RPS_PER_IP} RPS, Min {MIN_IAT_MS}ms IAT", flush=True)
    print(f"   - L4 Model: Isolation Forest (Auto-training...)", flush=True)
    logger.info("Starting Flask app on port 5000")
    app.run(port=5000, threaded=True)
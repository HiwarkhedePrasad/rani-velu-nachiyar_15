import requests
import threading
import time
import random
import sys
from rich.console import Console
from rich.progress import Progress

console = Console()

TARGET_URL = "http://localhost:5000"
TOTAL_BOTS = 50

# --- SIMULATION CONFIG ---
NORMAL_IAT_RANGE = (0.1, 0.5)  # Faster normal users
FLOOD_IAT_RANGE = (0.001, 0.01)   # Extreme speed
SLOWLORIS_HOLD = 2.0           # Faster cycling

# Add counters for better visibility
request_counters = {
    "normal_success": 0,
    "normal_blocked": 0,
    "attack_sent": 0,
    "attack_blocked": 0
}
counter_lock = threading.Lock()

def normal_user(user_id):
    """Simulates a legitimate user reading pages."""
    while True:
        try:
            sleep_time = random.uniform(*NORMAL_IAT_RANGE)
            time.sleep(sleep_time)
            
            headers = {'X-Simulation-ID': f"user_{user_id}"}
            resp = requests.get(f"{TARGET_URL}/page{random.randint(1,5)}", headers=headers, timeout=5)
            
            with counter_lock:
                if resp.status_code == 403:
                    request_counters["normal_blocked"] += 1
                    console.print(f"[red]❌ User {user_id}: FALSE POSITIVE Block! ({resp.text})[/red]")
                    print(f"❌ User {user_id}: FALSE POSITIVE - {resp.status_code}", flush=True)
                else:
                    request_counters["normal_success"] += 1
                    console.print(f"[green]✅ User {user_id}: Normal View ({resp.status_code})[/green]")
                    print(f"✅ User {user_id}: Success - {resp.status_code}", flush=True)

        except Exception as e:
            console.print(f"[yellow]⚠️ User {user_id}: Connection error - {e}[/yellow]")
            time.sleep(1)

def flood_bot(bot_id):
    """L7 ATTACK: HTTP Flood (High RPS)."""
    headers = {'X-Simulation-ID': f"bot_flood_{bot_id}"}
    session = requests.Session()
    session.headers.update(headers)
    
    request_count = 0
    while True:
        try:
            with counter_lock:
                request_counters["attack_sent"] += 1
                
            resp = session.get(f"{TARGET_URL}/flood", timeout=1)
            request_count += 1
            
            with counter_lock:
                if resp.status_code == 403:
                    request_counters["attack_blocked"] += 1
                    
            if request_count % 500 == 0:
                console.print(f"[red]🔥 Flood Bot {bot_id}: {request_count} requests sent[/red]")
                
        except Exception:
            # Don't sleep on error, just retry fast
            pass

def slowloris_bot(bot_id):
    """L7 ATTACK: Slowloris (Connection Exhaustion)."""
    headers = {'X-Simulation-ID': f"bot_slow_{bot_id}"}
    attack_count = 0
    while True:
        try:
            resp = requests.get(f"{TARGET_URL}/slow", headers=headers, timeout=10)
            attack_count += 1
            
            with counter_lock:
                request_counters["attack_sent"] += 1
                if resp.status_code == 403:
                    request_counters["attack_blocked"] += 1
                    
            if attack_count % 10 == 0:
                console.print(f"[yellow]🐌 Slowloris Bot {bot_id}: {attack_count} slow requests[/yellow]")
                
            time.sleep(SLOWLORIS_HOLD)
        except Exception as e:
            time.sleep(1)

def volumetric_bot(bot_id):
    """L4 ATTACK: Volumetric Simulation (High Byte Count)."""
    headers = {'X-Simulation-ID': f"bot_vol_{bot_id}"}
    session = requests.Session()
    session.headers.update(headers)
    payload = "X" * 1024 * 5 # Reduced to 5KB for speed
    
    attack_count = 0
    while True:
        try:
            with counter_lock:
                request_counters["attack_sent"] += 1

            resp = session.post(f"{TARGET_URL}/volumetric", data=payload, timeout=1)
            attack_count += 1
            
            with counter_lock:
                if resp.status_code == 403:
                    request_counters["attack_blocked"] += 1
                    
            if attack_count % 50 == 0:
                console.print(f"[magenta]📦 Volumetric Bot {bot_id}: {attack_count} payloads sent[/magenta]")
                
        except Exception:
            pass

def stats_reporter():
    """Print statistics every 5 seconds."""
    while True:
        time.sleep(5)
        with counter_lock:
            console.print(f"\n[bold cyan]📊 STATS:[/bold cyan] Normal OK: {request_counters['normal_success']} | "
                         f"Normal Blocked: {request_counters['normal_blocked']} | "
                         f"Attacks Sent: {request_counters['attack_sent']} | "
                         f"Attacks Blocked: {request_counters['attack_blocked']}\n")
            print(f"\n📊 STATS: OK={request_counters['normal_success']}, "
                  f"FalsePos={request_counters['normal_blocked']}, "
                  f"AttacksSent={request_counters['attack_sent']}, "
                  f"AttacksBlocked={request_counters['attack_blocked']}\n", flush=True)

def start_simulation(mode):
    threads = []
    
    # Start stats reporter
    stats_thread = threading.Thread(target=stats_reporter)
    stats_thread.daemon = True
    stats_thread.start()
    
    if mode == 1: # Normal
        console.print("[green]🚀 Launching 20 Normal Users...[/green]")
        print("🚀 Launching 20 Normal Users...", flush=True)
        for i in range(20):
            t = threading.Thread(target=normal_user, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)
            
    elif mode == 2: # Attack
        console.print("[red]🚀 Launching 50 MIXED Attack Bots (Flood, Slow, Volumetric)...[/red]")
        print("🚀 Launching 50 MIXED Attack Bots...", flush=True)
        for i in range(50):
            r = random.random()
            if r < 0.6: 
                target = flood_bot
                name = "Flood"
            elif r < 0.8:
                target = slowloris_bot
                name = "Slowloris"
            else:
                target = volumetric_bot
                name = "Volumetric"
                
            t = threading.Thread(target=target, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)

    elif mode == 3: # Mixed
        console.print("[yellow]🚀 Launching Mixed Traffic (10 Users vs 30 Bots)...[/yellow]")
        print("🚀 Launching Mixed Traffic (10 Users vs 30 Bots)...", flush=True)
        # 10 Users
        for i in range(10):
            t = threading.Thread(target=normal_user, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)
        # 30 Bots
        for i in range(30):
            r = random.random()
            if r < 0.7: 
                target = flood_bot
            else:
                target = volumetric_bot
            
            t = threading.Thread(target=target, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)
            
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold]🛑 Simulation Stopped[/bold]")
        print("\n🛑 Simulation Stopped", flush=True)

if __name__ == "__main__":
    console.print("\n[bold cyan]🛡️ THE STORM: Traffic Generator (Hyper-Scale)[/bold cyan]")
    console.print("1. Normal Traffic Only")
    console.print("2. Full Assault (Flood/Slow/Volume)")
    console.print("3. Mixed Reality")
    
    print("\n🛡️ THE STORM: Traffic Generator", flush=True)
    print("1. Normal Traffic Only", flush=True)
    print("2. Full Assault (Flood/Slow/Volume)", flush=True)
    print("3. Mixed Reality", flush=True)
    
    try:
        choice = int(input("Enter choice: "))
        start_simulation(choice)
    except ValueError:
        print("Invalid choice", flush=True)
from flask import Flask, jsonify, make_response
import random
import sys
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

visitor_count = 0

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def home(path):
    global visitor_count
    visitor_count += 1
    
    # Multiple logging methods for visibility
    print(f"👤 User #{visitor_count} accessed the Vault. Path: /{path}", flush=True)
    print(f"LOG: Request received for path: {path}", file=sys.stderr, flush=True)
    logger.info(f"👤 User #{visitor_count} accessed /{path}")

    data = {
        "status": "success",
        "message": "Welcome to the Origin Server (The Vault).",
        "visitor_number": visitor_count,
        "server": "Origin/1.0",
        "random_id": random.randint(1, 100000)
    }
    
    response = make_response(jsonify(data))
    
    # Disable Caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

if __name__ == "__main__":
    print("🔐 The Vault (Origin Server) is running on Port 5001...", flush=True)
    logger.info("🔐 The Vault (Origin Server) starting on Port 5001")
    
    # Run with PYTHONUNBUFFERED environment variable effect
    app.run(host='0.0.0.0', port=5001, debug=False)
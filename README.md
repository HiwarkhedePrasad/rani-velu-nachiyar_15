# rani-velu-nachiyar_15
---

# 🛡️ Sentinel: Hybrid DDoS Defense System

### Multi-Layered L4/L7 Protection with Isolation Forest ML

Sentinel is an intelligent reverse proxy designed to safeguard origin servers from modern DDoS vectors. By combining **Deterministic Rule-Based Filtering (L7)** with **Machine Learning Anomaly Detection (L4)**, the system creates a resilient "Shield" that learns from traffic patterns in real-time.

---

## 🏗️ System Architecture

The system operates on a **Triple-Node Model** to simulate a real-world network environment:

1. **The Storm (Traffic Generator):** A multi-threaded engine capable of simulating legitimate user behavior and aggressive attack patterns (HTTP Floods, Slowloris, etc.).
2. **The Shield (Defense Proxy):** The brain of the system. It intercepts traffic, extracts features, queries the ML model, and decides whether to forward the request to the origin or drop it.
3. **The Vault (Origin Server):** The protected backend resource that remains isolated from direct public internet exposure.

---

## 🛡️ Defense Stack

### Layer 7: Deterministic Rules

| Feature | Logic | Purpose |
| --- | --- | --- |
| **Adaptive Rate Limiting** | Dynamic RPS thresholds per IP | Prevents brute-force and high-frequency flooding. |
| **IAT Analysis** | Inter-Arrival Time consistency check | Detects bot-driven scripts with robotic request intervals. |
| **Stateful Blacklisting** | Automated IP banning | Temporarily or permanently drops packets from known offenders. |

### Layer 4: Behavioral AI

Sentinel utilizes an **Isolation Forest** (Unsupervised Learning) to detect "Outliers."

* **Feature Engineering:** The proxy tracks  (Requests per second) and .
* **Self-Healing:** The model can be re-trained on live data to adapt to "Flash Crowds" (legitimate traffic spikes).

---

## 📂 Project Structure

```text
.
├── proxy.py               # Core Logic: Reverse Proxy + ML Defense Layer
├── origin.py              # Backend: The protected "Vault" server
├── traffic_generator.py   # Simulator: Generates Normal vs. Malicious loads
├── requirements.txt       # Dependencies (Flask, Scikit-learn, Pandas)
└── README.md              # Documentation

```

---

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repo
git clone https://github.com/HiwarkhedePrasad/rani-velu-nachiyar_15
cd sentinel-ddos

# Install dependencies
pip install -r requirements.txt

```

### 2. Execution Sequence

Open three terminal tabs and run the following in order:

| Step | Command | Endpoint | Description |
| --- | --- | --- | --- |
| **1** | `python origin.py` | `localhost:5001` | Starts the hidden backend. |
| **2** | `python proxy.py` | `localhost:5000` | Starts the Defense Shield. |
| **3** | `python traffic_generator.py` | N/A | Launches the attack simulator. |

---

## 📊 API Reference (Monitoring)

The Proxy exposes several endpoints for real-time monitoring and control:

* **`GET /api/stats`**: Returns JSON data on total requests, blocked IPs, and current system health.
* **`POST /api/toggle_shield`**: Remotely enable or disable the AI defense layer for A/B testing.
* **`POST /api/reset_stats`**: Wipes the current session data and clears the blacklist.

---

## ⚠️ Limitations & Future Scope

* **Current State:** Optimized for educational demos and hackathon presentations.
* **Roadmap:**
* [ ] Implement **JWT validation** at the proxy level.
* [ ] Add **Redis** support for persistent IP blacklisting across restarts.
* [ ] Integration of **Grafana/Prometheus** for visual traffic dashboards.



---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

**Disclaimer:** This tool is for **educational purposes only**. Use it to learn how to defend, not how to attack.



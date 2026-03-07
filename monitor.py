import time
import subprocess
import os

LOG_FILE = "/Users/Mrt0309/Desktop/openclaw_seo/logs/openclaw.log"
CONTAINER_NAME = "openclaw_isolated"

def monitor_logs():
    print(f"👁️ Monitoring {LOG_FILE} for anomalies...")
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("Log monitoring started\n")

    with open(LOG_FILE, 'r') as f:
        # Go to the end of the file
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(1)
                continue
            
            # Simple anomaly detection: check for "ERROR" or restricted Keywords
            if "CRITICAL_ERROR" in line or "UNAUTHORIZED_ACCESS" in line:
                print(f"🚨 Anomaly detected: {line.strip()}")
                stop_container()
                break

def stop_container():
    print(f"🛑 Stopping container {CONTAINER_NAME}...")
    subprocess.run(["docker-compose", "stop", CONTAINER_NAME], cwd="/Users/Mrt0309/Desktop/openclaw_seo")
    print("✅ Container stopped due to anomaly.")

if __name__ == "__main__":
    monitor_logs()

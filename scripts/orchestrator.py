import os
import subprocess
import logging
import time
import sys
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_DIR = "/app"
LOG_FILE = os.path.join(BASE_DIR, "logs/system.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_command(cmd):
    logging.info(f"Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing {' '.join(cmd)}: {e.stderr}")
        raise

def main_loop():
    logging.info("=== Starting Autonomous OpenClaw Loop ===")
    
    try:
        # 1. Fetch & Analyze (Default area: Setagaya for demo)
        run_command(["python3", "/app/scripts/api_fetcher.py", "13112"]) # Setagaya code
        run_command(["python3", "/app/scripts/data_importer.py", "13112"])
        run_command(["python3", "/app/scripts/price_analyzer.py", "世田谷区"])

        # 2. Generate Content
        # Example area to focus on based on analysis
        run_command(["python3", "/app/scripts/article_generator.py", "世田谷区", "三軒茶屋"])
        
        # 3. Optimization (Content/LLMO)
        # Note: Update logic here when LLMO structure changes for articles vs notes

        # 4. Links & Tools
        run_command(["python3", "/app/scripts/calculators.py"])
        run_command(["python3", "/app/scripts/internal_link_builder.py"])

        # 5. Build & Publish (Dry run for commit)
        run_command(["python3", "/app/scripts/deploy_site.py"])
        run_command(["python3", "/app/scripts/publish_site.py"])

        # 6. Analyze Traffic & Discover Topics
        if os.path.exists("/app/brain/04_Output/analytics_dummy.json"):
            run_command(["python3", "/app/scripts/traffic_analyzer.py"])
            run_command(["python3", "/app/scripts/topic_discovery.py"])

        # 7. Autonomous Improvement
        logging.info("Starting Improvement Engine...")
        run_command(["python3", "/app/scripts/improvement_engine.py"])

        # 8. Data Refinement & Quality
        logging.info("Starting Data Refinement...")
        run_command(["python3", "/app/scripts/data_refiner.py"])
        run_command(["python3", "/app/scripts/data_exporter.py"])

        logging.info("=== Autonomous Loop Cycle Complete ===")

    except Exception as e:
        logging.error(f"Fatal error in orchestrator: {e}")
        print(f"Orchestrator failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--loop":
        interval_hours = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        interval_seconds = interval_hours * 3600
        logging.info(f"Starting Orchestrator in Loop Mode (Every {interval_hours} hours)")
        print(f"🚀 Starting Autonomous Loop Mode (Every {interval_hours} hours)...")
        while True:
            main_loop()
            print(f"Sleeping for {interval_hours} hours...")
            time.sleep(interval_seconds)
    else:
        main_loop()

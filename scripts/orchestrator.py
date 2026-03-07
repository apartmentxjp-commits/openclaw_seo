import os
import subprocess
import logging
import time

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
        run_command(["python3", "/app/scripts/visual_generator.py", "世田谷区", "三軒茶屋"])
        
        # 3. LLMO & Optimization
        # Find latest file
        note_dir = "/app/brain/04_Output/Note"
        latest_file = sorted([os.path.join(note_dir, f) for f in os.listdir(note_dir) if f.endswith(".md")], key=os.path.getmtime)[-1]
        run_command(["python3", "/app/scripts/llmo_optimizer.py", latest_file])

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
    main_loop()

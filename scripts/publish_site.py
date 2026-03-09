import os
import subprocess
import logging

# Configuration
BASE_DIR = "/app"
PUBLIC_DIR = os.path.join(BASE_DIR, "site/public")
LOG_FILE = os.path.join(BASE_DIR, "logs/system.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_command(cmd, cwd=None):
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {' '.join(cmd)} - Error: {e.stderr}")
        raise

def publish():
    print("🚀 Starting auto-publish to GitHub Pages...")
    
    if not os.path.exists(PUBLIC_DIR):
        print("Error: Public directory not found. Please run deploy_site.py first.")
        return

    try:
        # Note: In a real environment, we'd need git credentials configured.
        # This assumes the /app directory (mapped to host) is already a git repo
        # or we are pushing the public folder specifically.
        
        # For this demo, let's assume we are acting on the project root
        os.chdir(BASE_DIR)
        
        print("Adding changes...")
        run_command(["git", "add", "."])
        
        print("Committing updates...")
        commit_msg = f"Auto-publish: {os.popen('date').read().strip()}"
        run_command(["git", "commit", "-m", commit_msg])
        
        print("Pushing to GitHub...")
        run_command(["git", "push", "origin", "main"])
        
        print("✅ Site changes committed and pushed autonomously.")
        logging.info("Auto-publish successful.")

    except Exception as e:
        print(f"❌ Publish failed: {e}")
        logging.error(f"Publish failed: {e}")

if __name__ == "__main__":
    publish()

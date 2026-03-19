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

    try:
        os.chdir(BASE_DIR)

        # ── Step 1: サムネイル自動追加 ──────────────────────────
        thumb_script = os.path.join(BASE_DIR, "scripts", "add_thumbnails.py")
        if os.path.exists(thumb_script):
            print("🖼️  Adding thumbnails to new articles...")
            run_command(["python3", thumb_script])
        else:
            print(f"⚠️  Thumbnail script not found: {thumb_script}")

        # ── Step 2: Hugo ビルド ──────────────────────────────────
        site_dir = os.path.join(BASE_DIR, "site")
        docs_dir = os.path.join(BASE_DIR, "docs")
        print("🔨 Building site with Hugo...")
        run_command(["hugo", "--minify", "--destination", docs_dir], cwd=site_dir)

        if not os.path.exists(docs_dir):
            print("Error: docs directory not found after Hugo build.")
            return

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

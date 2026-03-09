import os
import shutil
import subprocess

# Paths
NOTE_DIR = "/app/brain/04_Output/articles"
IMAGE_DIR = "/app/brain/04_Output/images"
HUGO_CONTENT_DIR = "/app/site/content/post"
HUGO_STATIC_DIR = "/app/site/static"
HUGO_SITE_DIR = "/app/site"

def sync_content():
    print("Cleaning and syncing content to Hugo...")
    print("Syncing content to Hugo...")
    os.makedirs(HUGO_CONTENT_DIR, exist_ok=True)
    
    # Sync Markdown files (excluding tests/txt)
    for root, dirs, files in os.walk(NOTE_DIR):
        for file in files:
            if file.endswith(".md"):
                try:
                    shutil.copy(os.path.join(root, file), HUGO_CONTENT_DIR)
                except Exception as e:
                    print(f"Warning: Could not copy {file}: {e}")

    # Sync Images
    print("Syncing images...")
    if os.path.exists(IMAGE_DIR):
        # We want to copy everything in images/ to site/static/images/
        dest_img_dir = os.path.join(HUGO_STATIC_DIR, "images")
        dest_img_dir = os.path.join(HUGO_STATIC_DIR, "images")
        if not os.path.exists(dest_img_dir):
            os.makedirs(dest_img_dir, exist_ok=True)
        # shutil.copytree(IMAGE_DIR, dest_img_dir, dirs_exist_ok=True) # Ensure Python 3.8+ or use alternate method

def build_site():
    print("Building Hugo site...")
    try:
        result = subprocess.run(["hugo", "-s", HUGO_SITE_DIR], check=True, capture_output=True, text=True)
        print(result.stdout)
        print("✅ Site built successfully in /app/site/public")
    except subprocess.CalledProcessError as e:
        print(f"❌ Hugo build failed: {e.stderr}")

if __name__ == "__main__":
    sync_content()
    build_site()

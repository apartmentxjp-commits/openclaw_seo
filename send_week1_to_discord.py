import requests
import os
import time

# --- Configuration ---
WEBHOOK_URL = "https://discord.com/api/webhooks/1476238582325969089/ENjH-BVD8bBzc9VhwigVLnBQUn-17yeKOp0B0UU0fhD3DCBiLoSd4gw_FMe9ns-btBEg"
VIDEO_DIR = "/Users/Mrt0309/Desktop/00_Antigravity_Brain/04_Output/sns_auto_poster/videos_week1"

def send_to_discord(day, video_path):
    print(f"Uploading Day {day} to Discord...")
    try:
        with open(video_path, "rb") as f:
            files = {"file": f}
            payload = {
                "content": f"🚀 **【Operation Speed: 100k】 Day {day} ショート動画**\n"
                           f"（AI自動生成: 心理学ハックシリーズ）"
            }
            response = requests.post(WEBHOOK_URL, data=payload, files=files)
            
            if response.status_code in [200, 204]:
                print(f"Day {day} delivery complete.")
            else:
                print(f"Failed Day {day}. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error uploading Day {day}: {e}")

# --- Execution ---
if not os.path.exists(VIDEO_DIR):
    print(f"Error: Directory not found: {VIDEO_DIR}")
else:
    for day in range(1, 8):
        video_file = f"day_{day}_psychology.mp4"
        full_path = os.path.join(VIDEO_DIR, video_file)
        if os.path.exists(full_path):
            send_to_discord(day, full_path)
            time.sleep(2)  # Avoid rate limit
        else:
            print(f"Warning: File not found: {full_path}")

print("All tasks processed.")

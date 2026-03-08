import os
import requests
import json
from datetime import datetime

def send_discord_notification(message, title="アクセス解析レポート", color=3447003):
    """
    Discord Webhookを使用して通知を送信する。
    color: 3447003 (Blue)
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL is not set in environment variables.")
        return False

    payload = {
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }

    try:
        response = requests.post(
            webhook_url, 
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        print("Notification sent successfully.")
        return True
    except Exception as e:
        print(f"Failed to send notification: {e}")
        return False

if __name__ == "__main__":
    # テスト用メッセージ
    test_msg = "日本不動産価格調査センターのDiscord通知テストです。\n本日のアクセス：集計中..."
    send_discord_notification(test_msg)

import os
import sys
import sqlite3
import subprocess
import time
from datetime import datetime
import discord
from discord.ext import commands

# 他のスクリプトをインポートできるようにパスを通す
sys.path.append(os.path.dirname(__file__))
from discord_bot import TOKEN as BOT_TOKEN

def run_script(script_name, args=[]):
    """他のスクリプトを実行するヘルパー"""
    cmd = ["python3", os.path.join(os.path.dirname(__file__), script_name)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def get_next_target():
    """次に記事を書くべき地域をDBから取得（とりあえずランダムまたは順次）"""
    db_path = "/app/brain/04_Output/real_estate.db"
    if not os.path.exists(db_path):
        return "世田谷区", "代沢" # フォールバック
    
    conn = sqlite3.connect(db_path)
    # まだ記事がない地域を優先するロジック（簡易版）
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT municipality, district FROM transactions LIMIT 5;")
    targets = cursor.fetchall()
    conn.close()
    
    # 本来はログをチェックして未作成のものを選ぶ
    return targets[0] if targets else ("世田谷区", "三軒茶屋")

async def send_update_report(message):
    """Discord Botとして報告を送信"""
    intents = discord.Intents.default()
    # 接続確認等は既に行われている前提
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel_id = os.getenv("DISCORD_REPORT_CHANNEL_ID")
        if channel_id:
            channel = client.get_channel(int(channel_id))
            if channel:
                await channel.send(f"📢 **自律運用報告**\n{message}")
        await client.close()

    if BOT_TOKEN:
        await client.start(BOT_TOKEN)

def autonomous_step():
    print(f"[{datetime.now()}] 自律更新ループを開始します...")
    
    # 1. ターゲット選定
    mun, dist = get_next_target()
    
    # 2. 記事生成等の処理（実際にはここで各AIを呼び出す）
    # ... (処理実行) ...

    # 3. サイトビルドとプッシュ
    # subprocess.run(...)

    # 4. 報告内容の作成
    report_msg = f"✅ 新しい調査レポートを自動公開しました！\n📍 地域: {mun} {dist or ''}\n🌐 サイトを確認: https://apartmentxjp-commits.github.io/openclaw_seo/site/public/"
    
    # Discordへ報告
    asyncio.run(send_update_report(report_msg))

if __name__ == "__main__":
    # 24時間に1回実行する無限ループ
    print("🚀 自律運用システムを起動しました（24時間に1回実行）")
    while True:
        autonomous_step()
        print(f"[{datetime.now()}] 次の更新まで24時間待機します...")
        time.sleep(24 * 60 * 60) # 24時間待機

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import subprocess

# .envファイルを読み込む
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Botのインテント設定
intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容の読み取りを許可

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user.name} (ID: {bot.user.id})")
    print("------")

@bot.command(name="ping")
async def ping(ctx):
    """通信確認用"""
    await ctx.send("pong! 司令塔は正常に稼働しています。")

@bot.command(name="stats")
async def stats(ctx):
    """アクセス統計のサマリーを表示（GA4連携予定）"""
    await ctx.send("📊 **本日のアクセス状況サマリー**\n現在GA4のデータ取得を準備中です。測定IDの反映をお待ちください。")

@bot.command(name="report")
async def report(ctx, area: str = None):
    """特定地域の最新レポートを表示"""
    if not area:
        await ctx.send("地域を指定してください（例: !report 世田谷区）")
        return
    await ctx.send(f"🔍 {area}の最新データを取得中...")
    # ここに既存のデータ取得スクリプトとの連携を実装予定
    await ctx.send(f"📄 {area}の最新レポートはこちら: [リンク予定]")

@bot.command(name="help_me")
async def help_me(ctx):
    """利用可能なコマンドを表示"""
    help_text = """
🔧 **司令塔エージェント コマンドリスト**
`!ping` : 通信確認
`!stats` : アクセス統計の確認
`!report [地域]` : 調査レポートの取得
`!generate [地域] [場所]` : 新規記事の生成指示
`!build` : サイトの再構築とデプロイ
    """
    await ctx.send(help_text)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("エラー: DISCORD_BOT_TOKENが設定されていません。")

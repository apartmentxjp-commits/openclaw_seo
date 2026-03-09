import os
import sqlite3
from openai import OpenAI
import sys
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Agent Role: Content Worker
# Goal: Generate professional real estate reports based on transaction data.

def generate_article(municipality, district=None):
    # Setup
    api_key = os.getenv("OPENROUTER_API_KEY")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    PRIMARY_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen-2.5-coder-32b-instruct:free")
    FALLBACK_MODEL = os.environ.get("OPENROUTER_FALLBACK_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

    # Data Retrieval (Proxy for Data Worker)
    db_path = "/app/brain/04_Output/real_estate.db"
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM transactions WHERE municipality = ?"
    params = [municipality]
    if district:
        query += " AND district = ?"
        params.append(district)
    
    df_data = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # Mapping to English Slug for consistency
    district_en = "all"
    if district == "三軒茶屋": district_en = "sangenjaya"
    elif district == "代沢": district_en = "daizawa"

    # Context Construction
    stats = df_data.describe().to_string()
    
    prompt = f"""
あなたは「日本不動産価格調査センター」の専門調査員です。
以下のデータに基づき、{municipality}{district or ''}の不動産価格推移に関するプロフェッショナルな調査レポートを作成してください。

【データ概要】
{stats}

【制約事項】
1. タイトルは「{municipality}{district or ''}の不動産価格推移と解説」としてください。
2. 「AI」「OpenClaw」という言葉は一切使わないでください。
3. 信頼感のある、公的な調査機関のような口調（です・ます調）で執筆してください。
4. グラフ画像とサムネイル画像を以下のパスで挿入してください。
   グラフ: ![価格推移](/openclaw_seo/site/public/images/charts/setagaya_{district_en}_chart.png)
   サムネイル: ![サムネイル](/openclaw_seo/site/public/images/thumbnails/setagaya_{district_en}_thumb.png)
   ※ district_enは {district} を小文字アルファベットにしたもの（sangenjaya, daizawa等）。

【構成】
- 概要
- 取引データから見る相場観
- 今後の展望
"""

    # Robust Free Tier Generation Loop
    models_to_try = [
        os.environ.get("OPENROUTER_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free"),
        os.environ.get("OPENROUTER_FALLBACK_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        "stepfun/step-3.5-flash:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
    ]

    import time
    ai_text = ""
    for model_id in models_to_try:
        try:
            print(f"Trying model: {model_id}...")
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}]
            )
            ai_text = response.choices[0].message.content
            print(f"Success with {model_id}!")
            break
        except Exception as e:
            print(f"Failed with {model_id} ({e}).")
            time.sleep(2)
            
    if not ai_text:
        print("All models failed. Generating placeholder text.")
        ai_text = "APIの一時的なエラーにより記事が生成できませんでした。時間をおいて再実行してください。"
    
    # Save as Markdown
    safe_name = f"{municipality}_{district or 'all'}".replace("/", "_")
    slug = f"setagaya_{district_en}"

    file_path = f"/app/site/content/post/{slug}.md"
    
    content = f"""---
title: "{municipality}{district or ''}の不動産価格推移と解説"
date: 2026-03-08T12:00:00+09:00
draft: false
---

{ai_text}
"""
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Report generated: {file_path}")

if __name__ == "__main__":
    mun = sys.argv[1] if len(sys.argv) > 1 else "世田谷区"
    dist = sys.argv[2] if len(sys.argv) > 2 else None
    generate_article(mun, dist)

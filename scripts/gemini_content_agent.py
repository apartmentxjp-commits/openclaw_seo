import os
import sqlite3
import google.generativeai as genai
import sys

# Agent Role: Content Worker (Gemini)
# Goal: Generate professional real estate reports based on transaction data.

def generate_article(municipality, district=None):
    # Setup
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("API Key missing.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')

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

    response = model.generate_content(prompt)
    
    # Save as Markdown
    safe_name = f"{municipality}_{district or 'all'}".replace("/", "_")
    # Mapping to English Slug for consistency
    slug = "setagaya_all"
    if district == "三軒茶屋": slug = "setagaya_sangenjaya"
    elif district == "代沢": slug = "setagaya_daizawa"

    file_path = f"/app/site/content/post/{slug}.md"
    
    content = f"""---
title: "{municipality}{district or ''}の不動産価格推移と解説"
date: 2026-03-08T12:00:00+09:00
draft: false
---

{response.text}
"""
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Report generated: {file_path}")

if __name__ == "__main__":
    import pandas as pd
    mun = sys.argv[1] if len(sys.argv) > 1 else "世田谷区"
    dist = sys.argv[2] if len(sys.argv) > 2 else None
    generate_article(mun, dist)

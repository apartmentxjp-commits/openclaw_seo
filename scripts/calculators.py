import os
import json

CONTENT_DIR = "/app/brain/04_Output/Note"

def create_tool_pages():
    os.makedirs(CONTENT_DIR, exist_ok=True)
    
    tools = {
        "yield-calculator.md": {
            "title": "利回り計算ツール",
            "content": "## 不動産投資 利回り計算\n\n物件価格と予定家賃から、表面利回りを即座にシミュレーションします。"
        },
        "loan-calculator.md": {
            "title": "住宅ローン計算ツール",
            "content": "## 住宅ローン 支払シミュレーション\n\n借入金額、金利、返済期間から月々の返済額を算出します。"
        },
        "rent-estimator.md": {
            "title": "家賃相場シミュレーター",
            "content": "## 近隣家賃相場 推定\n\nエリアデータに基づき、想定される家賃レンジを表示します。"
        },
        "price-prediction.md": {
            "title": "AI価格予測ツール",
            "content": "## 将来価格予測\n\n過去の推移データから、5年後の推定価格をAIが予測します。"
        }
    }

    for filename, data in tools.items():
        md = f"""---
title: "{data['title']}"
date: 2026-03-07T00:00:00+09:00
draft: false
layout: "tool"
---

{data['content']}
"""
        with open(os.path.join(CONTENT_DIR, filename), "w", encoding="utf-8") as f:
            f.write(md)
    
    print(f"✅ {len(tools)} tool pages created/updated.")

if __name__ == "__main__":
    create_tool_pages()

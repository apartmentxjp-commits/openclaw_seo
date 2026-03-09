import os
import json
from openai import OpenAI

# Configuration
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)
PRIMARY_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen-2.5-coder-32b-instruct:free")
FALLBACK_MODEL = os.environ.get("OPENROUTER_FALLBACK_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

def optimize_content(article_path, performance_data_path):
    if not os.path.exists(article_path):
        print(f"Error: Article not found {article_path}")
        return

    with open(article_path, "r", encoding="utf-8") as f:
        content = f.read()

    performance = {}
    if os.path.exists(performance_data_path):
        with open(performance_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Find performance for this specifically if possible, or use general data
            performance = data

    prompt = f"""
以下の不動産解説記事を、提供されたパフォーマンスデータに基づいて最適化（改善）してください。

記事内容:
{content}

パフォーマンスデータ:
{json.dumps(performance, indent=2, ensure_ascii=False)}

改善方針:
1. **CTR（クリック率）が低い場合**: タイトルやリード文をより引きの強いものに変更してください。
2. **セッション数が少ない場合**: AI検索（LLMO）を意識したキーワードの追加や、情報の網羅性を高めてください。
3. **読了率向上のため**: 内容が難しい箇所を平易にしたり、構成を整理して読みやすくしてください。

出力はMarkdown形式の「記事全体」を返してください。フロントマターは維持してください。
"""

    try:
        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        optimized_content = response.choices[0].message.content
    except Exception as e:
        print(f"Primary model failed ({e}), trying fallback...")
        response = client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        optimized_content = response.choices[0].message.content

    # Overwrite the article with the optimized version
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(optimized_content)
    
    print(f"✅ Article improved based on performance: {article_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 content_optimizer.py <article_path> [performance_data_path]")
    else:
        article = sys.argv[1]
        perf = sys.argv[2] if len(sys.argv) > 2 else "/app/brain/04_Output/analytics_dummy.json"
        optimize_content(article, perf)

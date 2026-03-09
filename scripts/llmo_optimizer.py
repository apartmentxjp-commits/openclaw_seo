import os
import json
from openai import OpenAI
from datetime import datetime

# Configuration
CONFIG_PATH = "/app/config/usage_stats.json"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)
PRIMARY_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen-2.5-coder-32b-instruct:free")
FALLBACK_MODEL = os.environ.get("OPENROUTER_FALLBACK_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

def update_usage(chars):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            stats = json.load(f)
    else:
        stats = {"api_calls": {"total": 0}, "character_counts": {"total": 0}}
        
    stats["api_calls"]["total"] += 1
    stats["character_counts"]["total"] += chars
    with open(CONFIG_PATH, "w") as f:
        json.dump(stats, f, indent=2)

def optimize_article(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    prompt = f"""
以下の不動産解説記事を、AI検索エンジン（Perplexity, ChatGPT, Google AI Overviews等）に引用されやすいよう「LLM最適化（LLMO/GEO）」してください。

記事内容:
{original_content}

以下の要素を追加・調整してください：
1. **要約 (Summary)**: 冒頭に3行程度の簡潔な要約を追加。
2. **FAQ**: 読者が抱きそうな疑問と回答を3つ作成。
3. **データ表**: 取引事例や価格情報を比較しやすいテーブル形式（Markdown）で整理。
4. **見出しの最適化**: 具体的で検索意図に沿った見出し（H2, H3）に調整。

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
    
    update_usage(len(original_content) + len(optimized_content))

    # Overwrite or save as new? Let's overwrite for optimization.
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(optimized_content)
    
    print(f"✅ Article optimized for LLMs: {file_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 llmo_optimizer.py <file_path>")
    else:
        optimize_article(sys.argv[1])

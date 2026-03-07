import os
import json
import google.generativeai as genai
from datetime import datetime

# Configuration
CONFIG_PATH = "/app/config/usage_stats.json"
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-flash-latest')

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

    response = model.generate_content(prompt)
    optimized_content = response.text
    
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

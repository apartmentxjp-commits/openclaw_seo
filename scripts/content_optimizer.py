import os
import json
import google.generativeai as genai

# Configuration
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-flash-latest')

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

    response = model.generate_content(prompt)
    optimized_content = response.text

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

import json
import os
from openai import OpenAI

# Configuration
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)
PRIMARY_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen-2.5-coder-32b-instruct:free")
FALLBACK_MODEL = os.environ.get("OPENROUTER_FALLBACK_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

def discover_topics(traffic_data_path):
    if not os.path.exists(traffic_data_path):
        # Fallback to a default set of popular areas if no data provided
        current_topics = ["世田谷区", "三軒茶屋", "代沢"]
    else:
        with open(traffic_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            current_topics = [p.get("url", "").split("/")[-1] for p in data.get("pages", []) if p.get("url")]

    prompt = f"""
不動産価格情報サイトの運用を支援してください。
現在は以下のトピック（地域）の記事が人気です: {', '.join(current_topics)}

これらのトピックに関連性が高く、かつユーザーが次に興味を持ちそうな「新しい住宅地やエリア」を5つ提案してください。
提案は以下のJSON形式で出力してください：
{{
  "new_topics": [
    {{ "area": "市区町村名", "district": "町名", "reason": "提案理由" }}
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.choices[0].message.content
    except Exception as e:
        print(f"Primary model failed ({e}), trying fallback...")
        try:
            response = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.choices[0].message.content
        except Exception:
            text = ""

    try:
        # Simple extraction of JSON from response
        start = text.find('{')
        end = text.rfind('}') + 1
        result = json.loads(text[start:end])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        print(text)

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "/app/brain/04_Output/analytics_dummy.json"
    discover_topics(path)

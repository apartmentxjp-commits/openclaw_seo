import os
import sqlite3
import json
from openai import OpenAI
from datetime import datetime

# Configuration
LOG_DB = "/app/brain/04_Output/improvement_log.db"
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)
PRIMARY_MODEL = os.environ.get("OPENROUTER_MODEL", "qwen/qwen-2.5-coder-32b-instruct:free")
FALLBACK_MODEL = os.environ.get("OPENROUTER_FALLBACK_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

def init_log_db():
    conn = sqlite3.connect(LOG_DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS improvements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_path TEXT,
            issue_type TEXT,
            proposed_change TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            performance_before REAL,
            performance_after REAL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def propose_improvement(page_content, metrics):
    prompt = f"""
あなたはSEOとLPOのプロフェッショナルです。以下のページのパフォーマンスデータと内容を基に、改善提案を1つ作成してください。

【現在のパフォーマンス】:
{json.dumps(metrics, indent=2)}

【ページ内容】:
{page_content[:2000]}

【出力フォーマット（JSONのみ）】:
{{
  "issue": "特定された問題点",
  "proposal": "具体的な改善内容（タイトル変更、コンテンツ追加等）",
  "target_section": "改善対象のセクション名",
  "new_content": "更新後のテキスト"
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
        # Simple extraction for JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except:
        return None

def apply_improvement(file_path, proposal):
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # In a real scenario, this would involve smart replacement or appending
    # For now, let's append the "Improvement" section as a demonstration
    improvement_note = f"\n\n## AIによる自律改善 ({datetime.now().strftime('%Y-%m-%d')})\n\n{proposal['proposal']}\n\n{proposal['new_content']}\n"
    
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(improvement_note)
    
    return True

if __name__ == "__main__":
    init_log_db()
    # Example logic for the loop
    print("Improvement engine initialized.")

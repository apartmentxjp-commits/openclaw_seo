"""
英語説明一括補完スクリプト

description_en が null の物件に対して Groq で英語翻訳を生成し、DBを更新する。
エージェント情報（【取扱店舗名】など）は翻訳前に除去する。

使い方:
    python backend/scripts/translate_descriptions.py
    python backend/scripts/translate_descriptions.py --limit 20   # 件数制限
    python backend/scripts/translate_descriptions.py --dry-run    # 確認のみ
"""

import os
import re
import sys
import json
import argparse
import time

# ─────────────────────────────────────────────────────────────────────────────
# エージェント情報の除去
# ─────────────────────────────────────────────────────────────────────────────
_AGENT_PATTERN = re.compile(
    r'【(?:取扱店舗名|取扱店舗住所|取扱店舗ＴＥＬ|取扱店舗TEL|仲介業者|問合せ)】[^【]*',
    re.UNICODE
)

def _clean_description(text: str) -> str:
    if not text:
        return ""
    text = _AGENT_PATTERN.sub("", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Groq による翻訳
# ─────────────────────────────────────────────────────────────────────────────
TRANSLATE_PROMPT = """Translate this Japanese real estate listing to natural English for international buyers.
- Keep Japanese cultural terms (kominka, machiya, satoyama, noka, minka) in parentheses when used
- Do NOT include any real estate agency names, phone numbers, or agent contact info
- Write a clean, buyer-friendly description
- If description is empty, write a short description based on the title only

Title: {title}
Description: {description}

Respond with JSON only: {{"title_en": "...", "description_en": "..."}}"""


def _translate_with_groq(title: str, description: str) -> tuple[str, str]:
    from groq import Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    cleaned_desc = _clean_description(description)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=512,
        messages=[{"role": "user", "content": TRANSLATE_PROMPT.format(
            title=title[:300],
            description=cleaned_desc[:600],
        )}],
        response_format={"type": "json_object"},
    )

    text = response.choices[0].message.content.strip()
    result = json.loads(text)
    return result.get("title_en", title), result.get("description_en", "")


# ─────────────────────────────────────────────────────────────────────────────
# Supabase
# ─────────────────────────────────────────────────────────────────────────────
def _get_supabase():
    from supabase import create_client
    url = os.getenv("AKIYA_SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("AKIYA_SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Supabase 環境変数 (AKIYA_SUPABASE_URL, AKIYA_SUPABASE_SERVICE_ROLE_KEY) が未設定")
    return create_client(url, key)


# ─────────────────────────────────────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="英語説明一括補完")
    parser.add_argument("--limit", type=int, default=0, help="処理件数上限 (0=全件)")
    parser.add_argument("--dry-run", action="store_true", help="DBを更新せず確認のみ")
    args = parser.parse_args()

    if "GROQ_API_KEY" not in os.environ:
        print("❌ GROQ_API_KEY が未設定です", file=sys.stderr)
        sys.exit(1)

    supabase = _get_supabase()

    # description_en が null の物件を取得
    query = supabase.table("properties") \
        .select("id, title, description, title_en") \
        .is_("description_en", "null") \
        .order("created_at", desc=False)

    if args.limit > 0:
        query = query.limit(args.limit)

    rows = query.execute().data
    print(f"▶ 対象: {len(rows)} 件 (description_en が null)")

    if args.dry_run:
        for r in rows[:5]:
            print(f"  - [{r['id']}] {r['title'][:40]}")
        if len(rows) > 5:
            print(f"  ... 他 {len(rows) - 5} 件")
        print("(dry-run: DBは更新しません)")
        return

    ok = 0
    fail = 0
    for i, row in enumerate(rows):
        pid = row["id"]
        title = row.get("title") or ""
        description = row.get("description") or ""

        print(f"[{i+1}/{len(rows)}] {title[:50]}", end=" ... ", flush=True)
        try:
            title_en, desc_en = _translate_with_groq(title, description)

            update: dict = {"description_en": desc_en}
            # title_en も未設定なら一緒に更新
            if not row.get("title_en"):
                update["title_en"] = title_en

            supabase.table("properties").update(update).eq("id", pid).execute()
            print(f"✓ ({len(desc_en)} chars)")
            ok += 1
        except Exception as e:
            print(f"✗ {e}")
            fail += 1

        # レートリミット対策
        if i < len(rows) - 1:
            time.sleep(0.2)

    print(f"\n完了: {ok} 件更新, {fail} 件失敗")


if __name__ == "__main__":
    main()

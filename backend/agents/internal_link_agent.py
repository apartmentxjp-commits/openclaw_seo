"""
Internal Link Agent: 記事間の相互リンクを自動生成して SEO 内部リンク強化
  - 同一都道府県内の記事同士を関連付け
  - 同一エリア内の異なる物件タイプ記事をクロスリンク
  - ガイド/Q&A → エリア記事への誘導リンク
  - ランキング → 各エリア詳細記事へのリンク
  - 生成リンクは internal_links テーブル + 記事 Markdown 末尾セクションに追記
"""

import os
import re
import psycopg2
from datetime import datetime
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "")
BASE_URL = os.getenv("SITE_BASE_URL", "https://realestate.tacky-consulting.com")


def _get_pg_conn():
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")
    return psycopg2.connect(url)


# ─────────────────────────────────────────────
# 1. 記事間リンク候補の選定ロジック
# ─────────────────────────────────────────────

def find_link_candidates(conn, article_id: int, article_slug: str,
                          prefecture: str, area: str, article_type: str) -> list[dict]:
    """
    対象記事に関連するリンク先候補を取得する。
    Returns: [{"slug": str, "title": str, "type": str, "anchor": str}]
    """
    cur = conn.cursor()
    candidates = []

    # --- A. 同一エリア・異なる物件種別 ---
    cur.execute("""
        SELECT slug, title, article_type, property_type
        FROM articles
        WHERE prefecture = %s AND area = %s
          AND slug != %s AND status = 'published'
          AND published_at IS NOT NULL
        LIMIT 4
    """, (prefecture, area, article_slug))
    for row in cur.fetchall():
        candidates.append({
            "slug": row[0], "title": row[1],
            "type": "same_area", "article_type": row[2],
            "anchor": f"{row[3]}の価格相場"
        })

    # --- B. 同一都道府県・ランキング記事 ---
    if article_type == "area":
        cur.execute("""
            SELECT slug, title
            FROM articles
            WHERE prefecture = %s AND article_type = 'ranking'
              AND slug != %s AND published_at IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 2
        """, (prefecture, article_slug))
        for row in cur.fetchall():
            candidates.append({
                "slug": row[0], "title": row[1],
                "type": "prefecture_ranking", "article_type": "ranking",
                "anchor": f"{prefecture}の地価ランキング"
            })

    # --- C. 同一都道府県・ガイド/Q&A 記事 ---
    if article_type in ("area", "ranking"):
        cur.execute("""
            SELECT slug, title, article_type
            FROM articles
            WHERE prefecture = %s
              AND article_type IN ('guide', 'qa')
              AND slug != %s AND published_at IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 2
        """, (prefecture, article_slug))
        for row in cur.fetchall():
            label = "不動産ガイド" if row[2] == "guide" else "よくある質問"
            candidates.append({
                "slug": row[0], "title": row[1],
                "type": "guide_qa", "article_type": row[2],
                "anchor": label
            })

    # --- D. 全国ランキング記事 (prefecture=全国) ---
    if article_type == "area":
        cur.execute("""
            SELECT slug, title
            FROM articles
            WHERE prefecture = '全国' AND article_type = 'ranking'
              AND slug != %s AND published_at IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        """, (article_slug,))
        for row in cur.fetchall():
            candidates.append({
                "slug": row[0], "title": row[1],
                "type": "national_ranking", "article_type": "ranking",
                "anchor": "全国地価ランキング"
            })

    cur.close()

    # 重複除去（slug 単位）
    seen = set()
    deduped = []
    for c in candidates:
        if c["slug"] not in seen:
            seen.add(c["slug"])
            deduped.append(c)
    return deduped[:6]  # 最大6件


# ─────────────────────────────────────────────
# 2. internal_links テーブルへの保存
# ─────────────────────────────────────────────

def save_internal_links(conn, from_slug: str, candidates: list[dict]) -> int:
    """internal_links に保存。既存はスキップ（UPSERT）。保存件数を返す"""
    if not candidates:
        return 0
    cur = conn.cursor()
    saved = 0
    for c in candidates:
        try:
            cur.execute("""
                INSERT INTO internal_links (from_slug, to_slug, anchor_text, link_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (from_slug, to_slug) DO NOTHING
            """, (from_slug, c["slug"], c["anchor"], c["type"]))
            if cur.rowcount > 0:
                saved += 1
        except Exception as e:
            print(f"[InternalLink] 保存エラー: {e}", flush=True)
    conn.commit()
    cur.close()
    return saved


# ─────────────────────────────────────────────
# 3. Markdown ファイルへのリンクセクション追記
# ─────────────────────────────────────────────

CONTENT_DIR = os.getenv(
    "HUGO_CONTENT_DIR",
    "/app/site/content/post"  # コンテナ内パス（ローカルでは別途設定）
)

# ローカル実行時のパス解決
_LOCAL_CONTENT_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../../../site/content/post"
)


def _get_content_dir() -> str:
    if os.path.isdir(CONTENT_DIR):
        return CONTENT_DIR
    resolved = os.path.realpath(_LOCAL_CONTENT_DIR)
    if os.path.isdir(resolved):
        return resolved
    return CONTENT_DIR  # fallback


def inject_related_links_to_md(slug: str, candidates: list[dict]) -> bool:
    """
    Markdown ファイル末尾に「関連記事」セクションを挿入または更新する。
    Returns: 成功 True / 失敗 False
    """
    if not candidates:
        return False

    content_dir = _get_content_dir()
    md_path = os.path.join(content_dir, f"{slug}.md")
    if not os.path.isfile(md_path):
        return False

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 既存の関連記事セクションを削除（再生成）
    content = re.sub(
        r"\n\n## 関連記事\n\n.*",
        "",
        content,
        flags=re.DOTALL
    )

    # 新しいセクションを追記
    link_section = "\n\n## 関連記事\n\n"
    for c in candidates:
        url = f"{BASE_URL}/post/{c['slug']}/"
        link_section += f"- [{c['title']}]({url})\n"

    content = content.rstrip() + link_section

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


# ─────────────────────────────────────────────
# 4. メイン実行
# ─────────────────────────────────────────────

def run_internal_linking(limit: int = 30) -> dict:
    """
    内部リンクを生成・保存する。
    limit: 処理する記事数の上限
    Returns: {"processed": int, "links_added": int, "md_updated": int}
    """
    print(f"[InternalLink] Internal Link Agent 開始 (limit={limit})", flush=True)
    stats = {"processed": 0, "links_added": 0, "md_updated": 0}

    try:
        conn = _get_pg_conn()
    except Exception as e:
        print(f"[InternalLink] DB接続失敗: {e}", flush=True)
        return stats

    cur = conn.cursor()
    # 未処理または古い記事を優先（internal_links に少ない記事）
    cur.execute("""
        SELECT a.id, a.slug, a.prefecture, a.area, a.article_type
        FROM articles a
        WHERE a.status = 'published' AND a.published_at IS NOT NULL
        ORDER BY (
            SELECT COUNT(*) FROM internal_links il WHERE il.from_slug = a.slug
        ) ASC,
        a.created_at DESC
        LIMIT %s
    """, (limit,))
    articles = cur.fetchall()
    cur.close()

    for art in articles:
        art_id, slug, prefecture, area, article_type = art
        article_type = article_type or "area"

        try:
            candidates = find_link_candidates(conn, art_id, slug, prefecture, area, article_type)

            if not candidates:
                continue

            # DB に保存
            added = save_internal_links(conn, slug, candidates)
            stats["links_added"] += added

            # Markdown ファイルに追記
            if inject_related_links_to_md(slug, candidates):
                stats["md_updated"] += 1

            stats["processed"] += 1

        except Exception as e:
            print(f"[InternalLink] エラー (slug={slug}): {e}", flush=True)

    conn.close()
    print(
        f"[InternalLink] 完了: 処理{stats['processed']}件 / "
        f"リンク追加{stats['links_added']}件 / MD更新{stats['md_updated']}件",
        flush=True
    )
    return stats


if __name__ == "__main__":
    run_internal_linking(limit=50)

"""
Publisher: DB記事 → GitHub REST API → GitHub Pages

フロー:
  1. articles テーブルから status='published', published_at IS NULL の記事を取得
  2. GitHub Contents API で site/content/post/{slug}.md を直接作成/更新
  3. GitHub Actions が Hugo ビルドして GitHub Pages に公開
  ※ git バイナリ不使用（macOS Docker bind mount デッドロック回避）
"""

import os
import base64
import asyncio
import urllib.request
import urllib.error
import json
from datetime import datetime
from sqlalchemy import select

from database import AsyncSessionLocal
from models import Article

# ─── 設定 ────────────────────────────────────────────────
GH_TOKEN = os.getenv("GH_TOKEN", "")
GITHUB_REPO = "apartmentxjp-commits/openclaw_seo"
HUGO_POST_PATH = "site/content/post"
GIT_USER_NAME = os.getenv("GIT_USER_NAME", "OpenClaw Bot")
GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "bot@openclaw.local")


def _write_hugo_markdown(article: Article) -> tuple[str, str]:
    """記事オブジェクトをHugoのMarkdown文字列に変換し、(filename, content)を返す"""
    keywords = article.keywords or []
    kw_str = ", ".join(f'"{k}"' for k in keywords[:8]) if keywords else ""

    date_str = article.created_at.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    description = (article.meta_description or "").replace('"', "'")
    title_safe = article.title.replace('"', "'")

    lines = [
        "---",
        'title: "' + title_safe + '"',
        "date: " + date_str,
        'slug: "' + article.slug + '"',
        'area: "' + article.area + '"',
        'prefecture: "' + article.prefecture + '"',
        'property_type: "' + article.property_type + '"',
        'description: "' + description + '"',
        "keywords: [" + kw_str + "]",
        "draft: false",
        "---",
        "",
    ]
    front_matter = "\n".join(lines) + "\n"
    content = front_matter + (article.content or "")
    filename = f"{article.slug}.md"
    return filename, content


def _github_api_push_file(filename: str, content: str, commit_msg: str) -> bool:
    """GitHub Contents API でファイルを作成/更新する（git バイナリ不使用）"""
    if not GH_TOKEN:
        print("[Publisher] GH_TOKEN が未設定のため GitHub push をスキップします")
        return False

    api_path = f"{HUGO_POST_PATH}/{filename}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{api_path}"
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "OpenClaw-Publisher/1.0",
    }

    # 既存ファイルの SHA を取得（更新の場合に必要）
    sha = None
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"[Publisher] SHA取得エラー: {e}")
            return False

    # PUT でファイル作成または更新
    payload = {
        "message": commit_msg,
        "content": encoded,
        "branch": "main",
        "committer": {
            "name": GIT_USER_NAME,
            "email": GIT_USER_EMAIL,
        },
    }
    if sha:
        payload["sha"] = sha

    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="PUT")
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            action = "更新" if sha else "作成"
            print(f"[Publisher] GitHub API {action}成功: {api_path} (commit: {result['commit']['sha'][:7]})")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[Publisher] GitHub API push失敗 ({e.code}): {err_body[:300]}")
        return False
    except Exception as e:
        print(f"[Publisher] GitHub API push エラー: {e}")
        return False


async def publish_pending_articles() -> int:
    """
    DBの未公開記事をGitHub APIで直接pushする。
    公開済みにした記事数を返す。
    """
    async with AsyncSessionLocal() as db:
        q = await db.execute(
            select(Article)
            .where(Article.status == "published")
            .where(Article.published_at == None)  # noqa: E711
            .order_by(Article.created_at.asc())
        )
        articles = q.scalars().all()

        if not articles:
            print("[Publisher] 未公開記事なし")
            return 0

        published_count = 0
        for article in articles:
            try:
                filename, content = _write_hugo_markdown(article)
                now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                commit_msg = f"feat: add article [{now}] {article.title}"

                success = await asyncio.to_thread(
                    _github_api_push_file, filename, content, commit_msg
                )
                if success:
                    article.published_at = datetime.utcnow()
                    published_count += 1
                    print(f"[Publisher] 公開完了: {article.title}")
                else:
                    print(f"[Publisher] push失敗: {article.title}")
            except Exception as e:
                print(f"[Publisher] エラー (ID={article.id}): {e}")

        if published_count > 0:
            await db.commit()
            print(f"[Publisher] {published_count}件を公開済みにしました")

        return published_count

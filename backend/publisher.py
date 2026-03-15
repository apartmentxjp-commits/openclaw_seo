"""
Publisher: DB記事 → Hugo Markdown → git push → GitHub Pages

フロー:
  1. articles テーブルから status='published', published_at IS NULL の記事を取得
  2. Hugo形式の .md ファイルを site/content/post/ に書き出す
  3. git add / commit / push → GitHub Actions が Hugo ビルドして GitHub Pages に公開
"""

import os
import subprocess
import asyncio
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import Article

# ─── 設定 ────────────────────────────────────────────────
SITE_DIR = os.getenv("SITE_DIR", "/mainproject/site")
HUGO_CONTENT_DIR = os.path.join(SITE_DIR, "content", "post")
PROJECT_DIR = os.getenv("PROJECT_DIR", "/mainproject")
GH_TOKEN = os.getenv("GH_TOKEN", "")
GITHUB_REPO = "apartmentxjp-commits/openclaw_seo"
GIT_USER_NAME = os.getenv("GIT_USER_NAME", "OpenClaw Bot")
GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "bot@openclaw.local")


def _write_hugo_markdown(article: Article) -> str:
    """記事オブジェクトをHugoのMarkdownファイルとして書き出す"""
    os.makedirs(HUGO_CONTENT_DIR, exist_ok=True)

    keywords = article.keywords or []
    kw_str = ", ".join(f'"{k}"' for k in keywords[:8]) if keywords else ""

    date_str = article.created_at.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    description = (article.meta_description or "").replace('"', "'")
    title_safe = article.title.replace('"', "'")

    # f-string を使わず文字列結合（Python 3.11 f-string内バックスラッシュ制限を回避）
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
    filepath = os.path.join(HUGO_CONTENT_DIR, f"{article.slug}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter + (article.content or ""))

    return filepath


def _git_push(files: list[str], commit_msg: str) -> bool:
    """指定ファイルをgit add/commit/pushする"""
    if not GH_TOKEN:
        print("[Publisher] GH_TOKEN が未設定のため git push をスキップします")
        return False

    try:
        remote_url = f"https://{GH_TOKEN}@github.com/{GITHUB_REPO}.git"

        env = {**os.environ, "GIT_AUTHOR_NAME": GIT_USER_NAME, "GIT_AUTHOR_EMAIL": GIT_USER_EMAIL,
               "GIT_COMMITTER_NAME": GIT_USER_NAME, "GIT_COMMITTER_EMAIL": GIT_USER_EMAIL}

        def run(cmd, **kwargs):
            result = subprocess.run(
                cmd, cwd=PROJECT_DIR, capture_output=True, text=True, env=env, **kwargs
            )
            if result.returncode != 0:
                raise RuntimeError(f"{' '.join(cmd)}: {result.stderr.strip()}")
            return result.stdout.strip()

        # 認証付きリモートを一時設定
        run(["git", "remote", "set-url", "origin", remote_url])

        # ファイルをステージ
        for f in files:
            run(["git", "add", f])

        # コミット（差分がなければスキップ）
        status = run(["git", "status", "--porcelain"])
        if not status:
            print("[Publisher] 差分なし、push をスキップ")
            return True

        run(["git", "commit", "-m", commit_msg])
        run(["git", "push", "origin", "main"])
        print(f"[Publisher] git push 完了: {commit_msg}")
        return True

    except Exception as e:
        print(f"[Publisher] git push 失敗: {e}")
        return False
    finally:
        # リモートURLを元に戻す（トークンを残さない）
        try:
            subprocess.run(
                ["git", "remote", "set-url", "origin",
                 f"https://github.com/{GITHUB_REPO}.git"],
                cwd=PROJECT_DIR, capture_output=True
            )
        except Exception:
            pass


async def publish_pending_articles() -> int:
    """
    DBの未公開記事をHugoに書き出してgit pushする。
    公開済みにした記事数を返す。
    """
    async with AsyncSessionLocal() as db:
        # published_at IS NULL の記事を取得（新規生成分）
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

        written_files = []
        titles = []

        for article in articles:
            try:
                filepath = _write_hugo_markdown(article)
                written_files.append(filepath)
                titles.append(article.title)
                print(f"[Publisher] Markdown書き出し: {filepath}")
            except Exception as e:
                print(f"[Publisher] 書き出し失敗 (ID={article.id}): {e}")

        if not written_files:
            return 0

        # git push
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        count = len(written_files)
        msg = f"feat: add {count} article(s) [{now}]\n\n" + "\n".join(f"- {t}" for t in titles)
        pushed = _git_push(written_files, msg)

        if pushed:
            # published_at を更新
            for article in articles:
                article.published_at = datetime.utcnow()
            await db.commit()
            print(f"[Publisher] {count}件を公開済みにしました")

        return count if pushed else 0

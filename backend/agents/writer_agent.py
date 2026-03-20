"""
Writer Agent - Groq (Llama 3.3 70b) による不動産記事自動執筆エージェント
Phase 1 拡張:
  - 記事タイプ対応: area / guide / qa / ranking
  - 文字数強化: 2000〜3000文字
  - 内部リンク自動挿入（シミュレーターへの誘導）
  - リスク対策: Groq エラー時の graceful fallback
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Optional
from groq import Groq
from slugify import slugify
from agents.thoughts import emit_thought

# 地価公示データ取得（PostgreSQL経由）
import psycopg2

# ─────────────────────────────────────────────────────────────────────────────
# 内部リンク自動挿入ルール（SEOリスク対策: シミュレーター誘導）
# ─────────────────────────────────────────────────────────────────────────────
TOOL_LINK_RULES = {
    "ローン":       ("住宅ローン返済シミュレーター", "https://realestate.tacky-consulting.com/post/loan-calculator/"),
    "金利":         ("住宅ローン返済シミュレーター", "https://realestate.tacky-consulting.com/post/loan-calculator/"),
    "返済":         ("住宅ローン返済シミュレーター", "https://realestate.tacky-consulting.com/post/loan-calculator/"),
    "借入":         ("住宅ローン返済シミュレーター", "https://realestate.tacky-consulting.com/post/loan-calculator/"),
    "家賃":         ("家賃相場シミュレーター",       "https://realestate.tacky-consulting.com/post/rent-estimator/"),
    "賃料":         ("家賃相場シミュレーター",       "https://realestate.tacky-consulting.com/post/rent-estimator/"),
    "家賃相場":     ("家賃相場シミュレーター",       "https://realestate.tacky-consulting.com/post/rent-estimator/"),
    "利回り":       ("不動産投資 利回り計算ツール",   "https://realestate.tacky-consulting.com/post/yield-calculator/"),
    "投資収益":     ("不動産投資 利回り計算ツール",   "https://realestate.tacky-consulting.com/post/yield-calculator/"),
    "表面利回り":   ("不動産投資 利回り計算ツール",   "https://realestate.tacky-consulting.com/post/yield-calculator/"),
    "価格予測":     ("AI価格予測シミュレーター",     "https://realestate.tacky-consulting.com/post/price-prediction/"),
    "将来価格":     ("AI価格予測シミュレーター",     "https://realestate.tacky-consulting.com/post/price-prediction/"),
}

def inject_tool_links(content: str, article_type: str) -> str:
    """
    記事本文にシミュレーターへの内部リンクを挿入する。
    リスク対策:
      - 既にリンクがある場合はスキップ
      - 末尾の「関連ツール」セクションとして追加（本文改変を最小化）
    """
    injected_tools = {}
    for keyword, (label, url) in TOOL_LINK_RULES.items():
        if keyword in content and url not in content:
            injected_tools[label] = url

    if not injected_tools:
        return content

    tool_section = "\n\n## 関連シミュレーターで試してみよう\n\n"
    for label, url in injected_tools.items():
        tool_section += f"- [{label}]({url})\n"

    # まとめセクションの直前に挿入、なければ末尾に追加
    if "## まとめ" in content:
        content = content.replace("## まとめ", tool_section + "## まとめ", 1)
    elif "## 結論" in content:
        content = content.replace("## 結論", tool_section + "## 結論", 1)
    else:
        content = content + tool_section

    return content


def get_land_price_context(prefecture: str, area: str) -> str:
    """地価公示データをDBから取得してエリアの価格情報文字列を返す"""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        return ""
    try:
        url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        city_prefix = area[:4]
        cur.execute("""
            SELECT land_use, avg_price_per_sqm, max_price_per_sqm,
                   min_price_per_sqm, sample_count, avg_change_rate, sample_features
            FROM land_prices
            WHERE prefecture = %s AND city LIKE %s
            ORDER BY sample_count DESC
            LIMIT 6
        """, (prefecture, f"{city_prefix}%"))
        rows = cur.fetchall()
        if not rows and len(area) > 3:
            cur.execute("""
                SELECT land_use, avg_price_per_sqm, max_price_per_sqm,
                       min_price_per_sqm, sample_count, avg_change_rate, sample_features
                FROM land_prices
                WHERE prefecture = %s AND city LIKE %s
                ORDER BY sample_count DESC
                LIMIT 6
            """, (prefecture, f"{area[:3]}%"))
            rows = cur.fetchall()
        cur.close()
        conn.close()
        if not rows:
            return ""
        lines = ["【国土交通省 地価公示データ（2024年）】"]
        for land_use, avg_p, max_p, min_p, cnt, rate, samples in rows:
            rate_str = f"前年比 {rate:+.1f}%" if rate else ""
            lines.append(f"・{land_use}: 平均 {avg_p:,}円/㎡ {rate_str}（調査地点 {cnt}件）")
            if samples:
                s_list = samples if isinstance(samples, list) else json.loads(samples)
                for s in s_list[:2]:
                    if s.get("env"):
                        lines.append(f"  └ 地域特性: {s['env']}")
                    if s.get("station") and s.get("dist_m"):
                        try:
                            walk = int(s["dist_m"]) // 80
                            lines.append(f"  └ 最寄り駅: {s['station']}（徒歩約{walk}分）")
                        except Exception:
                            pass
        return "\n".join(lines)
    except Exception:
        return ""


def get_ranking_context(prefecture: str) -> str:
    """都道府県内の地価ランキングデータをDBから取得"""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        return ""
    try:
        url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("""
            SELECT city, land_use, avg_price_per_sqm, avg_change_rate, sample_count
            FROM land_prices
            WHERE prefecture = %s AND land_use = '住宅'
            ORDER BY avg_price_per_sqm DESC
            LIMIT 15
        """, (prefecture,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if not rows:
            return ""
        lines = [f"【{prefecture} 住宅地価ランキング（国土交通省 地価公示2024年）】"]
        for i, (city, lu, avg_p, rate, cnt) in enumerate(rows, 1):
            rate_str = f"前年比{rate:+.1f}%" if rate else ""
            lines.append(f"{i}位. {city}: {avg_p:,}円/㎡ {rate_str}")
        return "\n".join(lines)
    except Exception:
        return ""


def get_knowledge_base_context(prefecture: str, article_type: str) -> str:
    """
    knowledge_base テーブルから記事に有用な追加コンテキストを取得。
    - 日銀政策金利（全国共通）
    - 都道府県別人口
    - 都道府県別住宅地価サマリー（land_prices と重複しない概要）
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        return ""
    try:
        url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        lines = []

        # 1. 日銀政策金利（全記事タイプで注入 - ローン関連に重要）
        cur.execute("""
            SELECT summary, data FROM knowledge_base
            WHERE category='financial' AND subcategory='interest_rate' AND scope='national'
              AND is_active=1
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            try:
                d = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                lines.append(f"【金融情報】日銀政策金利: {d.get('rate', '?')}%（{d.get('period', '?')}時点）")
            except Exception:
                lines.append(f"【金融情報】{row[0]}")

        # 2. 都道府県人口（エリア・ランキング記事で有用）
        if article_type in ("area", "ranking") and prefecture and prefecture != "全国":
            cur.execute("""
                SELECT summary, data FROM knowledge_base
                WHERE category='demographics' AND subcategory='population'
                  AND scope='prefecture' AND prefecture=%s AND is_active=1
                LIMIT 1
            """, (prefecture,))
            row = cur.fetchone()
            if row:
                try:
                    d = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                    pop = d.get("population_man", "?")
                    lines.append(f"【人口データ】{prefecture}の推計人口: 約{pop}万人")
                except Exception:
                    lines.append(f"【人口データ】{row[0]}")

        # 3. 都道府県地価サマリー（ランキング記事以外でも補完情報として）
        if prefecture and prefecture != "全国":
            cur.execute("""
                SELECT summary, data FROM knowledge_base
                WHERE category='real_estate' AND subcategory='land_price'
                  AND scope='prefecture' AND prefecture=%s AND is_active=1
                LIMIT 1
            """, (prefecture,))
            row = cur.fetchone()
            if row:
                try:
                    d = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                    avg = d.get("avg", 0)
                    cnt = d.get("count", 0)
                    if avg and cnt:
                        lines.append(
                            f"【地価概要】{prefecture}住宅地平均: {avg:,.0f}円/㎡"
                            f"（{cnt}地点調査, 国土交通省2024年）"
                        )
                except Exception:
                    lines.append(f"【地価概要】{row[0]}")

        cur.close()
        conn.close()
        return "\n".join(lines)
    except Exception:
        return ""


MODEL = "llama-3.3-70b-versatile"

# ─────────────────────────────────────────────────────────────────────────────
# 記事タイプ別システムプロンプト
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "area": """
あなたは不動産業界の専門ライターです。
SEO・AIO（AI Overview）対策に優れた、日本の不動産価格情報記事を執筆します。

執筆ルール:
1. 見出し構造 (H2, H3) を明確に使用する
2. 具体的な数値・データを必ず含める（国土交通省データがあれば必ず引用）
3. 読者の疑問に直接答えるQ&A形式を含める（最低3問）
4. 地域の特性・生活環境・交通アクセスも記述する
5. 物件購入・賃貸の判断基準となる情報を含める
6. 必ず「まとめ」セクションを末尾に入れる
7. 文体: 丁寧語、専門的かつ読みやすく
8. 文字数: 2000〜3000文字（重要: 必ず2000文字以上書くこと）
9. Markdown形式で出力

AIO対策:
- 冒頭の100文字以内に記事の核心情報（価格帯・特徴）を入れる
- 箇条書きで要点をまとめるセクションを含める
- FAQセクションを必ず含める（3〜5問）
- データテーブルを1つ以上含める
""",

    "guide": """
あなたは不動産業界の専門ライターです。
読者が不動産に関する意思決定をできるよう、教育的で実用的なガイド記事を執筆します。

執筆ルール:
1. 初心者でも理解できる丁寧な説明
2. ステップ形式（手順1→2→3）で流れを示す
3. 具体的な数値例・シミュレーション例を含める
4. よくある失敗・注意点のセクションを含める
5. チェックリスト形式のまとめを末尾に入れる
6. 文体: 丁寧語、分かりやすく
7. 文字数: 2000〜3000文字（重要: 必ず2000文字以上書くこと）
8. Markdown形式で出力

AIO対策:
- 冒頭に「この記事でわかること」を箇条書きで提示
- FAQ（よくある質問）セクションを3〜5問含める
- 定義・用語解説ボックスを適宜挿入
""",

    "qa": """
あなたは不動産業界の専門家です。
読者の具体的な疑問・質問に直接答えるQ&A記事を執筆します。

執筆ルール:
1. 記事全体をQ&A形式で構成（5〜8問）
2. 各回答は具体的な数値・事例を含める
3. 「結論から言うと〜」で各回答を始める
4. 専門用語は必ず括弧内で解説する
5. 最後に「関連する質問」セクションを追加
6. 文体: 丁寧語、直接的で明快に
7. 文字数: 2000〜3000文字（重要: 必ず2000文字以上書くこと）
8. Markdown形式で出力

AIO対策:
- 各質問をH2見出しにする（AIが抽出しやすい形式）
- 回答の最初の1文に核心情報を入れる
- 箇条書きを積極的に活用する
""",

    "ranking": """
あなたは不動産データアナリスト兼ライターです。
実データに基づいたランキング・比較記事を執筆します。

執筆ルール:
1. ランキング表（Markdownテーブル）を必ず含める
2. 各順位の解説・特徴を記述する
3. 「なぜこのエリアが高い/低いか」の分析を加える
4. 投資・居住判断のための示唆を含める
5. データの出典を明記する（国土交通省 地価公示等）
6. 「まとめ」と「投資・居住の観点からの推薦」を末尾に入れる
7. 文体: データドリブン、客観的かつ読みやすく
8. 文字数: 2000〜3000文字（重要: 必ず2000文字以上書くこと）
9. Markdown形式で出力

AIO対策:
- ランキング表は必ず含める（AI引用されやすい）
- 冒頭にランキングの結論サマリーを箇条書きで提示
- FAQセクションを3問以上含める
""",
}

SEO_SYSTEM_PROMPT = """
あなたはSEO専門家です。
与えられた記事からSEOメタデータを生成します。
必ずJSON形式のみで回答してください。前置きや説明は不要です。

出力形式:
{
  "meta_title": "60文字以内のタイトル",
  "meta_description": "120〜160文字の説明文",
  "keywords": ["キーワード1", "キーワード2", ...],
  "og_title": "OGPタイトル",
  "structured_data": {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "記事タイトル",
    "description": "説明",
    "keywords": "キーワード"
  }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# 記事タイプ別プロンプトビルダー
# ─────────────────────────────────────────────────────────────────────────────

def build_prompt(article_type: str, topic: dict, extra_context: str = "") -> str:
    """記事タイプに応じたプロンプトを生成"""

    pref  = topic.get("prefecture", "")
    area  = topic.get("area", "")
    ptype = topic.get("property_type", "")
    hint  = topic.get("title_hint", "")

    if article_type == "area":
        return f"""
以下の条件で不動産価格情報記事を執筆してください。

対象エリア: {pref} {area}
物件種別: {property_type_label(ptype)}
タイトルヒント: {hint or f'{area}の{ptype}価格相場・最新動向'}

追加情報・実データ:
{extra_context or '一般的な相場観を基に執筆'}

【重要】
- 「追加情報・実データ」に国土交通省データが含まれている場合は、その具体的な数値（円/㎡、前年比）を必ず引用してください
- データ出典を「国土交通省 地価公示（2024年）」として明記してください
- 数値は万円/㎡単位・坪単価に換算して記述してください
- 2000文字以上、できれば2500文字を目指してください

記事タイトルも含めて、Markdown形式で出力してください。
"""

    elif article_type == "guide":
        return f"""
以下のテーマで不動産ガイド記事を執筆してください。

テーマ: {hint or f'{ptype}購入・活用の完全ガイド'}
対象読者: {pref}で{ptype}購入・賃貸を検討している方
地域: {pref} {area}（地域固有情報があれば活用）

追加情報:
{extra_context or '一般的な不動産知識を基に執筆'}

【重要】
- 2000文字以上、できれば2500文字を目指してください
- ステップ形式で手順を説明してください
- 具体的な数値例（価格・金利・諸費用率など）を含めてください
- チェックリスト形式のまとめを末尾に入れてください

記事タイトルも含めて、Markdown形式で出力してください。
"""

    elif article_type == "qa":
        return f"""
以下のテーマで不動産Q&A記事を執筆してください。

テーマ: {hint or f'{pref}の不動産購入に関するQ&A'}
対象: {pref} {area}の{ptype}

追加情報:
{extra_context or '一般的な不動産知識を基に執筆'}

【重要】
- Q&A形式で5〜8問を設定し、それぞれ詳しく回答してください
- 2000文字以上、できれば2500文字を目指してください
- 各回答は具体的な数値や事例を含めてください
- よくある誤解や落とし穴についての質問も含めてください

記事タイトルも含めて、Markdown形式で出力してください。
"""

    elif article_type == "ranking":
        return f"""
以下のテーマでランキング・比較記事を執筆してください。

テーマ: {hint or f'{pref} エリア別地価・不動産価格ランキング'}
対象: {pref}内のエリア比較

ランキングデータ（国土交通省 地価公示2024年）:
{extra_context or 'データなし（一般的な相場観で執筆）'}

【重要】
- Markdownテーブルでランキング表を作成してください
- 各エリアの特徴・価格上昇/下落の理由を分析してください
- 2000文字以上、できれば2500文字を目指してください
- 投資・居住両方の観点から推薦エリアを提示してください
- データ出典を「国土交通省 地価公示（2024年）」として明記してください

記事タイトルも含めて、Markdown形式で出力してください。
"""

    return ""


def property_type_label(ptype: str) -> str:
    labels = {
        "マンション": "マンション（分譲・賃貸）",
        "一戸建て": "一戸建て（新築・中古）",
        "土地": "土地（宅地）",
        "投資": "投資用不動産",
    }
    return labels.get(ptype, ptype)


# ─────────────────────────────────────────────────────────────────────────────
# Writer Agent
# ─────────────────────────────────────────────────────────────────────────────

class WriterAgent:
    """Groq (Llama 3.3 70b) 記事執筆エージェント"""

    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

    async def generate_article(
        self,
        area: str,
        prefecture: str,
        property_type: str,
        article_type: str = "area",
        title_hint: str = "",
        price_avg: Optional[int] = None,
        unit_price: Optional[int] = None,
        extra_context: str = "",
        **kwargs,
    ) -> dict:
        """指定タイプの不動産記事を生成（リスク対策: 最大2回リトライ）"""

        # コンテキスト収集: 地価公示データ
        if article_type == "ranking":
            land_data = get_ranking_context(prefecture)
        else:
            land_data = get_land_price_context(prefecture, area)

        if land_data:
            extra_context = (land_data + "\n\n" + extra_context).strip()

        # Phase 4: knowledge_base からの追加コンテキスト（日銀金利・人口・地価概要）
        kb_context = get_knowledge_base_context(prefecture, article_type)
        if kb_context:
            extra_context = (extra_context + "\n\n" + kb_context).strip()

        topic = {
            "prefecture": prefecture,
            "area": area,
            "property_type": property_type,
            "title_hint": title_hint,
        }
        prompt = build_prompt(article_type, topic, extra_context)
        system_prompt = SYSTEM_PROMPTS.get(article_type, SYSTEM_PROMPTS["area"])

        await emit_thought("writer",
                           f"タスク受信: {prefecture} {area} [{article_type}]",
                           "thinking",
                           detail=f"モデル: {MODEL}")
        await asyncio.sleep(0.3)

        # ── Groq API呼び出し（リスク対策: 最大2リトライ）─────────────────
        content = None
        duration_ms = 0
        last_error = None
        for attempt in range(2):
            start = time.time()
            try:
                await emit_thought("writer",
                                   f"Groq に接続中... 執筆開始（試行{attempt+1}）",
                                   "working",
                                   detail=f"{area} {article_type}記事を生成")
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=4096,
                )
                content = response.choices[0].message.content
                duration_ms = int((time.time() - start) * 1000)
                break
            except Exception as e:
                last_error = e
                await asyncio.sleep(3 * (attempt + 1))  # 指数バックオフ

        if content is None:
            await emit_thought("writer", f"❌ Groq API エラー（2回失敗）", "error",
                               detail=str(last_error)[:80])
            raise RuntimeError(f"記事生成エラー（2回リトライ後）: {last_error}")

        # ── タイトル抽出 ───────────────────────────────────────────────────
        title = f"{area} {property_type}の{article_type_label(article_type)}"
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line.replace("# ", "").strip()
                break

        # ── 内部リンク挿入（SEO Agentの機能を組み込み）─────────────────────
        content = inject_tool_links(content, article_type)

        await emit_thought("writer",
                           f"記事完成 ({len(content)}文字)。SEOメタデータ生成中...",
                           "working",
                           detail=f"タイトル候補: {title[:40]}")

        # ── スラッグ生成 ────────────────────────────────────────────────────
        slug = slugify(
            f"{prefecture}-{area}-{property_type}-{datetime.now().strftime('%Y%m%d%H%M')}",
            allow_unicode=False
        ).replace("--", "-")

        # ── SEOメタデータ生成 ───────────────────────────────────────────────
        seo_data = await self._generate_seo(title, content, area, property_type, article_type)

        await emit_thought("writer",
                           f"✅ 「{title[:28]}...」完成",
                           "success",
                           detail=f"{duration_ms}ms / {len(content)}文字 / type:{article_type}")

        return {
            "slug": slug,
            "title": title,
            "content": content,
            "excerpt": self._extract_excerpt(content),
            "area": area,
            "prefecture": prefecture,
            "property_type": property_type,
            "article_type": article_type,
            "status": "published",
            "generated_by": "groq",
            "duration_ms": duration_ms,
            **seo_data,
        }

    def article_type_label(self, atype: str) -> str:
        return {"area": "価格相場", "guide": "ガイド", "qa": "Q&A", "ranking": "ランキング"}.get(atype, "記事")

    async def _generate_seo(
        self, title: str, content: str, area: str,
        property_type: str, article_type: str = "area"
    ) -> dict:
        """SEOメタデータをGroqで生成（リスク対策: 失敗時はデフォルト値）"""
        schema_type = {
            "area": "Article", "guide": "HowTo", "qa": "FAQPage", "ranking": "Article"
        }.get(article_type, "Article")

        prompt = f"""
記事タイトル: {title}
記事タイプ: {article_type}
対象: {area}の{property_type}情報

記事の最初の500文字:
{content[:500]}

上記のSEOメタデータをJSON形式で生成してください。
structured_data の @type は "{schema_type}" を使用してください。
"""
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=MODEL,
                messages=[
                    {"role": "system", "content": SEO_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
            )
            text = response.choices[0].message.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            seo = json.loads(text.strip())
            return {
                "meta_title": seo.get("meta_title", title[:60]),
                "meta_description": seo.get("meta_description", ""),
                "keywords": seo.get("keywords", [area, property_type, "価格", "相場"]),
                "structured_data": seo.get("structured_data", {}),
            }
        except Exception:
            return {
                "meta_title": title[:60],
                "meta_description": f"{area}の{property_type}情報。不動産価格・相場データをお届けします。",
                "keywords": [area, property_type, "価格", "相場", "不動産"],
                "structured_data": {},
            }

    def _extract_excerpt(self, content: str, max_len: int = 200) -> str:
        lines = [l.strip() for l in content.split("\n")
                 if l.strip() and not l.startswith("#") and not l.startswith("-")]
        text = " ".join(lines[:3])
        return text[:max_len] + "..." if len(text) > max_len else text


def article_type_label(atype: str) -> str:
    return {"area": "価格相場", "guide": "ガイド", "qa": "Q&A", "ranking": "ランキング"}.get(atype, "記事")


# ─────────────────────────────────────────────────────────────────────────────
# トピックリスト（topic_queue テーブルに移行後も後方互換として保持）
# Phase 1: DBが空の場合のフォールバック用
# ─────────────────────────────────────────────────────────────────────────────
ARTICLE_TOPICS = [
    # ── 北海道 ──
    {"area": "札幌市中央区", "prefecture": "北海道", "property_type": "マンション"},
    {"area": "札幌市豊平区", "prefecture": "北海道", "property_type": "マンション"},
    {"area": "札幌市西区",   "prefecture": "北海道", "property_type": "一戸建て"},
    {"area": "函館市",       "prefecture": "北海道", "property_type": "マンション"},
    {"area": "旭川市",       "prefecture": "北海道", "property_type": "一戸建て"},
    # ── 青森県 ──
    {"area": "青森市", "prefecture": "青森県", "property_type": "マンション"},
    {"area": "弘前市", "prefecture": "青森県", "property_type": "一戸建て"},
    # ── 岩手県 ──
    {"area": "盛岡市", "prefecture": "岩手県", "property_type": "マンション"},
    {"area": "奥州市", "prefecture": "岩手県", "property_type": "一戸建て"},
    # ── 宮城県 ──
    {"area": "仙台市青葉区",   "prefecture": "宮城県", "property_type": "マンション"},
    {"area": "仙台市泉区",     "prefecture": "宮城県", "property_type": "一戸建て"},
    {"area": "仙台市宮城野区", "prefecture": "宮城県", "property_type": "マンション"},
    # ── 秋田県 ──
    {"area": "秋田市", "prefecture": "秋田県", "property_type": "マンション"},
    {"area": "横手市", "prefecture": "秋田県", "property_type": "一戸建て"},
    # ── 山形県 ──
    {"area": "山形市", "prefecture": "山形県", "property_type": "マンション"},
    {"area": "米沢市", "prefecture": "山形県", "property_type": "一戸建て"},
    # ── 福島県 ──
    {"area": "福島市",   "prefecture": "福島県", "property_type": "マンション"},
    {"area": "郡山市",   "prefecture": "福島県", "property_type": "一戸建て"},
    {"area": "いわき市", "prefecture": "福島県", "property_type": "一戸建て"},
    # ── 茨城県 ──
    {"area": "つくば市", "prefecture": "茨城県", "property_type": "一戸建て"},
    {"area": "水戸市",   "prefecture": "茨城県", "property_type": "マンション"},
    {"area": "日立市",   "prefecture": "茨城県", "property_type": "一戸建て"},
    # ── 栃木県 ──
    {"area": "宇都宮市", "prefecture": "栃木県", "property_type": "マンション"},
    {"area": "小山市",   "prefecture": "栃木県", "property_type": "一戸建て"},
    # ── 群馬県 ──
    {"area": "前橋市", "prefecture": "群馬県", "property_type": "マンション"},
    {"area": "高崎市", "prefecture": "群馬県", "property_type": "一戸建て"},
    # ── 埼玉県 ──
    {"area": "さいたま市浦和区", "prefecture": "埼玉県", "property_type": "マンション"},
    {"area": "さいたま市大宮区", "prefecture": "埼玉県", "property_type": "マンション"},
    {"area": "川口市",           "prefecture": "埼玉県", "property_type": "マンション"},
    {"area": "川越市",           "prefecture": "埼玉県", "property_type": "一戸建て"},
    # ── 千葉県 ──
    {"area": "千葉市中央区", "prefecture": "千葉県", "property_type": "マンション"},
    {"area": "船橋市",       "prefecture": "千葉県", "property_type": "一戸建て"},
    {"area": "柏市",         "prefecture": "千葉県", "property_type": "一戸建て"},
    {"area": "松戸市",       "prefecture": "千葉県", "property_type": "マンション"},
    # ── 東京都 ──
    {"area": "港区",   "prefecture": "東京都", "property_type": "マンション"},
    {"area": "渋谷区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "新宿区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "世田谷区", "prefecture": "東京都", "property_type": "一戸建て"},
    {"area": "目黒区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "品川区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "中野区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "豊島区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "文京区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "江東区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "杉並区", "prefecture": "東京都", "property_type": "一戸建て"},
    {"area": "練馬区", "prefecture": "東京都", "property_type": "一戸建て"},
    {"area": "板橋区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "立川市", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "八王子市", "prefecture": "東京都", "property_type": "一戸建て"},
    # ── 神奈川県 ──
    {"area": "横浜市西区",  "prefecture": "神奈川県", "property_type": "マンション"},
    {"area": "横浜市港北区","prefecture": "神奈川県", "property_type": "マンション"},
    {"area": "横浜市青葉区","prefecture": "神奈川県", "property_type": "一戸建て"},
    {"area": "川崎市中原区","prefecture": "神奈川県", "property_type": "マンション"},
    {"area": "藤沢市",      "prefecture": "神奈川県", "property_type": "一戸建て"},
    {"area": "相模原市",    "prefecture": "神奈川県", "property_type": "一戸建て"},
    # ── 山梨県 ──
    {"area": "甲府市", "prefecture": "山梨県", "property_type": "一戸建て"},
    {"area": "甲斐市", "prefecture": "山梨県", "property_type": "一戸建て"},
    # ── 長野県 ──
    {"area": "長野市", "prefecture": "長野県", "property_type": "マンション"},
    {"area": "松本市", "prefecture": "長野県", "property_type": "一戸建て"},
    # ── 新潟県 ──
    {"area": "新潟市中央区", "prefecture": "新潟県", "property_type": "マンション"},
    {"area": "長岡市",       "prefecture": "新潟県", "property_type": "一戸建て"},
    # ── 富山県 ──
    {"area": "富山市", "prefecture": "富山県", "property_type": "マンション"},
    {"area": "高岡市", "prefecture": "富山県", "property_type": "一戸建て"},
    # ── 石川県 ──
    {"area": "金沢市", "prefecture": "石川県", "property_type": "マンション"},
    {"area": "白山市", "prefecture": "石川県", "property_type": "一戸建て"},
    # ── 福井県 ──
    {"area": "福井市", "prefecture": "福井県", "property_type": "マンション"},
    {"area": "越前市", "prefecture": "福井県", "property_type": "一戸建て"},
    # ── 静岡県 ──
    {"area": "静岡市葵区", "prefecture": "静岡県", "property_type": "マンション"},
    {"area": "浜松市中区", "prefecture": "静岡県", "property_type": "マンション"},
    {"area": "沼津市",     "prefecture": "静岡県", "property_type": "一戸建て"},
    # ── 愛知県 ──
    {"area": "名古屋市中区",  "prefecture": "愛知県", "property_type": "マンション"},
    {"area": "名古屋市千種区","prefecture": "愛知県", "property_type": "マンション"},
    {"area": "名古屋市天白区","prefecture": "愛知県", "property_type": "一戸建て"},
    {"area": "豊田市", "prefecture": "愛知県", "property_type": "一戸建て"},
    {"area": "岡崎市", "prefecture": "愛知県", "property_type": "一戸建て"},
    # ── 岐阜県 ──
    {"area": "岐阜市",   "prefecture": "岐阜県", "property_type": "マンション"},
    {"area": "各務原市", "prefecture": "岐阜県", "property_type": "一戸建て"},
    # ── 三重県 ──
    {"area": "津市",    "prefecture": "三重県", "property_type": "マンション"},
    {"area": "四日市市","prefecture": "三重県", "property_type": "一戸建て"},
    # ── 滋賀県 ──
    {"area": "大津市", "prefecture": "滋賀県", "property_type": "マンション"},
    {"area": "草津市", "prefecture": "滋賀県", "property_type": "一戸建て"},
    # ── 京都府 ──
    {"area": "京都市左京区", "prefecture": "京都府", "property_type": "マンション"},
    {"area": "京都市中京区", "prefecture": "京都府", "property_type": "マンション"},
    {"area": "京都市伏見区", "prefecture": "京都府", "property_type": "一戸建て"},
    # ── 大阪府 ──
    {"area": "大阪市北区",  "prefecture": "大阪府", "property_type": "マンション"},
    {"area": "大阪市中央区","prefecture": "大阪府", "property_type": "マンション"},
    {"area": "大阪市西区",  "prefecture": "大阪府", "property_type": "マンション"},
    {"area": "豊中市", "prefecture": "大阪府", "property_type": "一戸建て"},
    {"area": "吹田市", "prefecture": "大阪府", "property_type": "マンション"},
    {"area": "枚方市", "prefecture": "大阪府", "property_type": "一戸建て"},
    # ── 兵庫県 ──
    {"area": "神戸市中央区", "prefecture": "兵庫県", "property_type": "マンション"},
    {"area": "神戸市東灘区", "prefecture": "兵庫県", "property_type": "マンション"},
    {"area": "西宮市", "prefecture": "兵庫県", "property_type": "一戸建て"},
    {"area": "姫路市", "prefecture": "兵庫県", "property_type": "マンション"},
    # ── 奈良県 ──
    {"area": "奈良市",  "prefecture": "奈良県", "property_type": "マンション"},
    {"area": "橿原市",  "prefecture": "奈良県", "property_type": "一戸建て"},
    # ── 和歌山県 ──
    {"area": "和歌山市", "prefecture": "和歌山県", "property_type": "マンション"},
    {"area": "田辺市",   "prefecture": "和歌山県", "property_type": "一戸建て"},
    # ── 鳥取県 ──
    {"area": "鳥取市", "prefecture": "鳥取県", "property_type": "マンション"},
    {"area": "米子市", "prefecture": "鳥取県", "property_type": "一戸建て"},
    # ── 島根県 ──
    {"area": "松江市", "prefecture": "島根県", "property_type": "マンション"},
    {"area": "出雲市", "prefecture": "島根県", "property_type": "一戸建て"},
    # ── 岡山県 ──
    {"area": "岡山市北区", "prefecture": "岡山県", "property_type": "マンション"},
    {"area": "倉敷市",     "prefecture": "岡山県", "property_type": "一戸建て"},
    # ── 広島県 ──
    {"area": "広島市中区",   "prefecture": "広島県", "property_type": "マンション"},
    {"area": "広島市安佐南区","prefecture": "広島県", "property_type": "一戸建て"},
    {"area": "福山市",       "prefecture": "広島県", "property_type": "マンション"},
    # ── 山口県 ──
    {"area": "山口市", "prefecture": "山口県", "property_type": "マンション"},
    {"area": "下関市", "prefecture": "山口県", "property_type": "一戸建て"},
    # ── 徳島県 ──
    {"area": "徳島市", "prefecture": "徳島県", "property_type": "マンション"},
    {"area": "阿南市", "prefecture": "徳島県", "property_type": "一戸建て"},
    # ── 香川県 ──
    {"area": "高松市", "prefecture": "香川県", "property_type": "マンション"},
    {"area": "丸亀市", "prefecture": "香川県", "property_type": "一戸建て"},
    # ── 愛媛県 ──
    {"area": "松山市", "prefecture": "愛媛県", "property_type": "マンション"},
    {"area": "今治市", "prefecture": "愛媛県", "property_type": "一戸建て"},
    # ── 高知県 ──
    {"area": "高知市", "prefecture": "高知県", "property_type": "マンション"},
    {"area": "南国市", "prefecture": "高知県", "property_type": "一戸建て"},
    # ── 福岡県 ──
    {"area": "福岡市中央区",     "prefecture": "福岡県", "property_type": "マンション"},
    {"area": "福岡市博多区",     "prefecture": "福岡県", "property_type": "マンション"},
    {"area": "福岡市東区",       "prefecture": "福岡県", "property_type": "一戸建て"},
    {"area": "北九州市小倉北区", "prefecture": "福岡県", "property_type": "マンション"},
    # ── 佐賀県 ──
    {"area": "佐賀市", "prefecture": "佐賀県", "property_type": "マンション"},
    {"area": "唐津市", "prefecture": "佐賀県", "property_type": "一戸建て"},
    # ── 長崎県 ──
    {"area": "長崎市",  "prefecture": "長崎県", "property_type": "マンション"},
    {"area": "佐世保市","prefecture": "長崎県", "property_type": "一戸建て"},
    # ── 熊本県 ──
    {"area": "熊本市中央区", "prefecture": "熊本県", "property_type": "マンション"},
    {"area": "熊本市東区",   "prefecture": "熊本県", "property_type": "一戸建て"},
    {"area": "菊陽町",       "prefecture": "熊本県", "property_type": "一戸建て"},
    # ── 大分県 ──
    {"area": "大分市", "prefecture": "大分県", "property_type": "マンション"},
    {"area": "別府市", "prefecture": "大分県", "property_type": "マンション"},
    # ── 宮崎県 ──
    {"area": "宮崎市", "prefecture": "宮崎県", "property_type": "マンション"},
    {"area": "都城市", "prefecture": "宮崎県", "property_type": "一戸建て"},
    # ── 鹿児島県 ──
    {"area": "鹿児島市", "prefecture": "鹿児島県", "property_type": "マンション"},
    {"area": "霧島市",   "prefecture": "鹿児島県", "property_type": "一戸建て"},
    # ── 沖縄県 ──
    {"area": "那覇市",  "prefecture": "沖縄県", "property_type": "マンション"},
    {"area": "浦添市",  "prefecture": "沖縄県", "property_type": "一戸建て"},
    {"area": "沖縄市",  "prefecture": "沖縄県", "property_type": "マンション"},
]

"""
Writer Agent - Gemini による不動産記事自動執筆エージェント
役割: SEO最適化された不動産価格情報記事を自動生成
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Optional
import google.generativeai as genai
from slugify import slugify

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

# 無料枠最適 - gemini-1.5-flash (高速・低コスト)
MODEL = "gemini-1.5-flash"

ARTICLE_SYSTEM_PROMPT = """
あなたは不動産業界の専門ライターです。
SEO・AIO（AI Overview）対策に優れた、日本の不動産価格情報記事を執筆します。

執筆ルール:
1. 見出し構造 (H2, H3) を明確に使用する
2. 具体的な数値・データを含める
3. 読者の疑問に直接答えるQ&A形式を含める
4. 地域の特性・生活環境も記述する
5. 必ず「まとめ」セクションを末尾に入れる
6. 文体: 丁寧語、専門的かつ読みやすく
7. 文字数: 1500〜2500文字
8. Markdown形式で出力

AIO対策:
- 冒頭の100文字以内に記事の核心情報を入れる
- 箇条書きで要点をまとめるセクションを含める
- FAQセクションを含める (3〜5問)
"""

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


class WriterAgent:
    """Gemini記事執筆エージェント"""

    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=ARTICLE_SYSTEM_PROMPT,
        )
        self.seo_model = genai.GenerativeModel(
            model_name=MODEL,
            system_instruction=SEO_SYSTEM_PROMPT,
        )

    async def generate_article(
        self,
        area: str,
        prefecture: str,
        property_type: str,
        price_avg: Optional[int] = None,
        unit_price: Optional[int] = None,
        extra_context: str = "",
    ) -> dict:
        """指定エリア・物件種別の価格記事を生成"""

        price_info = ""
        if price_avg:
            price_info = f"平均価格: 約{price_avg:,}万円"
        if unit_price:
            price_info += f"、坪単価: 約{unit_price}万円/㎡"

        prompt = f"""
以下の条件で不動産価格情報記事を執筆してください。

対象エリア: {prefecture} {area}
物件種別: {property_type}
価格情報: {price_info or '最新相場を参考に'}
追加情報: {extra_context}

記事タイトルも含めて、Markdown形式で出力してください。
"""

        start = time.time()
        try:
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            content = response.text
            duration_ms = int((time.time() - start) * 1000)

            # タイトル抽出 (最初の # 行)
            title = area + " " + property_type + "の価格相場"
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break

            # スラッグ生成
            slug = slugify(f"{prefecture}-{area}-{property_type}-{datetime.now().strftime('%Y%m')}", allow_unicode=False)
            slug = slug.replace("--", "-")

            # SEOメタデータ生成
            seo_data = await self._generate_seo(title, content, area, property_type)

            return {
                "slug": slug,
                "title": title,
                "content": content,
                "excerpt": self._extract_excerpt(content),
                "area": area,
                "prefecture": prefecture,
                "property_type": property_type,
                "status": "published",
                "generated_by": "gemini",
                "generation_prompt": prompt,
                "duration_ms": duration_ms,
                **seo_data,
            }

        except Exception as e:
            raise RuntimeError(f"記事生成エラー: {e}")

    async def _generate_seo(self, title: str, content: str, area: str, property_type: str) -> dict:
        """SEOメタデータをGeminiで生成"""
        prompt = f"""
記事タイトル: {title}
対象: {area}の{property_type}価格情報

記事の最初の500文字:
{content[:500]}

上記のSEOメタデータをJSON形式で生成してください。
"""
        try:
            response = await asyncio.to_thread(
                self.seo_model.generate_content, prompt
            )
            text = response.text.strip()
            # JSONブロックを抽出
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
                "meta_description": f"{area}の{property_type}価格相場情報。最新の不動産価格データをお届けします。",
                "keywords": [area, property_type, "価格", "相場", "不動産"],
                "structured_data": {},
            }

    def _extract_excerpt(self, content: str, max_len: int = 200) -> str:
        """記事から抜粋を抽出"""
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        text = " ".join(lines[:3])
        return text[:max_len] + "..." if len(text) > max_len else text


# ── バッチ記事生成 ────────────────────────────────────
ARTICLE_TOPICS = [
    {"area": "港区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "渋谷区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "新宿区", "prefecture": "東京都", "property_type": "マンション"},
    {"area": "世田谷区", "prefecture": "東京都", "property_type": "一戸建て"},
    {"area": "横浜市", "prefecture": "神奈川県", "property_type": "マンション"},
    {"area": "さいたま市", "prefecture": "埼玉県", "property_type": "マンション"},
    {"area": "千葉市", "prefecture": "千葉県", "property_type": "一戸建て"},
    {"area": "大阪市北区", "prefecture": "大阪府", "property_type": "マンション"},
    {"area": "名古屋市中区", "prefecture": "愛知県", "property_type": "マンション"},
    {"area": "福岡市中央区", "prefecture": "福岡県", "property_type": "マンション"},
]

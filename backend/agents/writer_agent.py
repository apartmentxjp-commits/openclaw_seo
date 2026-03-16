"""
Writer Agent - Groq (Llama 3.3 70b) による不動産記事自動執筆エージェント
役割: SEO最適化された不動産価格情報記事を自動生成
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

MODEL = "llama-3.3-70b-versatile"

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
    """Groq (Llama 3.3 70b) 記事執筆エージェント"""

    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

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

        await emit_thought("writer", f"タスク受信: {prefecture} {area} の{property_type}記事", "thinking",
                           detail=f"モデル: {MODEL}")
        await asyncio.sleep(0.3)

        start = time.time()
        try:
            await emit_thought("writer", f"Groq に接続中... 執筆開始", "working",
                               detail=f"{area} {property_type}の価格相場記事を生成")

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=MODEL,
                messages=[
                    {"role": "system", "content": ARTICLE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
            )
            content = response.choices[0].message.content
            duration_ms = int((time.time() - start) * 1000)

            # タイトル抽出 (最初の # 行)
            title = area + " " + property_type + "の価格相場"
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break

            await emit_thought("writer", f"記事完成 ({len(content)}文字)。SEOメタデータ生成中...", "working",
                               detail=f"タイトル候補: {title[:40]}")

            # スラッグ生成
            slug = slugify(f"{prefecture}-{area}-{property_type}-{datetime.now().strftime('%Y%m%d%H%M')}", allow_unicode=False)
            slug = slug.replace("--", "-")

            # SEOメタデータ生成
            seo_data = await self._generate_seo(title, content, area, property_type)

            await emit_thought("writer", f"✅ 「{title[:28]}...」完成・保存完了", "success",
                               detail=f"{duration_ms}ms で生成 / {len(content)}文字")

            return {
                "slug": slug,
                "title": title,
                "content": content,
                "excerpt": self._extract_excerpt(content),
                "area": area,
                "prefecture": prefecture,
                "property_type": property_type,
                "status": "published",
                "generated_by": "groq",
                "generation_prompt": prompt,
                "duration_ms": duration_ms,
                **seo_data,
            }

        except Exception as e:
            await emit_thought("writer", f"❌ エラー: {str(e)[:60]}", "error",
                               detail=f"{area} {property_type} の記事生成に失敗")
            raise RuntimeError(f"記事生成エラー: {e}")

    async def _generate_seo(self, title: str, content: str, area: str, property_type: str) -> dict:
        """SEOメタデータをGroqで生成"""
        prompt = f"""
記事タイトル: {title}
対象: {area}の{property_type}価格情報

記事の最初の500文字:
{content[:500]}

上記のSEOメタデータをJSON形式で生成してください。
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
# 全47都道府県カバー: 約150トピック × 30分間隔 = 約75時間で一巡
ARTICLE_TOPICS = [
    # ── 北海道 ──
    {"area": "札幌市中央区", "prefecture": "北海道", "property_type": "マンション"},
    {"area": "札幌市豊平区", "prefecture": "北海道", "property_type": "マンション"},
    {"area": "札幌市西区", "prefecture": "北海道", "property_type": "一戸建て"},
    {"area": "函館市", "prefecture": "北海道", "property_type": "マンション"},
    {"area": "旭川市", "prefecture": "北海道", "property_type": "一戸建て"},
    # ── 青森県 ──
    {"area": "青森市", "prefecture": "青森県", "property_type": "マンション"},
    {"area": "弘前市", "prefecture": "青森県", "property_type": "一戸建て"},
    # ── 岩手県 ──
    {"area": "盛岡市", "prefecture": "岩手県", "property_type": "マンション"},
    {"area": "奥州市", "prefecture": "岩手県", "property_type": "一戸建て"},
    # ── 宮城県 ──
    {"area": "仙台市青葉区", "prefecture": "宮城県", "property_type": "マンション"},
    {"area": "仙台市泉区", "prefecture": "宮城県", "property_type": "一戸建て"},
    {"area": "仙台市宮城野区", "prefecture": "宮城県", "property_type": "マンション"},
    # ── 秋田県 ──
    {"area": "秋田市", "prefecture": "秋田県", "property_type": "マンション"},
    {"area": "横手市", "prefecture": "秋田県", "property_type": "一戸建て"},
    # ── 山形県 ──
    {"area": "山形市", "prefecture": "山形県", "property_type": "マンション"},
    {"area": "米沢市", "prefecture": "山形県", "property_type": "一戸建て"},
    # ── 福島県 ──
    {"area": "福島市", "prefecture": "福島県", "property_type": "マンション"},
    {"area": "郡山市", "prefecture": "福島県", "property_type": "一戸建て"},
    {"area": "いわき市", "prefecture": "福島県", "property_type": "一戸建て"},
    # ── 茨城県 ──
    {"area": "つくば市", "prefecture": "茨城県", "property_type": "一戸建て"},
    {"area": "水戸市", "prefecture": "茨城県", "property_type": "マンション"},
    {"area": "日立市", "prefecture": "茨城県", "property_type": "一戸建て"},
    # ── 栃木県 ──
    {"area": "宇都宮市", "prefecture": "栃木県", "property_type": "マンション"},
    {"area": "小山市", "prefecture": "栃木県", "property_type": "一戸建て"},
    # ── 群馬県 ──
    {"area": "前橋市", "prefecture": "群馬県", "property_type": "マンション"},
    {"area": "高崎市", "prefecture": "群馬県", "property_type": "一戸建て"},
    # ── 埼玉県 ──
    {"area": "さいたま市浦和区", "prefecture": "埼玉県", "property_type": "マンション"},
    {"area": "さいたま市大宮区", "prefecture": "埼玉県", "property_type": "マンション"},
    {"area": "川口市", "prefecture": "埼玉県", "property_type": "マンション"},
    {"area": "川越市", "prefecture": "埼玉県", "property_type": "一戸建て"},
    # ── 千葉県 ──
    {"area": "千葉市中央区", "prefecture": "千葉県", "property_type": "マンション"},
    {"area": "船橋市", "prefecture": "千葉県", "property_type": "一戸建て"},
    {"area": "柏市", "prefecture": "千葉県", "property_type": "一戸建て"},
    {"area": "松戸市", "prefecture": "千葉県", "property_type": "マンション"},
    # ── 東京都 ──
    {"area": "港区", "prefecture": "東京都", "property_type": "マンション"},
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
    {"area": "横浜市西区", "prefecture": "神奈川県", "property_type": "マンション"},
    {"area": "横浜市港北区", "prefecture": "神奈川県", "property_type": "マンション"},
    {"area": "横浜市青葉区", "prefecture": "神奈川県", "property_type": "一戸建て"},
    {"area": "川崎市中原区", "prefecture": "神奈川県", "property_type": "マンション"},
    {"area": "藤沢市", "prefecture": "神奈川県", "property_type": "一戸建て"},
    {"area": "相模原市", "prefecture": "神奈川県", "property_type": "一戸建て"},
    # ── 山梨県 ──
    {"area": "甲府市", "prefecture": "山梨県", "property_type": "一戸建て"},
    {"area": "甲斐市", "prefecture": "山梨県", "property_type": "一戸建て"},
    # ── 長野県 ──
    {"area": "長野市", "prefecture": "長野県", "property_type": "マンション"},
    {"area": "松本市", "prefecture": "長野県", "property_type": "一戸建て"},
    # ── 新潟県 ──
    {"area": "新潟市中央区", "prefecture": "新潟県", "property_type": "マンション"},
    {"area": "長岡市", "prefecture": "新潟県", "property_type": "一戸建て"},
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
    {"area": "沼津市", "prefecture": "静岡県", "property_type": "一戸建て"},
    # ── 愛知県 ──
    {"area": "名古屋市中区", "prefecture": "愛知県", "property_type": "マンション"},
    {"area": "名古屋市千種区", "prefecture": "愛知県", "property_type": "マンション"},
    {"area": "名古屋市天白区", "prefecture": "愛知県", "property_type": "一戸建て"},
    {"area": "豊田市", "prefecture": "愛知県", "property_type": "一戸建て"},
    {"area": "岡崎市", "prefecture": "愛知県", "property_type": "一戸建て"},
    # ── 岐阜県 ──
    {"area": "岐阜市", "prefecture": "岐阜県", "property_type": "マンション"},
    {"area": "各務原市", "prefecture": "岐阜県", "property_type": "一戸建て"},
    # ── 三重県 ──
    {"area": "津市", "prefecture": "三重県", "property_type": "マンション"},
    {"area": "四日市市", "prefecture": "三重県", "property_type": "一戸建て"},
    # ── 滋賀県 ──
    {"area": "大津市", "prefecture": "滋賀県", "property_type": "マンション"},
    {"area": "草津市", "prefecture": "滋賀県", "property_type": "一戸建て"},
    # ── 京都府 ──
    {"area": "京都市左京区", "prefecture": "京都府", "property_type": "マンション"},
    {"area": "京都市中京区", "prefecture": "京都府", "property_type": "マンション"},
    {"area": "京都市伏見区", "prefecture": "京都府", "property_type": "一戸建て"},
    # ── 大阪府 ──
    {"area": "大阪市北区", "prefecture": "大阪府", "property_type": "マンション"},
    {"area": "大阪市中央区", "prefecture": "大阪府", "property_type": "マンション"},
    {"area": "大阪市西区", "prefecture": "大阪府", "property_type": "マンション"},
    {"area": "豊中市", "prefecture": "大阪府", "property_type": "一戸建て"},
    {"area": "吹田市", "prefecture": "大阪府", "property_type": "マンション"},
    {"area": "枚方市", "prefecture": "大阪府", "property_type": "一戸建て"},
    # ── 兵庫県 ──
    {"area": "神戸市中央区", "prefecture": "兵庫県", "property_type": "マンション"},
    {"area": "神戸市東灘区", "prefecture": "兵庫県", "property_type": "マンション"},
    {"area": "西宮市", "prefecture": "兵庫県", "property_type": "一戸建て"},
    {"area": "姫路市", "prefecture": "兵庫県", "property_type": "マンション"},
    # ── 奈良県 ──
    {"area": "奈良市", "prefecture": "奈良県", "property_type": "マンション"},
    {"area": "橿原市", "prefecture": "奈良県", "property_type": "一戸建て"},
    # ── 和歌山県 ──
    {"area": "和歌山市", "prefecture": "和歌山県", "property_type": "マンション"},
    {"area": "田辺市", "prefecture": "和歌山県", "property_type": "一戸建て"},
    # ── 鳥取県 ──
    {"area": "鳥取市", "prefecture": "鳥取県", "property_type": "マンション"},
    {"area": "米子市", "prefecture": "鳥取県", "property_type": "一戸建て"},
    # ── 島根県 ──
    {"area": "松江市", "prefecture": "島根県", "property_type": "マンション"},
    {"area": "出雲市", "prefecture": "島根県", "property_type": "一戸建て"},
    # ── 岡山県 ──
    {"area": "岡山市北区", "prefecture": "岡山県", "property_type": "マンション"},
    {"area": "倉敷市", "prefecture": "岡山県", "property_type": "一戸建て"},
    # ── 広島県 ──
    {"area": "広島市中区", "prefecture": "広島県", "property_type": "マンション"},
    {"area": "広島市安佐南区", "prefecture": "広島県", "property_type": "一戸建て"},
    {"area": "福山市", "prefecture": "広島県", "property_type": "マンション"},
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
    {"area": "福岡市中央区", "prefecture": "福岡県", "property_type": "マンション"},
    {"area": "福岡市博多区", "prefecture": "福岡県", "property_type": "マンション"},
    {"area": "福岡市東区", "prefecture": "福岡県", "property_type": "一戸建て"},
    {"area": "北九州市小倉北区", "prefecture": "福岡県", "property_type": "マンション"},
    # ── 佐賀県 ──
    {"area": "佐賀市", "prefecture": "佐賀県", "property_type": "マンション"},
    {"area": "唐津市", "prefecture": "佐賀県", "property_type": "一戸建て"},
    # ── 長崎県 ──
    {"area": "長崎市", "prefecture": "長崎県", "property_type": "マンション"},
    {"area": "佐世保市", "prefecture": "長崎県", "property_type": "一戸建て"},
    # ── 熊本県 ──
    {"area": "熊本市中央区", "prefecture": "熊本県", "property_type": "マンション"},
    {"area": "熊本市東区", "prefecture": "熊本県", "property_type": "一戸建て"},
    {"area": "菊陽町", "prefecture": "熊本県", "property_type": "一戸建て"},
    # ── 大分県 ──
    {"area": "大分市", "prefecture": "大分県", "property_type": "マンション"},
    {"area": "別府市", "prefecture": "大分県", "property_type": "マンション"},
    # ── 宮崎県 ──
    {"area": "宮崎市", "prefecture": "宮崎県", "property_type": "マンション"},
    {"area": "都城市", "prefecture": "宮崎県", "property_type": "一戸建て"},
    # ── 鹿児島県 ──
    {"area": "鹿児島市", "prefecture": "鹿児島県", "property_type": "マンション"},
    {"area": "霧島市", "prefecture": "鹿児島県", "property_type": "一戸建て"},
    # ── 沖縄県 ──
    {"area": "那覇市", "prefecture": "沖縄県", "property_type": "マンション"},
    {"area": "浦添市", "prefecture": "沖縄県", "property_type": "一戸建て"},
    {"area": "沖縄市", "prefecture": "沖縄県", "property_type": "マンション"},
]

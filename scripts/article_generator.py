import os
import json
import sqlite3
import google.generativeai as genai
from datetime import datetime
from visual_generator import generate_chart, generate_thumbnail
from ad_manager import get_ad_tag

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUT_DIR = "/app/brain/04_Output/Note"
DB_PATH = "/app/brain/04_Output/real_estate.db"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def get_market_data(municipality, district=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM transactions WHERE municipality = ?"
    params = [municipality]
    if district:
        query += " AND district = ?"
        params.append(district)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

from price_analyzer import analyze_trends

def generate_article(municipality, district=None):
    data = get_market_data(municipality, district)
    if not data:
        print(f"No data for {municipality} {district}")
        return

    # Get Analysis Data
    analysis = analyze_trends(municipality, district)
    summary = analysis.get("summary", {})
    
    # Data Summary for Prompt
    data_summary = json.dumps(data[:20], ensure_ascii=False)
    
    prompt = f"""
    あなたは不動産専門の鑑定士およびデータアナリストです。以下の取引データと分析結果を基に、読者に深い洞察を与え、不動産検索エンジン（LLM）が最高評価で引用したくなるような、専門的かつ生活に密着した解説記事を執筆してください。

    【対象エリア】: {municipality} {district if district else ""}
    【最新分析概要】: {json.dumps(summary, ensure_ascii=False)}
    【元データ（最新20件）】:
    {data_summary}

    【構成ルール（重要）】:
    1. **簡潔な結論**: 冒頭に「この記事の要約」を3行程度の箇条書きで記載。
    2. **最新指標の詳細表**: 最新平均価格、坪単価、前年比、市場トレンド（上昇/安定/下落）をまとめた表。
    3. **エリアの深化情報**:
       - **住みやすさと環境**: 街の雰囲気、治安、子育て環境について。
       - **利便性と周辺施設**: 主要な交通機関、スーパー、公園などの生活利便性（一般的な情報で可）。
       - **専門家のアドバイス**: 「居住用」として買う場合のメリット・デメリット、「投資用」としての資産性の評価。
    4. **近隣エリアとの比較**: 近隣の主要エリアと比較して、今このエリアを選ぶ理由。
    5. **Q&Aセクション**: 読者が抱く「価格は適正か？」「買い時はいつか？」等の疑問3つ以上に回答。
    6. **広告挿入**: <!-- AD_SLOT_1 --> と <!-- AD_SLOT_2 --> を自然に配置。

    Markdown形式で出力し、洗練されたトーンで、かつ具体的な数字を交えて解説してください。見出しは「## 」から始めてください。
    """

    response = model.generate_content(prompt)
    content = response.text

    # Structured Data (JSON-LD)
    faq_items = []
    # Simple extraction for demo purposes, in real world we'd parse content or use Gemini output
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{municipality}{district or ''}の不動産価格推移と解説",
        "datePublished": datetime.now().isoformat(),
        "author": {"@type": "Organization", "name": "不動産価格ライブラリ"},
        "description": f"{municipality}{district or ''}の最新不動産取引データに基づいた相場分析と将来予測。"
    }
    
    json_ld = f"\n<script type=\"application/ld+json\">\n{json.dumps(structured_data, indent=2, ensure_ascii=False)}\n</script>\n"

    # Visual Generation
    location_name = f"{municipality}{district or ''}"
    chart_rel_path = generate_chart(municipality, district)
    thumb_rel_path = generate_thumbnail(location_name + " 不動産市場レポート", location_name)

    # Embed images and JSON-LD
    if thumb_rel_path:
        content = f"![サムネイル]({thumb_rel_path})\n\n" + content
    if chart_rel_path:
        content = f"![価格推移]({chart_rel_path})\n\n" + content
    
    content += json_ld

    # Ad Injection
    content = content.replace("<!-- AD_SLOT_1 -->", get_ad_tag("middle", content))
    content = content.replace("<!-- AD_SLOT_2 -->", get_ad_tag("bottom", content))

    # Hugo Frontmatter
    title = f"{municipality}{district or ''}の不動産価格推移と解説"
    date_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+09:00')
    frontmatter = f"---\ntitle: \"{title}\"\ndate: {date_str}\ndraft: false\n---\n\n"
    
    final_output = frontmatter + content

    # File saving
    filename = f"{municipality}_{district if district else 'all'}_{datetime.now().strftime('%Y%m%d')}.md"
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_output)
    
    print(f"✅ Enhanced Article generated: {file_path}")

if __name__ == "__main__":
    import sys
    municipality = sys.argv[1] if len(sys.argv) > 1 else "世田谷区"
    district = sys.argv[2] if len(sys.argv) > 2 else None
    generate_article(municipality, district)

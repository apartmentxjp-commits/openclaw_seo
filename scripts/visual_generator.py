import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image, ImageDraw, ImageFont
import sqlite3
import pandas as pd

# Paths
DB_PATH = "/app/brain/04_Output/real_estate.db"
CHART_DIR = "/app/brain/04_Output/images/charts"
THUMBNAIL_DIR = "/app/brain/04_Output/images/thumbnails"
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# Set global font for matplotlib
if os.path.exists(FONT_PATH):
    prop = fm.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = prop.get_name()
    # Add to font manager to avoid finding issues
    fm.fontManager.addfont(FONT_PATH)

# Ensure directories exist
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

def generate_chart(municipality, district=None):
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    query = "SELECT trade_period, CAST(trade_price AS INTEGER) as price FROM transactions WHERE municipality = ?"
    params = [municipality]
    if district:
        query += " AND district = ?"
        params.append(district)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return None

    # Group and calculate average
    df_avg = df.groupby('trade_period')['price'].mean().reset_index()
    df_avg['trade_period'] = df_avg['trade_period'].astype(str)
    df_avg = df_avg.sort_values('trade_period') # Very basic sort

    # Plot
    jp_font = fm.FontProperties(fname=FONT_PATH)
    plt.figure(figsize=(10, 6))
    
    # Simplify labels (remove "第X四半期" if user dislikes it, or just make it cleaner)
    clean_labels = [p.replace('年第', '/').replace('四半期', '') for p in df_avg['trade_period']]
    
    plt.plot(clean_labels, df_avg['price'], marker='o', linestyle='-', color='#1e88e5')
    
    title = f"{municipality}{district or ''} 不動産価格推移"
    plt.title(title, fontproperties=jp_font, fontsize=16)
    plt.xlabel("時期 (年/期)", fontproperties=jp_font)
    plt.ylabel("平均価格（円）", fontproperties=jp_font)
    plt.xticks(rotation=45)
    plt.tight_layout()

    filename = f"{municipality}_{district or 'all'}_chart.png"
    save_path = os.path.join(CHART_DIR, filename)
    plt.savefig(save_path)
    plt.close()
    return f"images/charts/{filename}"

def generate_thumbnail(title, location):
    # For now, create a nice colored placeholder with text
    img = Image.new('RGB', (1200, 630), color = (30, 136, 229))
    d = ImageDraw.Draw(img)
    
    try:
        # Use the same Noto font
        fnt = ImageFont.truetype(FONT_PATH, 60)
        fnt_small = ImageFont.truetype(FONT_PATH, 40)
    except:
        fnt = ImageFont.load_default()
        fnt_small = ImageFont.load_default()

    d.text((100,200), f"【{location}】", font=fnt_small, fill=(255,255,255))
    d.text((100,300), title[:25] + ("..." if len(title)>25 else ""), font=fnt, fill=(255,255,255))
    d.text((100,500), "日本不動産価格調査センター", font=fnt_small, fill=(255,255,255))

    filename = f"{location}_thumb.png".replace("/", "_")
    save_path = os.path.join(THUMBNAIL_DIR, filename)
    img.save(save_path)
    return f"images/thumbnails/{filename}"

if __name__ == "__main__":
    import sys
    mun = sys.argv[1] if len(sys.argv) > 1 else "世田谷区"
    dist = sys.argv[2] if len(sys.argv) > 2 else None
    chart_path = generate_chart(mun, dist)
    thumb_path = generate_thumbnail(f"{mun}{dist or ''} 不動産価格レポート", f"{mun}{dist or ''}")
    print(f"Chart: {chart_path}")
    print(f"Thumbnail: {thumb_path}")

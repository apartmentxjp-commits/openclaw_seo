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
    df_avg = df_avg.sort_values('trade_period')

    # Simplify labels for clarity (e.g. 2023 7-9月 instead of 2023年第3四半期)
    def format_period(p):
        year = p[:4]
        try:
            q = p[p.find('第')+1]
            if q == '1': return f"{year} 1-3月"
            if q == '2': return f"{year} 4-6月"
            if q == '3': return f"{year} 7-9月"
            if q == '4': return f"{year} 10-12月"
        except:
            pass
        return p
    clean_labels = [format_period(p) for p in df_avg['trade_period']]

    # Plot
    jp_font = fm.FontProperties(fname=FONT_PATH)
    plt.figure(figsize=(10, 6))
    plt.plot(clean_labels, df_avg['price'], marker='o', linestyle='-', color='#2563eb', linewidth=2)
    
    title = f"{municipality}{district or ''} 不動産価格推移"
    plt.title(title, fontproperties=jp_font, fontsize=16, pad=20)
    plt.xlabel("時期", fontproperties=jp_font)
    plt.ylabel("平均取引価格（円）", fontproperties=jp_font)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=0)
    plt.tight_layout()

    # Use English filename to prevent encoding issues
    base_name = "setagaya_all"
    if district == "三軒茶屋": base_name = "setagaya_sangenjaya"
    elif district == "代沢": base_name = "setagaya_daizawa"
    
    filename = f"{base_name}_chart.png"
    save_path = os.path.join(CHART_DIR, filename)
    plt.savefig(save_path)
    plt.close()
    return f"images/charts/{filename}"

def generate_thumbnail(title, location):
    # Professional Blue Template
    img = Image.new('RGB', (1200, 630), color = (15, 23, 42))
    d = ImageDraw.Draw(img)
    
    try:
        fnt = ImageFont.truetype(FONT_PATH, 60)
        fnt_small = ImageFont.truetype(FONT_PATH, 40)
    except:
        fnt = ImageFont.load_default()
        fnt_small = ImageFont.load_default()

    d.text((100,150), f"不動産価格調査レポート", font=fnt_small, fill=(148, 163, 184))
    d.text((100,220), f"【{location}】", font=fnt, fill=(255,255,255))
    d.text((100,320), title[:25] + ("..." if len(title)>25 else ""), font=fnt, fill=(255,255,255))
    
    # Official Footer Label
    d.rectangle([0, 530, 1200, 630], fill=(30, 41, 59))
    d.text((100, 550), "日本不動産価格調査センター", font=fnt_small, fill=(255, 255, 255))

    base_name = "setagaya_all"
    if "三軒茶屋" in location: base_name = "setagaya_sangenjaya"
    elif "代沢" in location: base_name = "setagaya_daizawa"

    filename = f"{base_name}_thumb.png"
    save_path = os.path.join(THUMBNAIL_DIR, filename)
    img.save(save_path)
    return f"images/thumbnails/{filename}"

if __name__ == "__main__":
    import sys
    mun = sys.argv[1] if len(sys.argv) > 1 else "世田谷区"
    dist = sys.argv[2] if len(sys.argv) > 2 else None
    chart_path = generate_chart(mun, dist)
    thumb_path = generate_thumbnail(f"{mun}{dist or ''} 不動産価格分析結果", f"{mun}{dist or ''}")
    print(f"Chart: {chart_path}")
    print(f"Thumbnail: {thumb_path}")

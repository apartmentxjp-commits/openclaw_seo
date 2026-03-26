"""
スクレイプ物件の画像を一括クリア

間取り図・ロゴ入り画像が混入しているため、
スクレイプ由来(source=ai/api)の全物件の images を空にリセットする。
次回スクレイプ時に改善されたフィルタで外観写真のみ再取得される。
"""
import os, sys
from supabase import create_client

url = os.getenv("AKIYA_SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
key = os.getenv("AKIYA_SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
if not url or not key:
    print("❌ Supabase 環境変数未設定"); sys.exit(1)

sb = create_client(url, key)

# スクレイプ由来の物件を対象に images を空配列にリセット
result = sb.table("properties") \
    .update({"images": []}) \
    .in_("source", ["ai", "api"]) \
    .execute()

print(f"✓ スクレイプ物件の images をクリアしました")

# 件数確認
count = sb.table("properties").select("id", count="exact").in_("source", ["ai", "api"]).execute()
print(f"  対象物件数: {count.count} 件")

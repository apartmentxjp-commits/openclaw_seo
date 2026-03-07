import json
import os

CONFIG_PATH = "/app/config/ad_units.json"

def get_ad_tag(position, keyword_context=None):
    if not os.path.exists(CONFIG_PATH):
        return f"<!-- AD_CONFIG_MISSING: {position} -->"
    
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
    
    client = config.get("default_client", "ca-pub-xxxxxxxxxxxxxx")
    pos_config = config.get("positions", {}).get(position, {})
    
    # Selection logic based on context
    ad_type = "general"
    if keyword_context:
        if "投資" in keyword_context or "利回り" in keyword_context:
            ad_type = "investment"
        elif "ローン" in keyword_context or "融資" in keyword_context:
            ad_type = "mortgage"
    
    unit = pos_config.get(ad_type) or pos_config.get("general")
    
    if not unit:
        return f"<!-- AD_UNIT_NOT_FOUND: {position}/{ad_type} -->"
    
    slot = unit.get("slot")
    format_attr = unit.get("format", "auto")
    responsive = unit.get("responsive", "true")

    tag = f"""
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="{client}"
     data-ad-slot="{slot}"
     data-ad-format="{format_attr}"
     data-full-width-responsive="{responsive}"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({{}});
</script>
"""
    return tag

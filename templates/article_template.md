# {{ TITLE }}

{% if TYPE == 'MUNICIPALITY' %}
## {{ MUNICIPALITY }}の不動産市場概況
{{ SUMMARY_METRICS }}

<!-- AD_SLOT_1 -->

### 価格推移と今後の予測
{{ MARKET_ANALYSIS }}

{% else %}
## {{ MUNICIPALITY }}{{ DISTRICT }}の成約事例と価格傾向
{{ RECENT_TRANSACTIONS }}

<!-- AD_SLOT_1 -->

### エリア特性と資産価値
{{ AREA_ANALYSIS }}
{% endif %}

<!-- AD_SLOT_2 -->

---
*本記事は国土交通省の不動産取引価格情報を基にAIが生成しています。*

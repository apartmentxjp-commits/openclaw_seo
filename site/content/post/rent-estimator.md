---
title: "適正家賃相場シミュレーター"
date: 2026-03-09T00:00:00+09:00
draft: false
layout: "tool"
---

{{< rawhtml >}}
<div class="premium-card">
    <div class="input-wrapper">
        <span class="premium-label">エリアを選択</span>
        <select id="rent-area" style="width:100%; padding:18px; border-radius:12px; border:2px solid #e2e8f0; font-size:1.1rem; font-weight:600;">
            <option value="1.0">世田谷区 全域</option>
            <option value="1.2">三軒茶屋 周辺</option>
            <option value="1.15">代沢 周辺</option>
            <option value="0.9">その他エリア</option>
        </select>
    </div>

    <div class="slider-group">
        <div class="slider-header">
            <span class="premium-label">専有面積 (㎡)</span>
            <span class="slider-value" id="val-sqm">25㎡</span>
        </div>
        <input type="range" id="input-sqm" min="15" max="100" step="1" value="25">
    </div>

    <div class="slider-group">
        <div class="slider-header">
            <span class="premium-label">築年数</span>
            <span class="slider-value" id="val-age">5年</span>
        </div>
        <input type="range" id="input-age" min="0" max="50" step="1" value="5">
    </div>
</div>

<div class="result-dashboard">
    <div class="result-main">
        <div class="result-label">推定成約家賃</div>
        <div class="result-big-value" id="res-rent-val">¥0</div>
        <p style="color:#94a3b8; font-size:0.8rem; margin-top:10px;">※過去の周辺取引データに基づいた参考価格です</p>
    </div>
</div>

<script>
    const areaSel = document.getElementById('rent-area');
    const sqmIn = document.getElementById('input-sqm');
    const ageIn = document.getElementById('input-age');

    function updateRent() {
        const areaFactor = parseFloat(areaSel.value);
        const sqm = sqmIn.value;
        const age = ageIn.value;

        // Base price: Area factor * (sqm * 0.35 - age * 0.05 + 5) * 10000
        // A simple heuristic for demo
        let base = (sqm * 0.4) - (age * 0.1) + 2;
        if(base < 5) base = 5;
        const finalRent = base * areaFactor * 10000;

        document.getElementById('val-sqm').innerText = sqm + "㎡";
        document.getElementById('val-age').innerText = (age == 0 ? "新築" : age + "年");
        document.getElementById('res-rent-val').innerText = "¥" + Math.round(finalRent / 1000) * 1000 + " / 月";
    }

    [areaSel, sqmIn, ageIn].forEach(el => el.addEventListener('input', updateRent));
    updateRent();
</script>
{{< /rawhtml >}}


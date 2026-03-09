---
title: "不動産利回り計算機"
date: 2026-03-09T00:00:00+09:00
draft: false
layout: "tool"
---

{{< rawhtml >}}
<div class="premium-card">
<div class="input-wrapper">
    <span class="premium-label">物件価格</span>
    <input type="number" id="yield-price" value="5000" placeholder="5000">
    <span class="unit-tag">万円</span>
</div>

<div class="input-wrapper">
    <span class="premium-label">月額家賃収入</span>
    <input type="number" id="yield-rent" value="20" placeholder="20">
    <span class="unit-tag">万円</span>
</div>

<div class="input-wrapper">
    <span class="premium-label">年間諸経費（管理費・固定資産税等）</span>
    <input type="number" id="yield-exp" value="60" placeholder="60">
    <span class="unit-tag">万円</span>
</div>
</div>

<div class="result-dashboard">
<div class="result-main">
    <div class="result-label">実質利回り (Net Yield)</div>
    <div class="result-big-value" id="res-net-yield">0.00%</div>
    <div class="result-grid">
        <div>
            <div class="result-sub-label">表面利回り</div>
            <div class="result-sub-value" id="res-gross-yield">0.00%</div>
        </div>
        <div>
            <div class="result-sub-label">年間純収益</div>
            <div class="result-sub-value" id="res-net-income">¥0</div>
        </div>
    </div>
</div>
</div>

<script>
const priceIn = document.getElementById('yield-price');
const rentIn = document.getElementById('yield-rent');
const expIn = document.getElementById('yield-exp');

function updateYield() {
    const price = priceIn.value * 10000;
    const annualRent = rentIn.value * 12 * 10000;
    const annualExp = expIn.value * 10000;

    const gross = (annualRent / price) * 100;
    const net = ((annualRent - annualExp) / price) * 100;

    document.getElementById('res-gross-yield').innerText = gross.toFixed(2) + "%";
    document.getElementById('res-net-yield').innerText = net.toFixed(2) + "%";
    document.getElementById('res-net-income').innerText = "¥" + Math.round(annualRent - annualExp).toLocaleString();
}

[priceIn, rentIn, expIn].forEach(el => el.addEventListener('input', updateYield));
updateYield();
</script>
{{< /rawhtml >}}


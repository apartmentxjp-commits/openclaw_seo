---
title: "住宅ローンシミュレーター"
date: 2026-03-09T00:00:00+09:00
draft: false
layout: "tool"
---

<div class="premium-card">
    <div class="slider-group">
        <div class="slider-header">
            <span class="premium-label">借入希望金額</span>
            <span class="slider-value" id="val-amount">5,000万円</span>
        </div>
        <input type="range" id="input-amount" min="100" max="20000" step="100" value="5000">
    </div>

    <div class="slider-group">
        <div class="slider-header">
            <span class="premium-label">借入期間</span>
            <span class="slider-value" id="val-years">35年</span>
        </div>
        <input type="range" id="input-years" min="1" max="40" step="1" value="35">
    </div>

    <div class="slider-group">
        <div class="slider-header">
            <span class="premium-label">金利（年利）</span>
            <span class="slider-value" id="val-rate">0.5%</span>
        </div>
        <input type="range" id="input-rate" min="0.1" max="5.0" step="0.05" value="0.5">
    </div>
</div>

<div class="result-dashboard">
    <div class="result-main">
        <div class="result-label">概算月返済額</div>
        <div class="result-big-value" id="res-monthly">¥0</div>
        <div class="result-grid">
            <div>
                <div class="result-sub-label">総返済額</div>
                <div class="result-sub-value" id="res-total">¥0</div>
            </div>
            <div>
                <div class="result-sub-label">利息合計</div>
                <div class="result-sub-value" id="res-interest">¥0</div>
            </div>
        </div>
    </div>
</div>

<script>
    const amountInput = document.getElementById('input-amount');
    const yearsInput = document.getElementById('input-years');
    const rateInput = document.getElementById('input-rate');

    function updateLoan() {
        const principal = amountInput.value * 10000;
        const years = yearsInput.value;
        const rate = rateInput.value / 100 / 12;
        const payments = years * 12;

        document.getElementById('val-amount').innerText = (amountInput.value / 100).toFixed(1) + "億円";
        if(amountInput.value < 10000) document.getElementById('val-amount').innerText = amountInput.value + "万円";
        
        document.getElementById('val-years').innerText = years + "年";
        document.getElementById('val-rate').innerText = rateInput.value + "%";

        const x = Math.pow(1 + rate, payments);
        const monthly = (principal * x * rate) / (x - 1);
        const total = monthly * payments;

        document.getElementById('res-monthly').innerText = "¥" + Math.round(monthly).toLocaleString();
        document.getElementById('res-total').innerText = "¥" + Math.round(total).toLocaleString();
        document.getElementById('res-interest').innerText = "¥" + Math.round(total - principal).toLocaleString();
    }

    [amountInput, yearsInput, rateInput].forEach(el => el.addEventListener('input', updateLoan));
    updateLoan();
</script>

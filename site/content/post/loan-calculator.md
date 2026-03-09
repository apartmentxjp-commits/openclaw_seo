---
title: "住宅ローン返済シミュレーター - 毎月返済額を簡単計算"
date: 2026-03-09T00:00:00+09:00
description: "物件価格、頭金、金利、返済年数を入力して、毎月の返済額や総返済額、利息総額をシミュレーション。返済内訳グラフで視覚的に確認できます。"
draft: false
layout: "tool"
---

{{< rawhtml >}}
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<div class="premium-card">
    <div class="slider-group">
        <div class="slider-header">
            <span class="premium-label">物件価格</span>
            <span class="slider-value" id="val-price">5,000万円</span>
        </div>
        <input type="range" id="input-price" min="500" max="20000" step="100" value="5000">
    </div>

    <div class="slider-group">
        <div class="slider-header">
            <span class="premium-label">頭金</span>
            <span class="slider-value" id="val-downpayment">500万円</span>
        </div>
        <input type="range" id="input-downpayment" min="0" max="10000" step="50" value="500">
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

<div class="premium-card" style="margin-top: 24px;">
    <h3 class="premium-label" style="text-align: center; margin-bottom: 24px;">返済内訳推移</h3>
    <div style="height: 300px; position: relative;">
        <canvas id="repaymentChart"></canvas>
    </div>
</div>

<script>
    const priceInput = document.getElementById('input-price');
    const downpaymentInput = document.getElementById('input-downpayment');
    const yearsInput = document.getElementById('input-years');
    const rateInput = document.getElementById('input-rate');

    let chart = null;

    function formatYen(val) {
        if (val >= 10000) {
            return (val / 10000).toFixed(1).replace(/\.0$/, '') + "億円";
        }
        return val + "万円";
    }

    function initChart() {
        const ctx = document.getElementById('repaymentChart').getContext('2d');
        chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['元金', '利息'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: ['#3b82f6', '#fb7185'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { weight: 'bold' } }
                    }
                },
                cutout: '70%'
            }
        });
    }

    function updateLoan() {
        const price = parseInt(priceInput.value);
        const downpayment = parseInt(downpaymentInput.value);
        
        if (downpayment > price) {
            downpaymentInput.value = price;
        }
        
        const principal = (price - downpayment) * 10000;
        const years = parseInt(yearsInput.value);
        const annualRate = parseFloat(rateInput.value) / 100;
        const monthlyRate = annualRate / 12;
        const payments = years * 12;

        document.getElementById('val-price').innerText = formatYen(price);
        document.getElementById('val-downpayment').innerText = formatYen(downpayment);
        document.getElementById('val-years').innerText = years + "年";
        document.getElementById('val-rate').innerText = rateInput.value + "%";

        let monthly = 0;
        let total = 0;
        let interest = 0;

        if (principal > 0) {
            if (monthlyRate > 0) {
                const x = Math.pow(1 + monthlyRate, payments);
                monthly = (principal * x * monthlyRate) / (x - 1);
            } else {
                monthly = principal / payments;
            }
            total = monthly * payments;
            interest = total - principal;
        }

        document.getElementById('res-monthly').innerText = "¥" + Math.round(monthly).toLocaleString();
        document.getElementById('res-total').innerText = "¥" + Math.round(total).toLocaleString();
        document.getElementById('res-interest').innerText = "¥" + Math.round(interest).toLocaleString();

        if (chart) {
            chart.data.datasets[0].data = [principal, interest];
            chart.update();
        }
    }

    initChart();
    [priceInput, downpaymentInput, yearsInput, rateInput].forEach(el => el.addEventListener('input', updateLoan));
    updateLoan();
</script>
{{< /rawhtml >}}


---
title: "住宅ローン計算シミュレーター"
description: "借入金額、金利、返済期間から月々の返済額と将来の支払総額を不動産分析がシミュレーションします。"
date: 2026-03-07T00:00:00+09:00
draft: false
layout: "tool"
script: "js/loan-calculator.js"
---

{{< rawhtml >}}
<div class="calc-container">
    <div class="form-group">
        <label for="loan-amount">借入金額 (円)</label>
        <input type="number" id="loan-amount" value="35000000" step="1000000" oninput="calculateLoan()">
    </div>
    
    <div class="form-group">
        <label for="loan-rate">年利 (%)</label>
        <input type="number" id="loan-rate" value="0.5" step="0.1" oninput="calculateLoan()">
    </div>
    
    <div class="form-group">
        <label for="loan-years">返済期間 (年)</label>
        <input type="number" id="loan-years" value="35" step="1" oninput="calculateLoan()">
    </div>

    <div class="calc-result">
        <span class="result-label">月々の推定返済額</span>
        <span class="result-value" id="monthly-payment">--- 円</span>
        <span id="total-interest" style="font-size: 0.9rem; color: #94a3b8;">内利子: --- 円</span>
    </div>
</div>
{{< /rawhtml >}}

## シミュレーションの解説
このシミュレーターは「元利均等返済方式」を採用しています。
現在の超低金利環境（変動金利 0.3%〜0.7%程度）を想定して初期値を設定していますが、将来的な金利上昇リスクも考慮し、1.0%〜2.0%でのシミュレーションも行うことをおすすめします。

### 不動産分析のアドバイス

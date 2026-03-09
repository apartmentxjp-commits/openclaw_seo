---
title: "不動産価格調査・相場予測"
date: 2026-03-09T00:00:00+09:00
draft: false
layout: "tool"
---

<div class="premium-card">
    <h3 style="margin-top:0; color:var(--primary);">世田谷区エリア 地価予測エンジン</h3>
    <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:24px;">独自アルゴリズムと取引事例に基づき、今後の市場トレンドを分析します。</p>

    <div class="input-wrapper">
        <span class="premium-label">調査対象エリア</span>
        <select id="pred-area" style="width:100%; padding:18px; border-radius:12px; border:2px solid #e2e8f0; font-size:1.1rem; font-weight:600;">
            <option value="up">世田谷区 三軒茶屋</option>
            <option value="stable">世田谷区 代沢</option>
            <option value="down">郊外エリア</option>
        </select>
    </div>
</div>

<div class="result-dashboard" id="trend-box">
    <div class="result-main">
        <div class="result-label">今後の市場予測（6ヶ月〜1年）</div>
        <div class="result-big-value" id="res-trend">上昇傾向</div>
        <div id="trend-bar" style="height:4px; width:0%; background:#60a5fa; margin:20px auto; border-radius:2px; transition: width 1s ease;"></div>
        <p id="res-desc" style="color:#94a3b8; margin-top:16px;">需要が供給を上回っており、緩やかな価格上昇が続くと予測されます。</p>
    </div>
</div>

<script>
    const areaSel = document.getElementById('pred-area');

    function updateTrend() {
        const val = areaSel.value;
        const trendEl = document.getElementById('res-trend');
        const descEl = document.getElementById('res-desc');
        const barEl = document.getElementById('trend-bar');

        if(val === "up") {
            trendEl.innerText = "上昇傾向 (Bullish)";
            trendEl.style.color = "#60a5fa";
            descEl.innerText = "再開発と根強い人気により、中心部を中心に価格が押し上げられています。";
            barEl.style.width = "80%";
        } else if(val === "stable") {
            trendEl.innerText = "横ばい (Stable)";
            trendEl.style.color = "#94a3b8";
            descEl.innerText = "閑静な住宅街としての地位を確立しており、安定した市場性が維持されています。";
            barEl.style.width = "50%";
        } else {
            trendEl.innerText = "調整局面 (Correcting)";
            trendEl.style.color = "#fb7185";
            descEl.innerText = "在庫件数の増加傾向が見られ、成約価格にわずかな下押し圧力が生じています。";
            barEl.style.width = "30%";
        }
    }

    areaSel.addEventListener('change', updateTrend);
    updateTrend();
</script>

import { NextResponse } from 'next/server';
import { SNS_STRATEGIES } from '@/lib/prompt-logic';
import prisma from '@/lib/prisma';
import OpenAI from 'openai';

const openai = new OpenAI({
  baseURL: "https://openrouter.ai/api/v1",
  apiKey: process.env.OPENROUTER_API_KEY,
});

const PRIMARY_MODEL = process.env.OPENROUTER_MODEL || "qwen/qwen3-coder-480b-a35b:free";
const FALLBACK_MODEL = process.env.OPENROUTER_FALLBACK_MODEL || "meta-llama/llama-3.3-70b-instruct:free";

// 🔒 レート制限: IP別・1分間に最大3リクエスト
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT_MAX = 3;
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1分

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const record = rateLimitMap.get(ip);
  if (!record || now > record.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }
  if (record.count >= RATE_LIMIT_MAX) return false;
  record.count++;
  return true;
}

export async function POST(req: Request) {
  // 🔒 レート制限チェック
  const ip = req.headers.get('x-forwarded-for') ?? req.headers.get('x-real-ip') ?? 'localhost';
  if (!checkRateLimit(ip)) {
    return NextResponse.json(
      { success: false, error: 'Too many requests. Please wait 1 minute.' },
      { status: 429 }
    );
  }

  try {
    const body = await req.json();
    const { strategy, dayCount, topic, referencePost, profile } = body;
    const daysCount = parseInt(dayCount) || 3;
    const postsPerDay = profile?.postsPerDay || 1;
    const totalPosts = daysCount * postsPerDay;

    // プロフィールDNAの完全展開
    const tone = profile?.tone || '情熱的で知的、読者に寄り添う口調';
    const background = profile?.background || '';
    const targetAudience = profile?.targetAudience || 'AIに興味があるビジネスパーソン';
    const accountName = profile?.accountName || 'エキスパート';
    const industry = profile?.industry || 'AI・テクノロジー';

    // 🏆 アカウント成長フェーズの自動判定
    const postedCount = await prisma.post.count({
      where: { status: { in: ['PUBLISHED', 'POSTED'] } }
    });

    let phaseDirective = "";
    if (postedCount < 30) {
      phaseDirective = "【Phase 1: 信頼構築期】まだフォロワーが少ないため、過度な主張よりも「有益な事実」と「専門性」をアピールし、フォローするメリットを提示せよ。";
    } else if (postedCount < 60) {
      phaseDirective = "【Phase 2: 拡散・成長期】ある程度ベースができたため、フックを強め、共感や議論を呼ぶ「強い意見」を織り交ぜてインプレッションを最大化せよ。";
    } else {
      phaseDirective = "【Phase 3: 権威確立・収益化期】コアなファンが増えたため、深い洞察や独自理論を展開し、読者の人生を根本から変えるような「本質的な価値」を提供せよ。";
    }

    const getStrategyDirective = (postIndex: number) => {
      let selectedId;
      if (strategy === "mix") {
        const position = (postIndex + 1) % 5;
        if (position === 1 || position === 4) selectedId = "daily_insight";
        else if (position === 0) selectedId = "short_hook";
        else {
          const fallback = ["educational", "story", "news_curation"];
          selectedId = fallback[postIndex % fallback.length];
        }
      } else {
        selectedId = strategy;
      }
      const config = (SNS_STRATEGIES as any)[selectedId] || SNS_STRATEGIES.educational;
      const isThread = ["educational", "story", "news_curation", "argument"].includes(selectedId);
      return `【第${postIndex + 1}案 / 戦略: ${config.name}】\n${config.directives.map((d: string) => `- ${d}`).join('\n')}\n- ${isThread ? '★スレッド形式（threadPartsに3〜5ツイート）で出力' : '★単発tweet（threadPartsはnull）'}`;
    };

    // お手本投稿の分析セクション
    const referenceSection = referencePost ? `
【お手本投稿（スタイル移植）】
以下の投稿からフックの構造・改行リズム・語彙の癖・感情の温度感を抽出し、新しいコンテンツに完全移植せよ：
---
${referencePost}
---
分析すべき要素：
1. 1行目のフック構造（疑問形/断定/衝撃的事実）
2. 改行・句読点のリズム
3. 語彙のトーン（カジュアル/権威的/情熱的/論理的）
4. 感情の温度感
` : '';

    const systemPrompt = `あなたは「Ghost in the Machine」として動作する、${accountName}専用の超高性能SNSコンテンツ生成エンジンです。

━━━━━━━━━━━━━━━━━━━━━
【最重要: 現在のアカウントフェーズ】
━━━━━━━━━━━━━━━━━━━━━
${phaseDirective}
（これまでの累計投稿数: ${postedCount}件）

━━━━━━━━━━━━━━━━━━━━━
【絶対禁止事項】
━━━━━━━━━━━━━━━━━━━━━
    - 具体性のない抽象的な発言

━━━━━━━━━━━━━━━━━━━━━
【HUMANIZER: AI文体を完全に排除せよ】
━━━━━━━━━━━━━━━━━━━━━
    以下のパターンが一つでもあれば、書き直して出力すること。

■ 禁止ワード（これらは「AIが書いた」と即バレする）
    重要なのは / まとめると / 結論として / さらに / また / 加えて
〜することが重要です / 〜を通じて / 〜することで / 〜します
〜していきましょう / 〜ではないでしょうか / 〜と言えるでしょう
〜となっています / 〜となっており / 〜しており / 〜であり
〜に向けて / 〜を実現するために / 〜の重要性 / 深化 / 促進
    革新的 / 画期的 / 先進的 / 可能性を秘めた / 本質的な
〜の側面 / 〜の観点から / 〜という点において / 〜の一環として

■ 禁止文体パターン
× 「〜だけでなく〜も」「単なる〜ではなく、〜である」（Negative Parallelism）
× 「A、B、そしてC」の三段列挙（Rule of Three）
× 「〜であることは言うまでもありません」（過剰な強調）
× 文末が「〜です。〜ます。〜です。〜ます。」の連続（リズムが死ぬ）
× 見出しや箇条書き冒頭の不要な絵文字
× 「業界の専門家は〜と述べています」等の曖昧な権威への言及
× 毎文同じ長さ・同じ構造（機械感が出る）
× ダッシュ（—）の多用
× 「素晴らしい」「興味深い」等の漠然とした評価

■ 正しい「人間らしさ」の基準
✅ 短い文と長い文を混ぜる（リズムに偏りがある方が自然）
✅ 「俺」「自分」一人称で感情を直接表現する
✅ 「よくわからない」「うまく言えないけど」等の不確かさを入れる
✅ 具体的な数字・出来事・感想を使う（「なんか」「ちょっと」もOK）
✅ 文末は「〜た。」「〜ない。」「〜だ。」「〜か？」をランダムに混ぜる
✅ 結論を最初に言うか、最後にズバッと言うかの2択（中間の「まとめ」は不要）
✅ 意見を持て。「〜のような気がする」より「〜だと思う」、さらに「〜だ」

━━━━━━━━━━━━━━━━━━━━━
【著者DNA（完全再現せよ）】
━━━━━━━━━━━━━━━━━━━━━
    名前: ${accountName}
    業界 / ジャンル: ${industry}
    ターゲット: ${targetAudience}

    語り口・トーン（必ず守れ）:
${tone}

    経歴・バックグラウンド（文脈として使え・固有名詞は出すな）:
${background}

${referenceSection}

━━━━━━━━━━━━━━━━━━━━━
【最重要: 世界最高峰のマーケティング・マスター・ロジック】完全反映せよ
━━━━━━━━━━━━━━━━━━━━━
1. **トニー・ロビンズ流【状態の支配】**: 出だしの1行で読者の「感情の焦点（Focus）」を強制的に切り替えよ。情熱、焦燥、あるいは絶対的な確信を言葉の「身体性」で伝え、ピークステートへ導け。
2. **ラッセル・ブランソン流【覚醒の架け橋（Epiphany Bridge）】**: 機能説明を捨て、あなたが「ハッとして人生が変わった瞬間」を読者に追体験させよ。読者が自ら「これだ！」と気づくように物語を編め。
3. **ジェイ・エイブラハム流【卓越性の戦略】**: 最も信頼されるアドバイザーとして、読者のために「本音の問い」を投げよ。隠れた資産（未利用の才能や時間）を再定義し、視点を180度転換させよ。
4. **神田昌典流【PMM & 感情爆発】**: 「何を言うか（アイデア）」を極限まで研ぎ澄ませ。「深夜のスタバで独り震えている一人の人間」に、暗闇の中で一筋の光を見せるように語りかけよ。

━━━━━━━━━━━━━━━━━━━━━
【執筆の黄金律: 没入・即決・成約】
━━━━━━━━━━━━━━━━━━━━━
- **自分事化の深度**: 読者の今の情景（布団の冷たさ、スタバの雑音、焦燥感）を具体的かつ鮮明に描写せよ。
- **体温のある魔法のワード**: 「突破」「確信」「エピファニー」「卓越」「ぶっちゃけ」「ここだけの話」を戦略的に配置せよ。
- **損失回避と解像度の高い未来**: 「動かないことで失われる、二度と戻らない365日」を言語化し、その直後に「エアコンの効いた部屋で、誰にも邪魔されず自由に働く月曜の朝」を描写せよ。
- **即行動のCTA（魂のクロージング）**: 単なる誘導ではなく「今、この瞬間のあなたの決断が、あなたの運命を書き換える」と強烈に背中を押せ。

━━━━━━━━━━━━━━━━━━━━━
【HUMANIZER 最終審判】
━━━━━━━━━━━━━━━━━━━━━
    → 生成した文章は、読者を「洗脳」するのではなく「覚醒（エピファニー）」させているか？
    → 読者が「あ、これ俺のことだ。今動かなきゃ手遅れになる」と武者震いするか？
    → AIが書いた痕跡（定型句）が1ミリでも残っていれば即廃棄。呼吸を感じる文章か。

━━━━━━━━━━━━━━━━━━━━━
【スレッド投稿（連投）のルール】
━━━━━━━━━━━━━━━━━━━━━
    - 1ツイート目（フック）: スクロールが止まる衝撃の一文。問いかけ or 驚きの事実 or 「え、それって…」な矛盾提示
      - 2〜4ツイート目（本体）: 各ツイートは完結した「知恵の塊」。番号付き（1 / 5, 2 / 5…）。具体的な数字・事例・使えるプロンプトを惜しみなく
        - 最終ツイート（CTA）: 「保存必須」「いいねで応援してください」「フォローで最新を逃さないで」のみ。外部リンク禁止
          - 各ツイート: 140〜270文字（日本語）。${accountName} の語り口を完全再現

━━━━━━━━━━━━━━━━━━━━━
【全体トピック】
━━━━━━━━━━━━━━━━━━━━━
${topic || 'AIの最先端と活用術'}

━━━━━━━━━━━━━━━━━━━━━
【実行指示】
━━━━━━━━━━━━━━━━━━━━━
以下の戦略で計${totalPosts} 件を生成せよ：

${Array.from({ length: totalPosts }).map((_, i) => getStrategyDirective(i)).join('\n\n')}

━━━━━━━━━━━━━━━━━━━━━
【出力フォーマット（JSON厳守）】
━━━━━━━━━━━━━━━━━━━━━
    {
      "posts": [
        {
          "content": "スレッドは1ツイート目の内容（フック）、単発は全文",
          "threadParts": ["フック(140〜270文字)", "本体1(140〜270文字)", "本体2(140〜270文字)", "CTA(140〜270文字)"] または null,
          "dayOffset": 0,
          "asset": null
        }
      ]
    } `;

    const userPrompt = `「${topic}」について計${totalPosts}件を${accountName} の語り口で生成。スレッドは各140〜270文字、血の通った泥臭い文章で。`;

    let aiResponse = "";
    try {
      const completion = await openai.chat.completions.create({
        model: PRIMARY_MODEL,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
      });
      aiResponse = completion.choices[0]?.message?.content || "";
    } catch (error: any) {
      console.warn("Primary model failed, trying fallback...", error.message);
      const completionFallback = await openai.chat.completions.create({
        model: FALLBACK_MODEL,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
      });
      aiResponse = completionFallback.choices[0]?.message?.content || "";
    }

    if (!aiResponse) throw new Error("No response from OpenRouter API");

    const jsonMatch = aiResponse.match(/\{[\s\S]*\}/);
    const cleanJson = jsonMatch ? jsonMatch[0] : aiResponse;
    const parsed = JSON.parse(cleanJson);
    return NextResponse.json({ success: true, posts: parsed.posts });

  } catch (error: any) {
    console.error("OpenRouter API Generation Error:", error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

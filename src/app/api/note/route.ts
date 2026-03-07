import { NextResponse } from 'next/server';
import { GoogleGenerativeAI } from "@google/generative-ai";

const apiKey = process.env.GEMINI_API_KEY || '';
const genAI = new GoogleGenerativeAI(apiKey);

export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { topic, targetLength, articleType, profile } = body;
        const wordCount = targetLength === 'long' ? '8,000〜10,000' : '5,000〜7,000';

        if (!apiKey) return NextResponse.json({ success: false, error: "Gemini API key is not set" }, { status: 500 });

        // プロフィールDNAの完全展開
        const tone = profile?.tone || '読者に寄り添う、情熱的で誠実な口調';
        const background = profile?.background || '';
        const targetAudience = profile?.targetAudience || 'AIに興味があるビジネスパーソン';
        const accountName = profile?.accountName || 'エキスパート';
        const industry = profile?.industry || 'AI・テクノロジー';

        const model = genAI.getGenerativeModel({ model: "gemini-flash-latest" });

        const systemPrompt = `あなたは「Ghost in the Machine」として動作する、${accountName}専用のnote記事生成エンジンです。
読者が「お金を払ってでも読みたい」「このnoteで人生が変わった」「スクリーンショットして永久保存する」と感じる超高密度のnote記事を執筆せよ。

━━━━━━━━━━━━━━━━━━━━━
【絶対禁止事項】
━━━━━━━━━━━━━━━━━━━━━
- 「ミッドナイトテープ」「Midnight Tape」等の固有プロジェクト名の使用
- AIが書いた感のある無機質・汎用的な文体
- エビデンスなしの主張（すべての主張に数字・事例・理由を添える）
- 読者を置いてけぼりにする専門用語の羅列

━━━━━━━━━━━━━━━━━━━━━
【著者DNA（完全再現せよ）】
━━━━━━━━━━━━━━━━━━━━━
著者名: ${accountName}
業界/ジャンル: ${industry}
ターゲット読者: ${targetAudience}

語り口・トーン（記事全体を通じて完全再現せよ）:
${tone}

著者の経歴・バックグラウンド（信頼性の文脈として使え・固有名詞は出すな）:
${background}

━━━━━━━━━━━━━━━━━━━━━
【Empire Engine: 内部思考プロセス（執筆前に必ず実行）】
━━━━━━━━━━━━━━━━━━━━━
STEP 1: 当たり前の排除
  → 日本のnoteで既知の情報か？ YES → 即捨て、海外一次ソースの知見を探す

STEP 2: 脳科学的構成設計
  → 冒頭（ドーパミン）: スクロールが止まる驚き・「え、それって本当？」な事実
  → 問題提起（コルチゾール）: 「このままでは〇〇になる」危機感の演出
  → 本論（ドーパミン×オキシトシン）: 発見の喜び +「あなたも変われる」希望
  → ロードマップ（ドーパミン）: 具体的な行動 = 報酬の可視化
  → 締め（オキシトシン）: 読者への感謝と信頼の絆

STEP 3: 独自性の強制付与
  → 他のnote/ブログが言っていない切り口を1つ必ず入れる
  → 統計・論文・海外事例を根拠にする（信頼度を明記）
  → 新しいフレームワーク名やネーミングを捏造して提唱する

━━━━━━━━━━━━━━━━━━━━━
【記事の必須構成（${wordCount}文字）】
━━━━━━━━━━━━━━━━━━━━━

## 1. タイトル & リード（合計400〜700文字）
- タイトル: 「〇〇した結果」「99%が知らない」「日本初公開」等の衝撃フレーズ
- サブタイトル: 具体的な価値提示（数字・Before/After）
- リード文: 読者の痛点を3行で切り込み → この記事で何が変わるかを約束

## 2. 問題の深刻化（300〜500文字）
- 数字・データで「今の問題」の深刻さを証明
- 「なぜここまで誰も解決できていなかったのか」の根本原因を暴く

## 3. 本論（章立て: 各800〜1,500文字 × 3〜5章）
各章に必ず:
- 衝撃的な章タイトル（問い・逆説・数字）
- 世界の最新データ or 著者の実体験（信頼度明記）
- 他の記事が言っていない独自の切り口
- 読者が「これ使える！」と思うプロンプト or テンプレート

## 4. 実践ロードマップ（800〜1,500文字）
- 「今日から始められる」7〜10ステップ
- 各ステップに「実際のプロンプト」「コピペできるテンプレート」を添付
- チェックリスト形式で読者が即行動できる状態に

## 5. よくある失敗と回避策（500〜800文字）
- 著者自身の失敗談（信頼性をUP）
- 初心者が99%ハマる罠とその具体的な解決法

## 6. まとめとクロージング（300〜500文字）
- 記事のエッセンスを3行で総括
- 読者への感謝と「あなたならできる」の言葉
- 「今すぐ〇〇してください」の具体的なネクストアクション（外部リンクなし）

━━━━━━━━━━━━━━━━━━━━━
【品質基準】
━━━━━━━━━━━━━━━━━━━━━
- スマホで読まれることを前提: 1段落3〜5行、頻繁な見出し・箇条書き
- 「これを無料で公開していいのか？」と読者が感じるレベル
- 全文を通じて${accountName}の語り口を完全再現
- Markdown形式で出力（noteにそのまま貼り付けられる状態）

━━━━━━━━━━━━━━━━━━━━━
【トピック】: ${topic}
━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━
【出力フォーマット（JSON厳守）】
━━━━━━━━━━━━━━━━━━━━━
{
  "title": "記事の完全なタイトル",
  "subtitle": "サブタイトル（数字・Before/After含む）",
  "headerImagePrompt": "英語プロンプト（FLUX/Midjourney用。記事テーマを視覚化した、クリックしたくなるサムネイルイメージ）",
  "content": "Markdown形式の本文全体（${wordCount}文字）",
  "readingTime": 推定読了時間（分、数値のみ）,
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"]
}`;

        const result = await model.generateContent([
            systemPrompt,
            `「${topic}」について${wordCount}文字の超高密度note記事を${accountName}の語り口で執筆。全章に具体的な数字・事例・使えるプロンプトを必ず入れること。`
        ]);

        const aiResponse = result.response.text();
        if (!aiResponse) throw new Error("No response from Gemini API");

        const jsonMatch = aiResponse.match(/\{[\s\S]*\}/);
        const cleanJson = jsonMatch ? jsonMatch[0] : aiResponse;
        const parsed = JSON.parse(cleanJson);
        return NextResponse.json({ success: true, article: parsed });

    } catch (error: any) {
        console.error("Note Generation Error:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

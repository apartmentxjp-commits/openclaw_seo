import { NextResponse } from 'next/server';
import { processQueue } from '@/lib/posting-service';

/**
 * 外部のCronサービスやローカルスクリプトから叩かれる実行エンジン
 * 🔒 セキュリティ: CRON_SECRET ヘッダーまたはクエリパラメータで認証
 */
export async function GET(request: Request) {
    // シークレットキー認証
    const cronSecret = process.env.CRON_SECRET;
    if (cronSecret) {
        const url = new URL(request.url);
        const providedSecret =
            request.headers.get('x-cron-secret') ||
            url.searchParams.get('secret');

        if (providedSecret !== cronSecret) {
            return NextResponse.json(
                { success: false, error: 'Unauthorized' },
                { status: 401 }
            );
        }
    }

    try {
        const result = await processQueue();
        return NextResponse.json(result);
    } catch (error: any) {
        console.error("Cron API Error:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

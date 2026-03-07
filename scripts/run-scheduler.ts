/**
 * SNS Auto Poster - ローカル実行シミュレーター
 * あなたのPC上でこのスクリプトを動かし続けることで、予約された投稿を自動的に実行します。
 * 
 * 実行方法: 
 * cd sns_auto_poster
 * npx tsx scripts/run-scheduler.ts
 */

const INTERVAL_MS = 10 * 60 * 1000;

async function checkAndPublish() {
    const timestamp = new Date().toLocaleString();
    const ports = ['3000', '3001'];
    let success = false;

    for (const port of ports) {
        const url = `http://127.0.0.1:${port}/api/cron`;
        try {
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                console.log(`[${timestamp}] Connected to Port ${port}`);
                if (data.success) {
                    if (data.processedCount > 0) {
                        console.log(`✅ Success: Processed ${data.processedCount} posts.`);
                    } else {
                        console.log('😴 No posts scheduled for now.');
                    }
                } else {
                    console.error('❌ Error from API:', data.error);
                }
                success = true;
                break;
            }
        } catch (e) {
            // 次のポートを試す
        }
    }

    if (!success) {
        console.error(`[${timestamp}] ❌ Connection failed. Make sure "npm run dev" is running on port 3000 or 3001.`);
    }

    console.log(`Next check in ${INTERVAL_MS / 60000} minutes...\n`);
}

// 初回実行
checkAndPublish();

// ループ設定
setInterval(checkAndPublish, INTERVAL_MS);

console.log('=========================================');
console.log('  SNS Auto Poster Simulator Started');
console.log(`  Interval: ${INTERVAL_MS / 60000} minutes`);
console.log('  Press Ctrl+C to stop');
console.log('=========================================');

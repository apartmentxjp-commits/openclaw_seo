import prisma from './prisma';
import { sendDiscordDraft, sendTelegramDraft } from './notifications';

export async function processQueue() {
    console.log('--- Processing Posting Queue (Manual Pivot Mode) ---');

    const now = new Date();
    // 取得条件: 予約中で予定時刻を過ぎたもの or 失敗したもの
    const postsToPublish = await prisma.post.findMany({
        where: {
            OR: [
                { status: 'SCHEDULED', scheduledAt: { lte: now } },
                { status: 'FAILED' }
            ]
        },
        orderBy: { scheduledAt: 'asc' }
    });

    if (postsToPublish.length === 0) {
        console.log('No posts to process at this time.');
        return { success: true, processedCount: 0 };
    }

    let successCount = 0;
    let failedCount = 0;

    const profile = await prisma.profile.findFirst();

    for (const post of postsToPublish) {
        try {
            console.log(`🚀 Sending draft for post: ${post.id}`);

            let fullDraft = post.content;
            const threadParts: string[] | null = post.threadParts ? JSON.parse(post.threadParts) : null;

            if (threadParts && threadParts.length > 1) {
                fullDraft = threadParts.map((t, i) => `[${i + 1}/${threadParts.length}]\n${t}`).join('\n\n---\n\n');
            }

            if (fullDraft.length > 500) {
                await sendTelegramDraft(fullDraft, profile?.telegramBotToken, profile?.telegramChatId);
                console.log(`   📬 Sent to Telegram (Long-form/Tegami)`);
            } else {
                await sendDiscordDraft(fullDraft, profile?.discordWebhookUrl);
                console.log(`   📬 Sent to Discord (X Draft)`);
            }

            await prisma.post.update({
                where: { id: post.id },
                data: { status: 'PUBLISHED', retries: { increment: 1 } }
            });
            console.log(`✅ Successfully processed draft for post: ${post.id}`);
            successCount++;
        } catch (error: any) {
            console.error(`❌ Failed to process draft for post: ${post.id}`, error);
            await prisma.post.update({
                where: { id: post.id },
                data: {
                    status: 'FAILED',
                    retries: { increment: 1 },
                    lastError: error.message || String(error)
                }
            });
            failedCount++;
        }
    }

    return { success: true, processedCount: postsToPublish.length, successCount, failedCount };
}

export async function publishSinglePost(postId: string) {
    const post = await prisma.post.findUnique({ where: { id: postId } });
    if (!post) throw new Error('Post not found');

    const profile = await prisma.profile.findFirst();

    let fullDraft = post.content;
    const threadParts: string[] | null = post.threadParts ? JSON.parse(post.threadParts) : null;
    if (threadParts && threadParts.length > 1) {
        fullDraft = threadParts.map((t, i) => `[${i + 1}/${threadParts.length}]\n${t}`).join('\n\n---\n\n');
    }

    if (fullDraft.length > 500) {
        await sendTelegramDraft(fullDraft, profile?.telegramBotToken, profile?.telegramChatId);
    } else {
        await sendDiscordDraft(fullDraft, profile?.discordWebhookUrl);
    }

    await prisma.post.update({ where: { id: postId }, data: { status: 'PUBLISHED' } });
}

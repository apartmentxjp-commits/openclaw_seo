import axios from 'axios';

/**
 * Discord Webhook でツイート下書きを送信
 */
export async function sendDiscordDraft(content: string, webhookUrl?: string | null, mediaUrl?: string) {
    if (!webhookUrl) {
        console.warn('⚠️ Discord Webhook URL is not provided. Skipping Discord notification.');
        return;
    }

    const payload = {
        username: 'SNS Draft Assistant',
        content: `📝 **X (Twitter) 投稿下書き**\n\`\`\`\n${content}\n\`\`\``,
        embeds: mediaUrl ? [{
            image: { url: mediaUrl }
        }] : []
    };

    try {
        await axios.post(webhookUrl, payload);
    } catch (e: any) {
        console.error('❌ Failed to send Discord notification:', e.message || String(e));
    }
}

/**
 * Telegram Bot で長文（Tegami/Note用）下書きを送信
 */
export async function sendTelegramDraft(content: string, botToken?: string | null, chatId?: string | null) {
    if (!botToken || !chatId) {
        console.warn('⚠️ Telegram credentials are not complete. Skipping Telegram notification.');
        return;
    }

    const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
    const payload = {
        chat_id: chatId,
        text: `📑 **Note / Long-form Draft**\n\n${content}`,
    };

    try {
        await axios.post(url, payload);
    } catch (e: any) {
        console.error('❌ Failed to send Telegram notification:', e.message || String(e));
    }
}

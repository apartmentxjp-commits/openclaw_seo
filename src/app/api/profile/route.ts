import { NextResponse } from 'next/server';
import prisma from '@/lib/prisma';

// プロフィール情報の取得
export async function GET() {
    try {
        let profile = await prisma.profile.findFirst();

        // まだデータがない場合は初期値を返す（またはnull）
        if (!profile) {
            return NextResponse.json({ success: true, profile: null });
        }

        return NextResponse.json({ success: true, profile });
    } catch (error: any) {
        console.error("Profile GET Error:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

// プロフィール情報の保存（新規作成 or 更新）
export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { accountName, industry, targetAudience, tone, background, postsPerDay, discordWebhookUrl, telegramBotToken, telegramChatId } = body;

        // 既存のプロフィールを探す
        const existingProfile = await prisma.profile.findFirst();

        let profile;
        if (existingProfile) {
            // 更新
            profile = await prisma.profile.update({
                where: { id: existingProfile.id },
                data: {
                    accountName, industry, targetAudience, tone, background,
                    postsPerDay: parseInt(postsPerDay) || 1,
                    discordWebhookUrl, telegramBotToken, telegramChatId
                }
            });
        } else {
            // 新規作成
            profile = await prisma.profile.create({
                data: {
                    accountName, industry, targetAudience, tone, background,
                    postsPerDay: parseInt(postsPerDay) || 1,
                    discordWebhookUrl, telegramBotToken, telegramChatId
                }
            });
        }

        return NextResponse.json({ success: true, profile });
    } catch (error: any) {
        console.error("Profile POST Error:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

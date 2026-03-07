import { NextResponse } from 'next/server';
import prisma from '@/lib/prisma';

export async function GET() {
    try {
        const account = await prisma.snsAccount.findFirst({
            where: { platform: 'X' }
        });

        if (!account) {
            return NextResponse.json({ success: true, account: null });
        }

        // セキュリティのためトークンは返さず、基本情報のみ返す
        return NextResponse.json({
            success: true,
            account: {
                id: account.id,
                platform: account.platform,
                screenName: account.screenName,
                updatedAt: account.updatedAt
            }
        });
    } catch (error: any) {
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

export async function DELETE() {
    try {
        await prisma.snsAccount.deleteMany({
            where: { platform: 'X' }
        });
        return NextResponse.json({ success: true });
    } catch (error: any) {
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

import { NextResponse } from 'next/server';
import prisma from '@/lib/prisma';

export async function GET() {
    try {
        const accounts = await prisma.snsAccount.findMany({
            select: {
                id: true,
                platform: true,
                screenName: true,
                createdAt: true,
            }
        });
        return NextResponse.json({ success: true, accounts });
    } catch (error: any) {
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

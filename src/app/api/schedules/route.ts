import { NextResponse } from 'next/server';
import prisma from '@/lib/prisma';

// 投稿スケジュール一覧の取得
export async function GET() {
    try {
        const schedules = await prisma.postingSchedule.findMany({
            orderBy: { time: 'asc' }
        });
        return NextResponse.json({ success: true, schedules });
    } catch (error: any) {
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

// 投稿スケジュールの一括更新
export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { schedules } = body; // Array of { time: string, active: boolean }

        // 今回は既存のスケジュールをリセットして上書きする簡易的な実装にします
        await prisma.$transaction([
            prisma.postingSchedule.deleteMany(),
            prisma.postingSchedule.createMany({
                data: schedules.map((s: any) => ({
                    time: s.time,
                    active: s.active ?? true
                }))
            })
        ]);

        const updatedSchedules = await prisma.postingSchedule.findMany({
            orderBy: { time: 'asc' }
        });

        return NextResponse.json({ success: true, schedules: updatedSchedules });
    } catch (error: any) {
        console.error("Schedule POST Error:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

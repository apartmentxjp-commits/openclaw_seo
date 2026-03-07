import { NextResponse } from 'next/server';
import prisma from '@/lib/prisma';

// 投稿一覧の取得
export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const dateStr = searchParams.get('date'); // YYYY-MM-DD

        let where = {};
        if (dateStr) {
            const start = new Date(dateStr);
            start.setHours(0, 0, 0, 0);
            const end = new Date(dateStr);
            end.setHours(23, 59, 59, 999);
            where = {
                scheduledAt: {
                    gte: start,
                    lte: end,
                }
            };
        }

        const posts = await prisma.post.findMany({
            where,
            orderBy: { scheduledAt: 'asc' }
        });
        return NextResponse.json({ success: true, posts });
    } catch (error: any) {
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

// 投稿の保存（一括または単発）
export async function POST(req: Request) {
    try {
        const body = await req.json();

        if (body.isBatch && Array.isArray(body.posts)) {
            // 一括保存 (スケジュール割り当て済み)
            const createdPosts = await Promise.all(
                body.posts.map((post: any) => prisma.post.create({
                    data: {
                        content: post.content,
                        scheduledAt: post.scheduledAt ? new Date(post.scheduledAt) : null,
                        timeString: post.timeString,
                        autoLike: post.autoLike ?? false,
                        autoRepost: post.autoRepost ?? false,
                        asset: post.asset || null,
                        threadParts: post.threadParts ? JSON.stringify(post.threadParts) : null,
                        status: post.status || 'SCHEDULED'
                    }
                }))
            );
            return NextResponse.json({ success: true, count: createdPosts.length });
        } else {
            // 単発保存
            const { content, scheduledAt, timeString, status, autoLike, autoRepost, asset, threadParts } = body;
            const post = await prisma.post.create({
                data: {
                    content,
                    scheduledAt: scheduledAt ? new Date(scheduledAt) : null,
                    timeString,
                    autoLike: autoLike ?? false,
                    autoRepost: autoRepost ?? false,
                    asset: asset || null,
                    threadParts: threadParts ? JSON.stringify(threadParts) : null,
                    status: status || 'DRAFT'
                }
            });
            return NextResponse.json({ success: true, post });
        }
    } catch (error: any) {
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

// 投稿の削除
export async function DELETE(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const id = searchParams.get('id');

        if (!id) {
            return NextResponse.json({ success: false, error: "ID is required" }, { status: 400 });
        }

        await prisma.post.delete({
            where: { id }
        });

        return NextResponse.json({ success: true });
    } catch (error: any) {
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

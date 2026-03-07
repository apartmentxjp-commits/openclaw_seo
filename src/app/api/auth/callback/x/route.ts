import { NextResponse } from 'next/server';
import { twitterAuth } from '@/lib/twitter';
import prisma from '@/lib/prisma';
import { cookies } from 'next/headers';

export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const errorParam = searchParams.get('error');

        if (errorParam) {
            return new NextResponse(`X Auth Error: You denied the app or there was an issue. Details: ${errorParam}`, { status: 400 });
        }

        // クッキーから一時情報を取得
        const cookieStore = await cookies();
        const savedState = cookieStore.get('x_auth_state')?.value;
        const codeVerifier = cookieStore.get('x_auth_code_verifier')?.value;

        const fs = require('fs');
        const debugInfo = `
[${new Date().toISOString()}]
Code: ${code}
State: ${state}
SavedState: ${savedState}
CodeVerifier: ${codeVerifier}
All Cookies: ${JSON.stringify(cookieStore.getAll())}
=====\n`;
        fs.appendFileSync('debug.log', debugInfo);

        if (!code || !state || state !== savedState || !codeVerifier) {
            return new NextResponse(`
                <h1>Authentication Failed</h1>
                <p>Status: Invalid state or code verifier</p>
                <ul>
                    <li>Has code: ${!!code}</li>
                    <li>State match: ${state === savedState}</li>
                    <li>Has verifier: ${!!codeVerifier}</li>
                </ul>
                <a href="/profile">Return to Profile</a>
            `, { status: 400, headers: { 'Content-Type': 'text/html' } });
        }

        // アクセストークンの取得
        const { client: loggedClient, accessToken, refreshToken, expiresIn } = await twitterAuth.loginWithOAuth2({
            code,
            codeVerifier,
            redirectUri: process.env.X_CALLBACK_URL || 'http://localhost:3000/api/auth/callback/x',
        });

        // ユーザー情報の取得
        const { data: user } = await loggedClient.v2.me();

        // データベースに保存
        const expiresAt = new Date();
        expiresAt.setSeconds(expiresAt.getSeconds() + (expiresIn || 0));

        await prisma.snsAccount.upsert({
            where: { id: 'x-default' }, // 今回は単一アカウント運用を想定し、固定IDで管理（実運用ではユーザーIDに紐付け）
            update: {
                platform: "X",
                platformId: user.id,
                screenName: user.username,
                accessToken,
                refreshToken,
                expiresAt,
            },
            create: {
                id: 'x-default',
                platform: "X",
                platformId: user.id,
                screenName: user.username,
                accessToken,
                refreshToken,
                expiresAt,
            }
        });

        // 連携完了後はプロフィールページに戻る
        return NextResponse.redirect(new URL('/profile', req.url));
    } catch (error: any) {
        console.error("X Callback Error:", error);
        return new NextResponse(`
            <h1>Fatal Error in X Callback</h1>
            <pre>${error.message || String(error)}</pre>
            <a href="/profile">Return to Profile</a>
        `, { status: 500, headers: { 'Content-Type': 'text/html' } });
    }
}

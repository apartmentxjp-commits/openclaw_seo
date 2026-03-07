import { NextRequest, NextResponse } from 'next/server';
import { twitterAuth } from '@/lib/twitter';
import prisma from '@/lib/prisma';
import { cookies } from 'next/headers';

export async function GET(request: NextRequest) {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    const cookieStore = await cookies();
    const storedState = cookieStore.get('x_oauth_state')?.value;
    const codeVerifier = cookieStore.get('x_oauth_code_verifier')?.value;

    if (!code || !state || !storedState || !codeVerifier || state !== storedState) {
        return NextResponse.json({ error: 'Invalid state or missing code' }, { status: 400 });
    }

    try {
        const callbackUrl = process.env.X_CALLBACK_URL || 'http://localhost:3000/api/auth/x/callback';

        // トークンの取得
        const { client: loggedClient, accessToken, refreshToken, expiresIn } = await twitterAuth.loginWithOAuth2({
            code: code,
            codeVerifier: codeVerifier,
            redirectUri: callbackUrl
        });

        // ユーザー情報の取得
        const { data: userObject } = await loggedClient.v2.me();

        // データベースに保存 (Upsert)
        // 今回はとりあえず最初の1つを上書きするか、新規作成するロジック
        const expiresAt = expiresIn ? new Date(Date.now() + expiresIn * 1000) : null;

        await prisma.snsAccount.upsert({
            where: { id: userObject.id }, // platformIdをIDとして使いたいが、uuid()なので調整が必要か
            // 実際には platform と platformId の複合キーが理想だが、現在のschemaに合わせて作成
            update: {
                accessToken,
                refreshToken,
                expiresAt,
                screenName: userObject.username,
                updatedAt: new Date(),
            },
            create: {
                id: userObject.id, // IDとしてSNSのIDを流用（簡略化）
                platform: 'X',
                platformId: userObject.id,
                screenName: userObject.username,
                accessToken,
                refreshToken,
                expiresAt,
            },
        });

        // 認証用Cookieを削除
        cookieStore.delete('x_oauth_state');
        cookieStore.delete('x_oauth_code_verifier');

        // 連携完了画面へリダイレクト
        return NextResponse.redirect(new URL('/integrations?success=true', request.url));
    } catch (error: any) {
        console.error("X Callback Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}

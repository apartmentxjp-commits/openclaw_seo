import { NextResponse } from 'next/server';
import { twitterAuth } from '@/lib/twitter';
import { cookies } from 'next/headers';

export async function GET() {
    try {
        // OAuth2.0 PKCE 認証用URLの生成
        const { url, codeVerifier, state } = twitterAuth.generateOAuth2AuthLink(
            process.env.X_CALLBACK_URL || 'http://localhost:3000/api/auth/callback/x',
            { scope: ['tweet.read', 'tweet.write', 'users.read', 'offline.access'] }
        );

        const cookieStore = await cookies();
        cookieStore.set('x_auth_state', state, { httpOnly: true, maxAge: 600, path: '/' });
        cookieStore.set('x_auth_code_verifier', codeVerifier, { httpOnly: true, maxAge: 600, path: '/' });

        return NextResponse.redirect(url);
    } catch (error: any) {
        console.error("X Auth Error:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }
}

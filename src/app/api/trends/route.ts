import { NextResponse } from 'next/server';

/**
 * Yahoo Japanニュース + NHKニュースRSSからホットトピックを取得
 * APIキー不要・完全無料
 */
export async function GET() {
    try {
        // Yahoo Japan 主要ニュースRSS (200 OK確認済み)
        const [yahooRes, nhkRes] = await Promise.allSettled([
            fetch('https://news.yahoo.co.jp/rss/topics/top-picks.xml', {
                headers: { 'User-Agent': 'Mozilla/5.0' },
                next: { revalidate: 1800 } // 30分キャッシュ
            }),
            fetch('https://www3.nhk.or.jp/rss/news/cat0.xml', {
                headers: { 'User-Agent': 'Mozilla/5.0' },
                next: { revalidate: 1800 }
            })
        ]);

        const keywords: { keyword: string; traffic: string; source: string }[] = [];

        // Yahoo ニュースから抽出
        if (yahooRes.status === 'fulfilled' && yahooRes.value.ok) {
            const xml = await yahooRes.value.text();
            const titles = xml.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>/g) ||
                xml.match(/<title>(.*?)<\/title>/g) || [];

            titles.slice(1, 12).forEach(t => {
                const keyword = t
                    .replace(/<title><!\[CDATA\[/, '').replace(/\]\]><\/title>/, '')
                    .replace(/<title>/, '').replace(/<\/title>/, '')
                    .trim();
                if (keyword && keyword.length > 2 && keyword.length < 40) {
                    keywords.push({ keyword, traffic: '', source: 'Yahoo Japan' });
                }
            });
        }

        // NHKニュースから抽出
        if (nhkRes.status === 'fulfilled' && nhkRes.value.ok) {
            const xml = await nhkRes.value.text();
            const titles = xml.match(/<title>(.*?)<\/title>/g) || [];

            titles.slice(1, 8).forEach(t => {
                const keyword = t
                    .replace(/<title>/, '').replace(/<\/title>/, '')
                    .trim();
                if (keyword && keyword.length > 2 && keyword.length < 40) {
                    // 重複除去
                    if (!keywords.some(k => k.keyword === keyword)) {
                        keywords.push({ keyword, traffic: '', source: 'NHK' });
                    }
                }
            });
        }

        if (keywords.length === 0) {
            throw new Error('ニュースの取得に失敗しました');
        }

        return NextResponse.json({
            success: true,
            trends: keywords.slice(0, 15),
            fetchedAt: new Date().toISOString()
        });
    } catch (error: any) {
        console.error('Trends fetch error:', error);
        return NextResponse.json(
            { success: false, error: error.message },
            { status: 500 }
        );
    }
}

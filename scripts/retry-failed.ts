import { PrismaClient } from '@prisma/client'
import { publishSinglePost } from '../src/lib/posting-service'

const prisma = new PrismaClient()

async function main() {
    const posts = await prisma.post.findMany({
        where: { status: 'FAILED' },
        orderBy: { updatedAt: 'desc' },
        take: 1
    })

    if (posts.length > 0) {
        const failedPost = posts[0];
        console.log(`Retrying Post ID: ${failedPost.id}`)

        try {
            await publishSinglePost(failedPost.id);
            console.log(`✅ Passed! Post published successfully.`)
        } catch (e: any) {
            console.error(`❌ Still failing: ${e.message}`)
            console.error(JSON.stringify(e?.data || e, null, 2))
        }
    } else {
        console.log("No failed posts found.")
    }
}

main().finally(() => prisma.$disconnect())

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    const posts = await prisma.post.findMany({
        where: { status: 'FAILED' },
        orderBy: { updatedAt: 'desc' },
        take: 1
    })

    if (posts.length > 0) {
        console.log(`Failed Post ID: ${posts[0].id}`)
        console.log(`Error Message: ${posts[0].lastError}`)
    } else {
        console.log("No failed posts found.")
    }
}

main().finally(() => prisma.$disconnect())

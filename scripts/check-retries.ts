import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    const posts = await prisma.post.findMany()

    console.log(`Total Posts in DB: ${posts.length}`)
    for (const post of posts) {
        console.log(`[${post.id}] Status: ${post.status}, Retries: ${post.retries}`)
    }
}

main().finally(() => prisma.$disconnect())

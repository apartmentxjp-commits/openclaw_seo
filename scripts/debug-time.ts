import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    const posts = await prisma.post.findMany({
        where: { status: 'SCHEDULED' },
        orderBy: { scheduledAt: 'asc' }
    })

    const now = new Date();

    console.log("Current Time (ISO):", now.toISOString())
    console.log("Current Time (Local):", now.toString())

    for (const post of posts) {
        const isPast = post.scheduledAt && post.scheduledAt <= now;
        console.log(`[${post.id}] Time: ${post.scheduledAt?.toISOString()} | Local: ${post.scheduledAt?.toString()} | Ready to post? ${isPast}`)
    }
}

main().finally(() => prisma.$disconnect())

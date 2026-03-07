import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    const posts = await prisma.post.findMany({
        where: { status: 'SCHEDULED' },
        orderBy: { scheduledAt: 'asc' }
    })

    console.log(`Found ${posts.length} scheduled posts.`)

    for (const post of posts) {
        console.log(`[${post.id}] Scheduled for: ${post.scheduledAt}`)

        // The user requested to change the time to "9시/9時" (probably 9:00 AM)
        // Let's set it to today at 09:00:00 JST
        const newTime = new Date()
        newTime.setHours(9, 0, 0, 0)

        // Since it's currently around 08:36 JST, setting it to 09:00 will make it in the future.
        // Wait, if we want to trigger it *now*, we should set it to past or run it now.
        // Let's just set it to 09:00 as requested. Wait, if it's set to 9:00, it won't trigger until 9:00.

        await prisma.post.update({
            where: { id: post.id },
            data: { scheduledAt: newTime }
        })
        console.log(`-> Updated to: ${newTime}`)
    }
}

main()
    .catch((e) => {
        console.error(e)
        process.exit(1)
    })
    .finally(async () => {
        await prisma.$disconnect()
    })

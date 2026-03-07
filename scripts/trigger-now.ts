import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    const current = new Date();
    const pastTime = new Date(current.getTime() - 60000); // 1 minute in the past

    await prisma.post.update({
        where: { id: '275c6b7a-01cf-4726-b041-50a6a11a9cfe' },
        data: { scheduledAt: pastTime }
    })

    console.log(`Set post 275c6b7a-01cf-4726-b041-50a6a11a9cfe to ${pastTime.toISOString()} so it fires immediately.`)
}

main().finally(() => prisma.$disconnect())

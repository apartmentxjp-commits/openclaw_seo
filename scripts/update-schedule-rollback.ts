import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    const posts = await prisma.post.findMany({
        where: { status: 'SCHEDULED' },
        orderBy: { createdAt: 'asc' } // Or however we can identify the original order
    })

    console.log(`Found ${posts.length} scheduled posts.`)

    // The original schedule was:
    // Post 1: Tue Mar 03 2026 08:00
    // Post 2: Wed Mar 04 2026 20:00
    // Post 3: Thu Mar 05 2026 08:00
    // Post 4: Fri Mar 06 2026 20:00
    // Post 5: Sat Mar 07 2026 08:00
    // Post 6: Sun Mar 08 2026 20:00

    // Actually, we can just sort by id or createdAt, since they were created sequentially.
    // Wait, I can see the IDs from the previous log!

    const idMappings = [
        { id: '275c6b7a-01cf-4726-b041-50a6a11a9cfe', time: new Date('2026-03-04T09:00:00+09:00') }, // Keep at 9:00 for today (Originally Mar 03 08:00)
        { id: '8eafc9bd-0436-4b1e-9c66-009cb1421e7b', time: new Date('2026-03-04T20:00:00+09:00') },
        { id: '392f3135-c2cf-4810-981c-8c6921620662', time: new Date('2026-03-05T08:00:00+09:00') },
        { id: '2b55ee40-7d07-4570-a973-38b2312cddac', time: new Date('2026-03-06T20:00:00+09:00') },
        { id: 'dc57874a-3229-4aa6-8775-d0a528e273db', time: new Date('2026-03-07T08:00:00+09:00') },
        { id: '2723b89c-c936-4c14-a865-a7b238833751', time: new Date('2026-03-08T20:00:00+09:00') },
    ]

    for (const mapping of idMappings) {
        await prisma.post.update({
            where: { id: mapping.id },
            data: { scheduledAt: mapping.time }
        })
        console.log(`Restored [${mapping.id}] to ${mapping.time}`)
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

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    await prisma.snsAccount.deleteMany({
        where: { platform: 'X' },
    })

    console.log("Cleared X account from DB. Please re-authenticate in the web UI.")
}

main().finally(() => prisma.$disconnect())

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
    const account = await prisma.snsAccount.findFirst({
        where: { platform: 'X' },
    })

    if (account) {
        console.log(`Platform ID: ${account.platformId}`)
        console.log(`Username: ${account.username}`)
        console.log(`Has Access Token? ${!!account.accessToken}`)
        console.log(`Has Refresh Token? ${!!account.refreshToken}`)
    } else {
        console.log("No X account found!")
    }
}

main().finally(() => prisma.$disconnect())

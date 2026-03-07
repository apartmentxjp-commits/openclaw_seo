import { PrismaClient } from '@prisma/client'

const prismaClientSingleton = () => {
    // Prisma 7 では URL 等の構成を別途管理できますが、
    // ここでは標準的なインスタンス生成を試みます
    return new PrismaClient()
}

declare const globalThis: {
    prismaGlobal: ReturnType<typeof prismaClientSingleton>;
} & typeof global;

const prisma = globalThis.prismaGlobal ?? prismaClientSingleton()

export default prisma

if (process.env.NODE_ENV !== 'production') globalThis.prismaGlobal = prisma

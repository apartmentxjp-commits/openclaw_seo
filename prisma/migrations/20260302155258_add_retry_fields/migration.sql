-- CreateTable
CREATE TABLE "Profile" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "accountName" TEXT,
    "industry" TEXT,
    "targetAudience" TEXT,
    "tone" TEXT,
    "background" TEXT,
    "postsPerDay" INTEGER NOT NULL DEFAULT 1,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "Post" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "content" TEXT NOT NULL,
    "dayOffset" INTEGER,
    "scheduledAt" DATETIME,
    "timeString" TEXT,
    "autoLike" BOOLEAN NOT NULL DEFAULT false,
    "autoRepost" BOOLEAN NOT NULL DEFAULT false,
    "asset" TEXT,
    "status" TEXT NOT NULL DEFAULT 'DRAFT',
    "retries" INTEGER NOT NULL DEFAULT 0,
    "lastError" TEXT,
    "threadParts" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "SnsAccount" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "platform" TEXT NOT NULL,
    "platformId" TEXT,
    "screenName" TEXT,
    "accessToken" TEXT NOT NULL,
    "refreshToken" TEXT,
    "expiresAt" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "PostingSchedule" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "time" TEXT NOT NULL,
    "active" BOOLEAN NOT NULL DEFAULT true,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

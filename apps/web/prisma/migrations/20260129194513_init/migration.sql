-- CreateEnum
CREATE TYPE "EditorStatus" AS ENUM ('DRAFT', 'REVIEWED', 'PUBLISHED');

-- CreateEnum
CREATE TYPE "InjuryStatus" AS ENUM ('OUT', 'DOUBTFUL', 'QUESTIONABLE', 'PROBABLE');

-- CreateEnum
CREATE TYPE "InjuryImpact" AS ENUM ('STAR', 'ROTATION', 'MINOR');

-- CreateTable
CREATE TABLE "Sport" (
    "id" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Sport_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Team" (
    "id" TEXT NOT NULL,
    "sportId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "abbr" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Team_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Game" (
    "id" TEXT NOT NULL,
    "sportId" TEXT NOT NULL,
    "date" TIMESTAMP(3) NOT NULL,
    "slug" TEXT NOT NULL,
    "homeTeamId" TEXT NOT NULL,
    "awayTeamId" TEXT NOT NULL,
    "startTime" TIMESTAMP(3),
    "venue" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Game_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "MarketSnapshot" (
    "id" TEXT NOT NULL,
    "gameId" TEXT NOT NULL,
    "capturedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "openSpreadHome" DOUBLE PRECISION,
    "currentSpreadHome" DOUBLE PRECISION,
    "openTotal" DOUBLE PRECISION,
    "currentTotal" DOUBLE PRECISION,
    "bestSpreadHome" DOUBLE PRECISION,
    "bestSpreadBook" TEXT,
    "bestTotal" DOUBLE PRECISION,
    "bestTotalBook" TEXT,
    "spreadDispersion" DOUBLE PRECISION,
    "totalDispersion" DOUBLE PRECISION,

    CONSTRAINT "MarketSnapshot_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "BookLine" (
    "id" TEXT NOT NULL,
    "marketId" TEXT NOT NULL,
    "book" TEXT NOT NULL,
    "capturedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "spreadHome" DOUBLE PRECISION,
    "spreadAway" DOUBLE PRECISION,
    "total" DOUBLE PRECISION,

    CONSTRAINT "BookLine_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ModelProjection" (
    "id" TEXT NOT NULL,
    "gameId" TEXT NOT NULL,
    "version" TEXT NOT NULL,
    "computedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "projSpreadHome" DOUBLE PRECISION NOT NULL,
    "projTotal" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "ModelProjection_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Writeup" (
    "id" TEXT NOT NULL,
    "gameId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "formatKey" TEXT NOT NULL,
    "body" TEXT NOT NULL,
    "disclosedAi" BOOLEAN NOT NULL DEFAULT true,
    "editorStatus" "EditorStatus" NOT NULL DEFAULT 'DRAFT',

    CONSTRAINT "Writeup_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Injury" (
    "id" TEXT NOT NULL,
    "teamId" TEXT NOT NULL,
    "date" TIMESTAMP(3) NOT NULL,
    "player" TEXT NOT NULL,
    "status" "InjuryStatus" NOT NULL,
    "note" TEXT,
    "impact" "InjuryImpact",
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Injury_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TeamProfileWeekly" (
    "id" TEXT NOT NULL,
    "teamId" TEXT NOT NULL,
    "weekStart" TIMESTAMP(3) NOT NULL,
    "summary" TEXT NOT NULL,
    "tempoRank" INTEGER,
    "offPpp" DOUBLE PRECISION,
    "defPpp" DOUBLE PRECISION,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "TeamProfileWeekly_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Sport_key_key" ON "Sport"("key");

-- CreateIndex
CREATE INDEX "Sport_key_idx" ON "Sport"("key");

-- CreateIndex
CREATE INDEX "Team_sportId_name_idx" ON "Team"("sportId", "name");

-- CreateIndex
CREATE UNIQUE INDEX "Team_sportId_slug_key" ON "Team"("sportId", "slug");

-- CreateIndex
CREATE INDEX "Game_sportId_date_idx" ON "Game"("sportId", "date");

-- CreateIndex
CREATE INDEX "Game_homeTeamId_date_idx" ON "Game"("homeTeamId", "date");

-- CreateIndex
CREATE INDEX "Game_awayTeamId_date_idx" ON "Game"("awayTeamId", "date");

-- CreateIndex
CREATE UNIQUE INDEX "Game_sportId_date_slug_key" ON "Game"("sportId", "date", "slug");

-- CreateIndex
CREATE UNIQUE INDEX "MarketSnapshot_gameId_key" ON "MarketSnapshot"("gameId");

-- CreateIndex
CREATE INDEX "MarketSnapshot_capturedAt_idx" ON "MarketSnapshot"("capturedAt");

-- CreateIndex
CREATE INDEX "BookLine_marketId_book_idx" ON "BookLine"("marketId", "book");

-- CreateIndex
CREATE INDEX "BookLine_capturedAt_idx" ON "BookLine"("capturedAt");

-- CreateIndex
CREATE UNIQUE INDEX "ModelProjection_gameId_key" ON "ModelProjection"("gameId");

-- CreateIndex
CREATE INDEX "ModelProjection_version_idx" ON "ModelProjection"("version");

-- CreateIndex
CREATE INDEX "ModelProjection_computedAt_idx" ON "ModelProjection"("computedAt");

-- CreateIndex
CREATE UNIQUE INDEX "Writeup_gameId_key" ON "Writeup"("gameId");

-- CreateIndex
CREATE INDEX "Writeup_formatKey_idx" ON "Writeup"("formatKey");

-- CreateIndex
CREATE INDEX "Writeup_editorStatus_idx" ON "Writeup"("editorStatus");

-- CreateIndex
CREATE INDEX "Injury_teamId_date_idx" ON "Injury"("teamId", "date");

-- CreateIndex
CREATE INDEX "Injury_status_idx" ON "Injury"("status");

-- CreateIndex
CREATE INDEX "TeamProfileWeekly_weekStart_idx" ON "TeamProfileWeekly"("weekStart");

-- CreateIndex
CREATE UNIQUE INDEX "TeamProfileWeekly_teamId_weekStart_key" ON "TeamProfileWeekly"("teamId", "weekStart");

-- AddForeignKey
ALTER TABLE "Team" ADD CONSTRAINT "Team_sportId_fkey" FOREIGN KEY ("sportId") REFERENCES "Sport"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Game" ADD CONSTRAINT "Game_sportId_fkey" FOREIGN KEY ("sportId") REFERENCES "Sport"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Game" ADD CONSTRAINT "Game_homeTeamId_fkey" FOREIGN KEY ("homeTeamId") REFERENCES "Team"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Game" ADD CONSTRAINT "Game_awayTeamId_fkey" FOREIGN KEY ("awayTeamId") REFERENCES "Team"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "MarketSnapshot" ADD CONSTRAINT "MarketSnapshot_gameId_fkey" FOREIGN KEY ("gameId") REFERENCES "Game"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "BookLine" ADD CONSTRAINT "BookLine_marketId_fkey" FOREIGN KEY ("marketId") REFERENCES "MarketSnapshot"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ModelProjection" ADD CONSTRAINT "ModelProjection_gameId_fkey" FOREIGN KEY ("gameId") REFERENCES "Game"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Writeup" ADD CONSTRAINT "Writeup_gameId_fkey" FOREIGN KEY ("gameId") REFERENCES "Game"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Injury" ADD CONSTRAINT "Injury_teamId_fkey" FOREIGN KEY ("teamId") REFERENCES "Team"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TeamProfileWeekly" ADD CONSTRAINT "TeamProfileWeekly_teamId_fkey" FOREIGN KEY ("teamId") REFERENCES "Team"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

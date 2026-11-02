# Mac runbook v2.3 — PLUMBING-ONLY (ccecea74)

Ryan's Mac. Dedicated **b1d857d3** worktree. Not `~/kosedge`. No W7. No
Odds/Railway/prod DB on the seal. Re-run = **new** snapshot.

Pin BASE first:

```bash
BASE=/abs/dedicated-b1d857d3-worktree
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"
IMV="$BASE/scripts/nfl/imv"
```

## 1. nflverse pre-stage (network ON) + sha pins

```bash
bash "$IMV/nfl-imv-prestage-nflverse.sh"
PRE=/var/tmp/nfl-imv-prestage-nflverse/LATEST
# add PBP (builder requires pbp_2025 + pbp_2026; pre-stage games only)
mkdir -p "$PRE/files"
curl -fsSL -o "$PRE/files/play_by_play_2025.parquet" \
  https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2025.parquet
curl -fsSL -o "$PRE/files/play_by_play_2026.parquet" \
  https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet
P25=$(shasum -a 256 "$PRE/files/play_by_play_2025.parquet" | awk '{print $1}')
P26=$(shasum -a 256 "$PRE/files/play_by_play_2026.parquet" | awk '{print $1}')
GSHA=$(awk -F'\t' '$3=="schedule_games_csv"{print $1; exit}' "$PRE/imv-w7-manifest.tsv")
GPATH=$(awk -F'\t' '$3=="schedule_games_csv"{print $2; exit}' "$PRE/imv-w7-manifest.tsv")
ASOF=$(awk -F'\t' '$3=="schedule_games_csv"{print $4; exit}' "$PRE/imv-w7-manifest.tsv")
{
  echo -e "${GSHA}\t${GPATH}\tschedule_games_csv\t${ASOF}"
  echo -e "${P25}\t${PRE}/files/play_by_play_2025.parquet\tpbp_2025\t${ASOF}"
  echo -e "${P26}\t${PRE}/files/play_by_play_2026.parquet\tpbp_2026\t${ASOF}"
} > "$PRE/imv-manifest.tsv"
cat "$PRE/imv-manifest.tsv"
# record those three shas; do not proceed if a sha is empty
```

Missing W4–W6 (or W6+W7 for W8) finals → **BLOCKED**. Do not invent scores.

## 2. Feature builds (network DENY; new --out each time)

Caps: W4 `4/3` · W5 `5/4` · W6 `6/5` · W8 `8/7`. pbp = game−1. W7 refused.

```bash
# W4
OUT4=/var/tmp/nfl-imv-features/w4-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.3.sh" --base "$BASE" --prestage "$PRE" \
  --out "$OUT4" --game-week-cap 4 --pbp-week-cap 3
# W5
OUT5=/var/tmp/nfl-imv-features/w5-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.3.sh" --base "$BASE" --prestage "$PRE" \
  --out "$OUT5" --game-week-cap 5 --pbp-week-cap 4
# W6 (retro store used by the W4–W6 seal)
OUT6=/var/tmp/nfl-imv-features/w6-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.3.sh" --base "$BASE" --prestage "$PRE" \
  --out "$OUT6" --game-week-cap 6 --pbp-week-cap 5
# W8 — only if now < 2026-10-29 20:15 ET
OUT8=/var/tmp/nfl-imv-features/w8-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.3.sh" --base "$BASE" --prestage "$PRE" \
  --out "$OUT8" --game-week-cap 8 --pbp-week-cap 7
```

If `BUILD_BLOCKED` exists or status is BLOCKED → **do not seal**. New `--out`
for a retry. Pin the **store** digest from **outside** the store:

```bash
mkdir -p /var/tmp/operator-pins
cp "$OUT6/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w6.sha256
cp "$OUT8/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w8.sha256
# do NOT: cat "$OUT6/store/FEATURE_STORE.sha256" back from inside a seal
```

Parity (optional; stays `NOT_RUN_NO_PROD_EXPORT` until an export is supplied):

```bash
export IMV_PROD_EXPORT=/abs/genuine-sealed-prod-export   # see nfl-imv-prod-export-spec-v2.3.md
python3 "$IMV/nfl_imv_v23.py" parity --local "$OUT6/store/features.jsonl" \
  --prod-export "$IMV_PROD_EXPORT" --week-cap 6
```

## 3. Seals (network DENY)

```bash
# W4–W6 RETROSPECTIVE (uses the W6 store; includes W4/W5/W6 rows)
IMV_FEATURE_STORE="$OUT6" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w6.sha256)" \
IMV_MANIFEST="$PRE/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.3.sh" --base "$BASE" retrospective-w4w6

# W8 PROSPECTIVE-RESEARCH — start before 2026-10-29 20:15 ET
# Games with kickoff <= seal time are excluded.
IMV_FEATURE_STORE="$OUT8" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w8.sha256)" \
IMV_MANIFEST="$PRE/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.3.sh" --base "$BASE" w8-pregame
```

Confirm seal `HELPERS.json`: v21 `050271467cd38f5a174043c67f2df9622d7f0b8125f137b822f888846f4c561f`
plus a v22 sha. Runner reads `$IMV_FEATURE_STORE/store`.

## 4. Copy tar + sha to Desktop (P-4)

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TAR="$HOME/Desktop/nfl-imv-v23-${STAMP}.tgz"
tar -czf "$TAR" \
  /var/tmp/nfl-imv-prestage-nflverse/LATEST \
  /var/tmp/nfl-imv-features \
  /var/tmp/nfl-imv-sealed-v2.3-retrospective-w4w6 \
  /var/tmp/nfl-imv-sealed-v2.3-w8-pregame \
  /var/tmp/operator-pins
shasum -a 256 "$TAR" | tee "$HOME/Desktop/nfl-imv-v23-${STAMP}.tgz.sha256"
# transfer both files; verify sha on the receiving host
```

Grade is **PLUMBING-ONLY**. Numbers are not certification.

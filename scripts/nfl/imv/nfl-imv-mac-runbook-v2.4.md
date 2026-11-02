# Mac runbook v2.4 — RETURNED (47616a70)

Ryan's Mac. Dedicated **b1d857d3** worktree. **Not** `~/kosedge`. No W7.
No Odds / Railway / prod DB on the seal. Re-run = **new** snapshot.

This runbook **returns** the v2.3 layout. Do not copy IMV scripts into
`$BASE/scripts`.

## 0. Separate sha-checked IMV folder (outside BASE)

```bash
BASE=/abs/dedicated-b1d857d3-worktree
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"

# PR / Desktop copy of scripts/nfl/imv — NOT $BASE/scripts
SRC=/abs/nfl-imv-v24-from-pr/scripts/nfl/imv
IMV=/var/tmp/nfl-imv-bundle-v24
rm -rf "$IMV"
mkdir -p "$IMV"
cp "$SRC"/nfl_imv_v2{1,2,3,4}.py "$IMV"/
cp "$SRC"/nfl-imv-feature-path-v2*.md "$IMV"/
cp "$SRC"/README.md "$IMV"/
cp "$SRC"/nfl-imv-feature-build-v2.4.sh "$IMV"/
cp "$SRC"/nfl-imv-sealed-v2.4.sh "$IMV"/
cp "$SRC"/nfl-imv-prestage-nflverse.sh "$IMV"/
python3 "$IMV/nfl_imv_v24.py" check-pins --imv-dir "$IMV"
# must print ok=true; v22 starts 57a419b4; v23 starts fe66b374
# FAIL if IMV is inside BASE
```

Box dest (CopyToBox from `~/Desktop`):

`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`

`<run>` = `retro-w4w6` or `w8-pregame`.

## 1. nflverse pre-stage (network ON)

W4–W6 retro may use the existing pre-stage.

**W8 order (returned):** re-pre-stage **after W7 finals** (after Mon
2026-10-26), **then** build+seal W8 **before** 2026-10-29 20:15 ET.

```bash
bash "$IMV/nfl-imv-prestage-nflverse.sh"
PRE=/var/tmp/nfl-imv-prestage-nflverse/LATEST
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
# keep the manifest (parquet shas). Do not tar the parquet files.
```

Missing W4–W6 (or W6+W7 for W8) finals → **BLOCKED**. Do not invent scores.

## 2. Feature builds (network DENY; new --out each time)

Caps: W4 `4/3` · W5 `5/4` · W6 `6/5` · W8 `8/7`. pbp = game−1. W7 refused.

```bash
# W6 store for the W4–W6 seal
OUT6=/var/tmp/nfl-imv-features/w6-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.4.sh" --base "$BASE" --prestage "$PRE" \
  --out "$OUT6" --game-week-cap 6 --pbp-week-cap 5

# W8 — only after the post-10-26 re-pre-stage, and only if now < 2026-10-29 20:15 ET
OUT8=/var/tmp/nfl-imv-features/w8-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.4.sh" --base "$BASE" --prestage "$PRE" \
  --out "$OUT8" --game-week-cap 8 --pbp-week-cap 7
```

If `BUILD_BLOCKED` exists or status is BLOCKED → **do not seal**.

### Store sha to box **before** each sealed run (returned 4)

```bash
BOX=/workspace/ops/nfl_t4132u_audit_2026-10-22/runs
mkdir -p "$HOME/Desktop/CopyToBox/retro-w4w6" "$HOME/Desktop/CopyToBox/w8-pregame"
cp "$OUT6/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/retro-w4w6/FEATURE_STORE.sha256"
# CopyToBox → $BOX/retro-w4w6/FEATURE_STORE.sha256   BEFORE the retro seal
cp "$OUT8/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/w8-pregame/FEATURE_STORE.sha256"
# CopyToBox → $BOX/w8-pregame/FEATURE_STORE.sha256   BEFORE the W8 seal

mkdir -p /var/tmp/operator-pins
cp "$OUT6/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w6.sha256
cp "$OUT8/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w8.sha256
```

Confirm `OUT/store/SHA256SUMS` is present (C-6, written last) and
`OUT/bundle` has v21/v22/v23/v24 + feature-path + README.

## 3. Seals (network DENY)

```bash
IMV_FEATURE_STORE="$OUT6" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w6.sha256)" \
IMV_MANIFEST="$PRE/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$BASE" retrospective-w4w6

# W8 — start before 2026-10-29 20:15 ET; games with kickoff <= seal time excluded
IMV_FEATURE_STORE="$OUT8" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w8.sha256)" \
IMV_MANIFEST="$PRE/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$BASE" w8-pregame
```

Confirm seal `HELPERS.json`: v22 `57a419b4…`, v23 `fe66b374…`, v21
`05027146…`.

## 4. Tar only stamped folders; no parquet (returned 5)

Name the tars for CopyToBox →
`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`.

**W8 tar before kickoff. Retro tar before any results discussion.**

```bash
# pick the explicit stamp dirs (do not tar the parent glob)
SEAL6=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
SEAL8=/var/tmp/nfl-imv-sealed-v2.4-w8-pregame/<STAMP>

# parquet sha manifest only — exclude *.parquet
TAR6="$HOME/Desktop/nfl-imv-v24-retro-w4w6-<STAMP>.tgz"
COPYFILE_DISABLE=1 tar -czf "$TAR6" \
  --exclude='*.parquet' \
  "$OUT6" \
  "$SEAL6" \
  "$PRE/imv-manifest.tsv" \
  /var/tmp/operator-pins/w6.sha256 \
  "$IMV"
shasum -a 256 "$TAR6" | tee "$TAR6.sha256"
# CopyToBox both files → .../runs/retro-w4w6/   before discussing results

TAR8="$HOME/Desktop/nfl-imv-v24-w8-pregame-<STAMP>.tgz"
COPYFILE_DISABLE=1 tar -czf "$TAR8" \
  --exclude='*.parquet' \
  "$OUT8" \
  "$SEAL8" \
  "$PRE/imv-manifest.tsv" \
  /var/tmp/operator-pins/w8.sha256 \
  "$IMV"
shasum -a 256 "$TAR8" | tee "$TAR8.sha256"
# CopyToBox both files → .../runs/w8-pregame/   before kickoff
```

Grade remains **PLUMBING-ONLY** until a genuine export meets the cert
bar. Numbers are not certification until C-1..C-3 PASS at 0.005.

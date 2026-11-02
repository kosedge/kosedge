# Mac runbook v2.4.3 — pin bash-3.2-safe builder v2.4.1

Ryan's Mac. Dedicated **b1d857d3** worktree. **Not** `~/kosedge`. No W7.
No Odds / Railway / prod DB on the seal. Re-run = **new** snapshot.
**Never `rm -rf` the IMV folder.** No deletion of that folder anywhere.

Reader for parity is **v2.6**. Plumbing build/seal still uses the v2.4
scripts (sha-checked). Do not run W7. Do not generate parity evidence
from this packet.

## Pre-run conditions 1–8

1. Worktree pinned and clean (`b1d857d3…`, porcelain empty).
2. Stamped IMV dir plus sha-check (N-2: SUMS anchored to `b0cf91da…`).
3. No prod env vars. Scripts refuse them.
4. Sandbox deny plus **EPERM_OK** sealed: confirm `EPERM_OK` in `OUT`
   (`$OUT/EPERM_PROBE.txt`) **and** in the seal
   (`$SEAL/EPERM_PROBE.txt`). Missing either → STOP.
5. Store sha on the box before that run's seal (K-4).
6. Tar zero parquet plus the timing in §4.
7. a BLOCKED build still seals and is reported BLOCKED.
8. Parity stays `NOT_RUN` until reader v2.6 is IMV-passed and a
   Ryan-authorized v3 export is sealed.

## 0. Fresh stamped IMV folder (K-1, N-2)

```bash
BASE=/abs/dedicated-b1d857d3-worktree
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"

# PR / Desktop copy of scripts/nfl/imv — NOT $BASE/scripts
SRC=/abs/nfl-imv-v26-from-pr/scripts/nfl/imv
IMV=/var/tmp/nfl-imv-bundle-v26-$(date -u +%Y%m%dT%H%M%SZ)
test ! -e "$IMV"
mkdir "$IMV"   # no -p; never rm -rf
# N-2: SHA256SUMS is the IMV-verified v2.5 file, NOT copied from $SRC
# as the check source. Recorded digest (04fd87a1 / v2.5 bundle):
SUMS_V25=/workspace/ops/nfl_t4132u_audit_2026-10-22/v2.5/SHA256SUMS
# fallback if the box copy is the artifact:
# SUMS_V25=/cursor/stores/self/artifacts/nfl-imv-bundle-v2.5/SHA256SUMS
test "$(shasum -a 256 "$SUMS_V25" | awk '{print $1}')" = \
  "b0cf91da6cccac015877a6a4bdd7af66b9290085f61fe9b5ca340d7c61f8f8e2"
# copy every v2.5 SUMS entry from SRC, then the v2.6 files
while read -r _ name; do
  test -f "$SRC/$name"
  cp "$SRC/$name" "$IMV/$name"
done < "$SUMS_V25"
cp "$SRC"/nfl_imv_v26.py "$IMV"/
cp "$SRC"/nfl_imv_v27.py "$IMV"/
cp "$SRC"/nfl-imv-mac-runbook-v2.4.3.md "$IMV"/
cp "$SRC"/nfl-imv-feature-build-v2.4.1.sh "$IMV"/
cp "$SRC"/nfl-imv-v2.6-r-trace.md "$IMV"/
cp "$SRC"/nfl-imv-feature-path-v2.6.md "$IMV"/
cp "$SRC"/SHA256SUMS.v2.5 "$IMV"/SHA256SUMS.v2.5
# no --ignore-missing — a failed cp is a STOP
cd "$IMV" && shasum -a 256 -c "$SUMS_V25"
# pin v25, v26, and the three shells (mismatch = STOP)
test "$(shasum -a 256 nfl_imv_v25.py | awk '{print $1}')" = \
  "582eb6cea720ab2e019e7085b731dab682bb61ee2438ccd3c7cf367064161565"
test "$(shasum -a 256 nfl-imv-feature-build-v2.4.sh | awk '{print $1}')" = \
  "105ac5be2daf40b57ccfdfe9a3daa1568e522d3366eb14a1498121096b6c921d"
test "$(shasum -a 256 nfl-imv-feature-build-v2.4.1.sh | awk '{print $1}')" = \
  "c3a521569e80e980600e07829f0d9535cd65efda5efc7843e79f43bfdc758a0a"
test "$(shasum -a 256 nfl-imv-sealed-v2.4.sh | awk '{print $1}')" = \
  "3a5da768e1b83c9a213be554f2865bf6b26fa17f21e89a08c337be8ef5898b2a"
test "$(shasum -a 256 nfl-imv-prestage-nflverse.sh | awk '{print $1}')" = \
  "cba5a4032f35a2c727771eda97ea97a661f6caa10f492a60b6aa604612aad059"
test "$(shasum -a 256 nfl_imv_v26.py | awk '{print $1}')" = \
  "b86b64d5ffcfe403fbf063db695a79e0ca1c65daecb869cfe45180d71d3d9ffe"
test "$(shasum -a 256 nfl_imv_v27.py | awk '{print $1}')" = \
  "4c5cd242650eef54ea6e6aa8d2f670122dab9fe9222b750ebcdb57a9a032a780"
python3 "$IMV/nfl_imv_v27.py" check-pins --imv-dir "$IMV" --sums-v25 "$SUMS_V25"
# must print ok=true
# v21 05027146…  v22 57a419b4…  v23 fe66b374…  v24 7c3f4dc7…  v25 582eb6ce…
# v26 b86b64d5…  v27 (this packet)  shells 105ac5be… / c3a52156… / 3a5da768… / cba5a403…
# FAIL if IMV is inside BASE
```

Box dest (CopyToBox from `~/Desktop`):

`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`

`<run>` = `retro-w4w6` or `w8-pregame`.

## 1. nflverse pre-stage (network ON)

### Retro pre-stage (N-1)

The prestage script writes its own stamped dir under
`/var/tmp/nfl-imv-prestage-nflverse/<STAMP>` and points `LATEST` at it.
Do **not** mkdir an empty `PRE_RETRO`. Read the stamp via `readlink`.

```bash
unset IMV_PRESTAGE_OUT
bash "$IMV/nfl-imv-prestage-nflverse.sh"
PRE_RETRO=$(readlink /var/tmp/nfl-imv-prestage-nflverse/LATEST)
test -d "$PRE_RETRO"
test -f "$PRE_RETRO/imv-w7-manifest.tsv"
printf '%s\n' "$PRE_RETRO" | tee /var/tmp/nfl-imv-prestage-nflverse/PRE_RETRO.txt
mkdir -p "$PRE_RETRO/files"
curl -fsSL -o "$PRE_RETRO/files/play_by_play_2025.parquet" \
  https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2025.parquet
curl -fsSL -o "$PRE_RETRO/files/play_by_play_2026.parquet" \
  https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet
P25=$(shasum -a 256 "$PRE_RETRO/files/play_by_play_2025.parquet" | awk '{print $1}')
P26=$(shasum -a 256 "$PRE_RETRO/files/play_by_play_2026.parquet" | awk '{print $1}')
GSHA=$(awk -F'\t' '$3=="schedule_games_csv"{print $1; exit}' "$PRE_RETRO/imv-w7-manifest.tsv")
GPATH=$(awk -F'\t' '$3=="schedule_games_csv"{print $2; exit}' "$PRE_RETRO/imv-w7-manifest.tsv")
ASOF=$(awk -F'\t' '$3=="schedule_games_csv"{print $4; exit}' "$PRE_RETRO/imv-w7-manifest.tsv")
{
  echo -e "${GSHA}\t${GPATH}\tschedule_games_csv\t${ASOF}"
  echo -e "${P25}\t${PRE_RETRO}/files/play_by_play_2025.parquet\tpbp_2025\t${ASOF}"
  echo -e "${P26}\t${PRE_RETRO}/files/play_by_play_2026.parquet\tpbp_2026\t${ASOF}"
} > "$PRE_RETRO/imv-manifest.tsv"
shasum -a 256 "$PRE_RETRO/imv-manifest.tsv" | tee "$PRE_RETRO/imv-manifest.tsv.sha256"
```

Missing W4–W6 finals → **BLOCKED**. Do not invent scores.
Keep `$PRE_RETRO`. Do not overwrite its manifest later.

### W8 re-pre-stage (K-3, N-1)

Only **on or after 2026-10-27 ET**, and only after every 2026 REG week-7
game in `games.csv` is final. New stamp. **Do not overwrite**
`$PRE_RETRO/imv-manifest.tsv`.

```bash
test "$(TZ=America/New_York date +%Y%m%d)" -ge 20261027
# confirm every 2026 REG week=7 row is final; else BLOCKED
unset IMV_PRESTAGE_OUT
bash "$IMV/nfl-imv-prestage-nflverse.sh"
PRE_W8=$(readlink /var/tmp/nfl-imv-prestage-nflverse/LATEST)
test -d "$PRE_W8"
test "$PRE_W8" != "$PRE_RETRO"
test -f "$PRE_W8/imv-w7-manifest.tsv"
printf '%s\n' "$PRE_W8" | tee /var/tmp/nfl-imv-prestage-nflverse/PRE_W8.txt
mkdir -p "$PRE_W8/files"
curl -fsSL -o "$PRE_W8/files/play_by_play_2025.parquet" \
  https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2025.parquet
curl -fsSL -o "$PRE_W8/files/play_by_play_2026.parquet" \
  https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet
P25=$(shasum -a 256 "$PRE_W8/files/play_by_play_2025.parquet" | awk '{print $1}')
P26=$(shasum -a 256 "$PRE_W8/files/play_by_play_2026.parquet" | awk '{print $1}')
GSHA=$(awk -F'\t' '$3=="schedule_games_csv"{print $1; exit}' "$PRE_W8/imv-w7-manifest.tsv")
GPATH=$(awk -F'\t' '$3=="schedule_games_csv"{print $2; exit}' "$PRE_W8/imv-w7-manifest.tsv")
ASOF=$(awk -F'\t' '$3=="schedule_games_csv"{print $4; exit}' "$PRE_W8/imv-w7-manifest.tsv")
{
  echo -e "${GSHA}\t${GPATH}\tschedule_games_csv\t${ASOF}"
  echo -e "${P25}\t${PRE_W8}/files/play_by_play_2025.parquet\tpbp_2025\t${ASOF}"
  echo -e "${P26}\t${PRE_W8}/files/play_by_play_2026.parquet\tpbp_2026\t${ASOF}"
} > "$PRE_W8/imv-manifest.tsv"
shasum -a 256 "$PRE_W8/imv-manifest.tsv" | tee "$PRE_W8/imv-manifest.tsv.sha256"
# retro tar still uses $PRE_RETRO/imv-manifest.tsv
```

Then build+seal W8 with seal **START** before 2026-10-29 20:15 ET.
Late = not a seal. No extension. W7 stays refused.

## 2. Feature builds (network DENY; new --out each time)

Caps: W4 `4/3` · W5 `5/4` · W6 `6/5` · W8 `8/7`. pbp = game−1. W7 refused.

```bash
OUT6=/var/tmp/nfl-imv-features/w6-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$BASE" --prestage "$PRE_RETRO" \
  --out "$OUT6" --game-week-cap 6 --pbp-week-cap 5
# condition 4: EPERM_OK in OUT
test "$(cat "$OUT6/EPERM_PROBE.txt")" = "EPERM_OK"
```

If `BUILD_BLOCKED` exists or status is BLOCKED: still proceed to the
seal. a BLOCKED build still seals and is reported BLOCKED.

### K-4 retro: store sha on the box, then seal

```bash
BOX=/workspace/ops/nfl_t4132u_audit_2026-10-22/runs
mkdir -p "$HOME/Desktop/CopyToBox/retro-w4w6"
cp "$OUT6/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/retro-w4w6/FEATURE_STORE.sha256"
# CopyToBox → $BOX/retro-w4w6/FEATURE_STORE.sha256
# IMV records the box timestamp and acknowledges receipt.
# ONLY THEN:
mkdir -p /var/tmp/operator-pins
cp "$OUT6/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w6.sha256
IMV_FEATURE_STORE="$OUT6" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w6.sha256)" \
IMV_MANIFEST="$PRE_RETRO/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$BASE" retrospective-w4w6
SEAL6=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
test "$(cat "$SEAL6/EPERM_PROBE.txt")" = "EPERM_OK"
```

Confirm `OUT/store/SHA256SUMS` is last and seal `HELPERS.json` has
v21 `05027146…`, v22 `57a419b4…`, v23 `fe66b374…`, v24 `7c3f4dc7…`.

## 3. W8 build + seal (only after K-3 / N-1 W8)

```bash
OUT8=/var/tmp/nfl-imv-features/w8-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$BASE" --prestage "$PRE_W8" \
  --out "$OUT8" --game-week-cap 8 --pbp-week-cap 7
test "$(cat "$OUT8/EPERM_PROBE.txt")" = "EPERM_OK"
# K-4 W8: box the store sha, IMV timestamp, THEN seal
mkdir -p "$HOME/Desktop/CopyToBox/w8-pregame"
cp "$OUT8/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/w8-pregame/FEATURE_STORE.sha256"
# CopyToBox → $BOX/w8-pregame/FEATURE_STORE.sha256  BEFORE the W8 seal
cp "$OUT8/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w8.sha256
IMV_FEATURE_STORE="$OUT8" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w8.sha256)" \
IMV_MANIFEST="$PRE_W8/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$BASE" w8-pregame
SEAL8=/var/tmp/nfl-imv-sealed-v2.4-w8-pregame/<STAMP>
test "$(cat "$SEAL8/EPERM_PROBE.txt")" = "EPERM_OK"
```

## 4. Tar only stamped folders; no parquet

Name the tars for CopyToBox →
`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`.

**W8 tar before kickoff. Retro tar before any results discussion.**

Before CopyToBox: `tar -tzf "$TAR" | grep -c '\.parquet$'` must be 0.
No top-level parent glob.

```bash
SEAL6=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
TAR6="$HOME/Desktop/nfl-imv-v242-retro-w4w6-<STAMP>.tgz"
COPYFILE_DISABLE=1 tar -czf "$TAR6" \
  --exclude='*.parquet' \
  "$OUT6" \
  "$SEAL6" \
  "$PRE_RETRO/imv-manifest.tsv" \
  "$PRE_RETRO/imv-manifest.tsv.sha256" \
  /var/tmp/operator-pins/w6.sha256 \
  "$IMV"
tar -tzf "$TAR6" | grep '\.parquet$' && echo FAIL_PARQUET && exit 2
shasum -a 256 "$TAR6" | tee "$TAR6.sha256"
# CopyToBox both files → .../runs/retro-w4w6/   before discussing results

SEAL8=/var/tmp/nfl-imv-sealed-v2.4-w8-pregame/<STAMP>
TAR8="$HOME/Desktop/nfl-imv-v242-w8-pregame-<STAMP>.tgz"
COPYFILE_DISABLE=1 tar -czf "$TAR8" \
  --exclude='*.parquet' \
  "$OUT8" \
  "$SEAL8" \
  "$PRE_W8/imv-manifest.tsv" \
  "$PRE_W8/imv-manifest.tsv.sha256" \
  /var/tmp/operator-pins/w8.sha256 \
  "$IMV"
tar -tzf "$TAR8" | grep '\.parquet$' && echo FAIL_PARQUET && exit 2
shasum -a 256 "$TAR8" | tee "$TAR8.sha256"
```

Grade remains **PLUMBING-ONLY**. Parity stays `NOT_RUN` until a
Ryan-authorized v3 export (`b10d6cfd…`) is sealed and reader v2.6 is
IMV-passed. Plumbing PASS is not cert.

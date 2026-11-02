# Mac runbook v2.4.4 — e5c65b0d items 1–7 (STOP on failure)

Ryan's Mac. Dedicated **b1d857d3** worktree. **Not** `~/kosedge`. No W7.
No Odds / Railway / prod DB on the seal. Re-run = **new** snapshot.
**Never `rm -rf` the IMV folder.** No deletion of that folder anywhere.
**L-1:** every block below starts with `set -euo pipefail`.

Reader for parity is **v2.6**. Builder is **v2.4.1**. Do not run W7.
Do not generate parity evidence from this packet.
RD-3: W4 `/var/tmp/nfl-imv-features/w4-20261022T173520Z` is
ABORTED-PARTIAL (bash 3.2 + set -u empty `PACK_ARG[@]`). Not evidence.

## Pre-run conditions 1–8

1. Worktree pinned and clean (`b1d857d3…`, porcelain empty).
2. Stamped IMV dir plus sha-check (N-2: SUMS_V25 from SRC; bundle SUMS `5d64a848…`).
3. No prod env vars. Scripts refuse them.
4. Sandbox deny plus **EPERM_OK** sealed: confirm `EPERM_OK` in `OUT`
   (`$OUT/EPERM_PROBE.txt`) **and** in the seal
   (`$SEAL/EPERM_PROBE.txt`). Missing either → STOP.
5. Store sha on the box before that run's seal (K-4).
6. Tar zero parquet plus the timing in §4.
7. a BLOCKED build still seals and is reported BLOCKED.
8. Parity stays `NOT_RUN` until reader v2.6 is IMV-passed and a
   Ryan-authorized v3 export is sealed.

## 0. Item 1 — mark W4 ABORTED-PARTIAL (no edit / delete / seal / reuse)

```bash
set -euo pipefail
W4_PARTIAL=/var/tmp/nfl-imv-features/w4-20261022T173520Z
test -d "$W4_PARTIAL"
# do not rm, chmod, write, seal, or reuse $W4_PARTIAL
RUN_REPORT="$HOME/Desktop/nfl-imv-run-report-w4-rerun.txt"
{
  printf '%s\n' "W4_PARTIAL=$W4_PARTIAL"
  printf '%s\n' "STATUS=ABORTED-PARTIAL"
  printf '%s\n' "NO_EDIT=1"
  printf '%s\n' "NO_DELETE=1"
  printf '%s\n' "NO_SEAL=1"
  printf '%s\n' "NO_REUSE=1"
  printf '%s\n' "RD-3=bash3.2+set -u empty PACK_ARG[@] aborted W4"
} | tee "$RUN_REPORT"
test "$(awk -F= '$1=="STATUS"{print $2; exit}' "$RUN_REPORT")" = "ABORTED-PARTIAL"
```

## 0b. Fresh stamped IMV folder (K-1, L-2, item 7)

```bash
set -euo pipefail
BASE=/abs/dedicated-b1d857d3-worktree
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"

# PR / Desktop copy of scripts/nfl/imv — NOT $BASE/scripts
SRC=/abs/nfl-imv-v26-from-pr/scripts/nfl/imv
IMV=/var/tmp/nfl-imv-bundle-v26-$(date -u +%Y%m%dT%H%M%SZ)
test ! -e "$IMV"
mkdir "$IMV"   # no -p; never rm -rf
# L-2: SUMS from SRC only. No box paths on the Mac.
SUMS_V25="$SRC/SHA256SUMS.v2.5"
SUMS="$SRC/SHA256SUMS.v2.6.1"
test -f "$SUMS_V25"
test -f "$SUMS"
test "$(shasum -a 256 "$SUMS_V25" | awk '{print $1}')" = \
  "b0cf91da6cccac015877a6a4bdd7af66b9290085f61fe9b5ca340d7c61f8f8e2"
# item 7: pin the v2.6.1 SHA256SUMS by full sha
test "$(shasum -a 256 "$SUMS" | awk '{print $1}')" = \
  "5d64a848bb5e903350051820d3a85faa941e3f9c755b75833f3d6ca73e6ad3d8"
while read -r _ name; do
  test -f "$SRC/$name"
  cp "$SRC/$name" "$IMV/$name"
done < "$SUMS"
cp "$SRC"/nfl-imv-mac-runbook-v2.4.4.md "$IMV"/
cp "$SRC"/nfl-imv-deviation-register-rd-p2.md "$IMV"/
cp "$SRC"/SHA256SUMS.v2.5 "$IMV"/SHA256SUMS.v2.5
cp "$SRC"/SHA256SUMS.v2.6.1 "$IMV"/SHA256SUMS.v2.6.1
cd "$IMV" && shasum -a 256 -c "$SUMS_V25"
cd "$IMV" && shasum -a 256 -c "$SUMS"
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
# item 7: v27 check-pins always with --sums and --sums-v25; exit 0 and ok=true
PINS="$(python3 "$IMV/nfl_imv_v27.py" check-pins --imv-dir "$IMV" --sums-v25 "$SUMS_V25" --sums "$SUMS")"
printf '%s\n' "$PINS"
printf '%s\n' "$PINS" | python3 -c 'import json,sys; d=json.load(sys.stdin); raise SystemExit(0 if d.get("ok") is True else 6)'
# FAIL if IMV is inside BASE
```

Box dest (CopyToBox from `~/Desktop`):

`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`

`<run>` = `retro-w4w6` or `w8-pregame`.

## 1. Item 2 — PRE_RETRO freeze (no re-download). Item 3 — skip retro prestage/curl

**No re-download for W4–W6.** Do **not** run section-1 prestage or curl
for retro. Reuse the recorded stamp.

```bash
set -euo pipefail
PRE_RETRO=/var/tmp/nfl-imv-prestage-nflverse/20261022T173338Z
MANIFEST_PIN=4c287d5b2d5ce49cd606818ab15345c15ddb378049a4b21a21cc3580c3dbd1f2
DESK="$HOME/Desktop/nfl-imv-prestage-retro-manifest.txt"
test -d "$PRE_RETRO"
test -f "$PRE_RETRO/imv-manifest.tsv"
test -f "$DESK"
# CoS copies $DESK to the box and matches $MANIFEST_PIN. STOP until CoS confirms.
test "${COS_BOX_MANIFEST_OK:-}" = "1"
# then sha256sum -c against PRE_RETRO; no --ignore-missing
printf '%s  %s\n' "$MANIFEST_PIN" "imv-manifest.tsv" | (cd "$PRE_RETRO" && sha256sum -c)
printf '%s  %s\n' "$MANIFEST_PIN" "$DESK" | sha256sum -c
chmod -R a-w "$PRE_RETRO"
test ! -w "$PRE_RETRO/imv-manifest.tsv"
printf '%s\n' "$PRE_RETRO" | tee /var/tmp/nfl-imv-prestage-nflverse/PRE_RETRO.txt
```

Missing W4–W6 finals → **BLOCKED**. Do not invent scores.
Keep `$PRE_RETRO`. Do not overwrite its manifest later.

### W8 re-pre-stage (K-3; own prestage on/after 2026-10-27 ET)

W8 **keeps** its own prestage. Only **on or after 2026-10-27 ET**, and
only after every 2026 REG week-7 game in `games.csv` is final. New
stamp. **Do not overwrite** `$PRE_RETRO/imv-manifest.tsv`.

```bash
set -euo pipefail
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

## plumb2 — seven checks (verbatim; STOP on fail; before each build)

```bash
set -euo pipefail
# plumb2-1 HEAD
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
# plumb2-2 porcelain
test -z "$(git -C "$BASE" status --porcelain)"
# plumb2-3 sparse (RD-1: sparse missed by R-b)
test "$(git -C "$BASE" config --bool core.sparseCheckout || true)" != "true"
test ! -s "$BASE/.git/info/sparse-checkout"
# plumb2-4 skip
test -z "$(git -C "$BASE" ls-files -v | awk '/^S/{print; exit}')"
# plumb2-5 assume-unchanged
test -z "$(git -C "$BASE" ls-files -v | awk '/^[[:lower:]]/{print; exit}')"
# plumb2-6 strict per-path
test -f "$BASE/apps/web/lib/nfl-canonical-schedule-2026.json"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test -f "$BASE/services/model-service/src/services/calibration.py"
# plumb2-7 sim path (RD-2: check-7 path erratum)
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test ! -e "$BASE/src/services/nfl_simulator.py"
```

## 2. Feature builds (network DENY; new --out each time)

Caps: W4 `4/3` · W5 `5/4` · W6 `6/5` · W8 `8/7`. pbp = game−1. W7 refused.
Fresh stamped dir. Never `$W4_PARTIAL`.

```bash
set -euo pipefail
W4_PARTIAL=/var/tmp/nfl-imv-features/w4-20261022T173520Z
# plumb2 before W4
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"
test "$(git -C "$BASE" config --bool core.sparseCheckout || true)" != "true"
test ! -s "$BASE/.git/info/sparse-checkout"
test -z "$(git -C "$BASE" ls-files -v | awk '/^S/{print; exit}')"
test -z "$(git -C "$BASE" ls-files -v | awk '/^[[:lower:]]/{print; exit}')"
test -f "$BASE/apps/web/lib/nfl-canonical-schedule-2026.json"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test -f "$BASE/services/model-service/src/services/calibration.py"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test ! -e "$BASE/src/services/nfl_simulator.py"
OUT4=/var/tmp/nfl-imv-features/w4-$(date -u +%Y%m%dT%H%M%SZ)
test "$OUT4" != "$W4_PARTIAL"
test ! -e "$OUT4"
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$BASE" --prestage "$PRE_RETRO" \
  --out "$OUT4" --game-week-cap 4 --pbp-week-cap 3
test "$(cat "$OUT4/EPERM_PROBE.txt")" = "EPERM_OK"

# plumb2 before W5
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"
test "$(git -C "$BASE" config --bool core.sparseCheckout || true)" != "true"
test ! -s "$BASE/.git/info/sparse-checkout"
test -z "$(git -C "$BASE" ls-files -v | awk '/^S/{print; exit}')"
test -z "$(git -C "$BASE" ls-files -v | awk '/^[[:lower:]]/{print; exit}')"
test -f "$BASE/apps/web/lib/nfl-canonical-schedule-2026.json"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test -f "$BASE/services/model-service/src/services/calibration.py"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test ! -e "$BASE/src/services/nfl_simulator.py"
OUT5=/var/tmp/nfl-imv-features/w5-$(date -u +%Y%m%dT%H%M%SZ)
test "$OUT5" != "$W4_PARTIAL"
test ! -e "$OUT5"
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$BASE" --prestage "$PRE_RETRO" \
  --out "$OUT5" --game-week-cap 5 --pbp-week-cap 4
test "$(cat "$OUT5/EPERM_PROBE.txt")" = "EPERM_OK"

# plumb2 before W6
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"
test "$(git -C "$BASE" config --bool core.sparseCheckout || true)" != "true"
test ! -s "$BASE/.git/info/sparse-checkout"
test -z "$(git -C "$BASE" ls-files -v | awk '/^S/{print; exit}')"
test -z "$(git -C "$BASE" ls-files -v | awk '/^[[:lower:]]/{print; exit}')"
test -f "$BASE/apps/web/lib/nfl-canonical-schedule-2026.json"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test -f "$BASE/services/model-service/src/services/calibration.py"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test ! -e "$BASE/src/services/nfl_simulator.py"
OUT6=/var/tmp/nfl-imv-features/w6-$(date -u +%Y%m%dT%H%M%SZ)
test "$OUT6" != "$W4_PARTIAL"
test ! -e "$OUT6"
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$BASE" --prestage "$PRE_RETRO" \
  --out "$OUT6" --game-week-cap 6 --pbp-week-cap 5
test "$(cat "$OUT6/EPERM_PROBE.txt")" = "EPERM_OK"
```

If `BUILD_BLOCKED` exists or status is BLOCKED: still proceed to the
seal. a BLOCKED build still seals and is reported BLOCKED.

### K-4 retro: store sha on the box, then seal

```bash
set -euo pipefail
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
P-2: that JSON stops at v24 (logged).

## 3. W8 build + seal (only after K-3 W8 prestage)

```bash
set -euo pipefail
W4_PARTIAL=/var/tmp/nfl-imv-features/w4-20261022T173520Z
# plumb2 before W8
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"
test "$(git -C "$BASE" config --bool core.sparseCheckout || true)" != "true"
test ! -s "$BASE/.git/info/sparse-checkout"
test -z "$(git -C "$BASE" ls-files -v | awk '/^S/{print; exit}')"
test -z "$(git -C "$BASE" ls-files -v | awk '/^[[:lower:]]/{print; exit}')"
test -f "$BASE/apps/web/lib/nfl-canonical-schedule-2026.json"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test -f "$BASE/services/model-service/src/services/calibration.py"
test -f "$BASE/services/model-service/src/services/nfl_simulator.py"
test ! -e "$BASE/src/services/nfl_simulator.py"
OUT8=/var/tmp/nfl-imv-features/w8-$(date -u +%Y%m%dT%H%M%SZ)
test "$OUT8" != "$W4_PARTIAL"
test ! -e "$OUT8"
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
set -euo pipefail
SEAL6=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
TAR6="$HOME/Desktop/nfl-imv-v244-retro-w4w6-<STAMP>.tgz"
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
TAR8="$HOME/Desktop/nfl-imv-v244-w8-pregame-<STAMP>.tgz"
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
IMV-passed. Plumbing PASS is not cert. The W4 ABORTED-PARTIAL dir is
not evidence.

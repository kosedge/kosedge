# Mac runbook v2.4.1 — K-1..K-4 closed (54ba672b)

Ryan's Mac. Dedicated **b1d857d3** worktree. **Not** `~/kosedge`. No W7.
No Odds / Railway / prod DB on the seal. Re-run = **new** snapshot.
**Never `rm -rf` the IMV folder.** No deletion of that folder anywhere.

Reader for parity is **v2.5**. Plumbing build/seal still uses the v2.4
scripts (sha-checked). Do not run W7. Do not generate parity evidence
from this packet.

## 0. Fresh stamped IMV folder (K-1, K-2)

```bash
BASE=/abs/dedicated-b1d857d3-worktree
test "$(git -C "$BASE" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"
test -z "$(git -C "$BASE" status --porcelain)"

# PR / Desktop copy of scripts/nfl/imv — NOT $BASE/scripts
SRC=/abs/nfl-imv-v25-from-pr/scripts/nfl/imv
IMV=/var/tmp/nfl-imv-bundle-v24-$(date -u +%Y%m%dT%H%M%SZ)
test ! -e "$IMV"
mkdir "$IMV"   # no -p; never rm -rf
cp "$SRC"/nfl_imv_v2{1,2,3,4,5}.py "$IMV"/
cp "$SRC"/nfl-imv-feature-path-v2*.md "$IMV"/
cp "$SRC"/README.md "$IMV"/
cp "$SRC"/nfl-imv-feature-build-v2.4.sh "$IMV"/
cp "$SRC"/nfl-imv-sealed-v2.4.sh "$IMV"/
cp "$SRC"/nfl-imv-prestage-nflverse.sh "$IMV"/
cp "$SRC"/nfl-imv-mac-runbook-v2.4.1.md "$IMV"/
cp "$SRC"/SHA256SUMS "$IMV"/   # from the v2.5 artifact bundle
# K-2: every copied file vs bundle SHA256SUMS. Non-zero → STOP.
cd "$IMV" && shasum -a 256 -c SHA256SUMS --ignore-missing
python3 "$IMV/nfl_imv_v25.py" check-pins --imv-dir "$IMV"
# must print ok=true
# v21 05027146…  v22 57a419b4…  v23 fe66b374…  v24 7c3f4dc7…
# also records v25 + the three shell shas
# FAIL if IMV is inside BASE
```

Box dest (CopyToBox from `~/Desktop`):

`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`

`<run>` = `retro-w4w6` or `w8-pregame`.

## 1. nflverse pre-stage (network ON)

### Retro pre-stage (do this first; keep the dir)

W4–W6 retro uses **this** stamped pre-stage. Do not overwrite it later.

```bash
PRE_RETRO=/var/tmp/nfl-imv-prestage-nflverse/retro-$(date -u +%Y%m%dT%H%M%SZ)
test ! -e "$PRE_RETRO"
mkdir "$PRE_RETRO"
bash "$IMV/nfl-imv-prestage-nflverse.sh"
# if the script writes LATEST, copy that stamp into PRE_RETRO rather than
# mutating it later. Record the manifest sha in the retro tar.
PRE="$PRE_RETRO"
# … fetch pbp + write $PRE/imv-manifest.tsv as in v2.4 …
shasum -a 256 "$PRE/imv-manifest.tsv" | tee "$PRE/imv-manifest.tsv.sha256"
```

Missing W4–W6 finals → **BLOCKED**. Do not invent scores.

### W8 re-pre-stage (K-3)

Only **on or after 2026-10-27 ET**, and only after every 2026 REG week-7
game in `games.csv` is final. A new stamped PRE. **Do not overwrite**
`$PRE_RETRO/imv-manifest.tsv`.

```bash
test "$(TZ=America/New_York date +%Y%m%d)" -ge 20261027
# confirm every 2026 REG week=7 row is final; else BLOCKED
PRE_W8=/var/tmp/nfl-imv-prestage-nflverse/w8-$(date -u +%Y%m%dT%H%M%SZ)
test ! -e "$PRE_W8"
mkdir "$PRE_W8"
# re-pre-stage into PRE_W8 only
shasum -a 256 "$PRE_W8/imv-manifest.tsv" | tee "$PRE_W8/imv-manifest.tsv.sha256"
# retro tar still uses $PRE_RETRO/imv-manifest.tsv
```

Then build+seal W8 with seal **START** before 2026-10-29 20:15 ET.
Late = not a seal. No extension. W7 stays refused.

## 2. Feature builds (network DENY; new --out each time)

Caps: W4 `4/3` · W5 `5/4` · W6 `6/5` · W8 `8/7`. pbp = game−1. W7 refused.

```bash
OUT6=/var/tmp/nfl-imv-features/w6-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.4.sh" --base "$BASE" --prestage "$PRE_RETRO" \
  --out "$OUT6" --game-week-cap 6 --pbp-week-cap 5
```

If `BUILD_BLOCKED` exists or status is BLOCKED → **do not seal**.

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
```

Confirm `OUT/store/SHA256SUMS` is last and seal `HELPERS.json` has
v21 `05027146…`, v22 `57a419b4…`, v23 `fe66b374…`, v24 `7c3f4dc7…`.

## 3. W8 build + seal (only after K-3)

```bash
OUT8=/var/tmp/nfl-imv-features/w8-$(date -u +%Y%m%dT%H%M%SZ)
bash "$IMV/nfl-imv-feature-build-v2.4.sh" --base "$BASE" --prestage "$PRE_W8" \
  --out "$OUT8" --game-week-cap 8 --pbp-week-cap 7
# K-4 W8: box the store sha, IMV timestamp, THEN seal
mkdir -p "$HOME/Desktop/CopyToBox/w8-pregame"
cp "$OUT8/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/w8-pregame/FEATURE_STORE.sha256"
# CopyToBox → $BOX/w8-pregame/FEATURE_STORE.sha256  BEFORE the W8 seal
cp "$OUT8/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w8.sha256
IMV_FEATURE_STORE="$OUT8" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w8.sha256)" \
IMV_MANIFEST="$PRE_W8/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$BASE" w8-pregame
```

## 4. Tar only stamped folders; no parquet

Name the tars for CopyToBox →
`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`.

**W8 tar before kickoff. Retro tar before any results discussion.**

Before CopyToBox: `tar -tzf "$TAR" | grep -c '\.parquet$'` must be 0.
No top-level parent glob.

```bash
SEAL6=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
TAR6="$HOME/Desktop/nfl-imv-v241-retro-w4w6-<STAMP>.tgz"
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
TAR8="$HOME/Desktop/nfl-imv-v241-w8-pregame-<STAMP>.tgz"
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
Ryan-authorized v3 export (`b10d6cfd…`) is sealed and reader v2.5 is
IMV-passed. Plumbing PASS is not cert.

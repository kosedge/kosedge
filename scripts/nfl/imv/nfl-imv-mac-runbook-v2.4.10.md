# Mac runbook v2.4.10 — 48c3cb6d RD-4 PATH pin

Ryan's Mac. Dedicated **b1d857d3** worktree. **Not** `~/kosedge`. No W7.
No Odds / Railway / prod DB on the seal. Re-run = **new** snapshot.
**Never `rm -rf` the IMV folder.** No deletion of that folder anywhere.
**L-1:** every block below starts with `set -euo pipefail`.
":?" exits a NON-interactive bash. If blocks are pasted into an interactive Terminal, the abort-on-expansion-error behaviour is UNVERIFIED. Run each block non-interactively (saved file, bash file).

Reader for parity is **v2.6**. Builder is **v2.4.1**. Do not run W7.
Do not generate parity evidence from this packet.
RD-3: W4 `/var/tmp/nfl-imv-features/w4-20261022T173520Z` is
ABORTED-PARTIAL (bash 3.2 + set -u empty `PACK_ARG[@]`). Not evidence.
RD-1: sparse-checkout file must be **absent**.

Items 1, 3, 5, 6 and 7 stay as closed in e3ae3984. This file writes B-1,
B-2 and B-3. **W4 and W5 each get their own seal and tar, the same as W6.**
They are never evidence unless sealed.

## IMV texts from filing e3ae3984 (copied word for word)

**B-1** (e3ae3984 l.32–46):

B-1: l.123 checks PRE_RETRO/imv-manifest.tsv against MANIFEST_PIN.
- The pin is the sha of the retro manifest listing file, not of imv-manifest.tsv. The listing's own entry for imv-manifest.tsv != pin (tool).
- So l.123 always fails. It fails closed, but the rerun can never pass.
- The required per-file -c against PRE_RETRO is never done.
- Fix: delete l.123 and, after l.124, run:
    awk '/^EVERY_FILE/{f=1;next} f&&NF==2' "$DESK" | shasum -a 256 -c
  Then chmod -R a-w.
- B-1b: use shasum -a 256 (as elsewhere in the runbook), not sha256sum. sha256sum on the Mac is UNVERIFIED.

**B-3** (81e3c5cb exact text). The FIRST line after set -euo pipefail in each seal block:

    W4: : "${IMV_SEAL_ACK_W4:?IMV ack required}"
    W5: : "${IMV_SEAL_ACK_W5:?IMV ack required}"
    W6: : "${IMV_SEAL_ACK_W6:?IMV ack required}"
    W8: : "${IMV_SEAL_ACK_W8:?IMV ack required}"

## Pre-run conditions 1–8

1. Worktree pinned and clean (`b1d857d3…`).
2. Stamped IMV dir plus sha-check (L-2: SUMS_V25 from SRC;
   SUMS full sha supplied as IMV_BUNDLE_SUMS_SHA (IMV-filed);
   sub-SUMS `a63150b5e7994862802f118e173eda3cc4761d7a6f10d448d18f4073167a1dc6`
   and `5d64a848bb5e903350051820d3a85faa941e3f9c755b75833f3d6ca73e6ad3d8`).
3. No prod env vars. Scripts refuse them.
4. Sandbox deny plus **EPERM_OK** sealed: confirm `EPERM_OK` in `OUT`
   (`$OUT/EPERM_PROBE.txt`) **and** in the seal
   (`$SEAL/EPERM_PROBE.txt`). Missing either → STOP.
5. Store sha on the box before that run's seal (K-4 / B-3).
6. Tar zero parquet plus the timing in §4.
7. a BLOCKED build is not sealed; a BLOCKED seal still seals and is reported BLOCKED.
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

## 0b. Fresh stamped IMV folder (K-1, L-2, both SUMS pins)

```bash
set -euo pipefail
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
BASE="$WT"
test "$(git -C "$WT" rev-parse HEAD)" = "b1d857d356d5afc422c86ffb1e9a25afdf2a4225"

# PR / Desktop copy of scripts/nfl/imv — NOT $WT/scripts
SRC=/abs/nfl-imv-v26-from-pr/scripts/nfl/imv
IMV=/var/tmp/nfl-imv-bundle-v26-$(date -u +%Y%m%dT%H%M%SZ)
test ! -e "$IMV"
mkdir "$IMV"   # no -p; never rm -rf
# L-2: SUMS from SRC only. No box paths on the Mac.
SUMS_V25="$SRC/SHA256SUMS.v2.5"
SUMS="$SRC/SHA256SUMS"
SUMS_V262="$SRC/SHA256SUMS.v2.6.2"
SUMS_V261="$SRC/SHA256SUMS.v2.6.1"
test -f "$SUMS_V25"
test -f "$SUMS"
test -f "$SUMS_V262"
test -f "$SUMS_V261"
test "$(shasum -a 256 "$SUMS_V25" | awk '{print $1}')" = \
  "b0cf91da6cccac015877a6a4bdd7af66b9290085f61fe9b5ca340d7c61f8f8e2"
SUMS_PIN="${IMV_BUNDLE_SUMS_SHA:?IMV bundle SUMS sha required}"
test "$(shasum -a 256 "$SUMS" | awk '{print $1}')" = "$SUMS_PIN"
test "$(shasum -a 256 "$SUMS_V262" | awk '{print $1}')" = \
  "a63150b5e7994862802f118e173eda3cc4761d7a6f10d448d18f4073167a1dc6"
test "$(shasum -a 256 "$SUMS_V261" | awk '{print $1}')" = \
  "5d64a848bb5e903350051820d3a85faa941e3f9c755b75833f3d6ca73e6ad3d8"
while read -r _ name; do
  test -f "$SRC/$name"
  cp "$SRC/$name" "$IMV/$name"
done < "$SUMS"
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
# SUMS full sha supplied as IMV_BUNDLE_SUMS_SHA (IMV-filed)
PINS="$(python3 "$IMV/nfl_imv_v27.py" check-pins --imv-dir "$IMV" --sums-v25 "$SUMS_V25" --sums "$SUMS")"
printf '%s\n' "$PINS"
printf '%s\n' "$PINS" | python3 -c 'import json,sys; d=json.load(sys.stdin); raise SystemExit(0 if d.get("ok") is True else 6)'
# FAIL if IMV is inside WT
```

Box dest (CopyToBox from `~/Desktop`):

`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`

`<run>` = `retro-w4` or `retro-w5` or `retro-w6` or `w8-pregame`.

## 1. B-1 — PRE_RETRO freeze (no re-download)

**No re-download for W4–W6.** Do **not** run section-1 prestage or curl
for retro. Reuse the recorded stamp.

The attached Desktop manifest is not a bare shasum file (headers +
`DOWNLOADED_FILES` extra columns). Conversion, quoted exactly from
e3ae3984:

`awk '/^EVERY_FILE/{f=1;next} f&&NF==2' "$DESK"`

```bash
set -euo pipefail
PRE_RETRO=/var/tmp/nfl-imv-prestage-nflverse/20261022T173338Z
MANIFEST_PIN=4c287d5b2d5ce49cd606818ab15345c15ddb378049a4b21a21cc3580c3dbd1f2
DESK="$HOME/Desktop/nfl-imv-prestage-retro-manifest.txt"
test -d "$PRE_RETRO"
test -f "$DESK"
# CoS copies $DESK to the box and matches $MANIFEST_PIN. STOP until CoS confirms.
test "${COS_BOX_MANIFEST_OK:-}" = "1"
# B-1b: shasum -a 256, not sha256sum. Desktop listing vs pin (l.124).
test "$(shasum -a 256 "$DESK" | awk '{print $1}')" = "$MANIFEST_PIN"
# Fix: delete l.123 and, after l.124, run:
cd "$PRE_RETRO" && awk '/^EVERY_FILE/{f=1;next} f&&NF==2' "$DESK" | shasum -a 256 -c
# Then chmod -R a-w.
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

## B-2 — seven checks (verbatim; STOP on fail; before each build)

WT is **/Users/ryankos/kosedge-imv-plumb2-b1d857d3**.
(1) HEAD = b1d857d3 full
(2) diff --quiet HEAD
(3) ls-files --others --exclude-standard = 0
(4) sparse absent: `test ! -e "$(git -C "$WT" rev-parse --git-path info/sparse-checkout)"`
(5) ls-files -v '^[a-zS]' = 0
(6) strict per-path MISSING = 0
`git ls-files -z | while IFS= read -r -d '' p; do [ -e "$p" ] || [ -L "$p" ] || echo "MISSING $p"; done | wc -l` → 0
(mode-160000 gitlinks excluded only by name)
(7) sim path `services/model-service/src/services/nfl_simulator.py` plus `git ls-files --error-unmatch`

```bash
set -euo pipefail
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
[ "$(git -C "$WT" rev-parse HEAD)" = b1d857d356d5afc422c86ffb1e9a25afdf2a4225 ]
git -C "$WT" --no-optional-locks diff --quiet HEAD
[ "$(git -C "$WT" --no-optional-locks ls-files --others --exclude-standard | wc -l | tr -d ' ')" = 0 ]
v=$(git -C "$WT" config --get core.sparseCheckout || true); [ -z "$v" ] || [ "$v" = false ]; [ ! -e "$(git -C "$WT" rev-parse --git-path info/sparse-checkout)" ]
[ "$(git -C "$WT" --no-optional-locks ls-files -v | grep -c '^[a-zS]' || true)" = 0 ]
[ "$(cd "$WT" && git --no-optional-locks ls-files -z | while IFS= read -r -d '' p; do [ -e "$p" ] || [ -L "$p" ] || echo "MISSING $p"; done | wc -l | tr -d ' ')" = 0 ]
test -f "$WT/services/model-service/src/services/nfl_simulator.py" || exit 7; git -C "$WT" --no-optional-locks ls-files --error-unmatch services/model-service/src/services/nfl_simulator.py >/dev/null
```

## 2. Feature builds (network DENY; new --out each time)

Caps: W4 `4/3` · W5 `5/4` · W6 `6/5` · W8 `8/7`. pbp = game−1. W7 refused.
Fresh stamped dir. Never `$W4_PARTIAL`.
**W4 and W5 each get their own seal and tar, the same as W6.**
a BLOCKED build is not sealed; a BLOCKED seal still seals and is reported BLOCKED.

### W4 build (B-2 then build; STOP when store sha and evidence are on the box)

```bash
set -euo pipefail
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
[ "$(git -C "$WT" rev-parse HEAD)" = b1d857d356d5afc422c86ffb1e9a25afdf2a4225 ]
git -C "$WT" --no-optional-locks diff --quiet HEAD
[ "$(git -C "$WT" --no-optional-locks ls-files --others --exclude-standard | wc -l | tr -d ' ')" = 0 ]
v=$(git -C "$WT" config --get core.sparseCheckout || true); [ -z "$v" ] || [ "$v" = false ]; [ ! -e "$(git -C "$WT" rev-parse --git-path info/sparse-checkout)" ]
[ "$(git -C "$WT" --no-optional-locks ls-files -v | grep -c '^[a-zS]' || true)" = 0 ]
[ "$(cd "$WT" && git --no-optional-locks ls-files -z | while IFS= read -r -d '' p; do [ -e "$p" ] || [ -L "$p" ] || echo "MISSING $p"; done | wc -l | tr -d ' ')" = 0 ]
test -f "$WT/services/model-service/src/services/nfl_simulator.py" || exit 7; git -C "$WT" --no-optional-locks ls-files --error-unmatch services/model-service/src/services/nfl_simulator.py >/dev/null
BASE="$WT"
W4_PARTIAL=/var/tmp/nfl-imv-features/w4-20261022T173520Z
OUT4=/var/tmp/nfl-imv-features/w4-$(date -u +%Y%m%dT%H%M%SZ)
test "$OUT4" != "$W4_PARTIAL"
test ! -e "$OUT4"
PY="${IMV_PY:?IMV pinned python required}"
test -x "$PY"
[ "$("$PY" -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
"$PY" -c 'import pandas,pyarrow,numpy'
[ "$("$PY" -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
PYBIN="$(cd "$(dirname "$PY")" && pwd -P)"
test -x "$PYBIN/python3"
export PATH="$PYBIN:$PATH"
hash -r
[ "$(command -v python3)" = "$PYBIN/python3" ]
[ "$(python3 -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
[ "$(python3 -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$WT" --prestage "$PRE_RETRO" \
  --out "$OUT4" --game-week-cap 4 --pbp-week-cap 3
test "$(cat "$OUT4/EPERM_PROBE.txt")" = "EPERM_OK"
mkdir -p "$HOME/Desktop/CopyToBox/retro-w4"
cp "$OUT4/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/retro-w4/FEATURE_STORE.sha256"
cp "$OUT4/EPERM_PROBE.txt" "$HOME/Desktop/CopyToBox/retro-w4/EPERM_PROBE.txt"
mkdir -p /var/tmp/operator-pins
cp "$OUT4/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w4.sha256
# B-3: STOP. Separate seal block. Do not call sealed-v2.4.sh here.
```

### W4 seal

```bash
set -euo pipefail
: "${IMV_SEAL_ACK_W4:?IMV ack required}"
PY="${IMV_PY:?IMV pinned python required}"
test -x "$PY"
[ "$("$PY" -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
"$PY" -c 'import pandas,pyarrow,numpy'
[ "$("$PY" -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
PYBIN="$(cd "$(dirname "$PY")" && pwd -P)"
test -x "$PYBIN/python3"
export PATH="$PYBIN:$PATH"
hash -r
[ "$(command -v python3)" = "$PYBIN/python3" ]
[ "$(python3 -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
[ "$(python3 -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
IMV_FEATURE_STORE="$OUT4" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w4.sha256)" \
IMV_MANIFEST="$PRE_RETRO/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$WT" retrospective-w4w6
SEAL4=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
test "$(cat "$SEAL4/EPERM_PROBE.txt")" = "EPERM_OK"
```

### W5 build (B-2 then build; STOP when store sha and evidence are on the box)

```bash
set -euo pipefail
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
[ "$(git -C "$WT" rev-parse HEAD)" = b1d857d356d5afc422c86ffb1e9a25afdf2a4225 ]
git -C "$WT" --no-optional-locks diff --quiet HEAD
[ "$(git -C "$WT" --no-optional-locks ls-files --others --exclude-standard | wc -l | tr -d ' ')" = 0 ]
v=$(git -C "$WT" config --get core.sparseCheckout || true); [ -z "$v" ] || [ "$v" = false ]; [ ! -e "$(git -C "$WT" rev-parse --git-path info/sparse-checkout)" ]
[ "$(git -C "$WT" --no-optional-locks ls-files -v | grep -c '^[a-zS]' || true)" = 0 ]
[ "$(cd "$WT" && git --no-optional-locks ls-files -z | while IFS= read -r -d '' p; do [ -e "$p" ] || [ -L "$p" ] || echo "MISSING $p"; done | wc -l | tr -d ' ')" = 0 ]
test -f "$WT/services/model-service/src/services/nfl_simulator.py" || exit 7; git -C "$WT" --no-optional-locks ls-files --error-unmatch services/model-service/src/services/nfl_simulator.py >/dev/null
BASE="$WT"
W4_PARTIAL=/var/tmp/nfl-imv-features/w4-20261022T173520Z
OUT5=/var/tmp/nfl-imv-features/w5-$(date -u +%Y%m%dT%H%M%SZ)
test "$OUT5" != "$W4_PARTIAL"
test ! -e "$OUT5"
PY="${IMV_PY:?IMV pinned python required}"
test -x "$PY"
[ "$("$PY" -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
"$PY" -c 'import pandas,pyarrow,numpy'
[ "$("$PY" -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
PYBIN="$(cd "$(dirname "$PY")" && pwd -P)"
test -x "$PYBIN/python3"
export PATH="$PYBIN:$PATH"
hash -r
[ "$(command -v python3)" = "$PYBIN/python3" ]
[ "$(python3 -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
[ "$(python3 -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$WT" --prestage "$PRE_RETRO" \
  --out "$OUT5" --game-week-cap 5 --pbp-week-cap 4
test "$(cat "$OUT5/EPERM_PROBE.txt")" = "EPERM_OK"
mkdir -p "$HOME/Desktop/CopyToBox/retro-w5"
cp "$OUT5/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/retro-w5/FEATURE_STORE.sha256"
cp "$OUT5/EPERM_PROBE.txt" "$HOME/Desktop/CopyToBox/retro-w5/EPERM_PROBE.txt"
mkdir -p /var/tmp/operator-pins
cp "$OUT5/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w5.sha256
# B-3: STOP. Separate seal block. Do not call sealed-v2.4.sh here.
```

### W5 seal

```bash
set -euo pipefail
: "${IMV_SEAL_ACK_W5:?IMV ack required}"
PY="${IMV_PY:?IMV pinned python required}"
test -x "$PY"
[ "$("$PY" -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
"$PY" -c 'import pandas,pyarrow,numpy'
[ "$("$PY" -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
PYBIN="$(cd "$(dirname "$PY")" && pwd -P)"
test -x "$PYBIN/python3"
export PATH="$PYBIN:$PATH"
hash -r
[ "$(command -v python3)" = "$PYBIN/python3" ]
[ "$(python3 -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
[ "$(python3 -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
IMV_FEATURE_STORE="$OUT5" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w5.sha256)" \
IMV_MANIFEST="$PRE_RETRO/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$WT" retrospective-w4w6
SEAL5=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
test "$(cat "$SEAL5/EPERM_PROBE.txt")" = "EPERM_OK"
```

### W6 build (B-2 then build; STOP when store sha and evidence are on the box)

```bash
set -euo pipefail
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
[ "$(git -C "$WT" rev-parse HEAD)" = b1d857d356d5afc422c86ffb1e9a25afdf2a4225 ]
git -C "$WT" --no-optional-locks diff --quiet HEAD
[ "$(git -C "$WT" --no-optional-locks ls-files --others --exclude-standard | wc -l | tr -d ' ')" = 0 ]
v=$(git -C "$WT" config --get core.sparseCheckout || true); [ -z "$v" ] || [ "$v" = false ]; [ ! -e "$(git -C "$WT" rev-parse --git-path info/sparse-checkout)" ]
[ "$(git -C "$WT" --no-optional-locks ls-files -v | grep -c '^[a-zS]' || true)" = 0 ]
[ "$(cd "$WT" && git --no-optional-locks ls-files -z | while IFS= read -r -d '' p; do [ -e "$p" ] || [ -L "$p" ] || echo "MISSING $p"; done | wc -l | tr -d ' ')" = 0 ]
test -f "$WT/services/model-service/src/services/nfl_simulator.py" || exit 7; git -C "$WT" --no-optional-locks ls-files --error-unmatch services/model-service/src/services/nfl_simulator.py >/dev/null
BASE="$WT"
W4_PARTIAL=/var/tmp/nfl-imv-features/w4-20261022T173520Z
OUT6=/var/tmp/nfl-imv-features/w6-$(date -u +%Y%m%dT%H%M%SZ)
test "$OUT6" != "$W4_PARTIAL"
test ! -e "$OUT6"
PY="${IMV_PY:?IMV pinned python required}"
test -x "$PY"
[ "$("$PY" -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
"$PY" -c 'import pandas,pyarrow,numpy'
[ "$("$PY" -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
PYBIN="$(cd "$(dirname "$PY")" && pwd -P)"
test -x "$PYBIN/python3"
export PATH="$PYBIN:$PATH"
hash -r
[ "$(command -v python3)" = "$PYBIN/python3" ]
[ "$(python3 -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
[ "$(python3 -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$WT" --prestage "$PRE_RETRO" \
  --out "$OUT6" --game-week-cap 6 --pbp-week-cap 5
test "$(cat "$OUT6/EPERM_PROBE.txt")" = "EPERM_OK"
mkdir -p "$HOME/Desktop/CopyToBox/retro-w6"
cp "$OUT6/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/retro-w6/FEATURE_STORE.sha256"
cp "$OUT6/EPERM_PROBE.txt" "$HOME/Desktop/CopyToBox/retro-w6/EPERM_PROBE.txt"
mkdir -p /var/tmp/operator-pins
cp "$OUT6/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w6.sha256
# B-3: STOP. Separate seal block. Do not call sealed-v2.4.sh here.
```

### W6 seal

```bash
set -euo pipefail
: "${IMV_SEAL_ACK_W6:?IMV ack required}"
PY="${IMV_PY:?IMV pinned python required}"
test -x "$PY"
[ "$("$PY" -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
"$PY" -c 'import pandas,pyarrow,numpy'
[ "$("$PY" -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
PYBIN="$(cd "$(dirname "$PY")" && pwd -P)"
test -x "$PYBIN/python3"
export PATH="$PYBIN:$PATH"
hash -r
[ "$(command -v python3)" = "$PYBIN/python3" ]
[ "$(python3 -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
[ "$(python3 -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
IMV_FEATURE_STORE="$OUT6" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w6.sha256)" \
IMV_MANIFEST="$PRE_RETRO/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$WT" retrospective-w4w6
SEAL6=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
test "$(cat "$SEAL6/EPERM_PROBE.txt")" = "EPERM_OK"
```

Confirm each sealed `OUT/store/SHA256SUMS` is last and seal `HELPERS.json`
has v21 `05027146…`, v22 `57a419b4…`, v23 `fe66b374…`, v24 `7c3f4dc7…`.
P-2: that JSON stops at v24 (logged).

## 3. W8 build + seal (only after K-3 W8 prestage)

### W8 build (B-2 then build; STOP when store sha and evidence are on the box)

```bash
set -euo pipefail
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
[ "$(git -C "$WT" rev-parse HEAD)" = b1d857d356d5afc422c86ffb1e9a25afdf2a4225 ]
git -C "$WT" --no-optional-locks diff --quiet HEAD
[ "$(git -C "$WT" --no-optional-locks ls-files --others --exclude-standard | wc -l | tr -d ' ')" = 0 ]
v=$(git -C "$WT" config --get core.sparseCheckout || true); [ -z "$v" ] || [ "$v" = false ]; [ ! -e "$(git -C "$WT" rev-parse --git-path info/sparse-checkout)" ]
[ "$(git -C "$WT" --no-optional-locks ls-files -v | grep -c '^[a-zS]' || true)" = 0 ]
[ "$(cd "$WT" && git --no-optional-locks ls-files -z | while IFS= read -r -d '' p; do [ -e "$p" ] || [ -L "$p" ] || echo "MISSING $p"; done | wc -l | tr -d ' ')" = 0 ]
test -f "$WT/services/model-service/src/services/nfl_simulator.py" || exit 7; git -C "$WT" --no-optional-locks ls-files --error-unmatch services/model-service/src/services/nfl_simulator.py >/dev/null
BASE="$WT"
W4_PARTIAL=/var/tmp/nfl-imv-features/w4-20261022T173520Z
OUT8=/var/tmp/nfl-imv-features/w8-$(date -u +%Y%m%dT%H%M%SZ)
test "$OUT8" != "$W4_PARTIAL"
test ! -e "$OUT8"
PY="${IMV_PY:?IMV pinned python required}"
test -x "$PY"
[ "$("$PY" -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
"$PY" -c 'import pandas,pyarrow,numpy'
[ "$("$PY" -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
PYBIN="$(cd "$(dirname "$PY")" && pwd -P)"
test -x "$PYBIN/python3"
export PATH="$PYBIN:$PATH"
hash -r
[ "$(command -v python3)" = "$PYBIN/python3" ]
[ "$(python3 -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
[ "$(python3 -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
bash "$IMV/nfl-imv-feature-build-v2.4.1.sh" --base "$WT" --prestage "$PRE_W8" \
  --out "$OUT8" --game-week-cap 8 --pbp-week-cap 7
test "$(cat "$OUT8/EPERM_PROBE.txt")" = "EPERM_OK"
mkdir -p "$HOME/Desktop/CopyToBox/w8-pregame"
cp "$OUT8/store/FEATURE_STORE.sha256" "$HOME/Desktop/CopyToBox/w8-pregame/FEATURE_STORE.sha256"
cp "$OUT8/EPERM_PROBE.txt" "$HOME/Desktop/CopyToBox/w8-pregame/EPERM_PROBE.txt"
cp "$OUT8/store/FEATURE_STORE.sha256" /var/tmp/operator-pins/w8.sha256
# B-3: STOP. Separate seal block. Do not call sealed-v2.4.sh here.
```

### W8 seal

```bash
set -euo pipefail
: "${IMV_SEAL_ACK_W8:?IMV ack required}"
PY="${IMV_PY:?IMV pinned python required}"
test -x "$PY"
[ "$("$PY" -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
"$PY" -c 'import pandas,pyarrow,numpy'
[ "$("$PY" -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
PYBIN="$(cd "$(dirname "$PY")" && pwd -P)"
test -x "$PYBIN/python3"
export PATH="$PYBIN:$PATH"
hash -r
[ "$(command -v python3)" = "$PYBIN/python3" ]
[ "$(python3 -c 'import sys;print(sys.version.split()[0])')" = "${IMV_PY_VERSION:?}" ]
[ "$(python3 -m pip freeze --all | LC_ALL=C sort | shasum -a 256 | awk '{print $1}')" = "${IMV_PY_FREEZE_SHA:?}" ]
WT=/Users/ryankos/kosedge-imv-plumb2-b1d857d3
IMV_FEATURE_STORE="$OUT8" \
IMV_FEATURE_STORE_SHA="$(cat /var/tmp/operator-pins/w8.sha256)" \
IMV_MANIFEST="$PRE_W8/imv-manifest.tsv" \
  bash "$IMV/nfl-imv-sealed-v2.4.sh" --base "$WT" w8-pregame
SEAL8=/var/tmp/nfl-imv-sealed-v2.4-w8-pregame/<STAMP>
test "$(cat "$SEAL8/EPERM_PROBE.txt")" = "EPERM_OK"
```

## 4. Tar only stamped folders; no parquet

**W4 and W5 each get their own seal and tar, the same as W6.**
Name the tars for CopyToBox →
`/workspace/ops/nfl_t4132u_audit_2026-10-22/runs/<run>/`.

**W8 tar before kickoff. Each retro tar before any results discussion.**

Before CopyToBox: `tar -tzf "$TAR" | grep -c '\.parquet$'` must be 0.
No top-level parent glob.

```bash
set -euo pipefail
SEAL4=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
TAR4="$HOME/Desktop/nfl-imv-v245-retro-w4-<STAMP>.tgz"
COPYFILE_DISABLE=1 tar -czf "$TAR4" \
  --exclude='*.parquet' \
  "$OUT4" \
  "$SEAL4" \
  "$PRE_RETRO/imv-manifest.tsv" \
  "$PRE_RETRO/imv-manifest.tsv.sha256" \
  /var/tmp/operator-pins/w4.sha256 \
  "$IMV"
tar -tzf "$TAR4" | grep '\.parquet$' && echo FAIL_PARQUET && exit 2
shasum -a 256 "$TAR4" | tee "$TAR4.sha256"

SEAL5=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
TAR5="$HOME/Desktop/nfl-imv-v245-retro-w5-<STAMP>.tgz"
COPYFILE_DISABLE=1 tar -czf "$TAR5" \
  --exclude='*.parquet' \
  "$OUT5" \
  "$SEAL5" \
  "$PRE_RETRO/imv-manifest.tsv" \
  "$PRE_RETRO/imv-manifest.tsv.sha256" \
  /var/tmp/operator-pins/w5.sha256 \
  "$IMV"
tar -tzf "$TAR5" | grep '\.parquet$' && echo FAIL_PARQUET && exit 2
shasum -a 256 "$TAR5" | tee "$TAR5.sha256"

SEAL6=/var/tmp/nfl-imv-sealed-v2.4-retrospective-w4w6/<STAMP>
TAR6="$HOME/Desktop/nfl-imv-v245-retro-w6-<STAMP>.tgz"
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
# CopyToBox each pair → .../runs/retro-w4/ retro-w5/ retro-w6/ before discussing results

SEAL8=/var/tmp/nfl-imv-sealed-v2.4-w8-pregame/<STAMP>
TAR8="$HOME/Desktop/nfl-imv-v245-w8-pregame-<STAMP>.tgz"
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

# nfl-hist-stage-b-t4923u

Bounded hist reconstruction **parity + coverage** pilot (t4923u). DRAFT research packet.

- Step 0: `STAGE_B_GAME_SELECTION_t4923u.md` (sealed before PBP)
- Rebuild: `build_recon_t4923u.py` (reuses W2 7e77c57f T1–T4)
- Report: `STAGE_B_PARITY_COVERAGE_REPORT_t4923u.md`

Reproduce (after Step 0 files exist):

1. Place `games.csv` pin 4fe1cdd7 at `data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv` (PR #638).
2. Remount `play_by_play_2016.parquet` / `2017` to `/workspace/data/raw/nfl/pbp/t4696u_s1_restage/` and sha256-match 95eba04e / 84eacd96 **before parse**.
3. Keep W2 builder + `RECON_MATRIX.csv` (708513db) at `data/ops/nfl-hist-bt-stage1b-w2-t4893u/`.
4. `python3 data/ops/nfl-hist-stage-b-t4923u/build_recon_t4923u.py`

CERT=0. No scoring. Stage C not authorized.

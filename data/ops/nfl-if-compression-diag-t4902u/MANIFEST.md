# Manifest — nfl-if-compression-diag-t4902u

READ-ONLY packet. No model code changed.

| File | Role |
|---|---|
| `DIAGNOSIS.md` | OWNER-readable verdict A/B/C, evidence, signed gaps, market orientation, bans |
| `TRACE.json` | Full intermediates (ratings → contract → transforms → μ → margin) + league audit |
| `TRACE_TEN_at_CIN.md` | Per-game trace |
| `TRACE_IND_at_JAX.md` | Per-game trace |
| `TRACE_ARI_at_DAL.md` | Per-game trace |
| `PINS.json` | Bound tips / sha256 |
| `SHA256SUMS` | Packet hashes |
| `COS_NOTE.md` | Short CoS note (`no prior grades`) |
| `replay_trace.py` | Repro: existing IF caller only |

```bash
# Replay requires IF tip 6ca03716 (not this PR's deploy-vercel tip).
PYTHONPATH=services/model-service python3 data/ops/nfl-if-compression-diag-t4902u/replay_trace.py
```

# RECEIPT t4768u — CLEAR-P1 local shadow E2E

**DRAFT only. Not merged. Not deployed.**

| | |
|--|--|
| Authority | DECISION `23c825de` · ORDER `a39c8f63` · plan sha8 `69b9ef5f` (PR #662) |
| Scope | Local D3 fixture → IF (`market_blend=0`) → L0 → L1 missing → pinned L4 |
| Tip parent | `1b39f4e9` (#657 CLEAR-A) |

## Artifacts

| File | Role |
|------|------|
| `scripts/nfl/shadow_handicap_e2e_t4761u.py` | Orchestrator (no live callers) |
| `services/model-service/tests/test_nfl_shadow_handicap_e2e_t4761u.py` | Deterministic tests |
| `data/ops/nfl-shadow-e2e-t4768u/receipt.json` | Auditable receipt |
| `data/ops/nfl-shadow-e2e-t4768u/ledger.jsonl` | Append-only L0/L1/L4 |

## Pins (this run)

| Item | Value |
|------|-------|
| Receipt core sha256 | `80b31800a30432db22133400825cf09d578e26665702f5f81399d51f21772b3b` |
| Receipt file sha256 | `32d7cd5f3150228488e6ca18ffbcaa43a18900897c222d21cfa1a748bb72c9d9` |
| Ledger file sha256 | `ac4bf1c1ab7fec134d2648efcfb151f6de276de83f2da3480fd90936fcc9e3b6` |
| D3(ii) blended SHA | `75ee2ee90dfb423c21cd66c8caab999cea20fda7277676e4944416596fac6224` (match) |
| IF market_blend | `0` |
| IF margin_mu / total_mu / sigma | `0.15714686663257818` / `43.8164760328315` / `10.0182` |
| L0 | `hl_c89bedb2217a92df2765d715d7dc9c56` |
| L1 (missing injury_availability, weather) | `hl_e72bc1a4046ff83b63c698a2d3f3ff1e` · `hl_b69c567e4c2bc6804a51ea9cd2fa1339` |
| L4 (pin-d3ii-3.5-43.5, not used as fair) | `hl_4f4c060ac0c4ad17838560f7c8e5a8bc` |
| Coming Soon / CERT | ON / 0 |
| HF rows | 0 |

## Tests

```bash
cd services/model-service
PYTHONPATH=. python3 -m pytest \
  tests/test_nfl_shadow_handicap_e2e_t4761u.py \
  tests/test_nfl_handicap_clear_a_*.py -q
# 41 passed (15 P1 + 26 CLEAR-A)
```

## Not done (HOLD)

P2/P3 · HF layer · DDL · Odds · Railway/C10 · live callers · merge to deploy-vercel · H-IFT-1 E2/E3 · EPA-trail / FAMILY_S1_LOOKS

Locks: NFL NO-GO · CERT=0 · Coming Soon ON · F2 frozen · C10 HOLD · overlays OFF

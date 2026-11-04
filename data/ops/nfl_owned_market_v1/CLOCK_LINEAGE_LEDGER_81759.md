# IDENTITY / CLOCK LEDGER — 81759 (t5329u)

CERT=0. Machine: `CLOCK_LINEAGE_LEDGER_81759.json`
sha256 `ce188c64f6d52c98ca76301455bf2654d30a6a59029cc5d7845944d7087bc5d7`.

Parent EVIDENCE 70648 Cos ACCEPT 451ea843 preserved.
`owned_completion_claimed=false`. freeze `#limitations` **not** marked verified.

## GATE0 / staged verify

| | |
|---|---|
| host | `cursor` · `bc-02a716be` |
| free | 245.324604 GiB on `/dev/vdc` · PASS |
| start | `98ec5d86` · Codex `8c0a04fb` |
| identities | `codex_staged/CSV_PROVIDER_EVENT_IDENTITIES.json` |
| sha256 | `f03041adfb6720f2de2600f6ec8d7db410e38084fbebac303f58fcdfb9d5ced5` **MATCH** |

Namespaces: provider `event_id` ≠ canonical `game_id`. Literal overlap 0 is expected.

## Proven mappings

**23 / 23** provider events → unique freeze selected REG `game_id`.
**44 / 44** CSV book associations inherit those game_ids.

Join key (no slop): exact `commence_time == kickoff_utc` + NFL REG season (month≥3) + explicit full-name → freeze source abbr.

Source-aware Rams/Chargers: freeze/ADMISSIBLE selected set uses `LA` (Rams) and `LAC` (Chargers) as distinct tokens. Short `"LA"` / `"Los Angeles"` / `"NY"` / `"Washington"` refused.

Uniqueness: bijection 23↔23 · `time_tolerance_seconds=0` · `ambiguous_abbreviation_fallback=false`.

## Remaining HOLD gaps (exact)

| field | locator | status |
|---|---|---|
| `publication_timestamp_status` | `7834cbc7:…/MARKET_ARM_FREEZE.json#limitations` | still **unverified** |
| `observation_timestamp_status` | same | still **unverified** |
| JSONL `captured_at\|available_at\|observed_at` | ADMISSIBLE / freeze quotes | unproven |
| **143 JSONL unknown clocks** | 187−44 | preserved |
| contemporaneous model availability | `pulled_at` 2026-08-18 | **not** causal |
| price/export lineage · all-187 coverage | — | **not claimed** |

Identity success is not scientific GO.

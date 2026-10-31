# EXEC CARD t4921u — #4 R1 Confirmatory (Cursor) · for CoS dispatch
Date: 2026-10-31 · From: Alex Rourke · Status: AWAITING CoS CLEAR/DISPATCH (not self-run) · NFL NO-GO · CERT=0

Governing protocol: ALEX_PROTOCOL_t4921u_HASH4_R1_BOUNDED_CONFIRMATION_v1.md
sha256 a1b4f03e2c5ee2c2dacee7b1ea21fd36584a656efe6920fa27629c467cb82b25 (sha8 a1b4f03e). Protocol governs on any conflict.

Goal: run the confirmatory addendum EXACTLY per protocol, one shot, and seal.

Inputs (read-only): parent Card A tip aa9605dc / seal 1f4ffde3 (RO b5de5df1); GAMES.json c73a9c0c… (captured pre-clamp μ_h, μ_a, σ; sealed P_model_home_win); SPEC fe4dc220 bands; IF 6ca03716; SOURCE 52d9e909; blend=0.
Frozen: 13 games in GAMES.json order (TNF CAR@GB excluded) · N=200_000/game · seed 49210000+i (i=0..12) · random.Random(seed).gauss home then away, max(0,·) · J9 uses sealed P_model (if regen: exact conv or MC N≥1e6 seed 49211999, sealed governs) · bands verbatim · no_rerun_until_pass=true.

Outputs: eval_w8_t4871u_coherence_r1_confirm_t4921u/ containing FROZEN_CONFIG.json (incl. protocol sha, sys.version), RESULTS.json (per-game stats + draw_array_sha256), TABLE_B.md/json (full audit), VERDICT_R1.json (four R1 checks → R1_PASS | R1_CONDITIONAL | R1_FAIL | BLOCKED; J11 status), PARENT_DIGESTS.json (parent files unchanged), CALL_AUDIT.json (zero Odds calls), SHA256SUMS.

Holds: no edit/reseed/tip swap of parent packet; no SOURCE/math/blend change; no reconstructed means; no Odds; no 2024–25; no merge/push to main; no pub/bet claims.
Stop: after seal, notify CoS + Alex for RO. One shot — result stands regardless of band.

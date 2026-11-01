# Later phases — DESIGN ONLY (t5044u)

**Do not execute in this PR.** Listed so a later ticket can freeze protocol
without inventing it after a look.

## 3. Alex pre-IF RO

RO of Gate 1 seal + Gate 2 recon/blocker. Confirm PBP remount plan if W9–W17
are to be completed. No IF until PASS.

## 4. IF + emit (after CLEAR)

- IF @ **6ca03716**, blend=0, sims=4000, game-ID seed
  `201710 + (int(sha256(game_id.encode()).hexdigest()[:12], 16) % 1000003)`.
- Rest BIND_PACKET_ONLY (sealed ET DOW). Not tip `90bf65ab`.
- Complete 27/27 only. Partial T2 stay visible, not scored.
- Emit `research.q2s.margin_mu_q2s = 0.5*IF.margin_mu + 0.5*q2_pm_new`.
- No aggregate metrics yet.

## 5. Freeze + receipt

Freeze **code / config / source / manifest / baseline rows / candidate rows**
and the metric protocol. Alex timestamped pre-look PASS **bound to those
hashes** (not `FREEZE.exists()` — t5035u / `404a4ab2`). Compare re-hashes
and refuses if the receipt is absent or mismatched.

## 6. ONE look

Paired ΔMAE + paired bootstrap B=10000 seed **20261102**. Week-block
sensitivity: 11 blocks, same B/seed. RMSE / weekly descriptive only.
If CI contains 0 → **INCONCLUSIVE**. No favorable claim if analyses disagree.
No second weight. No re-look of the examined 70. `03a4dd90` stays CLOSED.

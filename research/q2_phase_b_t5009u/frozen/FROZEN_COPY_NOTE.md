# FROZEN packet copy (t5018u writer)

Byte-identical copies of the sealed #679 FROZEN packet so this research
tree can verify pins without writing `ops/nfl_enterprise_green_t4359u/`.

- `FROZEN_CONFIG_Q2PB_t5009u.md` content sha256 prefix `28c582a1` (FROZEN md SoT)
- JSON `fit_object_sha256` prefix `70db070d` (sealed fit object)
- JSON `config_sha256` prefix `aa2b47b3` (sealed config)

Do not retune. Do not re-hash into a new fit. Writer applies `a_q2` / `b_q2` / λ / r only.

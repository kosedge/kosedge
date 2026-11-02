# Packaged QB1 flag and K-2 scan limits

R-1 values (distinct):

| value | meaning |
| --- | --- |
| `NOT_RECORDED` | no load was attempted for that season |
| `ABSENT` | a load ran; packaged depth file was missing |
| `PRESENT` | a load ran; packaged depth file was used |

Key: `packaged_qb1_flag` on `TeamContinuity.to_drivers()`.

## Downstream consumers of `to_drivers()` / continuity drivers

All of these store the dict or read known keys with `.get`. An extra
`packaged_qb1_flag` key is accepted (not unpacked positionally, not
schema-validated).

| consumer | how it uses the dict |
| --- | --- |
| `continuity_score.attach_continuity_drivers` | `out["continuity"] = continuity.to_drivers()` |
| `tasks.py` ~l.1248 | `pkg.notes["continuity"] = cont.to_drivers()` |
| `true_pr_product._load_continuity_qb_overlays` | `cont_overlay[team] = cont.to_drivers()` (lazy import; not W8 import-time) |
| `true_pr_product` continuity display (`_as_dict` / `.get`) | reads `continuity_score`, `band`, `fidelity`, `factors`, `prior_travel_weight` only |
| `tests/test_nfl_continuity_score.py` | asserts known keys; extra key ignored |
| `tests/test_nfl_true_pr_product_surface.py` | reads `available` / `band` on the display projection |
| `tests/test_nfl_w8_fail_closed.py` | asserts `packaged_qb1_flag` |

No consumer requires a closed key set. `true_pr_product.py` was not edited
(it is in the route-(b) 33-module import-time closure).

## K-2 opaque-load scan

Detected (STOP): non-literal `import_module` / `__import__` / `find_spec`
args; `getattr(..., "import_module"|"find_spec")`; `exec(`; `runpy`.

Known limits (not scanned): `compile()`, `eval()`, `importlib.machinery`,
custom loaders, `__loader__.load_module`, `zipimport`.

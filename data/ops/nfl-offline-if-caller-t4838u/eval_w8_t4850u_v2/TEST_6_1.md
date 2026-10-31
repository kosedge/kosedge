# TEST_6_1 fail-closed evidence

- cmd: `PYTHONPATH=services/model-service python3 scripts/nfl/run_offline_if_eval_w8_t4850u_v2.py --test-6-1-missing-field`
- exit: `2`
- passed: `True`
- imputed: `False`

## stdout

```
{
  "code": "INPUTS_INCOMPLETE",
  "contract": "b41f4b43 \u00a73/\u00a77",
  "exit_code": 2,
  "field": "home_off_epa_5g",
  "imputed": false,
  "message": "required contract fields missing: ['home_off_epa_5g']",
  "passed": true,
  "test": "6.1"
}
```

## stderr

```

```

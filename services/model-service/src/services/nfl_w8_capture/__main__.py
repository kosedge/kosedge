"""``python -m src.services.nfl_w8_capture`` — one-shot sealed-capture CLI.

Synthetic demo (no secrets, zero live Odds):

  cd services/model-service && PYTHONPATH=. NFL_W8_H1_AUTH_CITE=89fdd45f CREDENTIAL_POLICY=KEEP_EXISTING KEEP_AUTH_SHA8=a9ae5ae6 VERIFY_PASS_SHA8=e64e73ac H1C_AUTH_SHA8=89fdd45f T4500U_SHA8=20325274 ROTATION_ASSERTED=false python3 -m src.services.nfl_w8_capture --synthetic --bundle-dir /tmp/nfl-w8-synthetic-demo
"""

from src.services.nfl_w8_capture.oneshot import main

if __name__ == "__main__":
    raise SystemExit(main())

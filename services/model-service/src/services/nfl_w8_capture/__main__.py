"""``python -m src.services.nfl_w8_capture`` — one-shot sealed-capture CLI.

Exact argv (no secrets):

  cd services/model-service && PYTHONPATH=. python -m src.services.nfl_w8_capture --game-id <GAME_ID> --kickoff-utc <KICKOFF_UTC>
"""

from src.services.nfl_w8_capture.oneshot import main

if __name__ == "__main__":
    raise SystemExit(main())

"""CLI to record a known offseason roster move (departure, trade,
retirement, notable signing, or long-term injury known before the season
starts) into `nfl_roster_continuity_adjustments`.

This is the human-in-the-loop mechanism described in
services/model-service/src/services/nfl_roster_continuity.py: rather than
mutating the season-average+market preseason prior directly, entries here
flow through the same offense_multiplier/defense_multiplier path as the
in-season injury nowcast, applied at simulation time, so they stay
inspectable and easy to remove/adjust later.

Usage:
    python scripts/nfl/add_roster_adjustment.py \\
        --team CLE --position-group EDGE --impact-score -0.6 \\
        --reason trade --player-name "Myles Garrett" \\
        --notes "Traded to LA; placeholder magnitude, see notes." \\
        [--season 2026] [--source manual]

List existing entries for a team:
    python scripts/nfl/add_roster_adjustment.py --team CLE --list

Deactivate (soft-delete) an entry by id:
    python scripts/nfl/add_roster_adjustment.py --deactivate 3
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "model-service"))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ryankos:postgres@127.0.0.1:5432/kosedge")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

VALID_REASONS = {"departure", "trade", "retirement", "injury", "signing", "other"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--team", help="Team abbreviation, e.g. CLE")
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--player-name", dest="player_name", default=None)
    parser.add_argument(
        "--position-group",
        dest="position_group",
        help="One of QB/WR/RB/TE/OL/DL/EDGE/LB/DB/CB/S/K/P/OFFENSE/DEFENSE (see nfl_roster_continuity.py)",
    )
    parser.add_argument(
        "--impact-score",
        dest="impact_score",
        type=float,
        help="-1..1. Negative = team got worse (departure/injury). Positive = team got better (signing/return).",
    )
    parser.add_argument("--reason", choices=sorted(VALID_REASONS), default="departure")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--notes", default=None)
    parser.add_argument("--list", action="store_true", help="List active entries for --team (and --season if given)")
    parser.add_argument("--deactivate", type=int, default=None, metavar="ID", help="Soft-delete an entry by id")
    args = parser.parse_args()

    engine = create_engine(os.environ["DATABASE_URL"])
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        if args.deactivate is not None:
            session.execute(
                text("UPDATE nfl_roster_continuity_adjustments SET active = false, updated_at = NOW() WHERE id = :id"),
                {"id": args.deactivate},
            )
            session.commit()
            print(f"Deactivated entry id={args.deactivate}.")
            return

        if args.list:
            if not args.team:
                raise SystemExit("--list requires --team")
            rows = session.execute(
                text(
                    """
                    SELECT id, season, team, player_name, position_group, impact_score,
                           reason, source, notes, active, created_at
                    FROM nfl_roster_continuity_adjustments
                    WHERE team = :team AND season = :season
                    ORDER BY created_at
                    """
                ),
                {"team": args.team, "season": args.season},
            ).fetchall()
            if not rows:
                print(f"No entries for {args.team} season={args.season}.")
                return
            for r in rows:
                m = dict(r._mapping)
                status = "active" if m["active"] else "inactive"
                print(
                    f"  [{m['id']:>3}] {m['team']} {m['season']} {m['position_group']:<10} "
                    f"impact={float(m['impact_score']):+.2f} reason={m['reason']:<10} "
                    f"source={m['source']:<8} ({status}) player={m['player_name']!r} notes={m['notes']!r}"
                )
            return

        if not args.team or not args.position_group or args.impact_score is None:
            raise SystemExit("--team, --position-group, and --impact-score are required to add an entry")
        if not (-1.0 <= args.impact_score <= 1.0):
            raise SystemExit("--impact-score must be between -1 and 1")

        row = session.execute(
            text(
                """
                INSERT INTO nfl_roster_continuity_adjustments
                    (season, team, player_name, position_group, impact_score, reason, source, notes)
                VALUES
                    (:season, :team, :player_name, :position_group, :impact_score, :reason, :source, :notes)
                RETURNING id
                """
            ),
            {
                "season": args.season,
                "team": args.team,
                "player_name": args.player_name,
                "position_group": args.position_group,
                "impact_score": args.impact_score,
                "reason": args.reason,
                "source": args.source,
                "notes": args.notes,
            },
        ).fetchone()
        session.commit()
        print(
            f"Inserted id={row[0]}: {args.team} {args.season} {args.position_group} "
            f"impact_score={args.impact_score:+.2f} reason={args.reason} "
            f"player={args.player_name!r}"
        )
        print(
            "This will apply the next time fetch_nfl_injury_nowcast() runs for this team/season "
            "(e.g. on the next simulation re-run)."
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()

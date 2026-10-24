# Week column ignored — file:line

## Frozen fit `8d188da2` `load_rosters` (L289–314)

```
def load_rosters() -> ...:
    ...
    depth: Dict[Tuple[int, str, str], Dict[str, Any]] = {}
    for season in range(2012, 2024):
        path = RAW / "rosters" / f"roster_{season}.csv"
        ...
        for row in _load_csv(path):
            year = int(row.get("season") or season)
            ...
            pid = str(row.get("gsis_id") or "").strip()
            team = _alias(row.get("team") or "")
            if year >= 2013:
                by_team[year][team].add(pid)
                by_season[year].add(pid)
            pos = str(row.get("depth_chart_position") or row.get("position") or "").strip().upper()
            slot = str(row.get("depth_chart_position") or "").strip().upper()
            d = 1 if slot in STARTER_SLOTS else 2
            key = (year, team, pid)
            prev = depth.get(key)
            if prev is None or (d == 1 and prev.get("depth") != 1):
                depth[key] = {"position": pos or ..., "depth": d}
```

Fields read: `season`, `gsis_id`, `team`, `depth_chart_position`, `position`.
Fields present and unused: `week`, `game_type`, `status`.

The function body does not contain the substring `week`.

## Builder `247744d2` `load_rosters_dir` (L267–302)

Same key, same starter rule, same unused `week`. Schedule loader
(L217) and listings loader (L249) do read `week`. Roster loader does
not.

## CSV header (roster_2023.csv, sha `f98283e6`)

`season,team,position,depth_chart_position,...,gsis_id,...,week,game_type,status_description_abbr,...`

The week column exists. The builders ignore it.

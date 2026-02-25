#!/usr/bin/env python3
"""One-off: write data/raw/ratings/dratings_ratings_2026.csv from fetched table (stdlib only)."""
import csv
import re
from pathlib import Path

# Fetched 2025-02-13 from https://www.dratings.com/sports/ncaa-college-basketball-ratings/
# Table rows: | N. [Team Name](url)(W-L) | Overall | ...
TABLE_LINES = """
| 1. [Michigan Wolverines](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3004-michigan-wolverines)(25-1) | 4.6109 |
| 2. [Duke Blue Devils](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3001-duke-blue-devils)(24-2) | 4.2379 |
| 3. [Arizona Wildcats](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3005-arizona-wildcats)(24-2) | 4.1206 |
| 4. [Houston Cougars](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3149-houston-cougars)(23-3) | 3.7893 |
| 5. [Florida Gators](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3007-florida-gators)(20-6) | 3.6939 |
| 6. [Illinois Fighting Illini](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3018-illinois-fighting-illini)(22-5) | 3.6580 |
| 7. [Purdue Boilermakers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3124-purdue-boilermakers)(21-5) | 3.6342 |
| 8. [Iowa State Cyclones](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3046-iowa-state-cyclones)(23-3) | 3.6166 |
| 9. [Connecticut Huskies](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3040-connecticut-huskies)(24-3) | 3.5921 |
| 10. [Gonzaga Bulldogs](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3010-gonzaga-bulldogs)(26-2) | 3.3922 |
| 11. [Nebraska Cornhuskers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3116-nebraska-cornhuskers)(22-4) | 3.3375 |
| 12. [Michigan State Spartans](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3026-michigan-state-spartans)(21-5) | 3.2379 |
| 13. [Tennessee Volunteers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3050-tennessee-volunteers)(19-7) | 3.1585 |
| 14. [Alabama Crimson Tide](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3089-alabama-crimson-tide)(19-7) | 3.1347 |
| 15. [Louisville Cardinals](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3003-louisville-cardinals)(19-7) | 3.1321 |
| 16. [Vanderbilt Commodores](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3164-vanderbilt-commodores)(21-5) | 3.1134 |
| 17. [Brigham Young Cougars](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3053-brigham-young-cougars)(19-7) | 3.1124 |
| 18. [Kansas Jayhawks](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3002-kansas-jayhawks)(20-6) | 3.1113 |
| 19. [Texas Tech Red Raiders](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3215-texas-tech-red-raiders)(19-7) | 3.1036 |
| 20. [Virginia Cavaliers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3061-virginia-cavaliers)(23-3) | 3.0176 |
| 21. [Arkansas Razorbacks](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3078-arkansas-razorbacks)(19-7) | 2.9696 |
| 22. [St. John's Red Storm](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3097-st--john-s-red-storm)(21-5) | 2.9692 |
| 23. [Villanova Wildcats](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3106-villanova-wildcats)(21-5) | 2.6749 |
| 24. [Iowa Hawkeyes](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3043-iowa-hawkeyes)(19-7) | 2.6454 |
| 25. [Kentucky Wildcats](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3032-kentucky-wildcats)(17-9) | 2.6136 |
| 26. [Auburn Tigers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3200-auburn-tigers)(14-12) | 2.6024 |
| 27. [Wisconsin Badgers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3054-wisconsin-badgers)(18-8) | 2.5970 |
| 28. [NC State Wolfpack](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3017-nc-state-wolfpack)(19-8) | 2.5931 |
| 29. [Texas Longhorns](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3084-texas-longhorns)(17-9) | 2.5879 |
| 30. [Utah State Aggies](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3076-utah-state-aggies)(23-3) | 2.5356 |
| 31. [Saint Louis Billikens](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3052-saint-louis-billikens)(24-2) | 2.5112 |
| 32. [UNC Tar Heels](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3037-unc-tar-heels)(20-6) | 2.5014 |
| 33. [Ohio State Buckeyes](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3013-ohio-state-buckeyes)(17-9) | 2.4434 |
| 34. [Clemson Tigers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3117-clemson-tigers)(20-7) | 2.3821 |
| 35. [SMU Mustangs](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3152-smu-mustangs)(18-8) | 2.3693 |
| 36. [Miami Hurricanes](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3030-miami-hurricanes)(21-5) | 2.3599 |
| 37. [Indiana Hoosiers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3006-indiana-hoosiers)(17-9) | 2.3578 |
| 38. [Georgia Bulldogs](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3168-georgia-bulldogs)(18-8) | 2.3211 |
| 39. [Texas A&M Aggies](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3077-texas-a-m-aggies)(18-8) | 2.2976 |
| 40. [UCLA Bruins](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3039-ucla-bruins)(17-9) | 2.2324 |
| 41. [Saint Mary's College Gaels](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3057-saint-mary-s-college-gaels)(24-4) | 2.2293 |
| 42. [VCU Rams](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3016-vcu-rams)(21-6) | 2.0932 |
| 43. [Miami RedHawks](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3190-miami-redhawks)(26-0) | 2.0909 |
| 44. [Missouri Tigers](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3019-missouri-tigers)(18-8) | 2.0648 |
| 45. [UCF Knights](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3086-ucf-knights)(18-7) | 2.0550 |
| 46. [New Mexico Lobos](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3022-new-mexico-lobos)(20-6) | 2.0163 |
| 47. [Cincinnati Bearcats](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3012-cincinnati-bearcats)(14-12) | 2.0133 |
| 48. [USC Trojans](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3144-usc-trojans)(18-8) | 2.0107 |
| 49. [San Diego State Aztecs](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3028-san-diego-state-aztecs)(18-7) | 2.0045 |
| 50. [Santa Clara Broncos](https://www.dratings.com/teams/ncaa-college-basketball-ratings/3062-santa-clara-broncos)(22-6) | 1.9775 |
"""

def main():
    out_dir = Path(__file__).resolve().parent.parent / "data" / "raw" / "ratings"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dratings_ratings_2026.csv"
    team_re = re.compile(r"\[([^\]]+)\]")
    rows = []
    for line in TABLE_LINES.strip().splitlines():
        line = line.strip()
        if not line or not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) < 2:
            continue
        first = parts[0]
        rating_s = parts[1].split()[0] if parts[1] else ""
        m = team_re.search(first)
        team = m.group(1) if m else first
        try:
            rating = float(rating_s)
        except ValueError:
            continue
        rows.append({"team": team, "dratings_rating": rating})
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["team", "dratings_rating"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()

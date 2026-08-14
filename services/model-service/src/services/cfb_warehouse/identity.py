"""CFB warehouse identity spine — ESPN / packaged engine team codes.

Single source of truth for alias resolution. Historical calibration and
warehouse ingest both import from here. Do not invent peer substitutions
(Missouri is not Ole Miss). Unknown / FCS identities stay unmapped.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

ESPN_ABBR_TO_CODE: Dict[str, str] = {
    "ALA": "ALA",
    "APP": "APP",
    "ARIZ": "ARI",
    "ARI": "ARI",
    "ARK": "ARK",
    "ARMY": "ARMY",
    "ARST": "ARST",
    "ASU": "ASU",
    "AUB": "AUB",
    "BALL": "BALL",
    "BAY": "BAY",
    "BC": "BC",
    "BGSU": "BGSU",
    "BOIS": "BOISE",
    "BOISE": "BOISE",
    "BUFF": "BUFF",
    "BYU": "BYU",
    "CAL": "CAL",
    "CCU": "CCU",
    "CHAR": "CHAR",
    "CLT": "CHAR",
    "CIN": "CIN",
    "CLEM": "CLEM",
    "CMU": "CMU",
    "COLO": "COLO",
    "CONN": "CONN",
    "CSU": "CSU",
    "DEL": "DEL",
    "DUKE": "DUKE",
    "ECU": "ECU",
    "EMU": "EMU",
    "FAU": "FAU",
    "FIU": "FIU",
    "FLA": "UF",
    "FRES": "FRES",
    "FSU": "FSU",
    "GASO": "GASO",
    "GAST": "GAST",
    "GT": "GT",
    "HAW": "HAW",
    "HOU": "HOU",
    "ILL": "ILL",
    "IND": "IU",
    "IOWA": "IOWA",
    "ISU": "ISU",
    "IU": "IU",
    "JMU": "JMU",
    "JVST": "JVST",
    "JXST": "JVST",
    "KENN": "KENNESAW",
    "KENT": "KENT",
    "KSU": "KSU",
    "KU": "KU",
    "LIB": "LIB",
    "LOU": "LOU",
    "LSU": "LSU",
    "LT": "LT",
    "MD": "MD",
    "MEM": "MEM",
    "MIA": "MIA",
    "MICH": "MICH",
    "MINN": "MINN",
    "MISS": "MISS",
    "MIZ": "MIZZ",
    "MOST": "MOST",
    "MRSH": "MRSH",
    "MSST": "MSST",
    "MSU": "MSU",
    "MTSU": "MTSU",
    "NAVY": "NAVY",
    "NCSU": "NCSU",
    "ND": "ND",
    "NEB": "NEB",
    "NEV": "NEV",
    "NIU": "NIU",
    "NMSU": "NMSU",
    "NU": "NW",
    "NW": "NW",
    "ODU": "ODU",
    "OHIO": "OHIO",
    "OKST": "OKST",
    "ORE": "ORE",
    "ORST": "ORST",
    "OSU": "OSU",
    "OU": "OU",
    "PITT": "PITT",
    "PSU": "PSU",
    "PUR": "PUR",
    "RICE": "RICE",
    "RUT": "RUT",
    "RUTG": "RUT",
    "SC": "SCAR",
    "SCAR": "SCAR",
    "SDSU": "SDSU",
    "SHSU": "SHSU",
    "SJSU": "SJSU",
    "SMU": "SMU",
    "STAN": "STAN",
    "SYR": "SYR",
    "TAMU": "TAMU",
    "TA&M": "TAMU",
    "TCU": "TCU",
    "TEM": "TEM",
    "TENN": "TENN",
    "TEX": "TEX",
    "TLSA": "TLSA",
    "TOL": "TOL",
    "TROY": "TROY",
    "TTU": "TTU",
    "TULN": "TULN",
    "TXST": "TXST",
    "UAB": "UAB",
    "UCF": "UCF",
    "UCLA": "UCLA",
    "UF": "UF",
    "UGA": "UGA",
    "UK": "UK",
    "UL": "UL",
    "ULL": "UL",
    "ULM": "ULM",
    "UNC": "UNC",
    "UNLV": "UNLV",
    "UNM": "UNM",
    "UNT": "UNT",
    "USA": "USA",
    "USC": "USC",
    "USF": "USF",
    "USM": "USM",
    "USU": "UTAHST",
    "UTAH": "UTAH",
    "UTAHST": "UTAHST",
    "UTEP": "UTEP",
    "UTSA": "UTSA",
    "UVA": "UVA",
    "VAN": "VAN",
    "VT": "VT",
    "WAKE": "WAKE",
    "WASH": "WASH",
    "WIS": "WIS",
    "WKU": "WKU",
    "WMU": "WMU",
    "WSU": "WSU",
    "WVU": "WVU",
    "WYO": "WYO",
    "AFA": "AFA",
    "AKR": "AKR",
    "M-OH": "M-OH",
    "MASS": "MASS",
}

ESPN_NAME_TO_CODE: Dict[str, str] = {
    "Alabama Crimson Tide": "ALA",
    "Arizona Wildcats": "ARI",
    "Arizona State Sun Devils": "ASU",
    "Arkansas Razorbacks": "ARK",
    "Arkansas State Red Wolves": "ARST",
    "Auburn Tigers": "AUB",
    "Ball State Cardinals": "BALL",
    "Baylor Bears": "BAY",
    "Boise State Broncos": "BOISE",
    "Boston College Eagles": "BC",
    "Bowling Green Falcons": "BGSU",
    "Buffalo Bulls": "BUFF",
    "BYU Cougars": "BYU",
    "California Golden Bears": "CAL",
    "Central Michigan Chippewas": "CMU",
    "Charlotte 49ers": "CHAR",
    "Cincinnati Bearcats": "CIN",
    "Clemson Tigers": "CLEM",
    "Coastal Carolina Chanticleers": "CCU",
    "Colorado Buffaloes": "COLO",
    "Colorado State Rams": "CSU",
    "Duke Blue Devils": "DUKE",
    "East Carolina Pirates": "ECU",
    "Eastern Michigan Eagles": "EMU",
    "Florida Gators": "UF",
    "Florida Atlantic Owls": "FAU",
    "Florida International Panthers": "FIU",
    "Florida State Seminoles": "FSU",
    "Fresno State Bulldogs": "FRES",
    "Georgia Bulldogs": "UGA",
    "Georgia Southern Eagles": "GASO",
    "Georgia State Panthers": "GAST",
    "Georgia Tech Yellow Jackets": "GT",
    "Hawaii Rainbow Warriors": "HAW",
    "Houston Cougars": "HOU",
    "Illinois Fighting Illini": "ILL",
    "Indiana Hoosiers": "IU",
    "Iowa Hawkeyes": "IOWA",
    "Iowa State Cyclones": "ISU",
    "James Madison Dukes": "JMU",
    "Kansas Jayhawks": "KU",
    "Kansas State Wildcats": "KSU",
    "Kent State Golden Flashes": "KENT",
    "Kentucky Wildcats": "UK",
    "Louisiana Ragin' Cajuns": "UL",
    "Louisiana Tech Bulldogs": "LT",
    "Louisville Cardinals": "LOU",
    "LSU Tigers": "LSU",
    "Marshall Thundering Herd": "MRSH",
    "Maryland Terrapins": "MD",
    "Memphis Tigers": "MEM",
    "Miami Hurricanes": "MIA",
    "Miami (OH) RedHawks": "M-OH",
    "Michigan Wolverines": "MICH",
    "Michigan State Spartans": "MSU",
    "Minnesota Golden Gophers": "MINN",
    "Mississippi State Bulldogs": "MSST",
    "Missouri Tigers": "MIZZ",
    "Missouri State Bears": "MOST",
    "Navy Midshipmen": "NAVY",
    "NC State Wolfpack": "NCSU",
    "Nebraska Cornhuskers": "NEB",
    "Nevada Wolf Pack": "NEV",
    "New Mexico Lobos": "UNM",
    "New Mexico State Aggies": "NMSU",
    "North Carolina Tar Heels": "UNC",
    "North Texas Mean Green": "UNT",
    "Northwestern Wildcats": "NW",
    "Notre Dame Fighting Irish": "ND",
    "Ohio Bobcats": "OHIO",
    "Ohio State Buckeyes": "OSU",
    "Oklahoma Sooners": "OU",
    "Oklahoma State Cowboys": "OKST",
    "Old Dominion Monarchs": "ODU",
    "Ole Miss Rebels": "MISS",
    "Oregon Ducks": "ORE",
    "Oregon State Beavers": "ORST",
    "Penn State Nittany Lions": "PSU",
    "Pittsburgh Panthers": "PITT",
    "Purdue Boilermakers": "PUR",
    "Rice Owls": "RICE",
    "Rutgers Scarlet Knights": "RUT",
    "San Diego State Aztecs": "SDSU",
    "San José State Spartans": "SJSU",
    "San Jose State Spartans": "SJSU",
    "SMU Mustangs": "SMU",
    "South Alabama Jaguars": "USA",
    "South Carolina Gamecocks": "SCAR",
    "South Florida Bulls": "USF",
    "Southern Miss Golden Eagles": "USM",
    "Stanford Cardinal": "STAN",
    "Syracuse Orange": "SYR",
    "TCU Horned Frogs": "TCU",
    "Temple Owls": "TEM",
    "Tennessee Volunteers": "TENN",
    "Texas Longhorns": "TEX",
    "Texas A&M Aggies": "TAMU",
    "Texas State Bobcats": "TXST",
    "Texas Tech Red Raiders": "TTU",
    "Toledo Rockets": "TOL",
    "Troy Trojans": "TROY",
    "Tulane Green Wave": "TULN",
    "Tulsa Golden Hurricane": "TLSA",
    "UAB Blazers": "UAB",
    "UCF Knights": "UCF",
    "UCLA Bruins": "UCLA",
    "UConn Huskies": "CONN",
    "UL Monroe Warhawks": "ULM",
    "UNLV Rebels": "UNLV",
    "USC Trojans": "USC",
    "Utah Utes": "UTAH",
    "Utah State Aggies": "UTAHST",
    "UTEP Miners": "UTEP",
    "UTSA Roadrunners": "UTSA",
    "Vanderbilt Commodores": "VAN",
    "Virginia Cavaliers": "UVA",
    "Virginia Tech Hokies": "VT",
    "Wake Forest Demon Deacons": "WAKE",
    "Washington Huskies": "WASH",
    "Washington State Cougars": "WSU",
    "West Virginia Mountaineers": "WVU",
    "Western Kentucky Hilltoppers": "WKU",
    "Western Michigan Broncos": "WMU",
    "Wisconsin Badgers": "WIS",
    "Wyoming Cowboys": "WYO",
    "Air Force Falcons": "AFA",
    "Akron Zips": "AKR",
    "Appalachian State Mountaineers": "APP",
    "Army Black Knights": "ARMY",
    "Delaware Fightin' Blue Hens": "DEL",
    "Delaware Blue Hens": "DEL",
    "Kennesaw State Owls": "KENNESAW",
    "Jacksonville State Gamecocks": "JVST",
    "Liberty Flames": "LIB",
    "Louisiana-Monroe Warhawks": "ULM",
    "Massachusetts Minutemen": "MASS",
    "UMass Minutemen": "MASS",
    "Middle Tennessee Blue Raiders": "MTSU",
    "Northern Illinois Huskies": "NIU",
    "Sam Houston Bearkats": "SHSU",
}

# Only rename when the packaged universe uses a different canonical code.
# Do NOT invent peer substitutions (e.g. Missouri≠Ole Miss).
PACKAGED_CODE_ALIASES: Dict[str, str] = {
    "TA&M": "TAMU",
    "TXAM": "TAMU",
    "OLE": "MISS",
    "OREST": "ORST",
    "ULL": "UL",
    "FAU2": "FAU",
}

# ESPN abbreviation collisions that must never inherit the FBS code.
BLOCKED_NAMES = {
    "Findlay Oilers",
}


def canonical_code(code: str) -> str:
    raw = (code or "").strip().upper()
    return PACKAGED_CODE_ALIASES.get(raw, raw)


def resolve_team_code(
    *,
    abbr: str = "",
    name: str = "",
    known_codes: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    """Map ESPN team identity → packaged engine code (or None if FCS/unknown)."""
    name_s = (name or "").strip()
    abbr_u = (abbr or "").strip().upper()
    if name_s in BLOCKED_NAMES:
        return None
    if name_s in ESPN_NAME_TO_CODE:
        code = ESPN_NAME_TO_CODE[name_s]
    else:
        code = ESPN_ABBR_TO_CODE.get(abbr_u, abbr_u)
    code = canonical_code(code)
    if known_codes is None:
        return code if code else None
    if code in known_codes:
        return code
    if abbr_u in known_codes:
        return abbr_u
    return None


def known_engine_codes() -> Dict[str, bool]:
    return {
        **{c: True for c in ESPN_NAME_TO_CODE.values()},
        **{c: True for c in ESPN_ABBR_TO_CODE.values()},
        **{c: True for c in PACKAGED_CODE_ALIASES.values()},
    }


def alias_rows() -> list[dict[str, str]]:
    """Season-agnostic alias inventory for the warehouse team_aliases table."""
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    def add(alias: str, canonical: str, kind: str) -> None:
        key = (alias, canonical, kind)
        if key in seen:
            return
        seen.add(key)
        rows.append({"alias": alias, "team_id": canonical, "kind": kind, "season": 0})
    for abbr, code in ESPN_ABBR_TO_CODE.items():
        add(abbr, canonical_code(code), "espn_abbr")
    for name, code in ESPN_NAME_TO_CODE.items():
        add(name, canonical_code(code), "espn_name")
    for src, dst in PACKAGED_CODE_ALIASES.items():
        add(src, dst, "packaged_code")
    return rows

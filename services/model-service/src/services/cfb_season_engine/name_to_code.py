"""SP+ / public-table name → packaged FBS code.

P0 structural restore (2026-09-11): the 11 codes that silently fell through
to Independent + default 1.0 power must map. Missing names fail closed.
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional

from src.services.cfb_season_engine.team_features import MissingRequiredTeamFeature

# Model-QA list (2026-09-10): leftover Independent / null-power official FBS.
P0_REQUIRED_CODES = (
    "MIZZ",
    "ARST",
    "CSU",
    "ECU",
    "JVST",
    "NEV",
    "ODU",
    "TOL",
    "UAB",
    "UNM",
    "UNT",
)

# Public SP+ table + CFBD short names for the P0 codes.
P0_REQUIRED_NAME_TO_CODE: Dict[str, str] = {
    "Missouri": "MIZZ",
    "Missouri Tigers": "MIZZ",
    "Arkansas State": "ARST",
    "Arkansas State Red Wolves": "ARST",
    "Colorado State": "CSU",
    "Colorado State Rams": "CSU",
    "East Carolina": "ECU",
    "East Carolina Pirates": "ECU",
    "Jacksonville State": "JVST",
    "Jacksonville State Gamecocks": "JVST",
    "Nevada": "NEV",
    "Nevada Wolf Pack": "NEV",
    "Old Dominion": "ODU",
    "Old Dominion Monarchs": "ODU",
    "Toledo": "TOL",
    "Toledo Rockets": "TOL",
    "UAB": "UAB",
    "UAB Blazers": "UAB",
    "New Mexico": "UNM",
    "New Mexico Lobos": "UNM",
    "North Texas": "UNT",
    "North Texas Mean Green": "UNT",
    # ESPN final-2025 story abbreviations (year-locked carry source).
    "N. Texas": "UNT",
    "Arkansas St.": "ARST",
    "Colorado St.": "CSU",
    "Missouri St.": "MOST",
    "J'ville St.": "JVST",
    "ECU": "ECU",
    "ODU": "ODU",
    # Miami collision: Hurricanes vs RedHawks. Do not rely on table order alone.
    "Miami (OH)": "M-OH",
    "Miami (Ohio)": "M-OH",
    "Miami Ohio": "M-OH",
    "Miami-Ohio": "M-OH",
    "Miami (OH) RedHawks": "M-OH",
    "Miami-OH": "M-OH",
}

# ESPN story 46128861 (final-2025, published 2026-01-20) uses abbreviated
# display names. These 49 keys were the entire 87/136 "parser" miss — the
# HTML table is complete; unmapped abbreviations were dropped.
ESPN_FINAL_2025_STORY_NAME_TO_CODE: Dict[str, str] = {
    "Ohio St.": "OSU",
    "Penn St.": "PSU",
    "JMU": "JMU",
    "USF": "USF",
    "Iowa St.": "ISU",
    "Ga. Tech": "GT",
    "Florida St.": "FSU",
    "Kansas St.": "KSU",
    "San Diego St.": "SDSU",
    "S. Carolina": "SCAR",
    "NC St.": "NCSU",
    "Miss. St.": "MSST",
    "Arizona St.": "ASU",
    "Wash. St.": "WSU",
    "Boise St.": "BOISE",
    "Texas St.": "TXST",
    "Fresno St.": "FRES",
    "WKU": "WKU",
    "La. Tech": "LT",
    "WMU": "WMU",
    "Utah St.": "UTAHST",
    "Miami-OH": "M-OH",
    "Michigan St.": "MSU",
    "Kennesaw St.": "KENNESAW",
    "N. Carolina": "UNC",
    "W. Virginia": "WVU",
    "So. Miss": "USM",
    "Boston Coll.": "BC",
    "FAU": "FAU",
    "CMU": "CMU",
    "Ga. Southern": "GASO",
    "Va. Tech": "VT",
    "FIU": "FIU",
    "App. St.": "APP",
    "BGSU": "BGSU",
    "S. Alabama": "USA",
    "San Jose St.": "SJSU",
    "EMU": "EMU",
    "Oklahoma St.": "OKST",
    "Coastal Caro.": "CCU",
    "NMSU": "NMSU",
    "Oregon St.": "ORST",
    "MTSU": "MTSU",
    "N. Illinois": "NIU",
    "Kent St.": "KENT",
    "ULM": "ULM",
    "Ball St.": "BALL",
    "Georgia St.": "GAST",
    "UMass": "MASS",
}

# Public final-2025 SP+ table names (cfbupdate / ESPN story) + CFBD short names.
NAME_TO_CODE: Dict[str, str] = {
    "Indiana": "IU",
    "Ohio State": "OSU",
    "Oregon": "ORE",
    "Texas Tech": "TTU",
    "Ole Miss": "MISS",
    "Notre Dame": "ND",
    "Georgia": "UGA",
    "Utah": "UTAH",
    "Texas A&M": "TAMU",
    "Vanderbilt": "VAN",
    "Iowa": "IOWA",
    "Washington": "WASH",
    "Oklahoma": "OU",
    "Penn State": "PSU",
    "USC": "USC",
    "Texas": "TEX",
    "BYU": "BYU",
    "Tennessee": "TENN",
    "Alabama": "ALA",
    "Arizona": "ARI",
    "SMU": "SMU",
    "Illinois": "ILL",
    "Michigan": "MICH",
    "Louisville": "LOU",
    "James Madison": "JMU",
    "Auburn": "AUB",
    "South Florida": "USF",
    "Virginia": "UVA",
    "LSU": "LSU",
    "Iowa State": "ISU",
    "Clemson": "CLEM",
    "Georgia Tech": "GT",
    "TCU": "TCU",
    "Pittsburgh": "PITT",
    "Houston": "HOU",
    "Memphis": "MEM",
    "Florida State": "FSU",
    "Kansas State": "KSU",
    "Cincinnati": "CIN",
    "San Diego State": "SDSU",
    "Duke": "DUKE",
    "Nebraska": "NEB",
    "Tulane": "TULN",
    "South Carolina": "SCAR",
    "Northwestern": "NW",
    "Arkansas": "ARK",
    "UConn": "CONN",
    "Wake Forest": "WAKE",
    "Navy": "NAVY",
    "Mississippi State": "MSST",
    "NC State": "NCSU",
    "Kansas": "KU",
    "UNLV": "UNLV",
    "Arizona State": "ASU",
    "Washington State": "WSU",
    "Florida": "UF",
    "UTSA": "UTSA",
    "Boise State": "BOISE",
    "Fresno State": "FRES",
    "Kentucky": "UK",
    "Hawai'i": "HAW",
    "Hawaii": "HAW",
    "Baylor": "BAY",
    "Minnesota": "MINN",
    "Western Kentucky": "WKU",
    "Rutgers": "RUT",
    "Army": "ARMY",
    "Texas State": "TXST",
    "Maryland": "MD",
    "UCF": "UCF",
    "Louisiana Tech": "LT",
    "Western Michigan": "WMU",
    "Utah State": "UTAHST",
    "Air Force": "AFA",
    "California": "CAL",
    "Michigan State": "MSU",
    "Ohio": "OHIO",
    "Wisconsin": "WIS",
    "Marshall": "MRSH",
    "Troy": "TROY",
    "Temple": "TEM",
    "Kennesaw State": "KENNESAW",
    "Purdue": "PUR",
    "West Virginia": "WVU",
    "North Carolina": "UNC",
    "Southern Miss": "USM",
    "Buffalo": "BUFF",
    "Colorado": "COLO",
    "Boston College": "BC",
    "UCLA": "UCLA",
    "Florida Atlantic": "FAU",
    "Central Michigan": "CMU",
    "Liberty": "LIB",
    "Georgia Southern": "GASO",
    "Tulsa": "TLSA",
    "Louisiana": "UL",
    "Virginia Tech": "VT",
    "Florida International": "FIU",
    "Missouri State": "MOST",
    "Delaware": "DEL",
    "Wyoming": "WYO",
    "App State": "APP",
    "Appalachian State": "APP",
    "Stanford": "STAN",
    "Bowling Green": "BGSU",
    "South Alabama": "USA",
    "Syracuse": "SYR",
    "Rice": "RICE",
    "Akron": "AKR",
    "San José State": "SJSU",
    "San Jose State": "SJSU",
    "Oklahoma State": "OKST",
    "Eastern Michigan": "EMU",
    "Coastal Carolina": "CCU",
    "New Mexico State": "NMSU",
    "Oregon State": "ORST",
    "Middle Tennessee": "MTSU",
    "Northern Illinois": "NIU",
    "UTEP": "UTEP",
    "Kent State": "KENT",
    "UL Monroe": "ULM",
    "Ball State": "BALL",
    "Georgia State": "GAST",
    "Charlotte": "CHAR",
    "Sam Houston": "SHSU",
    "Massachusetts": "MASS",
    **P0_REQUIRED_NAME_TO_CODE,
    **ESPN_FINAL_2025_STORY_NAME_TO_CODE,
}


def mapped_code(name: str, mapping: Mapping[str, str] | None = None) -> Optional[str]:
    m = mapping if mapping is not None else NAME_TO_CODE
    code = m.get(str(name or "").strip())
    return str(code) if code else None


def resolve_public_table_name(
    name: str,
    *,
    miami_ordinal: int = 0,
    mapping: Mapping[str, str] | None = None,
) -> Optional[str]:
    """Map a public SP+ / ESPN-story name, including the Miami collision.

    Bare ``Miami`` is Hurricanes on the first sighting and RedHawks on later
    sightings (legacy table order). Explicit ``Miami (OH)`` variants always
    map to M-OH so official FBS never falls through to a 50-fill.
    """
    n = str(name or "").strip()
    if n in {
        "Miami (OH)",
        "Miami (Ohio)",
        "Miami Ohio",
        "Miami-Ohio",
        "Miami-OH",
        "Miami (OH) RedHawks",
    }:
        return "M-OH"
    if n == "Miami":
        return "MIA" if miami_ordinal <= 1 else "M-OH"
    return mapped_code(n, mapping)


def require_mapped_code(name: str, mapping: Mapping[str, str] | None = None) -> str:
    """Fail closed — never drop an official name into a silent None/1.0 fill."""
    code = mapped_code(name, mapping)
    if not code:
        raise MissingRequiredTeamFeature(
            f"Unmapped CFB name {name!r} — hard-fail, do not invent Independent/1.0"
        )
    return code


def assert_p0_codes_mapped(mapping: Mapping[str, str] | None = None) -> None:
    m = mapping if mapping is not None else NAME_TO_CODE
    missing = [c for c in P0_REQUIRED_CODES if c not in set(m.values())]
    if missing:
        raise MissingRequiredTeamFeature(
            f"NAME_TO_CODE missing required P0 codes: {missing}"
        )

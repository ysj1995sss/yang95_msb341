"""Where a posting is, for the Location filter (dogfood round 5, 2026-10-13).

Postings name one place many ways: a US job may say "United States", "Remote - USA", "Foster City, CA"
or just "Seattle". The filter used to match the typed text only, so "United States" found about a
quarter of the US jobs a search had. A country, state or province now also matches its other names;
anything else still matches part of the location, as before. A posting that names no country
("Remote", "Remote, Global") never counts as being in one."""

from __future__ import annotations

import re
from typing import Optional

US = "United States"
CANADA = "Canada"
UK = "United Kingdom"

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
CA_PROVINCES = {
    "ON": "Ontario", "BC": "British Columbia", "QC": "Quebec", "AB": "Alberta", "MB": "Manitoba",
    "SK": "Saskatchewan", "NS": "Nova Scotia", "NB": "New Brunswick", "NL": "Newfoundland and Labrador",
    "PE": "Prince Edward Island", "YT": "Yukon", "NT": "Northwest Territories", "NU": "Nunavut",
}
_SUBDIVISIONS = {**{a: (US, n) for a, n in US_STATES.items()}, **{a: (CANADA, n) for a, n in CA_PROVINCES.items()}}
_SUBDIVISION_NAMES = {name.casefold(): (country, abbr) for abbr, (country, name) in _SUBDIVISIONS.items()}

# Big cities postings often name alone ("Seattle"). A short list, not a gazetteer.
_CITIES = {
    US: {"new york", "new york city", "nyc", "brooklyn", "san francisco", "south san francisco", "seattle",
         "austin", "chicago", "boston", "los angeles", "santa monica", "denver", "atlanta", "mountain view",
         "palo alto", "menlo park", "sunnyvale", "san jose", "san diego", "redwood city", "foster city", "irvine",
         "miami", "dallas", "houston", "philadelphia", "pittsburgh", "salt lake city", "washington dc",
         "washington d.c.", "raleigh", "nashville", "phoenix", "minneapolis", "detroit", "portland"},
    CANADA: {"toronto", "vancouver", "montreal", "montréal", "ottawa", "calgary", "waterloo", "edmonton"},
    UK: {"london", "manchester", "edinburgh", "glasgow", "bristol", "belfast"},
}
# What a person may type for a country, and what postings say.
_ALIASES = {
    US: {"united states", "united states of america", "usa", "u.s.a.", "u.s.a", "u.s.", "u.s", "us"},
    CANADA: {"canada"},
    UK: {"united kingdom", "uk", "u.k.", "u.k", "great britain", "britain"},
}
# How a posting names each country. The case of US and UK matters: "us" is a word, not a country.
_NAMED = {
    US: (re.compile(r"\b(?:USA|US)\b"), re.compile(r"united states|\bu\.s\.", re.IGNORECASE)),
    CANADA: (re.compile(r"\bcanada\b", re.IGNORECASE),),
    UK: (re.compile(r"\b(?:UK|U\.K)\b"),
         re.compile(r"united kingdom|great britain|\b(?:england|scotland|wales)\b|northern ireland", re.IGNORECASE)),
}
_WORK_MODES = {"remote", "hybrid", "onsite", "on-site", "in-office", "in office", "flexible", "global"}


def _collapse(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _pieces(location: str) -> list:
    """Each place a location names: "San Francisco, CA | New York, NY" is two."""
    return [p for p in (re.sub(r"\(.*?\)", "", part).strip() for part in re.split(r"[|;/•·]", location)) if p]


def _parts(piece: str) -> list:
    """The comma or dash separated parts of one place, without work modes ("Hybrid - London": London)."""
    parts = [p.strip(" .") for p in re.split(r"\s*,\s*|\s+-\s+", piece)]
    return [p for p in parts if p and p.casefold() not in _WORK_MODES]


def _country_of(piece: str) -> Optional[str]:
    for country, patterns in _NAMED.items():
        if any(pattern.search(piece) for pattern in patterns):
            return country
    parts = _parts(piece)
    if not parts:
        return None
    last = parts[-1]
    if last.replace(".", "") in _SUBDIVISIONS:  # "Foster City, CA", "Washington, D.C."; never "Barcelona, CT, Spain"
        return _SUBDIVISIONS[last.replace(".", "")][0]
    if last.casefold() in _SUBDIVISION_NAMES:
        return _SUBDIVISION_NAMES[last.casefold()][0]
    if len(parts) == 1:  # "Seattle", "San Francisco Bay Area", "San Francisco HQ"
        name = last.casefold()
        return next((country for country, cities in _CITIES.items()
                     if any(name == city or name.startswith(city + " ") for city in cities)), None)
    return None


def _in_subdivision(piece: str, abbr: str) -> bool:
    country, name = _SUBDIVISIONS[abbr]
    if re.search(rf"\b{re.escape(name)}\b", piece, re.IGNORECASE):
        return True
    parts = [part.replace(".", "") for part in _parts(piece)]
    if parts and parts[-1] == abbr:
        return True
    # "Mountain View, CA, USA": the state, then its country.
    return len(parts) >= 2 and parts[-2] == abbr and _country_of(parts[-1]) == country


def canonical_place(piece: str) -> str:
    """One name per country, for the Location suggestions: "USA" and "U.S." are "United States"."""
    key = _collapse(piece).casefold()
    return next((country for country, names in _ALIASES.items() if key in names), piece)


def place_matches(location: Optional[str], wanted: Optional[str]) -> bool:
    """Whether a posting's location is in the place the person asked for."""
    wanted = _collapse(wanted)
    if not wanted:
        return True
    location = _collapse(location)
    key = wanted.casefold()
    country = next((c for c, names in _ALIASES.items() if key in names), None)
    if country:
        return any(_country_of(piece) == country for piece in _pieces(location))
    abbr = wanted.upper() if wanted.upper() in _SUBDIVISIONS else (_SUBDIVISION_NAMES.get(key) or (None, None))[1]
    if abbr and any(_in_subdivision(piece, abbr) for piece in _pieces(location)):
        return True
    # Part of the location, as before; a state's two letters only as the state ("CA" isn't "Chicago").
    if (len(key) > 2 or not abbr) and key in location.casefold():
        return True
    if "," in wanted:  # "San Francisco, CA": the city and the state, in the same place
        head, rest = (part.strip() for part in wanted.split(",", 1))
        return bool(head) and any(place_matches(piece, head) and place_matches(piece, rest)
                                  for piece in _pieces(location))
    return False

"""
Transit proximity scoring for GTA listings.

Scores are on a 0-10 scale:
  9-10  Subway/LRT station <5 min walk — top-tier access
  7-8   Subway/LRT station 5-15 min walk — excellent access
  5-6   Good bus grid / near LRT stop
  3-4   Decent local bus, suburban grid
  1-2   Limited transit, car-dependent

The final score is the maximum match across all corridor tables.
If no keyword match is found, the caller applies a city-level fallback
(Toronto=4, Mississauga=3, other GTA=2).
"""
from __future__ import annotations
from typing import Optional

# ── Ontario Line (under construction, ~2030) ────────────────────────────────
_ONTARIO_LINE: dict[str, int] = {
    "leslieville": 9,
    "riverside": 9,
    "corktown": 9,
    "distillery": 9,
    "east harbour": 10,
    "exhibition": 8,
    "ontario place": 8,
    "queen east": 8,
    "pape": 9,
    "donlands": 9,
    "greenwood": 9,
    "science centre": 9,
    "flemingdon": 8,
    "thorncliffe": 7,
    "little india": 8,
    "regent park": 9,
    "moss park": 9,
    "st. james town": 8,
    "cabbagetown": 8,
    "cabbagetow": 8,
    "rosedale": 7,
    "don mills": 8,
}

# ── Eglinton Crosstown LRT ───────────────────────────────────────────────────
_EGLINTON: dict[str, int] = {
    "mount dennis": 8,
    "keelesdale": 7,
    "fairbank": 8,
    "caledonia": 7,
    "dufferin grove": 7,
    "leaside": 9,
    "laird": 9,
    "bayview village": 8,
    "forest hill": 8,
    "midtown": 8,
    "yonge-eglinton": 10,
    "yonge eglinton": 10,
    "eglinton": 9,
    "davisville": 8,
    "chaplin estates": 7,
    "mt pleasant": 8,
    "mount pleasant": 8,
    "golden mile": 8,
    "kennedy": 7,
    "scarborough junction": 7,
    "avenue road": 7,
}

# ── TTC Yonge-University-Spadina Line ────────────────────────────────────────
_TTC_YONGE_UNIVERSITY: dict[str, int] = {
    # Downtown core
    "financial district": 9,
    "king west": 9,
    "king street": 8,
    "queen street west": 8,
    "queen west": 8,
    "dundas square": 9,
    "college street": 8,
    "bay street": 9,
    "bay corridor": 8,
    "st. patrick": 8,
    "st patrick": 8,
    "museum district": 8,
    "queen's park": 9,
    "queens park": 9,
    "university avenue": 8,
    "university ave": 8,
    # Midtown
    "summerhill": 8,
    "st. clair": 8,
    "st clair": 8,
    "deer park": 8,
    "moore park": 7,
    # North Toronto
    "lawrence park": 7,
    "bedford park": 7,
    "york mills": 8,
    "hoggs hollow": 7,
    "wilowdale": 7,
    "willowdale": 7,
    "sheppard-yonge": 9,
    "sheppard yonge": 9,
    "north york centre": 9,
    "north york city centre": 9,
    "mel lastman": 8,
    "finch": 8,
    "newtonbrook": 7,
    # West corridor (Spadina)
    "spadina": 8,
    "bloor annex": 8,
    "the annex": 8,
    "annex": 8,
    "ossington": 8,
    "dufferin": 7,
    "wilson heights": 7,
    "wilson": 7,
    "yorkdale": 8,
    "glen park": 7,
    "glencairn": 7,
    "lawrence west": 7,
    "allen road": 7,
    "downsview": 7,
    "york university": 7,
    "pioneer village": 6,
    "vaughan metropolitan": 8,
}

# ── TTC Bloor-Danforth Line ──────────────────────────────────────────────────
_TTC_BLOOR_DANFORTH: dict[str, int] = {
    # West
    "kipling": 8,
    "islington": 8,
    "royal york": 8,
    "old mill": 8,
    "jane street": 7,
    "runnymede": 8,
    "high park": 9,
    "keele": 7,
    "dundas west": 8,
    "lansdowne": 7,
    "dufferin bloor": 7,
    "ossington bloor": 8,
    "christie": 8,
    "bathurst bloor": 8,
    "bay bloor": 9,
    "bloor-yonge": 10,
    "bloor yonge": 10,
    "bloor street": 8,
    # East
    "sherbourne": 8,
    "castle frank": 7,
    "broadview": 9,
    "chester": 8,
    "greektown": 8,
    "danforth": 8,
    "playter estates": 7,
    "coxwell": 7,
    "woodbine": 7,
    "main street": 7,
    "victoria park": 7,
    "warden": 7,
    "scarborough": 6,
    "kennedy rd": 7,
    "bloor west village": 9,
    "junction triangle": 7,
    "the junction": 7,
    "swansea": 7,
    "parkdale": 7,
    "roncesvalles": 8,
}

# ── TTC Sheppard Subway ──────────────────────────────────────────────────────
_TTC_SHEPPARD: dict[str, int] = {
    "sheppard east": 8,
    "bayview sheppard": 8,
    "bessarion": 7,
    "leslie sheppard": 7,
    "don mills sheppard": 7,
    "oriole": 7,
    "consumers road": 7,
    "ibm": 6,
    "consumers": 6,
}

# ── Finch West LRT (under construction) ─────────────────────────────────────
_FINCH_WEST: dict[str, int] = {
    "finch west": 7,
    "humber college": 7,
    "etobicoke north": 6,
    "rexdale": 6,
    "martin grove": 6,
    "kipling finch": 7,
}

# ── Hurontario LRT (Mississauga, under construction) ────────────────────────
_HURONTARIO_LRT: dict[str, int] = {
    "port credit": 8,
    "lakeshore": 7,
    "cooksville": 7,
    "hurontario": 7,
    "mississauga city centre": 8,
    "city centre mississauga": 8,
    "square one": 8,
    "mississauga downtown": 8,
    "celebration square": 7,
    "shoppers world": 6,
    "bramalea": 6,
    "brampton downtown": 6,
    "main street brampton": 6,
}

# ── General Toronto well-served areas ────────────────────────────────────────
_TORONTO_GENERAL: dict[str, int] = {
    "downtown toronto": 9,
    "old toronto": 8,
    "downtown core": 9,
    "waterfront": 8,
    "entertainment district": 9,
    "fashion district": 8,
    "trinity bellwoods": 8,
    "little portugal": 7,
    "little italy": 7,
    "harbourfront": 8,
    "liberty village": 8,
    "little poland": 7,
    "greektown on the danforth": 8,
    "little tokyo": 7,
    "kensington market": 8,
    "chinatown toronto": 8,
    "little portugal toronto": 7,
    "corso italia": 7,
    "west queen west": 8,
    "church wellesley": 9,
    "church-wellesley": 9,
    "village toronto": 8,
    "st. lawrence market": 9,
    "st lawrence market": 9,
    "distillery district": 9,
    "south riverdale": 8,
    "north riverdale": 8,
    "east york": 6,
    "york toronto": 6,
    "north york": 7,
    "etobicoke": 6,
    "scarborough town": 6,
    "agincourt": 6,
    "malvern": 5,
    "rouge": 5,
    "highland creek": 5,
}

_ALL_TABLES = [
    _ONTARIO_LINE,
    _EGLINTON,
    _TTC_YONGE_UNIVERSITY,
    _TTC_BLOOR_DANFORTH,
    _TTC_SHEPPARD,
    _FINCH_WEST,
    _HURONTARIO_LRT,
    _TORONTO_GENERAL,
]


def get_transit_score(
    area: Optional[str],
    city: Optional[str],
    address: Optional[str],
) -> Optional[int]:
    """
    Return an integer 1-10 transit score based on keyword matching.

    Returns None when no keyword match is found — the API layer applies a
    city-level fallback so the frontend always receives a number.

    Catches all exceptions — never disrupts the listing normalisation loop.
    """
    try:
        tokens = " ".join(
            t.lower() for t in (area or "", city or "", address or "") if t
        )
        if not tokens.strip():
            return None
        best = 0
        for table in _ALL_TABLES:
            for keyword, score in table.items():
                if keyword in tokens:
                    best = max(best, score)
        return best if best > 0 else None
    except Exception:
        return None

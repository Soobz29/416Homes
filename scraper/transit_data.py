"""
Transit proximity scoring for GTA listings.

Scores are on a 0–10 scale:
  8–10  Ontario Line corridor (opens ~2030) — forward-looking premium
  6–9   Eglinton Crosstown LRT corridor (opened 2024)
  0     No meaningful proximity (returns None)

The final score is the maximum match across both corridor tables.
"""
from __future__ import annotations
from typing import Optional

# Neighbourhood/area keywords → score (Ontario Line, ~2030)
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

# Neighbourhood/area keywords → score (Eglinton Crosstown LRT, opened 2024)
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


def get_transit_score(
    area: Optional[str],
    city: Optional[str],
    address: Optional[str],
) -> Optional[int]:
    """
    Return an integer 0–10 transit score based on keyword matching against
    Ontario Line and Eglinton Crosstown corridor tables, or None if no match.

    Returns None (not 0) when no corridor match is found so the frontend can
    hide the badge entirely rather than display a meaningless zero.

    Catches all exceptions — never disrupts the listing normalisation loop.
    """
    try:
        tokens = " ".join(
            t.lower() for t in (area or "", city or "", address or "") if t
        )
        if not tokens.strip():
            return None
        best = 0
        for keyword, score in _ONTARIO_LINE.items():
            if keyword in tokens:
                best = max(best, score)
        for keyword, score in _EGLINTON.items():
            if keyword in tokens:
                best = max(best, score)
        return best if best > 0 else None
    except Exception:
        return None

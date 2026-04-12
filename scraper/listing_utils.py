"""
Shared helpers for normalizing listing data across scrapers.

- Reject badge/headline text (e.g. "Just listed", "Open House") being used as address.
- Detect and filter out sold/inactive listings.
"""
import re
from typing import Optional

# Phrases that are listing badges or headlines, not street addresses.
BADGE_HEADLINE_PATTERNS = re.compile(
    r"^(Just listed|Open House\b|Sold\b|Price reduced|New price|Leased\b|Conditional\b|"
    r"Coming soon|Back on market|Reduced|Auction\b)",
    re.IGNORECASE,
)

# Status/text indicating listing is not for sale.
SOLD_INACTIVE_PATTERNS = re.compile(
    r"\b(sold|leased|conditional|expired|withdrawn|cancelled|terminated)\b",
    re.IGNORECASE,
)

# Minimal real address: number + street word, or contains comma (city/province).
REAL_ADDRESS_PATTERN = re.compile(
    r"\d+\s+\w+.*(st|ave|rd|dr|blvd|cres|way|ct|ter|pl|ln|trail|circ|lane|pkwy|drive|street|avenue)",
    re.IGNORECASE,
)


def is_badge_or_headline_only(text: Optional[str]) -> bool:
    """True if text is only a badge/headline (e.g. 'Just listed', 'Open House Sat 2-4pm')."""
    if not text or not str(text).strip():
        return True
    t = str(text).strip()
    if BADGE_HEADLINE_PATTERNS.match(t):
        return True
    # Short non-address phrases that are common.
    if t.lower() in ("just listed", "open house", "sold", "new", "price reduced"):
        return True
    return False


def is_sold_or_inactive(status_or_text: Optional[str]) -> bool:
    """True if status/text indicates listing is sold or otherwise inactive."""
    if not status_or_text:
        return False
    return bool(SOLD_INACTIVE_PATTERNS.search(str(status_or_text)))


def looks_like_real_address(text: Optional[str]) -> bool:
    """True if text looks like a street address (number + street type, or contains comma)."""
    if not text or not str(text).strip():
        return False
    t = str(text).strip()
    if is_badge_or_headline_only(t):
        return False
    if REAL_ADDRESS_PATTERN.search(t):
        return True
    # "123 Main St, Toronto, ON" style
    if "," in t and len(t) > 10:
        return True
    return False


def pick_display_address(*candidates: Optional[str]) -> str:
    """
    Return the first candidate that looks like a real address, or the first
    non-badge non-empty string, or 'Unknown'.
    """
    for c in candidates:
        if not c or not str(c).strip():
            continue
        s = str(c).strip()
        if looks_like_real_address(s):
            return s
        if not is_badge_or_headline_only(s):
            return s
    return "Unknown"


# Assignment / pre-construction keywords.
_ASSIGNMENT_PATTERN = re.compile(
    r"\b(assignment\s*sale|assignment\b|pre[- ]?construction|preconstruction|"
    r"transfer\s+of\s+(purchase\s+)?contract)\b",
    re.IGNORECASE,
)


def detect_is_assignment(listing: dict) -> bool:
    """
    True if a listing appears to be an assignment sale or pre-construction unit.
    Checks title, description, address, status, and listing_type fields.
    Catches all exceptions and returns False — never disrupts the listing loop.
    """
    try:
        fields = (
            listing.get("title") or "",
            listing.get("description") or "",
            listing.get("address") or "",
            listing.get("status") or "",
            listing.get("listing_type") or "",
        )
        combined = " ".join(str(f) for f in fields)
        return bool(_ASSIGNMENT_PATTERN.search(combined))
    except Exception:
        return False

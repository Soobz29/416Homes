"""
Parse TRREB Market Watch PDF → sold_comps rows.

TRREB publishes free monthly Market Watch PDFs with average/median sale prices
by region. This script parses those PDFs and synthesises training rows for the
LightGBM model.

Download the PDF manually from:
  https://trreb.ca/market-data/market-watch/

Usage:
    python -m scripts.parse_trreb_market_watch path/to/mw2025-04.pdf
    python -m scripts.parse_trreb_market_watch path/to/mw2025-04.pdf --dry-run
"""

import argparse
import hashlib
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ── Region → city / neighbourhood mapping ─────────────────────────────────────
# TRREB region names as they appear in the PDF tables.  Maps to city + a
# representative neighbourhood for the model.
REGION_MAP: Dict[str, Dict[str, str]] = {
    "Toronto C01": {"city": "Toronto", "neighbourhood": "King West"},
    "Toronto C02": {"city": "Toronto", "neighbourhood": "Rosedale"},
    "Toronto C03": {"city": "Toronto", "neighbourhood": "Forest Hill"},
    "Toronto C04": {"city": "Toronto", "neighbourhood": "Lawrence Park"},
    "Toronto C06": {"city": "Toronto", "neighbourhood": "Bathurst Manor"},
    "Toronto C07": {"city": "Toronto", "neighbourhood": "North York"},
    "Toronto C08": {"city": "Toronto", "neighbourhood": "Distillery District"},
    "Toronto C09": {"city": "Toronto", "neighbourhood": "Rosedale"},
    "Toronto C10": {"city": "Toronto", "neighbourhood": "Leaside"},
    "Toronto C11": {"city": "Toronto", "neighbourhood": "Flemingdon Park"},
    "Toronto C12": {"city": "Toronto", "neighbourhood": "Bridle Path"},
    "Toronto C13": {"city": "Toronto", "neighbourhood": "Don Mills"},
    "Toronto C14": {"city": "Toronto", "neighbourhood": "Willowdale"},
    "Toronto C15": {"city": "Toronto", "neighbourhood": "Agincourt"},
    "Toronto E01": {"city": "Toronto", "neighbourhood": "Leslieville"},
    "Toronto E02": {"city": "Toronto", "neighbourhood": "The Beaches"},
    "Toronto E03": {"city": "Toronto", "neighbourhood": "East York"},
    "Toronto E04": {"city": "Toronto", "neighbourhood": "Scarborough"},
    "Toronto E05": {"city": "Toronto", "neighbourhood": "Scarborough"},
    "Toronto E06": {"city": "Toronto", "neighbourhood": "Scarborough"},
    "Toronto E07": {"city": "Toronto", "neighbourhood": "Scarborough"},
    "Toronto E08": {"city": "Toronto", "neighbourhood": "Scarborough"},
    "Toronto E09": {"city": "Toronto", "neighbourhood": "Scarborough"},
    "Toronto E10": {"city": "Toronto", "neighbourhood": "Scarborough"},
    "Toronto E11": {"city": "Toronto", "neighbourhood": "Scarborough"},
    "Toronto W01": {"city": "Toronto", "neighbourhood": "Roncesvalles"},
    "Toronto W02": {"city": "Toronto", "neighbourhood": "Junction"},
    "Toronto W03": {"city": "Toronto", "neighbourhood": "Stockyards"},
    "Toronto W04": {"city": "Toronto", "neighbourhood": "York"},
    "Toronto W05": {"city": "Toronto", "neighbourhood": "Etobicoke"},
    "Toronto W06": {"city": "Toronto", "neighbourhood": "Etobicoke"},
    "Toronto W07": {"city": "Toronto", "neighbourhood": "Etobicoke"},
    "Toronto W08": {"city": "Toronto", "neighbourhood": "Etobicoke"},
    "Toronto W09": {"city": "Toronto", "neighbourhood": "Etobicoke"},
    "Toronto W10": {"city": "Toronto", "neighbourhood": "Etobicoke"},
    "Mississauga":  {"city": "Mississauga", "neighbourhood": "Mississauga City Centre"},
    "Brampton":     {"city": "Brampton",    "neighbourhood": "Brampton"},
    "Markham":      {"city": "Markham",     "neighbourhood": "Markham"},
    "Richmond Hill":{"city": "Richmond Hill","neighbourhood": "Richmond Hill"},
    "Vaughan":      {"city": "Vaughan",     "neighbourhood": "Vaughan"},
    "Oakville":     {"city": "Oakville",    "neighbourhood": "Oakville"},
    "Burlington":   {"city": "Burlington",  "neighbourhood": "Burlington"},
    "Ajax":         {"city": "Ajax",        "neighbourhood": "Ajax"},
    "Pickering":    {"city": "Pickering",   "neighbourhood": "Pickering"},
    "Whitby":       {"city": "Whitby",      "neighbourhood": "Whitby"},
    "Oshawa":       {"city": "Oshawa",      "neighbourhood": "Oshawa"},
    "Newmarket":    {"city": "Newmarket",   "neighbourhood": "Newmarket"},
    "Aurora":       {"city": "Aurora",      "neighbourhood": "Aurora"},
    "King":         {"city": "King",        "neighbourhood": "King City"},
}

# Price variation multipliers — synthesise 5 comp rows per region median
_VARIATIONS = [0.90, 0.95, 1.00, 1.05, 1.10]

# Typical GTA sqft estimate from price-per-sqft assumption ($850/sqft)
_PPSF = 850.0


def _synthesise_rows(region: str, avg_price: int, sold_date: str) -> List[Dict[str, Any]]:
    """Create 5 synthetic sold-comp rows bracketing the reported average price."""
    meta = REGION_MAP.get(region, {"city": region.strip(), "neighbourhood": region.strip()})
    city = meta["city"]
    neighbourhood = meta["neighbourhood"]
    rows = []
    for v in _VARIATIONS:
        sp = int(avg_price * v)
        sqft_est = max(400, int(sp / _PPSF))
        uid = hashlib.md5(f"trreb_{region}_{sp}_{sold_date}".encode()).hexdigest()
        rows.append({
            "id": uid,
            "address": f"Market avg, {neighbourhood}",
            "city": city,
            "neighbourhood": neighbourhood,
            "sold_price": sp,
            "list_price": int(sp * 1.01),
            "bedrooms": "3",
            "bathrooms": "2",
            "sqft": sqft_est,
            "property_type": "Detached",
            "sold_date": sold_date,
            "days_on_market": 14,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })
    return rows


def _extract_price(cell: str) -> int:
    """Extract integer from a cell like '$1,250,000' or '1250000'."""
    if not cell:
        return 0
    m = re.search(r"[\d,]+", cell.replace("$", "").replace(" ", ""))
    if not m:
        return 0
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:
        return 0


def parse_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parse a TRREB Market Watch PDF and return sold_comps rows.

    The PDF contains many tables; we scan every table looking for rows where:
    - column 0 looks like a TRREB region name (matches REGION_MAP or contains
      'Toronto' / a known GTA city)
    - some column contains a plausible GTA sale price (100k – 5M)
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed. Run: pip install pdfplumber")
        sys.exit(1)

    # Infer sold_date from filename (e.g. mw2025-04.pdf → 2025-04-01)
    stem = Path(pdf_path).stem  # e.g. 'mw2025-04'
    date_m = re.search(r"(\d{4})[_\-](\d{2})", stem)
    if date_m:
        sold_date = f"{date_m.group(1)}-{date_m.group(2)}-01"
    else:
        sold_date = datetime.now(timezone.utc).date().isoformat()

    all_rows: List[Dict[str, Any]] = []
    seen_uids: set = set()

    known_regions = set(REGION_MAP.keys())
    # Also match partial names
    region_keywords = re.compile(
        r'toronto|mississauga|brampton|markham|richmond hill|vaughan|'
        r'oakville|burlington|ajax|pickering|whitby|oshawa|newmarket|aurora',
        re.IGNORECASE,
    )

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    if not row or len(row) < 3:
                        continue
                    region_cell = str(row[0] or "").strip()
                    if not region_cell:
                        continue

                    # Check if this row is for a known region
                    matched_region = None
                    for rk in known_regions:
                        if rk.lower() in region_cell.lower():
                            matched_region = rk
                            break
                    if matched_region is None and region_keywords.search(region_cell):
                        matched_region = region_cell  # use as-is, city lookup will fallback

                    if matched_region is None:
                        continue

                    # Scan cells for a plausible average price
                    avg_price = 0
                    for cell in row[1:]:
                        candidate = _extract_price(str(cell or ""))
                        if 100_000 < candidate < 5_000_000:
                            avg_price = candidate
                            break  # take first plausible value

                    if avg_price == 0:
                        continue

                    logger.debug(f"  Page {page_num}: {matched_region} → avg ${avg_price:,}")
                    for new_row in _synthesise_rows(matched_region, avg_price, sold_date):
                        uid = new_row["id"]
                        if uid not in seen_uids:
                            seen_uids.add(uid)
                            all_rows.append(new_row)

    logger.info(f"Parsed {len(all_rows)} synthetic rows from {pdf_path}")
    return all_rows


def upsert_to_supabase(rows: List[Dict[str, Any]]) -> int:
    from dotenv import load_dotenv
    from supabase import create_client

    load_dotenv()
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )
    total = 0
    for i in range(0, len(rows), 100):
        batch = rows[i:i + 100]
        client.table("sold_comps").upsert(batch, on_conflict="id").execute()
        total += len(batch)
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Parse TRREB Market Watch PDF into sold_comps")
    parser.add_argument("pdf", help="Path to TRREB Market Watch PDF")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not upsert to Supabase")
    args = parser.parse_args()

    rows = parse_pdf(args.pdf)
    print(f"\nParsed {len(rows)} synthetic sold-comp rows from {args.pdf}")

    if args.dry_run:
        for r in rows[:5]:
            print(f"  {r['neighbourhood']} — ${r['sold_price']:,} ({r['sqft']} sqft)")
        print("  ... (dry run, nothing upserted)")
    else:
        n = upsert_to_supabase(rows)
        print(f"Upserted {n} rows into sold_comps.")
        print("Re-run `python valuation/model.py` to retrain.")

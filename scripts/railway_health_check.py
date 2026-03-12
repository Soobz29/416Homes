#!/usr/bin/env python3
"""
Quick health and listings check for the Railway API.
Usage:
  python scripts/railway_health_check.py
  python scripts/railway_health_check.py https://your-app.up.railway.app
  RAILWAY_API_URL=https://... python scripts/railway_health_check.py
"""
import os
import sys
import urllib.request
import urllib.error
import json

DEFAULT_URL = "https://web-production-61e684.up.railway.app"


def main():
    base = os.getenv("RAILWAY_API_URL", DEFAULT_URL).rstrip("/")
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        base = sys.argv[1].rstrip("/")

    print(f"Checking API at: {base}\n")

    # 1. Health
    try:
        req = urllib.request.Request(f"{base}/api/health")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            status = data.get("status", "?")
            version = data.get("version", "?")
            print(f"  Health:  {status} (version {version})")
    except urllib.error.HTTPError as e:
        print(f"  Health:  FAILED HTTP {e.code}")
        return 1
    except Exception as e:
        print(f"  Health:  FAILED {e}")
        return 1

    # 2. Listings (sample)
    try:
        req = urllib.request.Request(f"{base}/api/listings?limit=3")
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            listings = data.get("listings", data) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            total = data.get("total", len(listings)) if isinstance(data, dict) else len(listings)
            if not isinstance(listings, list):
                listings = []
            print(f"  Listings: {len(listings)} (total={total})")
            for i, L in enumerate(listings[:3], 1):
                addr = (L.get("address") or "?")[:50]
                print(f"    {i}. {addr}")
    except urllib.error.HTTPError as e:
        print(f"  Listings: FAILED HTTP {e.code}")
        return 1
    except Exception as e:
        print(f"  Listings: FAILED {e}")
        return 1

    print("\n  All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

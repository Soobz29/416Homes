"""
Test the Telegram /link flow against your Supabase (same logic as the bot).
Run from project root:  python scripts/test_link_code.py TG-XXXX

Use a fresh code from the dashboard (Connect Telegram). Shows why a code
matches or doesn't (no rows, no match, expired, or success).
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Project root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

def main():
    code_arg = (sys.argv[1] or "").strip().upper()
    if not code_arg:
        print("Usage: python scripts/test_link_code.py TG-XXXX")
        print("Get a fresh code from the dashboard (Connect Telegram), then run this.")
        sys.exit(1)

    try:
        from supabase import create_client
    except ImportError:
        print("Install: pip install supabase")
        sys.exit(1)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_KEY in .env")
        sys.exit(1)

    client = create_client(url, key)
    print(f"Supabase: {url[:50]}...")
    print()

    resp = client.table("users").select("id,email,preferences").execute()
    rows = getattr(resp, "data", None) or []
    print(f"Loaded {len(rows)} user(s) from public.users.\n")

    now_utc = datetime.now(timezone.utc)
    target = None
    for i, row in enumerate(rows):
        prefs = row.get("preferences") or {}
        if not isinstance(prefs, dict):
            print(f"  Row {i+1}: id={row.get('id')} preferences not a dict, skip")
            continue
        stored_code = (prefs.get("link_code") or "").strip().upper()
        expires = prefs.get("link_expires_at")
        email = row.get("email", "")

        if not stored_code:
            print(f"  Row {i+1}: {email} — no link_code")
            continue

        match = stored_code == code_arg
        expiry_ok = True
        expiry_msg = "no expiry"
        if expires:
            try:
                s = str(expires).strip().replace("Z", "+00:00").rstrip(".")
                if s and "+00:00" not in s and "+" not in s and "Z" not in s:
                    s = s.rstrip("Z") + (":00" if s.count(":") == 1 else "") + "+00:00"
                if s:
                    expiry_dt = datetime.fromisoformat(s)
                    if expiry_dt.tzinfo is None:
                        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                    expiry_ok = expiry_dt >= now_utc
                    expiry_msg = f"expires {expires} -> {'valid' if expiry_ok else 'EXPIRED'}"
            except Exception as e:
                expiry_msg = f"parse error: {e} (treated as valid)"

        print(f"  Row {i+1}: {email}")
        print(f"           link_code={stored_code}  (input={code_arg})  match={match}")
        print(f"           {expiry_msg}")
        if match and expiry_ok:
            target = row
        elif match and not expiry_ok:
            print(f"           -> Code MATCHED but EXPIRED, so bot would reject.")
        print()

    if target:
        prefs = target.get("preferences") or {}
        expires_str = prefs.get("link_expires_at")
        expiry_utc = "N/A"
        minutes_left = None
        if expires_str:
            try:
                s = str(expires_str).strip().replace("Z", "+00:00").rstrip(".")
                if s and "+00:00" not in s and "+" not in s and "Z" not in s:
                    s = s.rstrip("Z") + (":00" if s.count(":") == 1 else "") + "+00:00"
                if s:
                    expiry_dt = datetime.fromisoformat(s)
                    if expiry_dt.tzinfo is None:
                        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                    expiry_utc = expiry_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                    delta = expiry_dt - now_utc
                    minutes_left = max(0, int(delta.total_seconds() / 60))
            except Exception:
                pass
        print("Result: ✅ MATCH — Code is valid")
        print(f"   User: {target.get('email', 'N/A')}")
        print(f"   Expires: {expiry_utc}")
        if minutes_left is not None:
            print(f"   Status: Valid ({minutes_left} minutes remaining)")
        else:
            print("   Status: Valid")
        print()
        print("If the real /link still fails, the problem is likely the Supabase .update() (e.g. column type or RLS).")
    else:
        print("Result: NO MATCH — Code not found, or every matching code was expired.")
        print("Generate a new code in the dashboard and run this again with that code.")
    print()

if __name__ == "__main__":
    main()

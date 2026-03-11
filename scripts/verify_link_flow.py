"""
Verify the Telegram link-code flow: API writes code -> Supabase has it -> bot can read it.
Run from project root. Requires API running (uvicorn api.main:app --port 8000) and .env with
SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and optionally NEXT_PUBLIC_API_URL or default localhost:8000.

  python scripts/verify_link_flow.py
  python scripts/verify_link_flow.py your@email.com
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

def main():
    email = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("VERIFY_LINK_EMAIL", "")).strip()
    if not email:
        print("Usage: python scripts/verify_link_flow.py <email>")
        print("  Or set VERIFY_LINK_EMAIL in .env")
        print("  Use an email that exists in public.users (or will be created).")
        sys.exit(1)

    base = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000").rstrip("/")
    url = f"{base}/api/link-code"

    print("1. Calling API to generate link code...")
    print(f"   POST {url}")
    print(f"   x-user-email: {email}")
    try:
        import urllib.request
        req = urllib.request.Request(url, method="POST", headers={"x-user-email": email})
        with urllib.request.urlopen(req, timeout=15) as r:
            import json
            data = json.loads(r.read().decode())
    except Exception as e:
        print(f"   FAILED: {e}")
        if "401" in str(e) or "Missing" in str(e):
            print("   -> API requires x-user-email header (already sent). Check API logs.")
        if "500" in str(e):
            print("   -> Server error. Ensure SUPABASE_SERVICE_ROLE_KEY is set and RLS allows service role.")
        sys.exit(1)

    code = data.get("code") or ""
    expires_at = data.get("expires_at") or ""
    if not code:
        print("   FAILED: API did not return a code.")
        sys.exit(1)
    print(f"   OK: code={code}  expires_at={expires_at}")

    print("\n2. Checking Supabase for the code...")
    url_sup = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url_sup or not key:
        print("   Skip: SUPABASE_URL or keys not in .env")
        sys.exit(0)
    try:
        from supabase import create_client
        client = create_client(url_sup, key)
        resp = client.table("users").select("id,email,preferences").execute()
        rows = getattr(resp, "data", None) or []
    except Exception as e:
        print(f"   FAILED: {e}")
        sys.exit(1)

    found = None
    for row in rows:
        prefs = row.get("preferences") or {}
        if isinstance(prefs, dict) and (prefs.get("link_code") or "").strip().upper() == code.upper():
            found = row
            break
    if not found:
        print(f"   FAILED: Code {code} not found in any user row.")
        print("   -> API may be using a different Supabase key or RLS blocked the update.")
        sys.exit(1)
    print(f"   OK: Found code for user {found.get('email')} (id={found.get('id')})")

    print("\n3. Verifying bot would accept it (expiry parse)...")
    expires = (found.get("preferences") or {}).get("link_expires_at")
    if expires:
        from datetime import datetime, timezone
        try:
            s = str(expires).strip().replace("Z", "+00:00").rstrip(".")
            if s and "+00:00" not in s and "+" not in s and "Z" not in s:
                s = s.rstrip("Z") + (":00" if s.count(":") == 1 else "") + "+00:00"
            if s:
                expiry_dt = datetime.fromisoformat(s)
                if expiry_dt.tzinfo is None:
                    expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if expiry_dt < now:
                    print(f"   WARN: Stored expiry {expires} is in the past; bot would reject.")
                else:
                    mins = int((expiry_dt - now).total_seconds() / 60)
                    print(f"   OK: Expiry valid ({mins} minutes left)")
        except Exception as e:
            print(f"   WARN: Could not parse expiry: {e}")
    else:
        print("   OK: No expiry stored (bot accepts)")

    print("\nResult: Link-code flow is working. Try /link", code, "in the public Telegram bot.")
    print("If /link still fails, ensure the bot process has SUPABASE_SERVICE_ROLE_KEY in its env.")

if __name__ == "__main__":
    main()

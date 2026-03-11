"""
Quick dependency sanity check.

Run:
    python -m scripts.verify_deps
or:
    python scripts/verify_deps.py
"""

def main() -> None:
    # Core HTTP + Supabase client
    import httpx  # noqa: F401
    from supabase import create_client  # noqa: F401

    # Telegram bot SDK
    import telegram  # noqa: F401

    # Gemini GenAI SDK (official)
    from google import genai  # noqa: F401

    print("All core deps imported successfully.")


if __name__ == "__main__":
    main()


import json
import os
from pathlib import Path

GTA_REGIONS = [
    "Toronto Downtown",
    "Toronto East (Scarborough)",
    "Toronto West (Etobicoke)",
    "Toronto North (North York)",
    "Mississauga",
    "Brampton",
    "Vaughan",
    "Markham",
    "Richmond Hill",
    "Oakville",
    "Burlington",
    "Ajax & Pickering"
]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear_screen()
    print("====================================================")
    print("       🏠 416Homes Agent Onboarding Script")
    print("====================================================\n")
    print("Welcome! Let's configure your white-label AI agent.\n")

    # 1. Branding
    brokerage_name = input("1. What is your brokerage name? (e.g., 416Homes): ") or "416Homes"
    agent_name = input(f"2. What is your agent name? (e.g., {brokerage_name} Agent): ") or f"{brokerage_name} Agent"
    agent_email = input("3. What is your agent email? (for alerts): ") or ""
    
    # 2. Market/Regions
    print("\nAvailable GTA Regions:")
    for i, region in enumerate(GTA_REGIONS, 1):
        print(f"  {i}. {region}")
    
    region_idxs = input("\n4. Which regions do you serve? (enter numbers separated by commas, or 'all'): ")
    if region_idxs.lower() == 'all':
        selected_regions = GTA_REGIONS
    else:
        try:
            idxs = [int(x.strip()) - 1 for x in region_idxs.split(",")]
            selected_regions = [GTA_REGIONS[i] for i in idxs if 0 <= i < len(GTA_REGIONS)]
        except:
            print("Invalid input, defaulting to Toronto Downtown.")
            selected_regions = ["Toronto Downtown"]

    # 3. Pricing
    price_range_raw = input("\n5. What is your price range? min-max (e.g., 400000-5000000): ") or "400000-5000000"
    try:
        p_min, p_max = map(int, price_range_raw.split("-"))
    except:
        p_min, p_max = 400000, 5000000

    # 4. API Keys
    print("\n--- API Configuration ---")
    tg_token = input("6. Telegram Bot Token: ")
    eleven_key = input("7. ElevenLabs API Key: ")
    gemini_key = input("8. Gemini API Key: ")
    resend_key = input("9. Resend API Key: ")

    # Build agent_config.json
    config = {
        "agent_name": agent_name,
        "agent_persona": f"Your 24/7 {selected_regions[0] if selected_regions else 'GTA'} real estate assistant",
        "brokerage_name": brokerage_name,
        "brokerage_logo_url": "",
        "agent_email": agent_email,
        "primary_colour": "#C9A84C",
        "telegram_welcome": f"Hello! I'm {agent_name}, your personal real estate assistant for {brokerage_name}.",
        "regions": selected_regions,
        "price_range": [p_min, p_max],
        "monthly_fee": 300,
        "setup_fee": 3000
    }

    with open("agent_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # Build .env
    env_content = f"""# 416Homes Agent Configuration
TELEGRAM_BOT_TOKEN={tg_token}
ELEVENLABS_API_KEY={eleven_key}
GEMINI_API_KEY={gemini_key}
RESEND_API_KEY={resend_key}

# Default Chat ID (will be populated on first use if needed)
TELEGRAM_CHAT_ID=
"""
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)

    print("\n✅ Configuration complete!")
    print("1. agent_config.json has been updated.")
    print("2. .env has been generated.")
    print("\nYour agent is configured. Run: python demo_api.py\n")

if __name__ == "__main__":
    main()

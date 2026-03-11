import asyncio
import os
import sys
import logging
from unittest.mock import MagicMock, AsyncMock
from telegram import Update, Message, Chat, User
from telegram.ext import ContextTypes

# Setup paths
sys.path.append(os.getcwd())

from telegram_bot import bot, _run_video_and_deliver

async def simulate():
    print("🚀 Simulating Telegram Commands...")
    
    # 1. Simulate /video command
    video_url = "https://www.realtor.ca/real-estate/29421416/1264-st-marys-avenue-mississauga-lakeview-lakeview"
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not chat_id:
        print("❌ Error: TELEGRAM_CHAT_ID not set in environment.")
        return

    print(f"🎬 Triggering video generation for {video_url}...")
    try:
        # Note: This will actually trigger a background task that sends real Telegram messages
        await _run_video_and_deliver(video_url, chat_id)
        print("✅ Video delivery task triggered and finished process (check Telegram).")
    except Exception as e:
        print(f"❌ Video simulation failed: {e}")

    # 2. Simulate 'add buyer' command
    buyer_cmd = "add buyer John Smith 800000-1200000 3 Mississauga"
    print(f"👥 Triggering buyer profile addition: {buyer_cmd}")
    
    # Create mock update for h_add_buyer
    mock_update = MagicMock(spec=Update)
    mock_message = MagicMock(spec=Message)
    
    mock_message.text = buyer_cmd
    # reply_text MUST be an AsyncMock because it is awaited
    mock_message.reply_text = AsyncMock(side_effect=lambda text, **kwargs: print(f"🤖 Bot Reply: {text}"))
    mock_update.message = mock_message
    
    try:
        await bot.h_add_buyer(mock_update, None)
        print("✅ Buyer addition simulation finished.")
    except Exception as e:
        print(f"❌ Buyer simulation failed: {e}")

if __name__ == "__main__":
    asyncio.run(simulate())

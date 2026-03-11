import os
import asyncio
from dotenv import load_dotenv

async def get_cassius():
    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("No API key found")
        return

    from elevenlabs.client import ElevenLabs
    client = ElevenLabs(api_key=api_key)
    
    # Get all voices available to the user
    response = client.voices.get_all()
    
    cassius_id = None
    for voice in response.voices:
        print(f"Found voice: {voice.name} (ID: {voice.voice_id})")
        if "Cassius" in voice.name:
            cassius_id = voice.voice_id
            
    if cassius_id:
        print(f"\n✅ Found Cassius ID: {cassius_id}")
    else:
        print("\n❌ Cassius not found in your currently added voices.")
        print("Note: If Cassius is from the public Voice Library, you may need to add it to your Voice Library in the ElevenLabs dashboard first for it to be accessible via standard voice listing, or use the shared voice API.")

if __name__ == "__main__":
    asyncio.run(get_cassius())

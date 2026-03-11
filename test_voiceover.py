import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

async def main():
    load_dotenv()
    from video_pipeline.video_producer import generate_voiceover

    # Setup temp dir
    job_dir = Path("video_pipeline/temp/test_voiceover")
    job_dir.mkdir(parents=True, exist_ok=True)
    
    script_text = "Welcome to 122 Macpherson Avenue, a stunning luxury property nestled in the heart of Toronto's exclusive Annex neighborhood. This masterpiece features elegant hardwood floors, a state-of-the-art chef's kitchen, and a private oasis backyard. Experience unparalleled sophistication and modern design."
    
    logging.info("Starting voiceover generation test with ElevenLabs...")
    
    out_path = await generate_voiceover(
        script_text=script_text,
        voice="male_cassius",
        job_dir=job_dir
    )
    
    if out_path:
        logging.info(f"SUCCESS: Voiceover created at {out_path}")
    else:
        logging.error("FAILED to create voiceover.")

if __name__ == "__main__":
    asyncio.run(main())

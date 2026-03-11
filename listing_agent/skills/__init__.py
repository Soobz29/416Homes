import os
import importlib.util
import logging
import json
import asyncio
from pathlib import Path
from typing import List, Callable, Dict, Any
from google import genai

logger = logging.getLogger(__name__)

SKILLS_DIR = Path("listing_agent/skills")

def load_skills() -> List[Callable[[Dict[str, Any]], bool]]:
    """Loads all .py files in the skills directory and returns their skill functions."""
    skills = []
    if not SKILLS_DIR.exists():
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        return skills

    for file in SKILLS_DIR.glob("skill_*.py"):
        try:
            skill_name = file.stem
            spec = importlib.util.spec_from_file_location(skill_name, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Expecting a function with the same name as the file (e.g., skill_has_pool)
            skill_func = getattr(module, skill_name, None)
            if skill_func and callable(skill_func):
                skills.append(skill_func)
                logger.info(f"Loaded skill: {skill_name}")
        except Exception as e:
            logger.error(f"Error loading skill {file}: {e}")
            
    return skills

async def generate_and_save_skill(prompt_text: str) -> str:
    """Uses Gemini to generate a Python skill function and saves it."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")

    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.5-flash"

    prompt = f"""
    Generate a Python function that takes a listing_data dictionary and returns a boolean value.
    The goal is: "{prompt_text}"
    
    The function should be named based on the goal (e.g., skill_has_pool).
    The dictionary `listing_data` has keys like: 'address', 'price', 'bedrooms', 'bathrooms', 'description', 'property_type', 'city'.
    
    The function should check the 'description' (string) and possibly other fields.
    Return ONLY the Python code for the function. No markdown fences, no extra text.
    
    Example output format:
    def skill_has_pool(listing_data: dict) -> bool:
        desc = listing_data.get('description', '').lower()
        return 'pool' in desc or 'swimming' in desc
    """

    response = await asyncio.to_thread(client.models.generate_content, model=model_id, contents=prompt)
    code = response.text.strip()
    
    # Simple cleanup to remove potential Markdown fences
    if code.startswith("```python"):
        code = code.split("```python")[1].split("```")[0].strip()
    elif code.startswith("```"):
        code = code.split("```")[1].split("```")[0].strip()

    # Extract function name from code
    import re
    match = re.search(r"def\s+(skill_\w+)", code)
    if not match:
        raise ValueError("Could not extract function name from generated code.")
    
    skill_name = match.group(1)
    file_path = SKILLS_DIR / f"{skill_name}.py"
    
    with open(file_path, "w") as f:
        f.write(f"# Auto-generated skill: {prompt_text}\n\n")
        f.write(code)
    
    logger.info(f"Generated and saved skill: {skill_name}")
    return skill_name

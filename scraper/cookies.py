"""
Cookie persistence for stealth scraping.

Cloudflare's `cf_clearance` cookie is the difference between getting through
and getting blocked. Re-using it across runs avoids the JS challenge each time.
"""
import json
from pathlib import Path
from typing import Any, List, Dict

COOKIE_DIR = Path(__file__).parent / "_cookies"
COOKIE_DIR.mkdir(exist_ok=True)


def _path_for(domain: str) -> Path:
    safe = "".join(c if c.isalnum() else "_" for c in domain)
    return COOKIE_DIR / f"{safe}.json"


def save_cookies(driver, domain: str) -> None:
    """Save cookies for a domain. `driver` can be Selenium/UC Chrome or DrissionPage."""
    try:
        cookies = driver.get_cookies()  # Selenium / UC API
    except AttributeError:
        try:
            cookies = driver.cookies()  # DrissionPage API
        except Exception:
            return
    try:
        _path_for(domain).write_text(json.dumps(cookies))
    except Exception:
        pass


def load_cookies(driver, domain: str) -> int:
    """Load saved cookies into the driver. Returns count loaded."""
    p = _path_for(domain)
    if not p.exists():
        return 0
    try:
        cookies: List[Dict[str, Any]] = json.loads(p.read_text())
    except Exception:
        return 0
    count = 0
    for c in cookies:
        try:
            driver.add_cookie(c)  # Selenium / UC
            count += 1
        except AttributeError:
            try:
                driver.set.cookies(c)  # DrissionPage
                count += 1
            except Exception:
                pass
        except Exception:
            pass
    return count

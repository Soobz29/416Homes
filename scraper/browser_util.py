"""
Shared browser utility for all scrapers.

On Windows: uses DrissionPage + Edge (stealth fingerprinting).
On Linux/CI: uses Playwright Chromium (headless, stealth args).

Also provides an `undetected-chromedriver` path for stubborn targets like
HouseSigma where Cloudflare's bot-detection blocks the default browsers.
Enable with: STEALTH_BROWSER=uc
"""

import logging
import os
import platform
import random
import time
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
_ON_LINUX = platform.system() != "Windows"
_USE_UC = os.getenv("STEALTH_BROWSER", "").lower() in ("uc", "undetected", "1", "true")

# ── Fingerprinting (shared) ────────────────────────────────────────────────────
try:
    from browserforge.fingerprints import FingerprintGenerator
    _FP_GEN: Optional[object] = None
    _CURRENT_FP = None
    _FP_USE_COUNT = 0
    _HAS_BROWSERFORGE = True
except ImportError:
    _HAS_BROWSERFORGE = False

CANVAS_NOISE_JS = r"""
(function() {
  try {
    const addNoise = function(ctx) {
      try {
        const w = Math.min(10, ctx.canvas.width);
        const h = Math.min(10, ctx.canvas.height);
        const imageData = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < imageData.data.length; i += 4) {
          imageData.data[i] += Math.floor(Math.random() * 3) - 1;
          imageData.data[i + 1] += Math.floor(Math.random() * 3) - 1;
          imageData.data[i + 2] += Math.floor(Math.random() * 3) - 1;
        }
        ctx.putImageData(imageData, 0, 0);
      } catch (e) {}
    };
    const toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {
      const ctx = this.getContext('2d');
      if (ctx) addNoise(ctx);
      return toDataURL.apply(this, arguments);
    };
  } catch (e) {}
})();
"""


def _get_fingerprint() -> Tuple[Optional[object], dict]:
    global _FP_GEN, _CURRENT_FP, _FP_USE_COUNT
    if not _HAS_BROWSERFORGE:
        return None, {}
    if _FP_GEN is None:
        _FP_GEN = FingerprintGenerator()
    if _CURRENT_FP is None or _FP_USE_COUNT >= 5:
        try:
            fp = _FP_GEN.generate(browser="chrome", os="windows")
            _CURRENT_FP = fp
            _FP_USE_COUNT = 0
        except Exception as e:
            logger.warning(f"browserforge HeaderGenerator failed, falling back to bare UA: {e}")
            _CURRENT_FP = None
    _FP_USE_COUNT += 1
    if _CURRENT_FP is not None:
        headers = getattr(_CURRENT_FP, "headers", None)
        return _CURRENT_FP, headers or {}
    return None, {}


# ── Playwright wrapper (Linux/CI path) ─────────────────────────────────────────

class _PWElement:
    """Thin wrapper making a Playwright element look like a DrissionPage element."""
    def __init__(self, el):
        self._el = el

    def attr(self, name):
        if self._el is None:
            return ""
        try:
            return self._el.get_attribute(name) or ""
        except Exception:
            return ""

    @property
    def text(self):
        if self._el is None:
            return ""
        try:
            return self._el.inner_text() or ""
        except Exception:
            return ""


class PlaywrightPage:
    """Thin wrapper making a Playwright page look like a DrissionPage."""

    def __init__(self, pw_page, pw_instance):
        self._page = pw_page
        self._pw = pw_instance  # keep reference so GC doesn't stop it

    def get(self, url, retry=1, interval=1, timeout=30):
        self._page.goto(url, timeout=timeout * 1000, wait_until="networkidle")

    def eles(self, selector):
        tag = selector[4:] if selector.startswith("tag:") else selector
        return [_PWElement(e) for e in self._page.query_selector_all(tag)]

    def ele(self, selector):
        tag = selector[4:] if selector.startswith("tag:") else selector
        e = self._page.query_selector(tag)
        return _PWElement(e) if e else None

    def run_js(self, js):
        try:
            self._page.evaluate(js)
        except Exception:
            pass

    def quit(self):
        try:
            self._page.context.browser.close()
        except Exception:
            pass

    class scroll:
        @staticmethod
        def down(px):
            pass  # no-op placeholder


def _create_playwright_browser(headless: bool = True) -> PlaywrightPage:
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = ctx.new_page()
    try:
        page.evaluate(CANVAS_NOISE_JS)
    except Exception:
        pass
    return PlaywrightPage(page, pw)


def _create_drission_browser(headless: bool = False):
    from DrissionPage import ChromiumPage, ChromiumOptions
    _, headers = _get_fingerprint()
    ua = headers.get("User-Agent")
    co = ChromiumOptions()
    co.headless(headless)
    co.set_browser_path(EDGE_PATH)
    co.set_argument("--disable-blink-features", "AutomationControlled")
    if ua:
        co.set_user_agent(ua)
    if random.choice([True, False]):
        co.set_argument("--disable-http2", None)
    page = ChromiumPage(co)
    try:
        page.run_js(CANVAS_NOISE_JS)
    except Exception:
        pass
    return page


# ── undetected-chromedriver wrapper (Cloudflare bypass path) ───────────────────

class _UCElement:
    """Thin wrapper making a Selenium WebElement look like a DrissionPage element."""

    def __init__(self, el):
        self._el = el

    def attr(self, name: str) -> str:
        if self._el is None:
            return ""
        try:
            return self._el.get_attribute(name) or ""
        except Exception:
            return ""

    @property
    def text(self) -> str:
        if self._el is None:
            return ""
        try:
            return self._el.text or ""
        except Exception:
            return ""


class _UCPage:
    """Thin wrapper making an undetected-chromedriver driver look like DrissionPage."""

    def __init__(self, driver):
        self._driver = driver

    # ── navigation ─────────────────────────────────────────────────────────────
    def get(self, url: str, retry: int = 1, interval: int = 1, timeout: int = 30):
        self._driver.set_page_load_timeout(timeout)
        for attempt in range(max(retry, 1)):
            try:
                self._driver.get(url)
                return
            except Exception as e:
                if attempt < retry - 1:
                    time.sleep(interval)
                else:
                    raise

    # ── element finders ────────────────────────────────────────────────────────
    def eles(self, selector: str):
        from selenium.webdriver.common.by import By
        css = selector[4:] if selector.startswith("tag:") else selector
        try:
            els = self._driver.find_elements(By.CSS_SELECTOR, css)
            return [_UCElement(e) for e in els]
        except Exception:
            return []

    def ele(self, selector: str):
        from selenium.webdriver.common.by import By
        css = selector[4:] if selector.startswith("tag:") else selector
        try:
            e = self._driver.find_element(By.CSS_SELECTOR, css)
            return _UCElement(e)
        except Exception:
            return None

    # ── JS execution ───────────────────────────────────────────────────────────
    def run_js(self, js: str):
        try:
            self._driver.execute_script(js)
        except Exception:
            pass

    # ── cookies ────────────────────────────────────────────────────────────────
    def get_cookies(self):
        return self._driver.get_cookies()

    def add_cookie(self, cookie: dict):
        self._driver.add_cookie(cookie)

    # ── scroll helper (DrissionPage-compatible interface) ──────────────────────
    class _Scroll:
        def __init__(self, driver):
            self._driver = driver

        def down(self, px: int = 500):
            try:
                self._driver.execute_script(f"window.scrollBy(0, {px});")
            except Exception:
                pass

    @property
    def scroll(self):
        return self._Scroll(self._driver)

    # ── cleanup ────────────────────────────────────────────────────────────────
    def quit(self):
        try:
            self._driver.quit()
        except Exception:
            pass


def _create_undetected_browser(headless: bool = False) -> _UCPage:
    """Create an undetected-chromedriver browser (best Cloudflare evasion, $0)."""
    import undetected_chromedriver as uc
    try:
        from fake_useragent import UserAgent
        ua_str = UserAgent().chrome
    except Exception:
        ua_str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

    options = uc.ChromeOptions()
    options.add_argument(f"--user-agent={ua_str}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    # Persistent profile preserves cf_clearance cookies between runs
    profile_dir = Path.home() / ".uc_profile_416homes"
    profile_dir.mkdir(exist_ok=True)
    options.add_argument(f"--user-data-dir={profile_dir}")
    if headless:
        options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, version_main=None)
    page = _UCPage(driver)
    try:
        page.run_js(CANVAS_NOISE_JS)
    except Exception:
        pass
    return page


def create_browser(headless: bool = True):
    """
    Return a browser page object.
    - STEALTH_BROWSER=uc: undetected-chromedriver (best for Cloudflare targets).
    - Linux/CI: Playwright Chromium (headless).
    - Windows default: DrissionPage + Edge (stealth).
    """
    if _USE_UC:
        return _create_undetected_browser(headless=headless)
    if _ON_LINUX:
        return _create_playwright_browser(headless=True)
    return _create_drission_browser(headless=headless)

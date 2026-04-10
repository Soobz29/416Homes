"""
Shared browser utility for all scrapers.

On Windows: uses DrissionPage + Edge (stealth fingerprinting).
On Linux/CI: uses Playwright Chromium (headless, stealth args).
"""

import logging
import platform
import random
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
_ON_LINUX = platform.system() != "Windows"

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


def create_browser(headless: bool = True):
    """
    Return a browser page object.
    - Linux/CI: Playwright Chromium (headless).
    - Windows: DrissionPage + Edge (stealth).
    """
    if _ON_LINUX:
        return _create_playwright_browser(headless=True)
    return _create_drission_browser(headless=headless)

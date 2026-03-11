"""
Shared DrissionPage browser utility for all scrapers.

Enhanced stealth mode:
* Uses browserforge to generate realistic browser fingerprints.
* Rotates fingerprints every 5 browser sessions.
* Randomizes TLS characteristics by toggling HTTP/2 usage.
* Injects a small canvas noise shim to randomize canvas fingerprints.
"""

import logging
import random
from typing import Optional, Tuple

from DrissionPage import ChromiumPage, ChromiumOptions
from browserforge.fingerprints import FingerprintGenerator

logger = logging.getLogger(__name__)

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

_FINGERPRINT_GEN: Optional[FingerprintGenerator] = None
_CURRENT_FP = None
_FP_USE_COUNT = 0

# Simple canvas noise shim inspired by common anti-fingerprinting techniques.
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

    const getImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function() {
      const res = getImageData.apply(this, arguments);
      // Touch a pixel to make the hash slightly unstable.
      if (res && res.data && res.data.length > 0) {
        const idx = Math.floor(Math.random() * Math.min(10, res.data.length));
        res.data[idx] = res.data[idx] ^ 0x01;
      }
      return res;
    };
  } catch (e) {}
})();
"""


def _get_fingerprint() -> Tuple[Optional[object], Optional[dict]]:
  """
  Generate or rotate a browserforge fingerprint.

  For now we mainly use the generated headers (User-Agent) to configure
  the DrissionPage instance. A new fingerprint is generated every 5
  create_browser() calls.
  """
  global _FINGERPRINT_GEN, _CURRENT_FP, _FP_USE_COUNT

  if _FINGERPRINT_GEN is None:
      _FINGERPRINT_GEN = FingerprintGenerator()

  if _CURRENT_FP is None or _FP_USE_COUNT >= 5:
      try:
          fp = _FINGERPRINT_GEN.generate(browser="chrome", os="windows")
          _CURRENT_FP = fp
          _FP_USE_COUNT = 0
      except Exception as e:  # pragma: no cover - defensive fallback
          logger.warning(f"browserforge FingerprintGenerator failed: {e}")
          _CURRENT_FP = None

  _FP_USE_COUNT += 1

  if _CURRENT_FP is not None:
      headers = getattr(_CURRENT_FP, "headers", None)
      return _CURRENT_FP, headers or {}
  return None, {}


def create_browser(headless: bool = False) -> ChromiumPage:
    """Create a DrissionPage browser instance using Edge and stealth settings."""
    _, headers = _get_fingerprint()
    ua = headers.get("User-Agent")

    co = ChromiumOptions()
    co.headless(headless)
    co.set_browser_path(EDGE_PATH)
    co.set_argument("--disable-blink-features", "AutomationControlled")

    # Apply User-Agent from fingerprint if available.
    if ua:
        co.set_user_agent(ua)

    # Crude TLS fingerprint randomization: occasionally disable HTTP/2,
    # which changes ALPN and TLS handshake characteristics.
    if random.choice([True, False]):
        co.set_argument("--disable-http2", None)

    page = ChromiumPage(co)

    # Inject canvas noise shim as soon as the page is ready.
    try:
        page.run_js(CANVAS_NOISE_JS)
    except Exception as e:  # pragma: no cover - injection is best-effort
        logger.debug(f"Canvas noise injection failed: {e}")

    return page

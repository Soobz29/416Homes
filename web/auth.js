/**
 * 416Homes Auth Helper
 *
 * Handles Supabase magic-link callback, persists session to localStorage,
 * and exposes helpers used by every page.
 *
 * Usage: include <script src="/auth.js"></script> before any page script,
 * then call Auth.getEmail() / Auth.headers() in fetch() calls.
 */
(function () {
  const SESSION_KEY = '416homes_session';

  /** Parse a hash like #access_token=...&token_type=bearer&... */
  function _parseHashTokens(hash) {
    const params = {};
    (hash || '').replace(/^#/, '').split('&').forEach(function (part) {
      const kv = part.split('=');
      if (kv.length === 2) params[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1]);
    });
    return params;
  }

  /** Persist a session object {email, access_token, expires_at} */
  function _saveSession(session) {
    try {
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    } catch (e) {}
  }

  /** Read persisted session or null */
  function _loadSession() {
    try {
      const raw = localStorage.getItem(SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  /** Clear session (logout) */
  function _clearSession() {
    try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  /**
   * On page load, check if Supabase redirected back with a magic-link token.
   * If so, exchange it for the user's email via /api/auth/session and persist.
   */
  async function _handleCallbackIfNeeded() {
    const tokens = _parseHashTokens(window.location.hash);
    if (!tokens.access_token) return;

    // Remove fragment from URL (clean up)
    history.replaceState(null, '', window.location.pathname + window.location.search);

    try {
      const resp = await fetch(window.location.origin + '/api/auth/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: tokens.access_token }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.email) {
          _saveSession({
            email: data.email,
            access_token: tokens.access_token,
            expires_at: tokens.expires_at || null,
          });
          // Redirect to dashboard if we were on the login page
          if (window.location.pathname.endsWith('login.html') || window.location.pathname === '/login') {
            window.location.href = '/dashboard';
          }
        }
      }
    } catch (e) {
      console.warn('Auth callback error:', e);
    }
  }

  /** Public API */
  window.Auth = {
    /** Returns the stored email string, or null */
    getEmail: function () {
      const s = _loadSession();
      return s ? s.email : null;
    },

    /** Returns headers dict with x-user-email (and Authorization if token present) */
    headers: function (extra) {
      const s = _loadSession();
      const h = Object.assign({ 'Content-Type': 'application/json' }, extra || {});
      if (s) {
        h['x-user-email'] = s.email;
        if (s.access_token) h['Authorization'] = 'Bearer ' + s.access_token;
      }
      return h;
    },

    /** Save session manually (called from login page after magic-link is sent + confirmed) */
    saveSession: _saveSession,

    /** Clear stored session (logout) */
    logout: function () {
      _clearSession();
      window.location.href = '/login';
    },

    /** True if a non-expired session exists */
    isLoggedIn: function () {
      const s = _loadSession();
      if (!s || !s.email) return false;
      if (s.expires_at) {
        const exp = parseInt(s.expires_at, 10) * 1000;
        if (!isNaN(exp) && Date.now() > exp) { _clearSession(); return false; }
      }
      return true;
    },

    /** Run the Supabase callback handler on page load */
    init: _handleCallbackIfNeeded,
  };

  // Auto-run on every page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _handleCallbackIfNeeded);
  } else {
    _handleCallbackIfNeeded();
  }
})();

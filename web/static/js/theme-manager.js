/**
 * Theme Manager for ImageGenPro Web v2
 * Supports Light / Dark / System modes with CSS Variables + data-theme attribute
 */

(function () {
  const THEME_KEY = 'igp-theme-preference';
  const THEME_TRANSITION_MS = 350;

  function getStoredTheme() {
    try {
      return localStorage.getItem(THEME_KEY);
    } catch (e) {
      return null;
    }
  }

  function setStoredTheme(theme) {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (e) {
      // ignore
    }
  }

  function applyTheme(theme) {
    const root = document.documentElement;
    if (!root) return;

    if (theme === 'light') {
      root.setAttribute('data-theme', 'light');
    } else if (theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
    } else {
      root.removeAttribute('data-theme');
    }

    updateToggleUI(theme);
  }

  function resolveSystemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function getEffectiveTheme() {
    const stored = getStoredTheme();
    if (stored === 'light' || stored === 'dark') return stored;
    return resolveSystemTheme();
  }

  function updateToggleUI(theme) {
    const buttons = document.querySelectorAll('[data-theme-toggle]');
    buttons.forEach((btn) => {
      const btnTheme = btn.getAttribute('data-theme-toggle');
      if (btnTheme === theme) {
        btn.classList.add('active');
        btn.setAttribute('aria-pressed', 'true');
      } else {
        btn.classList.remove('active');
        btn.setAttribute('aria-pressed', 'false');
      }
    });
  }

  function bindToggles() {
    const buttons = document.querySelectorAll('[data-theme-toggle]');
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const theme = btn.getAttribute('data-theme-toggle');
        if (!theme) return;
        setStoredTheme(theme);
        applyTheme(theme);
      });
    });
  }

  function listenToSystemChanges() {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    if (media && media.addEventListener) {
      media.addEventListener('change', () => {
        const stored = getStoredTheme();
        if (!stored || stored === 'system') {
          applyTheme('system');
        }
      });
    }
  }

  function init() {
    const stored = getStoredTheme() || 'system';
    applyTheme(stored);
    bindToggles();
    listenToSystemChanges();

    // Expose API for debugging
    window.ImageGenProTheme = {
      get: getStoredTheme,
      set: (theme) => {
        setStoredTheme(theme);
        applyTheme(theme);
      },
      effective: getEffectiveTheme,
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/** Theme: light/dark/auto (system). */
(function () {
  "use strict";

  const STORAGE_KEY = "relrag-theme";
  const LIGHT = "light";
  const DARK = "dark";
  const AUTO = "auto";

  function getSystemTheme() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? DARK
      : LIGHT;
  }

  function applyTheme(theme) {
    const resolved = theme === AUTO ? getSystemTheme() : theme;
    document.documentElement.setAttribute("data-theme", resolved);
    document.documentElement.classList.toggle("theme-dark", resolved === DARK);
    document.documentElement.classList.toggle("theme-light", resolved === LIGHT);
  }

  function init() {
    const saved = localStorage.getItem(STORAGE_KEY) || AUTO;
    applyTheme(saved);

    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
        if (localStorage.getItem(STORAGE_KEY) === AUTO) applyTheme(AUTO);
      });
    }
  }

  window.relragTheme = {
    LIGHT: LIGHT,
    DARK: DARK,
    AUTO: AUTO,

    init: init,

    get: function () {
      return localStorage.getItem(STORAGE_KEY) || AUTO;
    },

    set: function (theme) {
      localStorage.setItem(STORAGE_KEY, theme);
      applyTheme(theme);
    },

    cycle: function () {
      const cur = this.get();
      const next = cur === LIGHT ? DARK : cur === DARK ? AUTO : LIGHT;
      this.set(next);
      return next;
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

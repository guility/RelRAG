/** Common layout: theme button, nav. */
(function () {
  "use strict";

  function init() {
    const btn = document.getElementById("btnTheme");
    if (btn) {
      function updateLabel() {
        const t = window.relragTheme && window.relragTheme.get();
        const labels = { light: "Светлая", dark: "Тёмная", auto: "Авто (ОС)" };
        btn.title = "Тема: " + (labels[t] || t);
        btn.textContent = t === "light" ? "☀" : t === "dark" ? "🌙" : "🌓";
      }
      btn.onclick = function () {
        if (window.relragTheme) {
          window.relragTheme.cycle();
          updateLabel();
        }
      };
      if (window.relragTheme) updateLabel();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

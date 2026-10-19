/* DEEPLRN progressive-enhancement scripts (nonce'd by the base template). */
(function () {
  "use strict";

  function initNavToggle() {
    var layout = document.querySelector("[data-layout]");
    var toggle = document.querySelector("[data-nav-toggle]");
    if (!layout || !toggle) return;
    toggle.addEventListener("click", function () {
      var open = layout.hasAttribute("data-nav-open");
      if (open) layout.removeAttribute("data-nav-open");
      else layout.setAttribute("data-nav-open", "");
      toggle.setAttribute("aria-expanded", String(!open));
    });
  }

  function initUserMenu() {
    var menu = document.querySelector("[data-user-menu]");
    if (!menu) return;
    var button = menu.querySelector("[data-user-menu-toggle]");
    var panel = menu.querySelector(".user-menu-panel");
    button.addEventListener("click", function () {
      var hidden = panel.hasAttribute("hidden");
      if (hidden) panel.removeAttribute("hidden");
      else panel.setAttribute("hidden", "");
      button.setAttribute("aria-expanded", String(hidden));
    });
    document.addEventListener("click", function (event) {
      if (!menu.contains(event.target)) {
        panel.setAttribute("hidden", "");
        button.setAttribute("aria-expanded", "false");
      }
    });
  }

  function initTheme() {
    var toggle = document.querySelector("[data-theme-toggle]");
    var root = document.documentElement;
    var current = null;
    try {
      current = window.localStorage.getItem("deeplrn-theme");
    } catch (error) {
      current = null;
    }
    if (current) root.setAttribute("data-theme", current);
    else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      root.setAttribute("data-theme", "dark");
    }
    if (!toggle) return;
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try {
        window.localStorage.setItem("deeplrn-theme", next);
      } catch (error) {
        /* storage unavailable: theme is session-only */
      }
    });
  }

  function renderTrend(container, data) {
    /* data: [{date, percent, marked}] */
    var points = data.filter(function (point) {
      return point.percent !== null && point.percent !== undefined;
    });
    if (!points.length) return;
    var width = Math.max(container.clientWidth, 320);
    var height = 160;
    var pad = { top: 10, right: 10, bottom: 22, left: 10 };
    var plotWidth = width - pad.left - pad.right;
    var plotHeight = height - pad.top - pad.bottom;
    var barGap = plotWidth / points.length;
    var barWidth = Math.max(Math.min(barGap * 0.6, 28), 3);

    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("role", "img");

    var axis = document.createElementNS(ns, "line");
    axis.setAttribute("x1", pad.left);
    axis.setAttribute("x2", width - pad.right);
    axis.setAttribute("y1", height - pad.bottom);
    axis.setAttribute("y2", height - pad.bottom);
    axis.setAttribute("class", "axis");
    svg.appendChild(axis);

    points.forEach(function (point, index) {
      var value = Math.min(Math.max(Number(point.percent), 0), 100);
      var barHeight = (value / 100) * plotHeight;
      var x = pad.left + index * barGap + (barGap - barWidth) / 2;
      var bar = document.createElementNS(ns, "rect");
      bar.setAttribute("x", String(x));
      bar.setAttribute("y", String(height - pad.bottom - barHeight));
      bar.setAttribute("width", String(barWidth));
      bar.setAttribute("height", String(barHeight));
      bar.setAttribute("class", "bar");
      var title = document.createElementNS(ns, "title");
      title.textContent = point.date + ": " + point.percent + "% (" + point.marked + " marked)";
      bar.appendChild(title);
      svg.appendChild(bar);

      if (index === 0 || index === points.length - 1 || index % 5 === 0) {
        var label = document.createElementNS(ns, "text");
        label.setAttribute("x", String(x + barWidth / 2));
        label.setAttribute("y", String(height - 6));
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("class", "label");
        label.textContent = String(point.date).slice(5);
        svg.appendChild(label);
      }
    });
    container.replaceChildren(svg);
  }

  function initTrendChart() {
    var element = document.getElementById("trend-data");
    var container = document.querySelector("[data-trend-chart]");
    if (!element || !container) return;
    var data = JSON.parse(element.textContent);
    renderTrend(container, data);
    var timer = null;
    window.addEventListener("resize", function () {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        renderTrend(container, data);
      }, 200);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initNavToggle();
    initUserMenu();
    initTheme();
    initTrendChart();
  });
})();

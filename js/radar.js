/*
 * AgentStack — SVG-радар. Рисует 4 измеренные оси сплошным,
 * затенённые «замкнутые» оси — пунктиром с замком.
 * Поддерживает авто-отрисовку (анимация ~3с).
 */
(function (global) {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  function el(name, attrs) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) e.setAttribute(k, attrs[k]);
    return e;
  }

  // axes: [{label, pct, locked?}] — порядок по кругу.
  // opts: {size, animate, accent}
  function draw(container, axes, opts) {
    opts = opts || {};
    var size = opts.size || 360;
    var cx = size / 2, cy = size / 2;
    var R = size * 0.36;
    var n = axes.length;
    container.innerHTML = "";
    var svg = el("svg", { viewBox: "0 0 " + size + " " + size, width: "100%", height: "100%", role: "img" });

    // сетка-кольца
    [0.25, 0.5, 0.75, 1].forEach(function (f) {
      var pts = [];
      for (var i = 0; i < n; i++) {
        var a = (Math.PI * 2 * i) / n - Math.PI / 2;
        pts.push((cx + Math.cos(a) * R * f).toFixed(1) + "," + (cy + Math.sin(a) * R * f).toFixed(1));
      }
      svg.appendChild(el("polygon", { points: pts.join(" "), fill: "none",
        stroke: "rgba(255,255,255,0.10)", "stroke-width": "1" }));
    });

    // спицы + подписи
    axes.forEach(function (ax, i) {
      var a = (Math.PI * 2 * i) / n - Math.PI / 2;
      var ex = cx + Math.cos(a) * R, ey = cy + Math.sin(a) * R;
      svg.appendChild(el("line", { x1: cx, y1: cy, x2: ex, y2: ey,
        stroke: ax.locked ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.18)",
        "stroke-width": "1", "stroke-dasharray": ax.locked ? "3 4" : "0" }));
      var lx = cx + Math.cos(a) * (R + 26), ly = cy + Math.sin(a) * (R + 26);
      var anchor = Math.abs(Math.cos(a)) < 0.3 ? "middle" : (Math.cos(a) > 0 ? "start" : "end");
      var label = el("text", { x: lx.toFixed(1), y: (ly + 4).toFixed(1), "text-anchor": anchor,
        "font-size": "12", "font-weight": "600",
        fill: ax.locked ? "rgba(168,183,202,0.55)" : "#cfe2f5" });
      label.textContent = (ax.locked ? "🔒 " : "") + ax.label;
      svg.appendChild(label);
    });

    // измеренный полигон (только не-locked оси участвуют значением; locked рисуем у центра)
    var poly = [];
    axes.forEach(function (ax, i) {
      var a = (Math.PI * 2 * i) / n - Math.PI / 2;
      var f = ax.locked ? 0.12 : Math.max(0.04, (ax.pct || 0) / 100);
      poly.push([cx + Math.cos(a) * R * f, cy + Math.sin(a) * R * f]);
    });
    var ptsStr = poly.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" ");
    var accent = opts.accent || "#69e0ff";
    var fill = el("polygon", { points: ptsStr, fill: accent, "fill-opacity": "0.18",
      stroke: accent, "stroke-width": "2", "stroke-linejoin": "round" });
    svg.appendChild(fill);

    // вершины: красные для слабых не-locked осей (<55%)
    axes.forEach(function (ax, i) {
      if (ax.locked) return;
      var a = (Math.PI * 2 * i) / n - Math.PI / 2;
      var f = Math.max(0.04, (ax.pct || 0) / 100);
      var px = cx + Math.cos(a) * R * f, py = cy + Math.sin(a) * R * f;
      var weak = (ax.pct || 0) < 55;
      svg.appendChild(el("circle", { cx: px.toFixed(1), cy: py.toFixed(1), r: weak ? 5 : 4,
        fill: weak ? "#ff6b6b" : accent, stroke: "#07111f", "stroke-width": "1.5" }));
    });

    container.appendChild(svg);

    if (opts.animate) {
      fill.style.transition = "none";
      fill.style.transformOrigin = cx + "px " + cy + "px";
      fill.style.transform = "scale(0.04)";
      fill.style.opacity = "0";
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          fill.style.transition = "transform 1.4s cubic-bezier(.2,.9,.2,1), opacity 1.2s ease";
          fill.style.transform = "scale(1)";
          fill.style.opacity = "1";
        });
      });
    }
    return svg;
  }

  global.AgentStackRadar = { draw: draw };
})(typeof window !== "undefined" ? window : globalThis);

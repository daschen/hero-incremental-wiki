// Hero Incremental wiki: small progressive enhancements. Every page is readable without this file;
// it adds copy buttons, the hero role filter, the calculators and redirects for old #hash links.
(function () {
"use strict";
var BASE = document.body.getAttribute("data-base") || "/";

function $(s, r) { return (r || document).querySelector(s); }
function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
function el(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
function fmt(n) {
  if (!isFinite(n)) return "∞";
  var u = ["", "K", "M", "B", "T", "Qa"], i = 0;
  while (Math.abs(n) >= 1000 && i < u.length - 1) { n /= 1000; i++; }
  if (i === 0) return (n >= 100 ? Math.round(n) : n >= 10 ? Math.round(n * 10) / 10 : Math.round(n * 100) / 100).toLocaleString("en-US");
  return (n >= 100 ? n.toFixed(0) : n >= 10 ? n.toFixed(1) : n.toFixed(2)).replace(/\.?0+$/, "") + u[i];
}
function dur(sec) {
  if (!isFinite(sec) || sec > 3.15e9) return "Never";
  if (sec < 1) return "< 1s";
  if (sec < 60) return Math.round(sec) + "s";
  if (sec < 3600) return Math.round(sec / 60) + " min";
  if (sec < 86400) return (sec / 3600).toFixed(sec < 36000 ? 1 : 0).replace(/\.0$/, "") + " h";
  if (sec < 86400 * 365) return (sec / 86400).toFixed(sec < 864000 ? 1 : 0).replace(/\.0$/, "") + " days";
  return (sec / 86400 / 365).toFixed(1) + " years";
}

// ---------------------------------------------------------------- old single-page links (#codes etc.)
var OLD = { codes: "codes/", heroes: "heroes/", tiers: "tier-list/", ranks: "ranks/", runes: "runes/", tools: "calculator/", bots: "bots/", updates: "updates/" };
var hash = (location.hash || "").slice(1);
if (document.body.getAttribute("data-page") === "home" && OLD[hash]) { location.replace(BASE + OLD[hash]); return; }

// ---------------------------------------------------------------- nav: keep the current tab visible on phones
var cur = $(".nav a[aria-current]");
var navEl = $(".nav");
if (cur && navEl && navEl.scrollWidth > navEl.clientWidth + 2) navEl.scrollLeft = Math.max(0, cur.offsetLeft - navEl.clientWidth / 2 + cur.offsetWidth / 2);

// ---------------------------------------------------------------- "More" menu closes when you click away
var more = $("details.more");
if (more) {
  document.addEventListener("click", function (ev) { if (more.open && !more.contains(ev.target)) more.open = false; });
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") more.open = false; });
}

// ---------------------------------------------------------------- copy buttons
$$("button.copy[data-code]").forEach(function (b) {
  var label = b.firstChild;
  b.addEventListener("click", function () {
    var code = b.getAttribute("data-code");
    var reset = function () { setTimeout(function () { b.classList.remove("done"); label.textContent = "COPY"; }, 1600); };
    var done = function () { b.classList.add("done"); label.textContent = "COPIED"; reset(); };
    var fallback = function () {
      var t = b.parentNode.querySelector(".code-tag"), r = document.createRange();
      r.selectNodeContents(t); var s = getSelection(); s.removeAllRanges(); s.addRange(r);
      label.textContent = "SELECTED"; reset();
    };
    try { navigator.clipboard.writeText(code).then(done, fallback); } catch (e) { fallback(); }
  });
});

// ---------------------------------------------------------------- hero role filter
var tabs = $("#role-tabs");
if (tabs) {
  tabs.hidden = false;
  $$("button", tabs).forEach(function (b) {
    b.addEventListener("click", function () {
      var role = b.getAttribute("data-role");
      $$("button", tabs).forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      $$(".hero-tile[data-role]").forEach(function (t) { t.hidden = role !== "All" && t.getAttribute("data-role") !== role; });
    });
  });
}

// ---------------------------------------------------------------- calculators
var dataEl = document.getElementById("hi-data");
if (!dataEl) return;
var D = JSON.parse(dataEl.textContent);

function chances(altar, luck) {
  if (altar.global) {
    var total = altar.tiers.reduce(function (s, t) { return s + t[1]; }, 0);
    return altar.tiers.map(function (t) { return t[1] / total; });
  }
  var out = [], remaining = 1;
  for (var i = altar.tiers.length - 1; i >= 0; i--) {
    var p = Math.min(1, (luck || 1) / altar.tiers[i][1]);
    out[i] = remaining * p;
    remaining -= out[i];
  }
  return out;
}
function oddsText(p) { if (p <= 0) return "–"; if (p >= 0.1) return (p * 100).toFixed(1).replace(/\.0$/, "") + "%"; var n = 1 / p; return "1/" + (n < 1000 ? Math.round(n) : fmt(n)); }
function v(id) { var e = document.getElementById(id); return e.type === "checkbox" ? e.checked : Number(e.value); }
function on(ids, fn) { ids.forEach(function (id) { document.getElementById(id).addEventListener("input", fn); }); fn(); }

// rune odds
(function () {
  var sel = $("#ro-altar");
  if (!sel) return;
  D.ALTARS.forEach(function (a) { if (!a.global) sel.appendChild(el('<option value="' + a.id + '">' + a.name + "</option>")); });
  var ranges = ["ro-cluck", "ro-rluck", "ro-cspeed", "ro-rspeed", "ro-cbulk", "ro-rbulk", "ro-field", "ro-attune", "ro-shop"];
  on(["ro-altar", "ro-tierluck", "ro-pass-luck", "ro-pass-speed", "ro-pass-bulk", "ro-pass-clone", "ro-pots", "ro-rush"].concat(ranges), function () {
    ranges.forEach(function (id) { document.getElementById(id + "-o").textContent = v(id); });
    var a = D.ALTARS.filter(function (x) { return x.id === sel.value; })[0];
    var field = 1 + 0.15 * v("ro-field"), shop = 1 + 0.1 * v("ro-shop"), pot = v("ro-pots") ? 2 : 1;
    var luck = (1 + 0.25 * v("ro-cluck")) * (1 + 0.25 * v("ro-rluck")) * field * (1 + 0.25 * v("ro-attune")) * shop
      * Math.max(1, v("ro-tierluck") || 1) * (v("ro-pass-luck") ? 1.5 : 1) * pot * (v("ro-rush") ? 1.5 : 1);
    var speed = 2 * (1 + 0.2 * v("ro-cspeed")) * (1 + 0.2 * v("ro-rspeed")) * field * shop * (v("ro-pass-speed") ? 1.5 : 1) * pot;
    var bulk = (1 + 0.3 * v("ro-cbulk")) * (1 + 0.3 * v("ro-rbulk")) * field * shop * (v("ro-pass-bulk") ? 1.5 : 1) * pot;
    var clone = 1 + (v("ro-pass-clone") ? 1 : 0);
    var rps = speed * bulk * clone;
    $("#ro-readout").innerHTML =
      "<div><b>×" + fmt(luck) + "</b><span>Luck</span></div><div><b>" + fmt(speed) + "/s</b><span>Speed</span></div>" +
      "<div><b>" + fmt(bulk) + "</b><span>Bulk</span></div><div><b>" + clone + "</b><span>Clone</span></div>" +
      '<div><b style="color:var(--orange)">' + fmt(rps) + "/s</b><span>Runes per second</span></div>";
    var ch = chances(a, luck);
    $("#ro-table").innerHTML = a.tiers.map(function (t, i) {
      var perSec = rps * ch[i];
      return '<tr><td><span class="tier-dot" style="--tc:' + D.TIER_COLORS[i] + '"></span><b>' + t[0] + '</b></td><td class="r num">1/' + fmt(t[1]) +
        '</td><td class="r num">' + oddsText(ch[i]) + '</td><td class="r num">' + dur(1 / perSec) + '</td><td class="r num">' + fmt(perSec * 3600) +
        '</td><td class="r num">' + dur(t[3] / perSec) + "</td></tr>";
    }).join("");
  });
})();

// redeploy + SR
(function () {
  var sel = $("#rd-rank");
  if (!sel) return;
  D.RANKS.forEach(function (r, i) { if (i >= 1) sel.appendChild(el('<option value="' + i + '"' + (i === 2 ? " selected" : "") + ">" + r.name + "</option>")); });
  on(["rd-rank", "rd-credits", "rd-rm", "rd-ft", "rd-boost", "rd-earned"], function () {
    ["rd-rm", "rd-ft"].forEach(function (id) { document.getElementById(id + "-o").textContent = v(id); });
    var rank = Number(sel.value), credits = Math.max(0, v("rd-credits") || 0), min = D.MIN[rank - 1] || 0;
    var rp = credits < min ? 0 : Math.max(1, Math.floor(Math.sqrt(credits / 150) * Math.pow(2, v("rd-rm")) * (1 + 0.1 * v("rd-ft")) * Math.max(1, v("rd-boost") || 1)));
    var earned = Math.max(0, v("rd-earned") || 0);
    var srNow = Math.floor(Math.sqrt(earned / 2)), srAfter = Math.floor(Math.sqrt((earned + rp) / 2));
    $("#rd-readout").innerHTML = '<div><b style="color:var(--orange)">' + (credits < min ? "Need " + fmt(min) : fmt(rp)) + "</b><span>Redeploy points</span></div>" +
      "<div><b>" + fmt(rp * 100) + "</b><span>Rank XP</span></div><div><b>" + fmt(srNow) + " → " + fmt(srAfter) + "</b><span>SR at promotion</span></div>";
  });
})();

// rank-up planner
(function () {
  var sel = $("#rk-rank");
  if (!sel) return;
  D.RANKS.forEach(function (r, i) { if (i < D.RANKS.length - 1) sel.appendChild(el('<option value="' + i + '"' + (i === 2 ? " selected" : "") + ">" + r.name + "</option>")); });
  on(["rk-rank", "rk-credits", "rk-income"], function () {
    var from = Number(sel.value), have = Math.max(0, v("rk-credits") || 0), perMin = Math.max(1, v("rk-income") || 1);
    var rows = "", firstEta = null;
    for (var i = from + 1; i < D.RANKS.length; i++) {
      var need = Math.max(0, D.RANKS[i].cost - (i === from + 1 ? have : 0));
      var eta = need / perMin * 60;
      if (firstEta === null) firstEta = eta;
      rows += "<tr><td>" + D.RANKS[i].name + '</td><td class="r num">' + fmt(D.RANKS[i].cost) + '</td><td class="r num">' + fmt(need) +
        '</td><td class="r num">' + (need === 0 ? "Ready now" : dur(eta)) + "</td></tr>";
    }
    $("#rk-table").innerHTML = rows;
    var next = D.RANKS[from + 1], pct = Math.min(100, have / next.cost * 100);
    $("#rk-readout").innerHTML = "<div><b>" + next.name + "</b><span>Next rank</span></div><div><b>" + pct.toFixed(pct < 10 ? 1 : 0) + "%</b><span>Progress</span></div>" +
      '<div><b style="color:var(--orange)">' + (firstEta === 0 ? "Now" : dur(firstEta)) + "</b><span>Time to rank up</span></div>" +
      "<div><b>×" + D.RANKS[from].mult + " → ×" + next.mult + "</b><span>Credit multiplier</span></div>";
  });
})();

// ticket planner
(function () {
  var sel = $("#tk-boost");
  if (!sel) return;
  var BOOSTS = [["RuneLuck", "More Luck", 10, "rune Luck"], ["RuneBulk", "More Bulk", 10, "rune Bulk"], ["RuneSpeed", "More Speed", 10, "rune Speed"], ["Credits", "More Credits", 5, "Credits"], ["Redeploy", "More Redeploy", 5, "Redeploy"]];
  BOOSTS.forEach(function (b) { sel.appendChild(el('<option value="' + b[0] + '">' + b[1] + " (0 → 10)</option>")); });
  sel.appendChild(el('<option value="ALL">Every boost to level 10</option>'));
  on(["tk-hours", "tk-have", "tk-boost"], function () {
    var hours = v("tk-hours"), have = Math.max(0, v("tk-have") || 0), perDay = hours * 12;
    $("#tk-hours-o").textContent = hours;
    var pick = sel.value, rows = "", run = 0;
    var list = pick === "ALL" ? BOOSTS : BOOSTS.filter(function (b) { return b[0] === pick; });
    for (var l = 0; l < 10; l++) {
      var cost = 3 * (l + 1) * list.length;
      run += cost;
      var left = Math.max(0, run - have);
      rows += "<tr><td>" + (l + 1) + '</td><td class="r num">' + cost + '</td><td class="r num">' + run + '</td><td class="r num">' +
        (pick === "ALL" ? "Every boost" : "+" + list[0][2] * (l + 1) + "% " + list[0][3]) + '</td><td class="r num">' +
        (left === 0 ? "Now" : (left / perDay).toFixed(1).replace(/\.0$/, "") + " days") + "</td></tr>";
    }
    $("#tk-table").innerHTML = rows;
    var leftAll = Math.max(0, run - have);
    $("#tk-readout").innerHTML = "<div><b>" + perDay + "</b><span>Tickets per day</span></div><div><b>" + run + "</b><span>Tickets to max</span></div>" +
      '<div><b style="color:var(--orange)">' + (leftAll === 0 ? "Now" : (leftAll / perDay).toFixed(1).replace(/\.0$/, "") + " days") + "</b><span>Time to max</span></div>";
  });
})();
})();

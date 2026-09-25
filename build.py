"""Static site generator for the Hero Incremental wiki.

Edit src/data.json (codes, heroes, ranks, runes, bots, tier list, patch notes), then run:
    python build.py
It writes the whole site to docs/ (served by GitHub Pages), including sitemap.xml.
Each page's "Updated" date and sitemap <lastmod> only change when that page's content changes
(tracked in src/lastmod.json), so search engines see honest freshness dates.
"""
import datetime
import hashlib
import html
import json
import math
import pathlib
import re
import shutil

HERE = pathlib.Path(__file__).parent
SRC = HERE / "src"
OUT = HERE / "docs"
SITE = "https://daschen.github.io/hero-incremental-wiki"   # no trailing slash
BASE = "/hero-incremental-wiki/"                             # change to "/" if you move to a custom domain
GAME_URL = "https://www.roblox.com/games/75558507087279"
GOOGLE_VERIFY = "FJ00bImACFERceqv10BLJuMgPNszUCqIstSLtMqbvSM"
TODAY = datetime.date.today()

D = json.loads((SRC / "data.json").read_text(encoding="utf-8"))
HEROES = D["HEROES"]
HERO = {h["id"]: h for h in HEROES}
ROLE_COLOR = D["ROLE_COLOR"]
TIER_OF = {}
for _tier in D["TIERS"]:
    for _hid, _why in _tier["heroes"]:
        TIER_OF[_hid] = (_tier["t"], _tier["c"], _why)


def e(s):
    return html.escape(str(s), quote=True)


def fmt(n):
    u = ["", "K", "M", "B", "T", "Qa"]
    i = 0
    while abs(n) >= 1000 and i < len(u) - 1:
        n /= 1000
        i += 1
    if i == 0:
        return f"{n:,}" if n == int(n) else f"{n:,.2f}".rstrip("0").rstrip(".")
    s = f"{n:.0f}" if n >= 100 else f"{n:.1f}" if n >= 10 else f"{n:.2f}"
    return re.sub(r"\.?0+$", "", s) + u[i]


def img(name):
    return f"{BASE}img/{name}.webp"


def slug(hero_id):
    return hero_id.lower()


# ------------------------------------------------------------------------------------------ shared parts
NAV = [("", "Home"), ("codes/", "Codes"), ("heroes/", "Heroes"), ("tier-list/", "Tier List"), ("ranks/", "Ranks"),
       ("runes/", "Runes"), ("calculator/", "Tools"), ("bots/", "Bots"), ("updates/", "Updates")]

LOGO = ('<svg viewBox="0 0 40 40" aria-hidden="true"><polygon points="20,2 36,11 36,29 20,38 4,29 4,11" fill="none" stroke="#f99e1a" stroke-width="3"/>'
        '<polygon points="13,11 18,11 17,18 23,18 24,11 29,11 26,29 21,29 22,22 16,22 15,29 10,29" fill="#eef4ff"/></svg>')
WEAPON_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#0b1020" d="M2 10h13l2-2h5v4h-3l-1 2h-3l-1 5H9l1-5H2z"/></svg>'


def header(path):
    links = []
    for href, label in NAV:
        active = (href == "" and path == "") or (href != "" and path.startswith(href))
        cur = ' aria-current="page"' if active else ""
        links.append(f'<a href="{BASE}{href}"{cur}><span>{label}</span></a>')
    return f"""<header class="topbar">
  <div class="topbar-in">
    <a class="brand" href="{BASE}" aria-label="Hero Incremental wiki home">{LOGO}<b>HERO <span>INCREMENTAL</span></b></a>
    <nav class="nav" aria-label="Sections">{''.join(links)}</nav>
    <a class="btn btn-primary btn-sm play-mini" href="{GAME_URL}" target="_blank" rel="noopener"><span>Play</span></a>
  </div>
</header>"""


FOOTER = f"""<footer>
  <div class="foot">
    <div>
      <b>Hero Incremental</b>
      <p>A Roblox hero shooter incremental by gaurd21. Codes, guides and calculators, updated with every patch. Not affiliated with or endorsed by Roblox Corporation.</p>
    </div>
    <div>
      <b>Game</b>
      <a href="{GAME_URL}" target="_blank" rel="noopener">Play on Roblox</a>
      <a href="{BASE}codes/">Codes</a>
      <a href="{BASE}updates/">Patch notes</a>
      <a href="{BASE}bots/">Bots</a>
    </div>
    <div>
      <b>Guides</b>
      <a href="{BASE}heroes/">Heroes</a>
      <a href="{BASE}tier-list/">Tier list</a>
      <a href="{BASE}ranks/">Ranks &amp; unlocks</a>
      <a href="{BASE}runes/">Rune odds</a>
      <a href="{BASE}calculator/">Calculators</a>
    </div>
  </div>
</footer>"""


def crumbs(trail):
    """trail: list of (label, path) after Home. Returns visible breadcrumb HTML + BreadcrumbList JSON-LD."""
    items = [("Home", "")] + trail
    parts = []
    for i, (label, p) in enumerate(items):
        if i:
            parts.append('<span aria-hidden="true">/</span>')
        parts.append(f"<span>{e(label)}</span>" if i == len(items) - 1 else f'<a href="{BASE}{p}">{e(label)}</a>')
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": label, "item": f"{SITE}/{p}"} for i, (label, p) in enumerate(items)]}
    return f'<nav class="crumbs" aria-label="Breadcrumb">{"".join(parts)}</nav>', ld


def page_head(eyebrow, h1, lede, trail, stamp=True):
    bc, ld = crumbs(trail)
    st = '<p class="stamp">Updated <b>{{DATE_LONG}}</b></p>' if stamp else ""
    return f"""<div class="page-head">
    {bc}
    <div class="eyebrow">{e(eyebrow)}</div>
    <h1>{h1}</h1>
    <p class="lede">{lede}</p>
    {st}
  </div>""", ld


def code_rows(active_pill=False):
    out = []
    for c in D["CODES"]:
        extra = ' <span class="chip pill-active" style="margin-top:6px;"><span>Active</span></span>' if active_pill else ""
        exp = f" · expires {c['expires']}" if c.get("expires") else " · no expiry"
        out.append(f'<div class="code-row"><div class="code-tag">{e(c["code"])}</div><div class="code-reward">{e(c["reward"])}<small>{e(c["req"])}{exp}</small>{extra}</div>'
                   f'<button class="copy" type="button" data-code="{e(c["code"])}" aria-label="Copy code {e(c["code"])}"><span>COPY</span></button></div>')
    return "".join(out)


def hero_tiles():
    out = []
    for h in HEROES:
        out.append(f'<a class="hero-tile" href="{BASE}heroes/{slug(h["id"])}/" data-role="{h["role"]}" style="--c:{h["c"]}" aria-label="{h["id"]}, {h["role"]} hero">'
                   f'<img src="{img("Hero_" + h["id"])}" alt="{h["id"]} portrait" width="256" height="256" loading="lazy">'
                   f'<img class="role-ic" src="{img("Role_" + h["role"])}" alt="" width="24" height="24"><span class="name">{h["id"].upper()}</span></a>')
    return "".join(out)


def bonus_text(b):
    return " &nbsp;".join(f'<span class="bonus" style="color:{D["RUNE_STATS"][k][1]}">×{v} {D["RUNE_STATS"][k][0]}</span>' for k, v in b.items())


def tip_block(icon, title, text, suffix=""):
    return (f'<div class="tip"><img src="{img(icon)}" alt="" width="40" height="40" loading="lazy"><div>'
            f'<h3 class="tip-h">{e(title)}{suffix}</h3><p>{e(text)}</p></div></div>')


# ------------------------------------------------------------------------------------------ pages
PAGES = []


def add(path, title, desc, body, ld=None, page_id="page", head_extra=""):
    PAGES.append(dict(path=path, title=title, desc=desc, body=body, ld=ld or [], id=page_id, head_extra=head_extra))


def build_home():
    lineup = "".join(
        f'<a href="{BASE}heroes/{slug(i)}/" data-name="{i.upper()}" style="--c:{HERO[i]["c"]}"><img src="{img("Hero_" + i)}" alt="{i}" width="256" height="256"></a>'
        for i in ["Bulwark", "Ember", "Vanguard", "Longshot", "Broker", "Solace"])
    stats = "".join(f"<div><b>{n}</b><span>{l}</span></div>" for n, l in
                    [(len(HEROES), "Heroes"), (len(D["RANKS"]) - 1, "Ranks"), (len(D["SYSTEMS"]), "Systems"), (len(D["ALTARS"]), "Rune altars")])
    keys = "".join(f'<div class="key"><kbd>{k}</kbd>{e(v)}</div>' for k, v in D["KEYS"])
    p = D["PATCHES"][0]
    latest = "".join(f"<li>{e(x)}</li>" for x in p["items"][:4])
    quick = [("heroes/", "HeroToken", "Heroes", "All 12 heroes with weapons, abilities and ultimates."),
             ("tier-list/", "Credits", "Tier list", "Which heroes farm Credits fastest."),
             ("ranks/", "Promotion", "Ranks", "Every rank's cost, multiplier and unlocks."),
             ("runes/", "Runes", "Runes", "All four altars with full odds tables."),
             ("calculator/", "Ticket", "Calculators", "Rune odds, rank-up and ticket planners."),
             ("bots/", "Turrets", "Bots", "Health, armor and payouts for every bot.")]
    quick_html = "".join(f'<a href="{BASE}{h}"><img src="{img(i)}" alt="" width="52" height="52" loading="lazy"><span><b>{t}</b><small>{d}</small></span></a>' for h, i, t, d in quick)
    body = f"""<section class="wrap">
  <div class="hero-banner">
    <div class="hero-copy">
      <div class="eyebrow">Roblox · Hero shooter × incremental</div>
      <h1><span class="l1">Hero</span><span class="l2">Incremental</span></h1>
      <p class="lede">Pick a hero, clear waves of training bots and watch the numbers climb. Rank from Bronze to Silver, storm a castle town, and roll runes that make every hit bigger.</p>
      <div class="cta-row">
        <a class="btn btn-primary" href="{GAME_URL}" target="_blank" rel="noopener"><span>▶ Play on Roblox</span></a>
        <a class="btn btn-ghost" href="{BASE}codes/"><span>Active codes</span></a>
      </div>
      <div class="stat-strip">{stats}</div>
    </div>
    <div><div class="lineup">{lineup}<div class="lineup-glow" aria-hidden="true"></div></div></div>
  </div>
  <div class="page" style="padding-top: 24px;">
    <div class="home-grid">
      <div class="panel">
        <h2>Active codes</h2>
        {code_rows()}
        <p class="note" style="margin-top: 12px;">Redeem in the Shop (press <b>X</b>) under Codes, or in Settings. <a href="{BASE}codes/">How to redeem</a></p>
      </div>
      <div class="panel" style="--accent: var(--sky);">
        <h2>Controls</h2>
        <div class="keys">{keys}</div>
      </div>
      <div class="panel span2">
        <h2>Guides &amp; tools</h2>
        <div class="quick">{quick_html}</div>
      </div>
      <div class="panel span2">
        <h2>Latest update: {e(p['title'])}</h2>
        <ul class="lede" style="margin:0;padding-left:20px;display:grid;gap:6px;font-size:16px;">{latest}</ul>
        <p style="margin-top:14px;"><a class="btn btn-ghost btn-sm" href="{BASE}updates/"><span>All patch notes</span></a></p>
      </div>
      <div class="panel span2" style="--accent: var(--sky);">
        <div class="prose">
          <h2>What is Hero Incremental?</h2>
          <p>Hero Incremental is a Roblox game that mixes a hero shooter with an incremental progression loop. You pick one of {len(HEROES)} heroes, each with its own weapon, ability and ultimate, and fight training bots for Credits. Credits buy upgrades, upgrades make you hit harder, and ranking up raises your Credit multiplier so every kill pays more.</p>
          <p>As you climb from Bronze to Silver, new systems unlock: Redeploy and the Cargo Bay for permanent upgrades, the Payload and Control Point objectives, turrets, hero mastery, bounties and rune altars. At Silver you reach the castle town of Sturmfeste with the Siege Push, parkour, the Research Lab and Trials. This wiki covers all of it, with <a href="{BASE}codes/">working codes</a>, a <a href="{BASE}tier-list/">tier list</a>, <a href="{BASE}runes/">rune odds</a> and <a href="{BASE}calculator/">calculators</a>.</p>
        </div>
      </div>
    </div>
  </div>
</section>"""
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "Hero Incremental Wiki", "url": SITE + "/",
           "description": "Codes, heroes, tier list, rank guide, rune odds and calculators for Hero Incremental on Roblox."},
          {"@context": "https://schema.org", "@type": "VideoGame", "name": "Hero Incremental", "url": GAME_URL,
           "gamePlatform": "Roblox", "applicationCategory": "Game", "genre": ["Incremental", "Shooter"],
           "author": {"@type": "Person", "name": "gaurd21"},
           "description": "A Roblox hero shooter incremental: pick from 12 heroes, farm Credits, rank from Bronze to Silver and roll runes."}]
    add("", "Hero Incremental Wiki: Codes, Tier List, Heroes & Calculators",
        "The Hero Incremental (Roblox) wiki: working codes, all 12 heroes, a farming tier list, rank costs and unlocks, rune odds and calculators.",
        body, ld, "home", head_extra=f'<meta name="google-site-verification" content="{GOOGLE_VERIFY}">')


def build_codes():
    head, bc = page_head("Free rewards", "Hero Incremental codes",
                         "Every working code for Hero Incremental on Roblox, checked against the live game. Each code works once per account.", [("Codes", "codes/")])
    names = ", ".join(c["code"] for c in D["CODES"])
    faq = [
        ("What are the working Hero Incremental codes?", f"The working codes are {names}. " + " ".join(f"{c['code']} gives {c['reward']}." for c in D["CODES"])),
        ("How do I redeem codes in Hero Incremental?", "Join the game, press X to open the Shop, scroll to the Codes section, type the code and press Use. You can also redeem codes from the Settings menu (the gear icon)."),
        ("Why is my Hero Incremental code not working?", "Each code works once per account, so it may already be redeemed. Check the spelling, and note that some codes need a certain rank: STURMFESTE only works once you reach Silver. Expired codes stop working after their end date."),
        ("Where do new Hero Incremental codes come from?", "New codes are released with game updates and milestones. This page is updated whenever a code is added or expires."),
    ]
    faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
    body = f"""<section class="wrap page">
  {head}
  <div class="panel">
    <h2>Working codes ({{{{MONTH}}}})</h2>
    {code_rows(active_pill=True)}
  </div>
  <div class="home-grid">
    <div class="panel" style="--accent: var(--sky);">
      <h2>How to redeem</h2>
      <ol class="lede" style="margin: 0; padding-left: 22px; display: grid; gap: 8px; font-size: 16px;">
        <li>Join the game and press <kbd>X</kbd> to open the Shop.</li>
        <li>Scroll to the <b>Codes</b> section at the bottom.</li>
        <li>Type the code exactly as shown and press <b>Use</b>.</li>
      </ol>
      <p class="note" style="margin-top: 12px;">You can also redeem from the Settings menu (the gear icon, top right).</p>
    </div>
    <div class="panel" style="--accent: var(--dim);">
      <h2>Expired codes</h2>
      <p class="lede" style="font-size: 16px;">None yet. When a code expires it moves here, so you know not to bother trying it.</p>
    </div>
  </div>
  <div class="panel">
    <h2>Codes FAQ</h2>
    <div class="faq">{faq_html}</div>
  </div>
</section>"""
    ld = [bc, {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]
    add("codes/", "Hero Incremental Codes ({{MONTH}}): All Working Codes",
        f"All working Hero Incremental codes for {{{{MONTH}}}}: {names}. Rewards, requirements and how to redeem them on Roblox.", body, ld, "codes")


def hero_card(h):
    w, a, u = h["weapon"], h["ability"], h["ult"]
    stats = "".join(f"<span>{e(s)}</span>" for s in w["stats"])
    return f"""<div class="panel hero-detail" style="--c:{h['c']}">
    <div class="hd-portrait"><img src="{img('Hero_' + h['id'])}" alt="{h['id']} portrait" width="256" height="256"></div>
    <div class="hd-body">
      <div class="hd-name"><h1>{h['id']}</h1><span class="chip" style="color:{ROLE_COLOR[h['role']]}"><span><img src="{img('Role_' + h['role'])}" alt="" width="18" height="18">{h['role']}</span></span></div>
      <div class="hd-tag">{e(h['tag'])}</div>
      <p class="hd-desc">{e(h['desc'])}</p>
      <div class="kit">
        <div class="kit-card"><header><div class="kit-weapon-icon">{WEAPON_SVG}</div><div><span class="slot">Weapon</span><h2 class="kit-h">{e(w['name'])}</h2></div></header>
          <p>{e(w['blurb'])} {e(w['perk'])}</p><div class="stats">{stats}</div></div>
        <div class="kit-card"><header><img src="{img(a['icon'])}" alt="{e(a['name'])} icon" width="44" height="44"><div><span class="slot">Ability · E</span><h2 class="kit-h">{e(a['name'])}</h2></div></header>
          <p>{e(a['blurb'])}</p><div class="stats"><span>{a['cd']}s cooldown</span></div></div>
        <div class="kit-card"><header><img src="{img(u['icon'])}" alt="{e(u['name'])} icon" width="44" height="44"><div><span class="slot">Ultimate · Q</span><h2 class="kit-h">{e(u['name'])}</h2></div></header>
          <p>{e(u['blurb'])}</p></div>
      </div>
    </div>
  </div>"""


def build_heroes():
    head, bc = page_head("Hero select", "Hero Incremental heroes",
                         f"All {len(HEROES)} heroes in Hero Incremental across three roles. You start with one, then earn a Hero Token every rank up and spend it on any hero you like.",
                         [("Heroes", "heroes/")])
    tabs = "".join(f'<button type="button" data-role="{r}" aria-pressed="{"true" if r == "All" else "false"}"><span>'
                   + ("" if r == "All" else f'<img src="{img("Role_" + r)}" alt="" width="22" height="22">') + f"{r}</span></button>"
                   for r in ["All", "Tank", "Damage", "Support"])
    rows = "".join(
        f'<tr><td><a href="{BASE}heroes/{slug(h["id"])}/" style="--c:{h["c"]}"><img src="{img("Hero_" + h["id"])}" alt="" width="34" height="34" loading="lazy">{h["id"]}</a></td>'
        f'<td style="color:{ROLE_COLOR[h["role"]]}">{h["role"]}</td><td>{e(h["weapon"]["name"])}</td><td>{e(h["ability"]["name"])}</td><td>{e(h["ult"]["name"])}</td>'
        f'<td class="num">{TIER_OF.get(h["id"], ("–",))[0]}</td></tr>' for h in HEROES)
    body = f"""<section class="wrap page">
  {head}
  <div class="role-tabs" id="role-tabs" hidden>{tabs}</div>
  <div class="hero-grid">{hero_tiles()}</div>
  <div class="panel">
    <h2>Every hero at a glance</h2>
    <div class="table-scroll"><table class="hero-table"><thead><tr><th>Hero</th><th>Role</th><th>Weapon</th><th>Ability (E)</th><th>Ultimate (Q)</th><th>Tier</th></tr></thead><tbody>{rows}</tbody></table></div>
  </div>
</section>"""
    add("heroes/", "Hero Incremental Heroes: All 12 Heroes, Abilities & Ultimates",
        "Every Hero Incremental hero: Tank, Damage and Support roles, weapons, abilities, ultimates and how to unlock them with Hero Tokens.", body, [bc], "heroes")

    for i, h in enumerate(HEROES):
        s = slug(h["id"])
        bc_html, bc_ld = crumbs([("Heroes", "heroes/"), (h["id"], f"heroes/{s}/")])
        t = TIER_OF.get(h["id"])
        tier_html = (f'<div class="tier-callout" style="--t:{t[1]}"><b>{t[0]}</b><p><a href="{BASE}tier-list/">{t[0]} tier for farming.</a> {e(t[2])}</p></div>') if t else ""
        same = [x for x in HEROES if x["role"] == h["role"] and x["id"] != h["id"]]
        mini = "".join(
            f'<a href="{BASE}heroes/{slug(x["id"])}/" style="--c:{x["c"]}"' + (' aria-current="page"' if x["id"] == h["id"] else "") +
            f'><img src="{img("Hero_" + x["id"])}" alt="" width="92" height="92" loading="lazy">{x["id"]}</a>' for x in HEROES)
        prev_h, next_h = HEROES[i - 1], HEROES[(i + 1) % len(HEROES)]
        same_txt = ", ".join(f'<a href="{BASE}heroes/{slug(x["id"])}/">{x["id"]}</a>' for x in same) or "none yet"
        body = f"""<section class="wrap page">
  <div class="page-head" style="max-width:none;">{bc_html}<p class="stamp">Updated <b>{{{{DATE_LONG}}}}</b></p></div>
  {hero_card(h)}
  {tier_html}
  <div class="panel" style="--accent: var(--sky);">
    <div class="prose">
      <h2>How to play {h['id']}</h2>
      <p>{h['id']} is a {h['role']} hero in Hero Incremental. Weapon: the {e(h['weapon']['name'])}. {e(h['weapon']['blurb'])} Press <kbd>E</kbd> for {e(h['ability']['name'])} ({h['ability']['cd']}s cooldown) and <kbd>Q</kbd> for {e(h['ult']['name'])} once your ultimate is charged.</p>
      <p>Unlock {h['id']} with a Hero Token: you get one every time you rank up, and can spend it on any hero. Other {h['role']} heroes: {same_txt}.</p>
    </div>
  </div>
  <div class="hero-nav">
    <a class="btn btn-ghost btn-sm" href="{BASE}heroes/{slug(prev_h['id'])}/"><span>← {prev_h['id']}</span></a>
    <a class="btn btn-ghost btn-sm" href="{BASE}heroes/{slug(next_h['id'])}/"><span>{next_h['id']} →</span></a>
  </div>
  <div class="panel"><h2>All heroes</h2><div class="mini-heroes">{mini}</div></div>
</section>"""
        desc = (f"{h['id']} is a {h['role']} hero in Hero Incremental (Roblox). Weapon: {h['weapon']['name']}. "
                f"Ability: {h['ability']['name']}. Ultimate: {h['ult']['name']}." + (f" {t[0]} tier for farming." if t else ""))
        add(f"heroes/{s}/", f"{h['id']} Guide: {h['role']} Hero Abilities & Ultimate | Hero Incremental", desc, body, [bc_ld], "hero")


def build_tiers():
    head, bc = page_head("Dev picks", "Hero Incremental tier list",
                         "Which heroes earn Credits fastest once they're upgraded. Every hero can clear every zone; this ranks raw farming speed, not fun.", [("Tier List", "tier-list/")])
    rows = []
    for tier in D["TIERS"]:
        items = "".join(
            f'<div class="tier-item" style="--c:{HERO[hid]["c"]}"><a class="pic" href="{BASE}heroes/{slug(hid)}/"><img src="{img("Hero_" + hid)}" alt="{hid}" width="64" height="64" loading="lazy"></a>'
            f'<div><a href="{BASE}heroes/{slug(hid)}/"><b><img src="{img("Role_" + HERO[hid]["role"])}" alt="{HERO[hid]["role"]}" width="18" height="18">{hid}</b></a><p>{e(why)}</p></div></div>'
            for hid, why in tier["heroes"])
        rows.append(f'<div class="tier-row" style="--t:{tier["c"]}"><div class="tier-label">{tier["t"]}</div><div class="tier-items">{items}</div></div>')
    best = ", ".join(hid for hid, _ in D["TIERS"][0]["heroes"])
    body = f"""<section class="wrap page">
  {head}
  <div>{''.join(rows)}</div>
  <div class="panel" style="--accent: var(--sky);">
    <div class="prose">
      <h2>How this tier list works</h2>
      <p>Heroes are ranked by how quickly they turn bots into Credits at the same upgrade level. Heroes that multiply Credits directly (like Broker's Jackpot or Solace's Sanctuary) or hit several bots at once rank highest. The best farmers right now are {best}.</p>
      <p>Tanks and supports also make objectives easier: a tank holds the Payload and Control Point, and healers keep your On Fire streak going. Every rank up gives you a Hero Token, so you'll own most of the roster by Silver anyway. See every hero's kit on the <a href="{BASE}heroes/">heroes page</a>.</p>
    </div>
  </div>
</section>"""
    add("tier-list/", "Hero Incremental Tier List ({{MONTH}}): Best Heroes for Farming",
        f"The Hero Incremental tier list for {{{{MONTH}}}}: which of the 12 heroes farm Credits fastest, from S tier ({best}) down to C tier.", body, [bc], "tiers")


def build_ranks():
    head, bc = page_head("Progression", "Hero Incremental ranks &amp; unlocks",
                         "Ranking up costs Credits and raises your Credit multiplier. Almost every rank opens a new system, and every rank grants a Hero Token.", [("Ranks", "ranks/")])
    rows = []
    for i, r in enumerate(D["RANKS"]):
        chips = "".join(f'<span class="chip" title="{e(D["SYSTEMS"][k]["b"])}"><span><img src="{img(D["SYSTEMS"][k]["icon"])}" alt="" width="18" height="18">{D["SYSTEMS"][k]["t"]}</span></span>'
                        for k in D["UNLOCKS"].get(str(i), []))
        if i >= 1:
            chips += f'<span class="chip"><span><img src="{img("HeroToken")}" alt="" width="18" height="18">Hero Token</span></span>'
        if i == len(D["RANKS"]) - 1:
            chips += '<span class="chip pill-warn"><span>Gold: coming soon</span></span>'
        tier = r["name"].split(" ")[1] if " " in r["name"] else "–"
        cost = fmt(r["cost"]) if r["cost"] else "Start"
        rows.append(f'<tr><td><span class="rank-badge" style="--a:{r["a"]};--b:{r["b"]}"><i>{tier}</i>{r["name"]}</span></td><td class="r num">{cost}</td>'
                    f'<td class="r num mult">×{r["mult"]}</td><td><div class="unlocks">{chips}</div></td></tr>')
    systems = []
    for rank_s, keys in sorted(D["UNLOCKS"].items(), key=lambda kv: int(kv[0])):
        for k in keys:
            s = D["SYSTEMS"][k]
            systems.append(tip_block(s["icon"], s["t"], s["b"], f' <span class="note" style="font-style:normal;font-weight:600;">· {D["RANKS"][int(rank_s)]["name"]}</span>'))
    tips = "".join(tip_block(i, t, b) for i, t, b in D["TIPS"])
    top = D["RANKS"][-1]
    body = f"""<section class="wrap page">
  {head}
  <div class="panel">
    <h2>Rank ladder</h2>
    <div class="table-scroll"><table class="ladder"><thead><tr><th>Rank</th><th class="r">Cost (Credits)</th><th class="r">Credit mult.</th><th>Unlocks</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
    <p class="note" style="margin-top:10px;">Plan your next rank with the <a href="{BASE}calculator/#rank">rank-up calculator</a>.</p>
  </div>
  <div class="panel">
    <h2>Every system and when it unlocks</h2>
    <div class="sys-grid">{''.join(systems)}</div>
  </div>
  <div class="panel" style="--accent: var(--sky);">
    <h2>Progression tips</h2>
    <div class="tips">{tips}</div>
  </div>
</section>"""
    add("ranks/", "Hero Incremental Ranks: Costs, Multipliers & Unlocks",
        f"Every Hero Incremental rank from Bronze 5 to {top['name']}: Credit cost, Credit multiplier (up to ×{top['mult']}) and which systems each rank unlocks.", body, [bc], "ranks")


def build_runes():
    head, bc = page_head("Unlocks at Bronze 2", "Hero Incremental runes",
                         "Stand on a rune altar and it rolls for you every second. Every tier you own gives a permanent bonus that grows with your count until it hits [MAX]. Runes never reset.", [("Runes", "runes/")])
    legend = "".join(f'<div style="--sc:{c}"><b>{n}</b><span>{d}</span></div>' for n, c, d in
                     [("Luck", "#6ee678", "Shortens the odds of rare tiers."), ("Bulk", "#5aaaff", "Runes gained per roll."), ("Speed", "#ffc846", "Rolls per second. Starts at 2."),
                      ("Clone", "#d2a0ff", "Extra copies of every roll."), ("Runes/s", "#ff6a5a", "Speed × Clone × Bulk.")])
    jump = "".join(f'<a class="chip" href="#{a["id"].lower()}" style="text-decoration:none;color:{a["color"]}"><span>{a["name"]}</span></a>' for a in D["ALTARS"])
    secs = []
    for a in D["ALTARS"]:
        total = sum(t[1] for t in a["tiers"])

        def odds(t, a=a, total=total):
            if a.get("global"):
                pct = t[1] / total * 100
                return (f"{pct:.1f}".rstrip("0").rstrip(".") if pct >= 0.1 else f"{pct:.2g}") + "%"
            return "1/" + fmt(t[1])
        trs = "".join(f'<tr><td><span class="tier-dot" style="--tc:{D["TIER_COLORS"][i]}"></span><b>{t[0]}</b></td><td class="r num">{odds(t)}</td><td>{bonus_text(t[2])}</td><td class="r num">{fmt(t[3])}</td></tr>'
                      for i, t in enumerate(a["tiers"]))
        note = "<p class=\"note\" style=\"margin-bottom:6px;\">Whenever anyone buys Global Runes, every player in the server gets the rolls. Luck doesn't change these odds.</p>" if a.get("global") else ""
        secs.append(f"""<section class="panel altar-sec" id="{a['id'].lower()}" style="--accent:{a['color']}">
    <h2 style="color:{a['color']}">{a['name']}</h2>
    <div class="altar-meta"><span class="chip"><span>{e(a['where'])}</span></span><span class="chip"><span>Unlocks: {a['unlock']}</span></span><span class="chip"><span>Cost: {a['cost']}</span></span></div>
    {note}
    <div class="table-scroll"><table><thead><tr><th>Tier</th><th class="r">{'Chance' if a.get('global') else 'Base odds'}</th><th>Bonus at [MAX]</th><th class="r">[MAX] at</th></tr></thead><tbody>{trs}</tbody></table></div>
  </section>""")
    body = f"""<section class="wrap page">
  {head}
  <div class="stat-legend">{legend}</div>
  <div class="altar-jump">{jump}</div>
  {''.join(secs)}
  <div class="panel" style="--accent: var(--sky);">
    <div class="prose">
      <h2>How rune odds work</h2>
      <p>Each roll checks the rarest tier first. Your Luck divides that tier's odds (a 1/1,000 tier becomes 1/500 at ×2 Luck); if it misses, the next rarest tier is checked, down to the common tier. A tier's bonus grows with how many you own, fast at first and slower later, and stops at [MAX]. Bonuses from every altar multiply together.</p>
      <p>Luck comes from the Rune Luck pass (×1.5), Luck Potions (×2 for 15 minutes), the "More Luck" ticket boost (+10% per level), Rune Attunement in the Cargo Bay (+25% per level) and runes that give Luck. Work out your exact odds and time to [MAX] with the <a href="{BASE}calculator/">rune odds calculator</a>.</p>
    </div>
  </div>
</section>"""
    add("runes/", "Hero Incremental Runes: Altar Odds, Tiers & Bonuses",
        "Every Hero Incremental rune altar (Valor, Fortune, Tempest and Unity) with full tier odds, bonuses at [MAX], unlock costs and how Luck works.", body, [bc], "runes")


def build_calculator():
    head, bc = page_head("Calculators", "Hero Incremental calculators",
                         "Plug in your numbers to plan rune farming, rank ups and ticket spending. They use the same formulas as the game.", [("Calculators", "calculator/")])
    data = json.dumps({"RANKS": D["RANKS"], "ALTARS": D["ALTARS"], "TIER_COLORS": D["TIER_COLORS"]}, separators=(",", ":"))
    body = f"""<section class="wrap page">
  {head}
  <div class="panel tool altar-sec" id="runes">
    <div class="form">
      <h2 style="margin: 0;">Rune odds calculator</h2>
      <div class="field"><label for="ro-altar">Altar</label><select id="ro-altar"></select></div>
      <div class="field"><span class="lbl">Luck</span>
        <label class="check"><input type="checkbox" id="ro-pass-luck"> Rune Luck pass (×1.5)</label>
        <label class="check"><input type="checkbox" id="ro-pot-luck"> Luck Potion active (×2)</label>
      </div>
      <div class="field"><label for="ro-shop-luck">"More Luck" boost level</label><div class="range-row"><input type="range" id="ro-shop-luck" min="0" max="10" value="3"><output id="ro-shop-luck-o">3</output></div></div>
      <div class="field"><label for="ro-attune">Rune Attunement (Cargo Bay)</label><div class="range-row"><input type="range" id="ro-attune" min="0" max="3" value="1"><output id="ro-attune-o">1</output></div></div>
      <div class="field"><label for="ro-tierluck">Luck from owned runes (×)</label><input type="number" id="ro-tierluck" min="1" step="0.05" value="1.2"></div>
      <div class="field"><span class="lbl">Rolling</span>
        <label class="check"><input type="checkbox" id="ro-pass-speed"> Rune Speed pass (×1.5)</label>
        <label class="check"><input type="checkbox" id="ro-pass-bulk"> Rune Bulk pass (×1.5)</label>
        <label class="check"><input type="checkbox" id="ro-pass-clone"> Rune Clone pass (+1)</label>
      </div>
      <div class="field"><label for="ro-shop-speed">"More Speed" boost level</label><div class="range-row"><input type="range" id="ro-shop-speed" min="0" max="10" value="2"><output id="ro-shop-speed-o">2</output></div></div>
    </div>
    <div class="results">
      <div class="readout" id="ro-readout"></div>
      <div class="table-scroll"><table><thead><tr><th>Tier</th><th class="r">Base odds</th><th class="r">Your odds</th><th class="r">First pull in</th><th class="r">Per hour</th><th class="r">[MAX] in</th></tr></thead><tbody id="ro-table"></tbody></table></div>
      <p class="note">Example build shown. Times are averages: rare tiers can land much sooner or later. "Luck from owned runes" is the Luck bonus on your Runes menu stats line.</p>
    </div>
  </div>
  <div class="panel tool altar-sec" id="rank" style="--accent: var(--sky);">
    <div class="form">
      <h2 style="margin: 0;">Rank-up calculator</h2>
      <div class="field"><label for="rk-rank">Current rank</label><select id="rk-rank"></select></div>
      <div class="field"><label for="rk-credits">Credits you have</label><input type="number" id="rk-credits" min="0" step="1000" value="120000"></div>
      <div class="field"><label for="rk-income">Credits per minute</label><input type="number" id="rk-income" min="1" step="1000" value="45000"></div>
    </div>
    <div class="results">
      <div class="readout" id="rk-readout"></div>
      <div class="table-scroll"><table><thead><tr><th>Next rank</th><th class="r">Cost</th><th class="r">Still needed</th><th class="r">Time at this income</th></tr></thead><tbody id="rk-table"></tbody></table></div>
      <p class="note">Example numbers shown. Your income jumps after every rank up (higher Credit multiplier), so later ranks arrive sooner than this estimate.</p>
    </div>
  </div>
  <div class="panel tool altar-sec" id="tickets" style="--accent: var(--warn);">
    <div class="form">
      <h2 style="margin: 0;">Ticket planner</h2>
      <div class="field"><label for="tk-hours">Hours played per day</label><div class="range-row"><input type="range" id="tk-hours" min="0.5" max="8" step="0.5" value="2"><output id="tk-hours-o">2</output></div></div>
      <div class="field"><label for="tk-have">Tickets you have</label><input type="number" id="tk-have" min="0" value="40"></div>
      <div class="field"><label for="tk-boost">Plan for</label><select id="tk-boost"></select></div>
    </div>
    <div class="results">
      <div class="readout" id="tk-readout"></div>
      <div class="table-scroll"><table><thead><tr><th>Level</th><th class="r">Ticket cost</th><th class="r">Running total</th><th class="r">Bonus</th><th class="r">Ready in</th></tr></thead><tbody id="tk-table"></tbody></table></div>
      <p class="note">You earn 1 Ticket for every 5 minutes in the game (nothing while offline). Each boost level costs 3 Tickets more than the last. Potion packs cost 20 Tickets for 10 potions.</p>
    </div>
  </div>
</section>
<script type="application/json" id="hi-data">{data}</script>"""
    add("calculator/", "Hero Incremental Calculators: Rune Odds, Rank-Up & Ticket Planner",
        "Free Hero Incremental calculators: rune odds and time to [MAX] for every altar, time to your next rank, and how long to max ticket boosts.", body, [bc], "calculator")


def build_bots():
    head, bc = page_head("Enemy database", "Hero Incremental bots",
                         "Every bot type, where it spawns and what it pays. Credits listed are base payouts: your rank's Credit multiplier and every upgrade stack on top.", [("Bots", "bots/")])
    top = math.log10(max(b["hp"] for b in D["BOTS"]))
    cards = []
    for b in D["BOTS"]:
        note = f'<p class="note">{e(b["note"])}</p>' if b.get("note") else ""
        cards.append(f"""<div class="panel bot" style="--accent:var(--damage)"><div><h2 class="bot-h">{b['name']}</h2><div class="where">{b['zone']} · from {b['rank']}</div></div>
      <div class="hp-bar" title="Health (log scale)"><i style="width:{math.log10(b['hp']) / top * 100:.1f}%"></i></div>
      <dl><div><dt>Health</dt><dd>{fmt(b['hp'])}</dd></div><div><dt>Armor</dt><dd>{round(b['armor'] * 100)}%</dd></div><div><dt>Hit</dt><dd>{b['dmg']}</dd></div>
      <div><dt>Credits</dt><dd style="color:var(--orange)">{fmt(b['credits'])}</dd></div><div><dt>Respawn</dt><dd>{b['respawn']}s</dd></div><div><dt>Credits / HP</dt><dd>{b['credits'] / b['hp']:.2f}</dd></div></dl>{note}</div>""")
    body = f"""<section class="wrap page">
  {head}
  <div class="bot-grid">{''.join(cards)}</div>
</section>"""
    add("bots/", "Hero Incremental Bots: Health, Armor & Credits for Every Enemy",
        "Every Hero Incremental bot, from Training Drones to Wardens: health, armor, damage, Credit payout, respawn time and where each one spawns.", body, [bc], "bots")


def build_updates():
    head, bc = page_head("Patch notes", "Hero Incremental updates", "What changed in each build of Hero Incremental, newest first.", [("Updates", "updates/")])
    arts = []
    for i, p in enumerate(D["PATCHES"]):
        latest = '<span class="chip pill-active"><span>Latest</span></span>' if i == 0 else ""
        items = "".join(f"<li>{e(x)}</li>" for x in p["items"])
        arts.append(f'<article class="patch"><div class="patch-side"><b>{e(p["tag"])}</b>{latest}</div><div><h2 class="patch-h">{e(p["title"])}</h2><ul>{items}</ul></div></article>')
    body = f"""<section class="wrap page">
  {head}
  <div class="panel">{''.join(arts)}</div>
</section>"""
    add("updates/", "Hero Incremental Updates & Patch Notes",
        f"Hero Incremental patch notes and update log. Latest: {D['PATCHES'][0]['title']}.", body, [bc], "updates")


def build_404():
    body = f"""<section class="wrap page not-found">
  <div class="page-head">
    <div class="eyebrow">Error 404</div>
    <h1>Page not found</h1>
    <p class="lede">That page doesn't exist (or it moved). Try one of these instead.</p>
  </div>
  <div class="cta-row">
    <a class="btn btn-primary" href="{BASE}"><span>Home</span></a>
    <a class="btn btn-ghost" href="{BASE}codes/"><span>Codes</span></a>
    <a class="btn btn-ghost" href="{BASE}heroes/"><span>Heroes</span></a>
    <a class="btn btn-ghost" href="{BASE}tier-list/"><span>Tier list</span></a>
  </div>
</section>"""
    add("404.html", "Page Not Found | Hero Incremental Wiki", "This page doesn't exist.", body, [], "404")


# ------------------------------------------------------------------------------------------ render + write
def render(p, asset_v):
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False, separators=(",", ":"))}</script>' for x in p["ld"])
    is404 = p["path"] == "404.html"
    canonical = f"{SITE}/{p['path']}"
    meta_url = "" if is404 else f'<link rel="canonical" href="{canonical}">\n<meta property="og:url" content="{canonical}">'
    robots = '<meta name="robots" content="noindex">' if is404 else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(p['title'])}</title>
<meta name="description" content="{e(p['desc'])}">
{meta_url}{robots}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Hero Incremental Wiki">
<meta property="og:title" content="{e(p['title'])}">
<meta property="og:description" content="{e(p['desc'])}">
<meta property="og:image" content="{SITE}/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0a1224">
{p['head_extra']}
<link rel="icon" type="image/png" sizes="96x96" href="{BASE}assets/favicon-96.png">
<link rel="apple-touch-icon" href="{BASE}assets/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,500;0,600;0,700;1,600;1,700;1,800;1,900&family=Jost:wght@400;500;600&display=swap">
<link rel="stylesheet" href="{BASE}assets/site.css?v={asset_v}">
{ld}
</head>
<body data-base="{BASE}" data-page="{p['id']}">
{header(p['path'])}
<main>
{p['body']}
</main>
{FOOTER}
<script src="{BASE}assets/site.js?v={asset_v}" defer></script>
</body>
</html>
"""


def main():
    for f in (build_home, build_codes, build_heroes, build_tiers, build_ranks, build_runes, build_calculator, build_bots, build_updates, build_404):
        f()

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    shutil.copytree(SRC / "img", OUT / "img")
    for name in ("site.css", "site.js"):
        shutil.copy(SRC / name, OUT / "assets" / name)
    for f in (SRC / "assets").iterdir():
        shutil.copy(f, OUT / "assets" / f.name)
    (OUT / ".nojekyll").write_text("")
    asset_v = hashlib.sha1((SRC / "site.css").read_bytes() + (SRC / "site.js").read_bytes()).hexdigest()[:8]

    # honest freshness: a page's date only moves when its own content changes
    manifest_path = SRC / "lastmod.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    sitemap = []
    for p in PAGES:
        digest = hashlib.sha1((p["title"] + p["desc"] + p["body"]).encode("utf-8")).hexdigest()
        old = manifest.get(p["path"])
        date = old["date"] if old and old["hash"] == digest else TODAY.isoformat()
        manifest[p["path"]] = {"hash": digest, "date": date}
        d = datetime.date.fromisoformat(date)
        month, long = d.strftime("%B %Y"), f"{d.strftime('%B')} {d.day}, {d.year}"
        out = render(p, asset_v).replace("{{MONTH}}", month).replace("{{DATE_LONG}}", long)
        target = OUT / p["path"] if p["path"].endswith(".html") else OUT / p["path"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(out, encoding="utf-8")
        if p["path"] != "404.html":
            sitemap.append(f"  <url><loc>{SITE}/{p['path']}</loc><lastmod>{date}</lastmod></url>")
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "\n".join(sitemap) + "\n</urlset>\n", encoding="utf-8")
    print(f"built {len(PAGES)} pages -> {OUT} ({len(sitemap)} in sitemap)")


if __name__ == "__main__":
    main()

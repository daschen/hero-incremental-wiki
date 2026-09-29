"""Static site generator for the Hero Incremental wiki.

Edit src/content.py (all game data and text), then run:
    python build.py
It writes the whole site to docs/ (served by GitHub Pages), including sitemap.xml.
Each page's "Updated" date and sitemap <lastmod> only change when that page's content changes
(tracked in src/lastmod.json), so search engines see honest freshness dates.
"""
import datetime
import hashlib
import html
import importlib.util
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
GOOGLE_VERIFY = "FJ00bImACFERceqv10BLJuMgPNszUCqIstSLtMqbvSM"
TODAY = datetime.date.today()

_spec = importlib.util.spec_from_file_location("content", SRC / "content.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

GAME_URL = C.GAME_URL
HEROES = C.HEROES
HERO = {h["id"]: h for h in HEROES}
ROLE_COLOR = C.ROLE_COLOR
TIER_OF = {}
for _tier in C.TIERS:
    for _hid, _why in _tier["heroes"]:
        TIER_OF[_hid] = (_tier["t"], _tier["c"], _why)
ORDER_OF = {row[1]: (i, row[0], row[2]) for i, row in enumerate(C.UNLOCK_ORDER)}


def e(s):
    return html.escape(str(s), quote=True)


SUFFIX = ["", "K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]


def fmt(n):
    if isinstance(n, str):
        return n
    i = 0
    while abs(n) >= 1000 and i < len(SUFFIX) - 1:
        n /= 1000
        i += 1
    if i == 0:
        return f"{n:,.0f}" if n == int(n) else f"{n:,.2f}".rstrip("0").rstrip(".")
    s = f"{n:.0f}" if n >= 100 else f"{n:.1f}" if n >= 10 else f"{n:.2f}"
    return re.sub(r"\.?0+$", "", s) + SUFFIX[i]


def img(name):
    return f"{BASE}img/{name}.webp"


def slug(hero_id):
    return hero_id.lower()


def hero_link(hid, pic=True):
    h = HERO[hid]
    p = f'<img src="{img("Hero_" + hid)}" alt="" width="34" height="34" loading="lazy">' if pic else ""
    return f'<a href="{BASE}heroes/{slug(hid)}/" style="--c:{h["c"]}">{p}{hid}</a>'


# ------------------------------------------------------------------------------------------ navigation
NAV = [("codes/", "Codes"), ("guide/", "Guide"), ("heroes/", "Heroes"), ("tier-list/", "Tier List"),
       ("ranks/", "Ranks"), ("runes/", "Runes"), ("upgrades/", "Upgrades"), ("calculator/", "Tools"), ("faq/", "FAQ")]
MORE = [("currencies/", "Currencies", "Credits"), ("objectives/", "Objectives", "Payload"), ("sturmfeste/", "Sturmfeste", "Island"),
        ("events/", "Events", "WorldBoss"), ("skins/", "Skins & Season", "Season"), ("shop/", "Shop & Passes", "Ticket"),
        ("bots/", "Bots", "Turrets"), ("updates/", "Updates", "Guide")]
WIKI = [("guide/", "Guide", "Beginner walkthrough, rank by rank.", "Guide"), ("heroes/", "Heroes", "Kits, passives, perks and tips.", "HeroToken"),
        ("tier-list/", "Tier List", "Best farmers and unlock order.", "Promotion"), ("ranks/", "Ranks", "Costs, multipliers, unlocks, resets.", "SR"),
        ("currencies/", "Currencies", "What every currency is for.", "Credits"), ("upgrades/", "Upgrades", "All 9 trees, every node.", "Upgrades"),
        ("runes/", "Runes", "Altars, odds, luck and bonuses.", "Runes"), ("objectives/", "Objectives", "Payload, capture points, bounties.", "Payload"),
        ("sturmfeste/", "Sturmfeste", "Siege, parkour, research, trials.", "Island"), ("events/", "Events", "World boss, boards, titles, daily.", "WorldBoss"),
        ("skins/", "Skins & Season", "27 skins and Season 1.", "SkinToken"), ("shop/", "Shop", "Passes, products, tickets.", "Ticket"),
        ("calculator/", "Calculators", "Runes, ranks, Redeploy, tickets.", "Research"), ("bots/", "Bots", "Every enemy's stats.", "Turrets"),
        ("codes/", "Codes", "Every working code.", "GlobalRunes"), ("faq/", "FAQ", "Quick answers to common questions.", "Guide")]

LOGO = ('<svg viewBox="0 0 40 40" aria-hidden="true"><polygon points="20,2 36,11 36,29 20,38 4,29 4,11" fill="none" stroke="#f99e1a" stroke-width="3"/>'
        '<polygon points="13,11 18,11 17,18 23,18 24,11 29,11 26,29 21,29 22,22 16,22 15,29 10,29" fill="#eef4ff"/></svg>')
WEAPON_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#0b1020" d="M2 10h13l2-2h5v4h-3l-1 2h-3l-1 5H9l1-5H2z"/></svg>'


def header(path):
    links = []
    for href, label in NAV:
        active = (href == "" and path == "") or (href != "" and path.startswith(href))
        links.append(f'<a href="{BASE}{href}"' + (' aria-current="page"' if active else "") + f"><span>{label}</span></a>")
    more_active = any(path.startswith(h) for h, _, _ in MORE)
    more = "".join(f'<a href="{BASE}{h}"' + (' aria-current="page"' if path.startswith(h) else "") + f'><img src="{img(i)}" alt="" width="26" height="26">{t}</a>' for h, t, i in MORE)
    return f"""<header class="topbar">
  <div class="topbar-in">
    <a class="brand" href="{BASE}" aria-label="Hero Incremental wiki home">{LOGO}<b>HERO <span>INCREMENTAL</span></b></a>
    <nav class="nav" aria-label="Sections">{''.join(links)}</nav>
    <details class="more{' active' if more_active else ''}"><summary><span>More ▾</span></summary><div class="more-menu">{more}</div></details>
    <a class="btn btn-primary btn-sm play-mini" href="{GAME_URL}" target="_blank" rel="noopener"><span>Play</span></a>
  </div>
</header>"""


FOOTER = f"""<footer>
  <div class="foot">
    <div>
      <b>Hero Incremental</b>
      <p>A Roblox hero shooter incremental by gaurd21. Codes, guides and calculators, updated with every patch. Not affiliated with or endorsed by Roblox Corporation.</p>
      <p style="margin-top:10px;"><a href="{GAME_URL}" target="_blank" rel="noopener">▶ Play on Roblox</a></p>
    </div>
    <div>
      <b>Guides</b>
      <a href="{BASE}guide/">Beginner guide</a><a href="{BASE}heroes/">Heroes</a><a href="{BASE}tier-list/">Tier list</a><a href="{BASE}ranks/">Ranks</a>
      <a href="{BASE}currencies/">Currencies</a><a href="{BASE}upgrades/">Upgrades</a><a href="{BASE}runes/">Runes</a><a href="{BASE}faq/">FAQ</a>
    </div>
    <div>
      <b>Game</b>
      <a href="{BASE}codes/">Codes</a><a href="{BASE}objectives/">Objectives</a><a href="{BASE}sturmfeste/">Sturmfeste</a><a href="{BASE}events/">Events</a>
      <a href="{BASE}skins/">Skins &amp; Season</a><a href="{BASE}shop/">Shop</a><a href="{BASE}bots/">Bots</a><a href="{BASE}calculator/">Calculators</a><a href="{BASE}updates/">Updates</a>
    </div>
  </div>
</footer>"""


def crumbs(trail):
    items = [("Home", "")] + trail
    parts = []
    for i, (label, p) in enumerate(items):
        if i:
            parts.append('<span aria-hidden="true">/</span>')
        parts.append(f"<span>{e(label)}</span>" if i == len(items) - 1 else f'<a href="{BASE}{p}">{e(label)}</a>')
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": label, "item": f"{SITE}/{p}"} for i, (label, p) in enumerate(items)]}
    return f'<nav class="crumbs" aria-label="Breadcrumb">{"".join(parts)}</nav>', ld


def page_head(eyebrow, h1, lede, trail, answer=None):
    bc, ld = crumbs(trail)
    ans = f'<div class="answer"><b class="k">Quick answer</b><p>{answer}</p></div>' if answer else ""
    return f"""<div class="page-head" style="max-width:900px;">
    {bc}
    <div class="eyebrow">{e(eyebrow)}</div>
    <h1>{h1}</h1>
    <p class="lede">{lede}</p>
    <p class="stamp">Updated <b>{{{{DATE_LONG}}}}</b></p>
  </div>
  {ans}""", ld


def faq_block(items, title="Questions"):
    html_ = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in items)
    ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}
    return f'<section class="panel sec" id="faq" style="--accent: var(--sky);"><h2>{e(title)}</h2><div class="faq">{html_}</div></section>', ld


def sec(id_, title, icon, sub, body, accent=None):
    ac = f' style="--accent:{accent}"' if accent else ""
    ic = f'<img src="{img(icon)}" alt="" width="44" height="44" loading="lazy">' if icon else ""
    sb = f"<small>{sub}</small>" if sub else ""
    return f'<section class="panel sec" id="{id_}"{ac}><div class="sec-h">{ic}<div><h2>{title}</h2>{sb}</div></div>{body}</section>'


def toc(items):
    return '<nav class="toc" aria-label="On this page">' + "".join(f'<a class="chip" href="#{i}"><span>{t}</span></a>' for i, t in items) + "</nav>"


def table(head, rows, cls="", right=()):
    th = "".join(f'<th{" class=\"r\"" if i in right else ""}>{h}</th>' for i, h in enumerate(head))
    trs = "".join("<tr>" + "".join(f'<td{" class=\"r num\"" if i in right else ""}>{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="table-scroll"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def code_rows(active_pill=False):
    out = []
    for c in C.CODES:
        extra = ' <span class="chip pill-active" style="margin-top:6px;"><span>Active</span></span>' if active_pill else ""
        exp = f" · expires {c['expires']}" if c.get("expires") else " · no expiry"
        out.append(f'<div class="code-row"><div class="code-tag">{e(c["code"])}</div><div class="code-reward">{e(c["reward"])}<small>{e(c["req"])}{exp}</small>{extra}</div>'
                   f'<button class="copy" type="button" data-code="{e(c["code"])}" aria-label="Copy code {e(c["code"])}"><span>COPY</span></button></div>')
    return "".join(out)


def hero_tiles():
    return "".join(
        f'<a class="hero-tile" href="{BASE}heroes/{slug(h["id"])}/" data-role="{h["role"]}" style="--c:{h["c"]}" aria-label="{h["id"]}, {h["role"]} hero">'
        f'<img src="{img("Hero_" + h["id"])}" alt="{h["id"]} portrait" width="256" height="256" loading="lazy">'
        f'<img class="role-ic" src="{img("Role_" + h["role"])}" alt="" width="24" height="24"><span class="name">{h["id"].upper()}</span></a>' for h in HEROES)


def bonus_text(b):
    return " &nbsp;".join(f'<span class="bonus" style="color:{C.RUNE_STATS[k][1]}">×{v} {C.RUNE_STATS[k][0]}</span>' for k, v in b.items())


def tip_block(icon, title, text, suffix=""):
    return (f'<div class="tip"><img src="{img(icon)}" alt="" width="40" height="40" loading="lazy"><div>'
            f'<h3 class="tip-h">{e(title)}{suffix}</h3><p>{e(text)}</p></div></div>')


def order_table(rows=None):
    rows = rows or C.UNLOCK_ORDER
    body = "".join(f'<tr><td>{e(r[0])}</td><td>{hero_link(r[1])}</td><td>{e(r[2])}</td></tr>' for r in rows)
    return f'<div class="table-scroll"><table class="order-table"><thead><tr><th>Token</th><th>Hero</th><th>Why now</th></tr></thead><tbody>{body}</tbody></table></div>'


RESET_TXT = {"run": ("Redeploy + rank up", "reset-run"), "rank": ("Rank up", "reset-rank"), "never": ("Never", "reset-never")}

# ------------------------------------------------------------------------------------------ pages
PAGES = []


def add(path, title, desc, body, ld=None, page_id="page", head_extra=""):
    PAGES.append(dict(path=path, title=title, desc=desc, body=body, ld=ld or [], id=page_id, head_extra=head_extra))


# ---- home ---------------------------------------------------------------------------------
def build_home():
    lineup = "".join(
        f'<a href="{BASE}heroes/{slug(i)}/" data-name="{i.upper()}" style="--c:{HERO[i]["c"]}"><img src="{img("Hero_" + i)}" alt="{i}" width="256" height="256"></a>'
        for i in ["Bulwark", "Broker", "Solace", "Ember", "Kestrel", "Anchor"])
    stats = "".join(f"<div><b>{n}</b><span>{l}</span></div>" for n, l in
                    [(len(HEROES), "Heroes"), (len(C.RANKS) - 1, "Ranks"), (len(C.TREES), "Upgrade trees"), (sum(len(v) for v in C.SKINS.values()), "Skins")])
    keys = "".join(f'<div class="key"><kbd>{k}</kbd>{e(v)}</div>' for k, v in C.KEYS[:12])
    p = C.PATCHES[0]
    latest = "".join(f"<li>{e(x)}</li>" for x in p["items"][:5])
    wiki = "".join(f'<a href="{BASE}{h}"><img src="{img(i)}" alt="" width="40" height="40" loading="lazy"><span><b>{t}</b><small>{d}</small></span></a>' for h, t, d, i in WIKI)
    faq_html, faq_ld = faq_block(C.FAQ[:6], "Common questions")
    body = f"""<section class="wrap">
  <div class="hero-banner">
    <div class="hero-copy">
      <div class="eyebrow">Roblox · Hero shooter × incremental</div>
      <h1><span class="l1">Hero</span><span class="l2">Incremental</span></h1>
      <p class="lede">The complete Hero Incremental wiki: every code, hero, rank, rune and upgrade tree, with calculators that use the game's own formulas.</p>
      <div class="cta-row">
        <a class="btn btn-primary" href="{BASE}guide/"><span>Beginner guide</span></a>
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
        <p class="note" style="margin-top: 12px;">Press <b>X</b> in game and use the Codes section. <a href="{BASE}codes/">How to redeem</a></p>
      </div>
      <div class="panel" style="--accent: var(--sky);">
        <h2>Controls</h2>
        <div class="keys">{keys}</div>
        <p class="note" style="margin-top:12px;">Every key is in the <a href="{BASE}guide/#controls">guide</a>.</p>
      </div>
      <div class="panel span2">
        <h2>The wiki</h2>
        <div class="wiki-grid">{wiki}</div>
      </div>
      <div class="panel span2">
        <h2>Which hero should I unlock?</h2>
        <p class="lede-sm" style="margin-bottom:12px;">You start with Vanguard and get a Hero Token every rank up. This order matches each hero to the system that unlocks at that rank.</p>
        {order_table(C.UNLOCK_ORDER[:6])}
        <p style="margin-top:14px;"><a class="btn btn-ghost btn-sm" href="{BASE}tier-list/#unlock-order"><span>Full unlock order &amp; tier list</span></a></p>
      </div>
      <div class="panel span2">
        <h2>Latest update: {e(p['title'])}</h2>
        <ul class="tiplist">{latest}</ul>
        <p style="margin-top:14px;"><a class="btn btn-ghost btn-sm" href="{BASE}updates/"><span>All patch notes</span></a></p>
      </div>
      <div class="panel span2" style="--accent: var(--sky);">
        <div class="prose">
          <h2>What is Hero Incremental?</h2>
          <p>Hero Incremental is a Roblox game that mixes a hero shooter with an incremental progression loop. You pick from {len(HEROES)} heroes, each with a weapon, ability, ultimate and passive, and fight waves of bots for Credits. Credits buy upgrades, upgrades make you hit harder, and every rank up raises your Credit multiplier so each kill pays more.</p>
          <p>Every rank opens a new layer that makes the last one faster: Redeploy and the Cargo Bay, payloads and capture points in three sectors, turrets, bounties, rune altars and the Command tree, then Silver's castle town of Sturmfeste with the Siege Push, parkour, the Research Lab, Trials and an hourly World Boss.</p>
        </div>
      </div>
      <div class="span2">{faq_html}</div>
    </div>
  </div>
</section>"""
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "Hero Incremental Wiki", "url": SITE + "/",
           "description": "Codes, heroes, tier list, rank guide, rune odds and calculators for Hero Incremental on Roblox."},
          {"@context": "https://schema.org", "@type": "VideoGame", "name": "Hero Incremental", "url": GAME_URL, "gamePlatform": "Roblox",
           "applicationCategory": "Game", "genre": ["Incremental", "Shooter"], "author": {"@type": "Person", "name": "gaurd21"},
           "description": "A Roblox hero shooter incremental: 12 heroes, Bronze to Silver ranks, runes, upgrade trees and a castle-town siege."}, faq_ld]
    add("", "Hero Incremental Wiki: Codes, Tier List, Heroes & Guides",
        "The Hero Incremental (Roblox) wiki: working codes, all 12 heroes, tier list and unlock order, ranks, runes, every upgrade tree and calculators.",
        body, ld, "home", head_extra=f'<meta name="google-site-verification" content="{GOOGLE_VERIFY}">')


# ---- codes --------------------------------------------------------------------------------
def build_codes():
    names = ", ".join(c["code"] for c in C.CODES)
    head, bc = page_head("Free rewards", "Hero Incremental codes",
                         "Every working code for Hero Incremental on Roblox, checked against the live game. Each code works once per account.",
                         [("Codes", "codes/")], f"The working Hero Incremental codes are <b>{names}</b>. Press X in game, scroll to Codes, type the code and press Use.")
    faq = [
        ("What are the working Hero Incremental codes?", f"The working codes are {names}. " + " ".join(f"{c['code']} gives {c['reward']}." for c in C.CODES)),
        ("How do I redeem codes in Hero Incremental?", "Join the game, press X to open the Shop, scroll to the Codes section, type the code and press Use. You can also redeem codes from the Settings menu (the gear icon)."),
        ("Why is my Hero Incremental code not working?", "Each code works once per account, so it may already be redeemed. Check the spelling. STURMFESTE only works after your first promotion to Silver, and expired codes stop working after their end date."),
        ("When do new codes come out?", "New codes are released with game updates and milestones. This page is updated whenever a code is added or expires."),
    ]
    faq_html, faq_ld = faq_block(faq, "Codes FAQ")
    body = f"""<section class="wrap page">
  {head}
  <div class="panel"><h2>Working codes ({{{{MONTH}}}})</h2>{code_rows(active_pill=True)}</div>
  <div class="home-grid">
    <div class="panel" style="--accent: var(--sky);">
      <h2>How to redeem</h2>
      <ol class="lede" style="margin:0;padding-left:22px;display:grid;gap:8px;font-size:16px;">
        <li>Join the game and press <kbd>X</kbd> to open the Shop.</li>
        <li>Scroll to the <b>Codes</b> section at the bottom.</li>
        <li>Type the code exactly as shown and press <b>Use</b>.</li>
      </ol>
      <p class="note" style="margin-top:12px;">You can also redeem from the Settings menu (the gear icon, top right).</p>
    </div>
    <div class="panel" style="--accent: var(--dim);">
      <h2>Expired codes</h2>
      <p class="lede" style="font-size:16px;">None yet. When a code expires it moves here, so you know not to bother trying it.</p>
    </div>
  </div>
  <div class="panel"><h2>More free rewards</h2><div class="tips">
    {tip_block("Daily", "Daily streak", "Log in on consecutive days: Credits every day, Cargo on days 3 and 5, and a Skin Token on day 7.")}
    {tip_block("Ticket", "Tickets", "1 Ticket every 5 minutes you play, plus World Boss and weekly board rewards.")}
    {tip_block("Season", "Season Pass free track", "30 tiers of Tickets, potions and Skin Tokens for playing.")}
    {tip_block("GlobalRunes", "Global Runes", "When anyone buys Global Runes, everyone in the server gets free rolls.")}
  </div></div>
  {faq_html}
</section>"""
    add("codes/", "Hero Incremental Codes ({{MONTH}}): All Working Codes",
        f"All working Hero Incremental codes for {{{{MONTH}}}}: {names}. Rewards, requirements and how to redeem them on Roblox.", body, [bc, faq_ld], "codes")


# ---- guide --------------------------------------------------------------------------------
def build_guide():
    head, bc = page_head("New player guide", "Hero Incremental beginner guide",
                         "How to go from your first kill to Silver: what to buy, when to Redeploy and which hero to unlock at every rank.", [("Guide", "guide/")],
                         "Shoot Training bots, buy Damage and Credit Multiplier, rank up to Bronze 5, then Redeploy often and buy Redeploy Multiplier and Credit Surge first. Spend every Hero Token (Ember first), spend Cargo right away, and keep a rune altar rolling from Bronze 2.")
    steps = "".join(f'<div class="step"><div><h3>{e(t)}</h3><p>{e(b)}</p></div></div>' for t, b in C.GUIDE_STEPS)
    tips = "".join(tip_block(i, t, b) for i, t, b in C.TIPS)
    keys = "".join(f'<div class="key"><kbd>{k}</kbd>{e(v)}</div>' for k, v in C.KEYS)
    priorities = [
        ("Credit tab", "Credits", "Damage until kills feel quick, then Credit Multiplier and Fire Rate. From Bronze 2 add Rune Speed, Luck and Bulk."),
        ("Redeploy tab", "Redeploy", "Redeploy Multiplier and Credit Surge first (each doubles your gains), then Quartermaster so Credit upgrades buy themselves."),
        ("Cargo Bay", "Cargo", "Supply Drop and Armory Uplink, then Priority Shipping for more Cargo. Later: Auto-Redeploy and Standing Orders."),
        ("Command tree", "Command", "Field Command for rune stats, then build one turret to open Rune Engine and Engineers."),
        ("Bounty shop", "Marks", "Trophy Hunter for Credits, Bounty Scope for more Marks, and Skin Vouchers for skins."),
        ("Skill Rating", "SR", "Veteran's Pay and Iron Sights, then Auto-Capture for idle CP."),
    ]
    prio = "".join(f'<div class="card"><h3><img src="{img(i)}" alt="" width="34" height="34">{t}</h3><p>{e(b)}</p></div>' for t, i, b in priorities)
    faq = [
        ("What should I do first in Hero Incremental?", "Kill Training bots in the Main Hall, put your first Credits into Damage, then Credit Multiplier and Fire Rate. Rank up to Bronze 5 at 5K Credits and spend your first Hero Token."),
        ("When should I Redeploy?", "Whenever the Redeploy payout on the board has grown a lot since your last one. Early on that's every few minutes. Once you own Auto-Redeploy (Cargo Bay), the game does it for you when the payout stops growing."),
        ("What should I buy with Redeploy points?", "Redeploy Multiplier and Credit Surge first: each level doubles your Redeploy payout or kill Credits. Then Quartermaster, which auto-buys Credit upgrades."),
        ("How long does it take to reach Silver?", "Around 70 minutes of active play to Bronze 1 and about 2 hours to Silver 5, if you keep Redeploying and spending permanent currencies. Silver 1 takes roughly a full day of play."),
    ]
    faq_html, faq_ld = faq_block(faq, "Guide FAQ")
    body = f"""<section class="wrap page">
  {head}
  {toc([("path", "Rank by rank"), ("priorities", "What to buy"), ("heroes", "Which heroes"), ("tips", "Tips"), ("controls", "Controls"), ("faq", "FAQ")])}
  {sec("path", "Rank by rank", "Promotion", "The path from your first kill to Silver", f'<div class="steps">{steps}</div>')}
  {sec("priorities", "What to buy first", "Upgrades", "Priorities in each tree", f'<div class="grid3">{prio}</div><p class="note" style="margin-top:10px;">Every node, cost and cap: <a href="{BASE}upgrades/">upgrades</a>.</p>')}
  {sec("heroes", "Which hero to unlock at each rank", "HeroToken", "You get one Hero Token per rank up", order_table())}
  {sec("tips", "Tips", "Guide", "Small things that add up", f'<div class="tips">{tips}</div>', "var(--sky)")}
  {sec("controls", "Controls", "Hub", "Keyboard and mouse (controller and touch are supported too)", f'<div class="keys">{keys}</div>')}
  {faq_html}
</section>"""
    add("guide/", "Hero Incremental Beginner Guide: What to Do First & Rank Up Fast",
        "A rank-by-rank Hero Incremental guide: what to buy first, when to Redeploy, which hero to unlock at each rank, and how to reach Silver fast.", body, [bc, faq_ld], "guide")


# ---- faq ----------------------------------------------------------------------------------
def build_faq():
    head, bc = page_head("Answers", "Hero Incremental FAQ", "Short answers to the questions players ask most.", [("FAQ", "faq/")])
    faq_html, faq_ld = faq_block(C.FAQ, "Frequently asked questions")
    body = f"""<section class="wrap page">
  {head}
  {faq_html.replace('<details>', '<details open>', 3)}
  <div class="panel"><h2>Still stuck?</h2><p class="lede-sm">Every system has its own page: <a href="{BASE}currencies/">currencies</a>, <a href="{BASE}upgrades/">upgrades</a>,
  <a href="{BASE}objectives/">objectives</a>, <a href="{BASE}sturmfeste/">Sturmfeste</a> and <a href="{BASE}events/">events</a>. You can also send feedback in game from the terminal on the Hub wall.</p></div>
</section>"""
    add("faq/", "Hero Incremental FAQ: Heroes, Resets, Runes, AFK & More",
        "Answers to common Hero Incremental questions: getting heroes, what resets on rank up, Redeploy, offline progress, AFK, runes, groups, skins and VIP.",
        body, [bc, faq_ld], "faq")


# ---- heroes -------------------------------------------------------------------------------
def statbars(h):
    out = []
    for k in ("Difficulty", "Survival", "Mobility", "Damage"):
        v = h["stats"][k]
        out.append(f'<div class="statbar"><span>{k}</span><i aria-label="{v} of 5">' + "".join(f'<b class="{"on" if j < v else ""}"></b>' for j in range(5)) + "</i></div>")
    return f'<div class="statbars">{"".join(out)}</div>'


def hero_card(h):
    w, a, u = h["weapon"], h["ability"], h["ult"]
    stats = "".join(f"<span>{e(s)}</span>" for s in w["stats"])
    alt = f'<span>Right-click: {e(w["alt"])}</span>' if w.get("alt") else ""
    return f"""<div class="panel hero-detail" style="--c:{h['c']}">
    <div class="hd-portrait"><img src="{img('Hero_' + h['id'])}" alt="{h['id']} portrait" width="256" height="256"></div>
    <div class="hd-body">
      <div class="hd-name"><h1>{h['id']}</h1><span class="chip" style="color:{ROLE_COLOR[h['role']]}"><span><img src="{img('Role_' + h['role'])}" alt="" width="18" height="18">{h['role']}</span></span></div>
      <div class="hd-tag">{e(h['tag'])}</div>
      <p class="hd-desc">{e(h['desc'])}</p>
      {statbars(h)}
      <div class="passive"><b>Passive</b><p><strong>{e(h['passive'][0])}</strong>{e(h['passive'][1])}</p></div>
      <div class="kit">
        <div class="kit-card"><header><div class="kit-weapon-icon">{WEAPON_SVG}</div><div><span class="slot">Weapon</span><h2 class="kit-h">{e(w['name'])}</h2></div></header>
          <p>{e(w['blurb'])} {e(w['perk'])}</p><div class="stats">{stats}{alt}</div></div>
        <div class="kit-card"><header><img src="{img(a['icon'])}" alt="{e(a['name'])} icon" width="44" height="44"><div><span class="slot">Ability · E</span><h2 class="kit-h">{e(a['name'])}</h2></div></header>
          <p>{e(a['blurb'])}</p><div class="stats"><span>{a['cd']}s cooldown</span></div></div>
        <div class="kit-card"><header><img src="{img(u['icon'])}" alt="{e(u['name'])} icon" width="44" height="44"><div><span class="slot">Ultimate · Q</span><h2 class="kit-h">{e(u['name'])}</h2></div></header>
          <p>{e(u['blurb'])}</p></div>
      </div>
    </div>
  </div>"""


def build_heroes():
    head, bc = page_head("Hero select", "Hero Incremental heroes",
                         f"All {len(HEROES)} heroes across three roles, with their passives, perks and farming tier.", [("Heroes", "heroes/")],
                         "There are 12 heroes: 2 Tanks (Bulwark, Anchor), 8 Damage and 2 Supports (Solace, Vesper). You start with Vanguard and earn a Hero Token every rank up to unlock any hero you like. Broker, Bulwark and Solace farm fastest.")
    tabs = "".join(f'<button type="button" data-role="{r}" aria-pressed="{"true" if r == "All" else "false"}"><span>'
                   + ("" if r == "All" else f'<img src="{img("Role_" + r)}" alt="" width="22" height="22">') + f"{r}</span></button>"
                   for r in ["All", "Tank", "Damage", "Support"])
    rows = [[hero_link(h["id"]), f'<span style="color:{ROLE_COLOR[h["role"]]}">{h["role"]}</span>', f'<b>{e(h["passive"][0])}</b>: {e(h["passive"][1])}',
             e(h["ability"]["name"]), e(h["ult"]["name"]), f'<b style="color:{TIER_OF[h["id"]][1]}">{TIER_OF[h["id"]][0]}</b>'] for h in HEROES]
    faq = [
        ("How do I unlock heroes in Hero Incremental?", "Every rank up and the promotion to Silver pay a Hero Token. Spend it at the Hero terminal in the Hub or press H. Tokens can also come from the Store, the Starter Pack and the THANKYOU code."),
        ("What is Hero Mastery?", "Kills level up the hero you're playing. At Mastery 2 you choose one of two minor perks, and at Mastery 3 one of two major perks (open HEROES > MASTERY). Mastery Tomes from the Bounty shop add 250 XP."),
        ("What does right-click do?", "Right-click is each hero's alt-fire: rifles and pistols aim down sights, Longshot scopes in, and the tanks (Bulwark and Anchor) raise a guard that cuts damage taken by 60% while slowing you down."),
        ("Which hero is best?", "For farming Credits: Broker, Bulwark and Solace (S tier). In a group Vesper joins them, because her passive doubles the Squad Bonus."),
    ]
    faq_html, faq_ld = faq_block(faq, "Hero FAQ")
    roles = [("Tank", "Big health pools and melee cleaves. Hold the cart and capture points; right-click raises a guard."),
             ("Damage", "The widest spread of weapons, from Ember's flamethrower to Longshot's rail. Most of the Credit farmers are here."),
             ("Support", "Heal themselves and boost the group: Solace doubles everyone's Credits, Vesper doubles the Squad Bonus.")]
    role_cards = "".join(f'<div class="card"><h3><img src="{img("Role_" + r)}" alt="" width="34" height="34">{r}</h3><p>{e(b)}</p></div>' for r, b in roles)
    body = f"""<section class="wrap page">
  {head}
  <div class="role-tabs" id="role-tabs" hidden>{tabs}</div>
  <div class="hero-grid">{hero_tiles()}</div>
  <div class="grid3">{role_cards}</div>
  <div class="panel"><h2>Every hero at a glance</h2>{table(["Hero", "Role", "Passive", "Ability (E)", "Ultimate (Q)", "Tier"], rows, "hero-table")}</div>
  <div class="panel"><h2>Recommended unlock order</h2><p class="lede-sm" style="margin-bottom:12px;">Vanguard is free. Each rank up pays one Hero Token; here's what to spend them on.</p>{order_table()}</div>
  {faq_html}
</section>"""
    add("heroes/", "Hero Incremental Heroes: All 12 Heroes, Passives, Perks & Ultimates",
        "Every Hero Incremental hero: roles, passives, weapons, abilities, ultimates, mastery perks and farming tier, plus the best order to unlock them.", body, [bc, faq_ld], "heroes")

    for i, h in enumerate(HEROES):
        s = slug(h["id"])
        bc_html, bc_ld = crumbs([("Heroes", "heroes/"), (h["id"], f"heroes/{s}/")])
        t = TIER_OF[h["id"]]
        order = ORDER_OF.get(h["id"])
        order_txt = ("Free: every player starts with Vanguard." if h["id"] == "Vanguard" else
                     f"Recommended token: <b>{e(order[1])}</b> (#{order[0] + 1} in the <a href=\"{BASE}tier-list/#unlock-order\">unlock order</a>). {e(order[2])}")
        perks = "".join(
            f'<div class="perk-col"><h3>{label}</h3>' + "".join(f'<div class="perk"><b>{e(n)}</b><span>{e(b)}</span></div>' for n, b in h["perks"][key]) + "</div>"
            for key, label in (("minor", "Mastery 2 · pick one"), ("major", "Mastery 3 · pick one")))
        skins = C.SKINS.get(h["id"], [])
        skin_html = "".join(
            f'<div class="skin" style="--sc:{sk[3]}"><div class="pic"><img src="{img("Hero_" + h["id"])}" alt="" width="64" height="64" loading="lazy"></div>'
            f'<div><b>{e(sk[0])}</b><span class="rar" style="color:{C.RARITY_COLORS[sk[1]]}">{sk[1]}{" · Season 1" if len(sk) > 4 else ""}</span><span>{e(sk[2])}</span></div></div>'
            for sk in skins)
        mini = "".join(
            f'<a href="{BASE}heroes/{slug(x["id"])}/" style="--c:{x["c"]}"' + (' aria-current="page"' if x["id"] == h["id"] else "") +
            f'><img src="{img("Hero_" + x["id"])}" alt="" width="92" height="92" loading="lazy">{x["id"]}</a>' for x in HEROES)
        prev_h, next_h = HEROES[i - 1], HEROES[(i + 1) % len(HEROES)]
        tips = "".join(f"<li>{e(x)}</li>" for x in h["tips"])
        faq = [
            (f"Is {h['id']} good in Hero Incremental?", f"{h['id']} is {t[0]} tier for farming Credits. {t[2]}"),
            (f"How do I unlock {h['id']}?", "Every player starts with Vanguard." if h["id"] == "Vanguard" else
             f"Spend a Hero Token at the Hero terminal (press H). You get one every rank up; the recommended moment for {h['id']} is {order[1]}."),
            (f"What is {h['id']}'s passive?", f"{h['passive'][0]}: {h['passive'][1]}"),
            (f"What are {h['id']}'s best perks?", f"At Mastery 2 pick {h['perks']['minor'][0][0]} or {h['perks']['minor'][1][0]}; at Mastery 3 pick {h['perks']['major'][0][0]} or {h['perks']['major'][1][0]}."),
        ]
        faq_html, faq_ld = faq_block(faq, f"{h['id']} FAQ")
        body = f"""<section class="wrap page">
  <div class="page-head" style="max-width:none;">{bc_html}<p class="stamp">Updated <b>{{{{DATE_LONG}}}}</b></p></div>
  {hero_card(h)}
  <div class="tier-callout" style="--t:{t[1]}"><b>{t[0]}</b><p><a href="{BASE}tier-list/">{t[0]} tier for farming.</a> {e(t[2])}</p></div>
  <div class="grid2">
    <div class="panel" style="--accent:{h['c']}"><h2>Mastery perks</h2><div class="perks">{perks}</div></div>
    <div class="panel" style="--accent: var(--sky);"><h2>How to play {h['id']}</h2><ul class="tiplist">{tips}</ul><p class="lede-sm" style="margin-top:12px;">{order_txt}</p></div>
  </div>
  {f'<div class="panel"><h2>{h["id"]} skins</h2><div class="skin-grid">{skin_html}</div><p class="note" style="margin-top:10px;">600 Tickets or one Skin Token each. <a href="{BASE}skins/">All skins</a></p></div>' if skins else ''}
  {faq_html}
  <div class="hero-nav">
    <a class="btn btn-ghost btn-sm" href="{BASE}heroes/{slug(prev_h['id'])}/"><span>← {prev_h['id']}</span></a>
    <a class="btn btn-ghost btn-sm" href="{BASE}heroes/{slug(next_h['id'])}/"><span>{next_h['id']} →</span></a>
  </div>
  <div class="panel"><h2>All heroes</h2><div class="mini-heroes">{mini}</div></div>
</section>"""
        desc = (f"{h['id']} ({h['role']}, {t[0]} tier) in Hero Incremental: {h['passive'][0]} passive, {h['weapon']['name']}, "
                f"{h['ability']['name']}, {h['ult']['name']}, mastery perks, skins and tips.")
        add(f"heroes/{s}/", f"{h['id']} Hero Incremental Guide: Passive, Perks, Tier & Skins", desc, body, [bc_ld, faq_ld], "hero")


# ---- tier list ----------------------------------------------------------------------------
def build_tiers():
    s_names = ", ".join(x[0] for x in C.TIERS[0]["heroes"])
    head, bc = page_head("Dev picks", "Hero Incremental tier list",
                         "Which heroes earn Credits fastest once they're upgraded, and the best order to spend your Hero Tokens.", [("Tier List", "tier-list/")],
                         f"S tier: <b>{s_names}</b>. They multiply Credits directly or clear whole packs. Unlock Ember first, then Bulwark, Broker, Solace and Rivet as their systems open.")
    rows = []
    for tier in C.TIERS:
        items = "".join(
            f'<div class="tier-item" style="--c:{HERO[hid]["c"]}"><a class="pic" href="{BASE}heroes/{slug(hid)}/"><img src="{img("Hero_" + hid)}" alt="{hid}" width="64" height="64" loading="lazy"></a>'
            f'<div><a href="{BASE}heroes/{slug(hid)}/"><b><img src="{img("Role_" + HERO[hid]["role"])}" alt="{HERO[hid]["role"]}" width="18" height="18">{hid}</b></a><p>{e(why)}</p></div></div>'
            for hid, why in tier["heroes"])
        rows.append(f'<div class="tier-row" style="--t:{tier["c"]}"><div class="tier-label">{tier["t"]}</div><div class="tier-items">{items}</div></div>')
    faq = [
        ("Who is the best hero in Hero Incremental?", f"For farming Credits the S tier is {s_names}. Broker takes +20% on every kill and his Jackpot makes kills pay 3×; Solace's Sanctuary doubles damage and Credits; Bulwark cleaves whole packs and ignores armor."),
        ("What hero should I buy first?", "Ember: her 4× fire rate, 120-round tank and burn damage suit the crowded Main Hall at Bronze 5. Then Bulwark at Bronze 4 for the payload."),
        ("Is Longshot bad?", "He's C tier for farming speed. The 6-round magazine and slow reload lose time between kills. Take the Bandolier perk (+3 magazine) at Mastery 2 if you play him."),
        ("Is Vesper good?", "Solo she's B tier. Her passive doubles the Squad Bonus to +20% Credits per friend in your server, which makes her S tier when you play with friends."),
    ]
    faq_html, faq_ld = faq_block(faq, "Tier list FAQ")
    body = f"""<section class="wrap page">
  {head}
  <div>{''.join(rows)}</div>
  <section class="panel sec" id="unlock-order"><div class="sec-h"><img src="{img('HeroToken')}" alt="" width="44" height="44"><div><h2>Recommended unlock order</h2><small>One Hero Token per rank up · Vanguard is free</small></div></div>
    {order_table()}
    <p class="note" style="margin-top:10px;">Each pick lines up with the system that unlocks at that rank. Playing with friends? Move Vesper up.</p></section>
  <div class="panel" style="--accent: var(--sky);"><div class="prose">
    <h2>How this tier list works</h2>
    <p>Heroes are ranked by how quickly they turn bots into Credits at the same upgrade level. Heroes that multiply Credits directly (Broker's Commission and Jackpot, Solace's Sanctuary) or clear whole packs (Bulwark's cleave) rank highest. Splash and bounce damage (Kestrel, Rivet) and grouping tools (Anchor) come next.</p>
    <p>Every hero can clear every zone, and tanks and supports make objectives easier. You'll own most of the roster by Silver anyway, since every rank up pays a token.</p>
  </div></div>
  {faq_html}
</section>"""
    add("tier-list/", "Hero Incremental Tier List ({{MONTH}}) & Hero Unlock Order",
        f"The Hero Incremental tier list for {{{{MONTH}}}}: S tier {s_names}, every hero ranked for farming Credits, and the best order to spend Hero Tokens.",
        body, [bc, faq_ld], "tiers")


# ---- ranks --------------------------------------------------------------------------------
def build_ranks():
    top = C.RANKS[-1]
    head, bc = page_head("Progression", "Hero Incremental ranks &amp; unlocks",
                         "Every rank's Credit cost, multiplier and new systems, plus what resets and how promotion to Silver works.", [("Ranks", "ranks/")],
                         f"There are 10 ranks: Bronze 5 to 1 and Silver 5 to 1. Bronze 5 costs 5K Credits and Silver 1 costs {fmt(top['cost'])}. Each rank raises your Credit multiplier (up to ×{top['mult']}), pays a Hero Token and opens a new system. Bronze 1 promotes to Silver.")
    rows = []
    for i, r in enumerate(C.RANKS):
        chips = "".join(f'<a class="chip" href="{BASE}{C.SYSTEMS[k]["page"]}" title="{e(C.SYSTEMS[k]["b"])}" style="text-decoration:none"><span><img src="{img(C.SYSTEMS[k]["icon"])}" alt="" width="18" height="18">{C.SYSTEMS[k]["t"]}</span></a>'
                        for k in C.UNLOCKS.get(i, []))
        if i >= 1:
            chips += f'<span class="chip"><span><img src="{img("HeroToken")}" alt="" width="18" height="18">Hero Token</span></span>'
        if i == len(C.RANKS) - 1:
            chips += '<span class="chip pill-warn"><span>Gold: coming soon</span></span>'
        tier = r["name"].split(" ")[1] if " " in r["name"] else "–"
        rows.append(f'<tr><td><span class="rank-badge" style="--a:{r["a"]};--b:{r["b"]}"><i>{tier}</i>{r["name"]}</span></td>'
                    f'<td class="r num">{fmt(r["cost"]) if r["cost"] else "Start"}</td><td class="r num mult">×{r["mult"]}</td>'
                    f'<td class="r num">{C.RANK_TIME.get(i, "–")}</td><td><div class="unlocks">{chips}</div></td></tr>')
    resets = [["Credits &amp; Credit upgrades", '<span class="reset-run">Redeploy + rank up</span>'],
              ["Redeploy points &amp; Redeploy tree", '<span class="reset-rank">Rank up</span> (Standing Orders keeps some nodes)'],
              ["Scrap", '<span class="reset-rank">Rank up</span>'], ["Turrets", '<span class="reset-rank">Rank up</span> (Engineers Lv2 keeps them)'],
              ["Cargo, Marks, CP, SR, Crowns, Momentum, Honor, Storm Essence", '<span class="reset-never">Never</span>'],
              ["Runes, heroes, skins, titles, Tickets", '<span class="reset-never">Never</span>'],
              ["Cargo Bay, Command, Bounty, Skill Rating, Mobility, Honor Hall, Tempest Forge trees", '<span class="reset-never">Never</span>']]
    gates = [["Advanced Combat", "Bronze 3", "1M Credits", "Armored bots, payload 2, capture point B"], ["Elite Combat", "Bronze 1", "5B Credits", "Elite bots, payload 3, capture point C"]]
    redeploy_min = " · ".join(f"{C.RANKS[i + 1]['name']} {fmt(v)}" for i, v in enumerate(C.REDEPLOY_MIN[:6]))
    faq = [
        ("How much does each rank cost in Hero Incremental?", "Bronze 5 costs 5K Credits, Bronze 4 45K, Bronze 3 540K, Bronze 2 75M, Bronze 1 37B and Silver 5 130T. Silver 4 to Silver 1 cost 6.7Sx, 96Sx, 200Sx and 1.7Sp."),
        ("What happens when I rank up?", "Your Credits, Credit upgrades, Redeploy points, Redeploy tree, Scrap and turrets reset. You get a Hero Token, 20 × your new rank in Cargo, a higher Credit multiplier and usually a new system, and you're sent back to spawn."),
        ("How do I get to Silver?", "At Bronze 1, collect 130T Credits and promote on the Rank board. Promotion trades this tier's Redeploy progress for Skill Rating: SR = √(Redeploy points earned this tier ÷ 2)."),
        ("What is the max rank?", "Silver 1 is the current top rank. Gold is coming soon."),
    ]
    faq_html, faq_ld = faq_block(faq, "Rank FAQ")
    body = f"""<section class="wrap page">
  {head}
  <div class="panel"><h2>Rank ladder</h2>
    <div class="table-scroll"><table class="ladder"><thead><tr><th>Rank</th><th class="r">Cost (Credits)</th><th class="r">Credit mult.</th><th class="r">Playtime</th><th>Unlocks</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
    <p class="note" style="margin-top:10px;">Playtime is the game's pacing target for an active player. Plan a rank with the <a href="{BASE}calculator/#rank">rank-up calculator</a>.</p></div>
  <div class="grid2">
    <div class="panel" style="--accent: var(--damage);"><h2>What resets</h2>{table(["What", "Resets on"], resets)}</div>
    <div class="panel"><h2>Zone gates</h2>{table(["Zone", "From", "Cost", "Opens"], gates)}<p class="note" style="margin-top:10px;">Gates are one-time purchases that stay open.</p></div>
  </div>
  <section class="panel sec" id="promotion"><div class="sec-h"><img src="{img('Promotion')}" alt="" width="44" height="44"><div><h2>Tier Promotion (Bronze 1 → Silver 5)</h2><small>Trade Redeploy progress for Skill Rating</small></div></div>
    <div class="prose"><p>At Bronze 1, once you hold 130T Credits, promote on the Rank board. You reset like a rank up and receive <b>SR = √(Redeploy points earned this tier ÷ 2)</b>, so every Redeploy you did in Bronze counts. SR buys the permanent <a href="{BASE}upgrades/#sr">Skill Rating tree</a>, and the promotion also pays a Hero Token.</p>
    <p>Redeploy minimums (Credits needed before the button works): {redeploy_min}.</p></div></section>
  {faq_html}
</section>"""
    add("ranks/", "Hero Incremental Ranks: Costs, Multipliers, Unlocks & Resets",
        f"Every Hero Incremental rank from Bronze 5 to Silver 1: Credit cost, multiplier (up to ×{top['mult']}), playtime, unlocks, what resets and how promotion works.",
        body, [bc, faq_ld], "ranks")


# ---- currencies ---------------------------------------------------------------------------
def build_currencies():
    head, bc = page_head("Economy", "Hero Incremental currencies",
                         "What every currency is for, how to earn it and whether it resets.", [("Currencies", "currencies/")],
                         "Credits buy Credit upgrades and rank ups. Redeploy points buy the Redeploy tree. Cargo, Bounty Marks, CP and SR buy permanent trees that never reset, and Silver adds Crowns, Momentum, Honor and Storm Essence.")
    cards = []
    for cur in C.CURRENCIES:
        rt, rc = RESET_TXT[cur["resets"]]
        cards.append(f'<div class="card sec" id="{cur["id"]}"><h3><img src="{img(cur["icon"])}" alt="" width="34" height="34">{e(cur["name"])}</h3>'
                     f'<dl class="kv"><dt>Unlocks</dt><dd>{e(cur["unlock"])}</dd><dt>Earn</dt><dd>{e(cur["earn"])}</dd><dt>Spend</dt><dd>{e(cur["spend"])}</dd>'
                     f'<dt>Resets</dt><dd><span class="{rc}">{rt}</span></dd></dl></div>')
    chain = [["Credits", "Credit upgrades, rank ups, gates, rune rolls", "Start"], ["Redeploy", "Redeploy tree (doubles Credits and Redeploy)", "Bronze 5"],
             ["Cargo", "Cargo Bay: permanent Credits, damage and automation", "Bronze 4"], ["Scrap / Marks", "Turrets, Command Scrap branch / Bounty shop", "Bronze 3"],
             ["CP", "Command tree: rune stats and capture speed", "Bronze 2"], ["SR", "Skill Rating: permanent boosts, Auto-Capture", "Promotion"],
             ["Crowns", "Research Lab", "Silver 5"], ["Momentum", "Mobility tree", "Silver 4"], ["Honor", "Honor Hall (research speed)", "Silver 2"],
             ["Storm Essence", "Tempest Forge (all Silver currencies)", "Silver 1"]]
    faq = [
        ("What are Bounty Marks used for?", "The Bounty shop (F, BOUNTY tab): Skin Vouchers, Ticket Bundles, Mastery Tomes, Bounty Scope (more Marks) and Trophy Hunter (more Credits). Marks never reset."),
        ("What are Competitive Points (CP) for?", "The Command tree (N): Field Command boosts all rune stats, plus capture speed, cheaper rune rolls and Scrap Magnet. CP never resets."),
        ("Does Cargo reset?", "No. Cargo and the Cargo Bay are permanent."),
        ("How do I get Crowns?", "Escort the Siege Push robot in Sturmfeste (Silver 5+): checkpoints pay 20, 45, 80 and 150 Crowns. Crowns also come from day 5 of the daily streak in Silver."),
        ("What are layer milestones?", C.MILESTONES),
    ]
    faq_html, faq_ld = faq_block(faq, "Currency FAQ")
    body = f"""<section class="wrap page">
  {head}
  <div class="panel"><h2>The layer chain</h2><p class="lede-sm" style="margin-bottom:12px;">Each new currency makes the one before it faster. The newest layer is usually the best place to spend time.</p>
    {table(["Currency", "Spent on", "Opens at"], chain)}</div>
  <div class="grid2">{''.join(cards)}</div>
  <div class="panel" style="--accent: var(--warn);"><div class="sec-h"><img src="{img('Promotion')}" alt="" width="44" height="44"><div><h2>Layer milestones</h2><small>Free nodes for new currencies</small></div></div><p class="lede-sm">{e(C.MILESTONES)}</p></div>
  {faq_html}
</section>"""
    add("currencies/", "Hero Incremental Currencies: What Every Currency Does",
        "Every Hero Incremental currency explained: Credits, Redeploy, Cargo, Scrap, Bounty Marks, CP, SR, Crowns, Momentum, Honor, Storm Essence, Tickets and tokens.",
        body, [bc, faq_ld], "currencies")


# ---- upgrades -----------------------------------------------------------------------------
def build_upgrades():
    total = sum(len(t["nodes"]) for t in C.TREES)
    head, bc = page_head("Every node", "Hero Incremental upgrade trees",
                         f"All {len(C.TREES)} upgrade trees and {total} upgrades: effect per level, max level, cost and when each unlocks.", [("Upgrades", "upgrades/")],
                         "Buy Redeploy Multiplier and Credit Surge first every rank: each level doubles your gains. Spend Cargo, Marks, CP and SR as soon as you have them, because those trees never reset.")
    secs = []
    for t in C.TREES:
        rows = []
        for n in t["nodes"]:
            title, blurb, e1, emax, mx, base, growth, rank = n
            if growth == "" or mx == 1:
                cost = fmt(base)
            elif isinstance(growth, str):
                cost = f"{fmt(base)} {growth}/lvl"
            elif t["curve"] == "lin":
                cost = f"{fmt(base)} +{growth}/lvl"
            else:
                cost = f"{fmt(base)} ×{growth}/lvl"
            rows.append([f"{e(title)}<small>{e(blurb)}</small>", e(e1), e(emax), mx, cost, e(rank) if rank else t["unlock"]])
        body = (f'<p class="lede-sm" style="margin-bottom:6px;">{e(t["blurb"])}</p><p class="note" style="margin-bottom:12px;">Wallet: <b>{e(t["wallet"])}</b> · Tab: {e(t["tab"])} · Resets: {e(t["resets"])}</p>'
                + table(["Upgrade", "Per level", "At max", "Max", "Cost", "Unlocks"], rows, "tree-table", right=(3,)))
        secs.append(sec(t["id"], t["title"], t["icon"], f"From {t['unlock']}", body))
    faq = [
        ("What should I upgrade first in Hero Incremental?", "Credit tab: Damage, then Credit Multiplier and Fire Rate. Redeploy tab: Redeploy Multiplier and Credit Surge, then Quartermaster. Cargo Bay: Supply Drop and Armory Uplink, then Priority Shipping."),
        ("How do upgrade costs scale?", "Most trees are exponential: cost = base × growth^level. The Bounty shop, Skill Rating and some Redeploy nodes are linear: cost = base + growth × level. Credit upgrade prices also scale with your rank's multiplier and Combat Pay."),
        ("Can upgrades be automated?", "Yes, and automation is earned: Quartermaster (Redeploy tab) buys Credit upgrades, Redeploy Quartermaster and Auto-Redeploy (Cargo Bay) handle Redeploys, Auto-Capture (SR) fills capture points, Engineers auto-upgrades turrets, and Lab Steward (Honor Hall) queues research."),
        ("Which upgrades keep through rank up?", "Standing Orders (Cargo Bay) keeps Quartermaster and Head Start at level 1, then Credit Surge at level 2 and Redeploy Multiplier at level 3. Every permanent tree (Cargo Bay, Bounty, Command, SR, Mobility, Honor Hall, Tempest Forge) always stays."),
    ]
    faq_html, faq_ld = faq_block(faq, "Upgrade FAQ")
    body = f"""<section class="wrap page">
  {head}
  {toc([(t["id"], t["title"]) for t in C.TREES])}
  {''.join(secs)}
  {faq_html}
</section>"""
    add("upgrades/", "Hero Incremental Upgrades: Every Tree, Node, Cost & Max Level",
        f"All {total} Hero Incremental upgrades across the Credit, Redeploy, Cargo Bay, Bounty, Command, Skill Rating, Mobility, Honor Hall and Tempest Forge trees.",
        body, [bc, faq_ld], "upgrades")


# ---- runes --------------------------------------------------------------------------------
def build_runes():
    head, bc = page_head("From Bronze 2", "Hero Incremental runes",
                         "How rune altars work, every tier's odds and bonus, where Luck comes from, and what the rune index pays.", [("Runes", "runes/")],
                         "Stand on a rune altar and it rolls every second. Altars are free and open by rank: Fortune at Bronze 2, Valor at Bronze 1 and Tempest at Silver 5. Each rune costs a few Credits. Every tier you own gives a permanent bonus that grows until it hits [MAX]. Runes never reset.")
    legend = "".join(f'<div style="--sc:{c}"><b>{n}</b><span>{d}</span></div>' for n, c, d in
                     [("Luck", "#6ee678", "Divides the odds of rare tiers."), ("Bulk", "#5aaaff", "Runes per roll."), ("Speed", "#ffc846", "Rolls per second. Starts at 2."),
                      ("Clone", "#d2a0ff", "Extra copies of every roll."), ("Runes/s", "#ff6a5a", "Speed × Clone × Bulk.")])
    sources = "".join(f'<div class="card"><h3>{k}</h3><ul class="tiplist">' + "".join(f"<li>{e(x)}</li>" for x in v) + "</ul></div>" for k, v in C.RUNE_SOURCES.items())
    secs = []
    for a in C.ALTARS:
        total = sum(t[1] for t in a["tiers"])

        def odds(t, a=a, total=total):
            if a.get("global"):
                pct = t[1] / total * 100
                return (f"{pct:.1f}".rstrip("0").rstrip(".") if pct >= 0.1 else f"{pct:.2g}") + "%"
            return "1/" + fmt(t[1])
        has_ms = any(t[4] for t in a["tiers"])
        trs = []
        for i, t in enumerate(a["tiers"]):
            row = [f'<span class="tier-dot" style="--tc:{C.TIER_COLORS[i]}"></span><b>{t[0]}</b>', odds(t), bonus_text(t[2]), fmt(t[3])]
            if not a.get("global"):
                row.append(f'{C.INDEX_TICKETS[i]} 🎟')
            if has_ms:
                row.append(e(t[4]) if t[4] else "")
            trs.append(row)
        head_cols = ["Tier", "Chance" if a.get("global") else "Base odds", "Bonus at [MAX]", "[MAX] at"] + ([] if a.get("global") else ["Index"]) + (["Milestone"] if has_ms else [])
        meta = f'<div class="altar-meta"><span class="chip"><span>{e(a["where"])}</span></span><span class="chip"><span>Opens: {a["unlock"]}</span></span></div>'
        secs.append(f'<section class="panel altar-sec sec" id="{a["id"].lower()}" style="--accent:{a["color"]}"><h2 style="color:{a["color"]}">{a["name"]}</h2>{meta}'
                     f'<p class="lede-sm" style="margin-bottom:10px;">{e(a["focus"])}</p>{table(head_cols, trs, right=(1, 3))}</section>')
    jump = "".join(f'<a class="chip" href="#{a["id"].lower()}" style="text-decoration:none;color:{a["color"]}"><span>{a["name"]}</span></a>' for a in C.ALTARS)
    faq = [
        ("How do runes work in Hero Incremental?", "Stand on an open rune altar and it rolls every second. Each roll checks the rarest tier first, with your Luck dividing its odds. Every tier you own gives a bonus that grows with your count, fast at first and slower later, until it hits [MAX]. Bonuses from all altars multiply together and never reset."),
        ("Do rune rolls cost anything?", "Yes: each rune costs half a Training-bot kill's worth of Credits at your current multipliers, so the price keeps pace with your income. Rune Rations (Command tree) cut it by up to 49%. Global (Unity) rolls are free."),
        ("How do I get more rune Luck?", "Rune Luck upgrades in the Credit and Redeploy tabs, Field Command, Rune Attunement, the More Luck ticket boost, the Rune Luck pass, Luck Potions, Rune Rush, completing altar indexes and Luck runes. They all multiply together."),
        ("Can I roll runes while away from the altar?", "Yes. Rune Engine in the Command tree's Scrap branch keeps your last altar rolling anywhere at 10–50% speed. The game rejoins you before the AFK kick, so you can also leave the game running on an altar."),
        ("What is the rune index?", "The first time you pull each tier you get Tickets (1 for the common tier up to 60 for the rarest). Completing an altar's whole index gives +10% rune Luck permanently."),
        ("What is a Rune Rush?", "When anyone buys Global Runes, the whole server gets ×1.5 rune Luck for 5 minutes (it stacks up to 30 minutes) and everyone gets the Rune of Unity rolls."),
    ]
    faq_html, faq_ld = faq_block(faq, "Rune FAQ")
    body = f"""<section class="wrap page">
  {head}
  <div class="stat-legend">{legend}</div>
  <div class="panel"><h2>How rolling works</h2><div class="prose">
    <p>Each roll checks the rarest tier first; your Luck divides its odds (a 1/1,000 tier becomes 1/500 at ×2 Luck). If it misses, the next rarest is checked, down to the common tier. A tier's bonus follows how many you own on a log curve and stops at its [MAX] count.</p>
    <p>Rolling costs Credits: each rune is worth half a Training kill at your current multipliers. If you run short, rolling pauses until you earn more. Work out your odds and time to [MAX] with the <a href="{BASE}calculator/#runes">rune calculator</a>.</p></div></div>
  <div class="panel"><h2>Where rune stats come from</h2><div class="grid2">{sources}</div></div>
  <div class="altar-jump">{jump}</div>
  {''.join(secs)}
  {faq_html}
</section>"""
    add("runes/", "Hero Incremental Runes: Altar Odds, Luck, Bonuses & Index",
        "Every Hero Incremental rune altar (Fortune, Valor, Tempest, Unity): tier odds, bonuses at [MAX], milestones, roll prices, Luck sources and index rewards.",
        body, [bc, faq_ld], "runes")


# ---- objectives ---------------------------------------------------------------------------
def build_objectives():
    head, bc = page_head("Training Facility", "Hero Incremental objectives",
                         "Payloads, capture points, bounties, turrets, On Fire, hero mastery and contracts in the Training Facility.", [("Objectives", "objectives/")],
                         "The Facility has three sectors (Main Hall, Advanced Combat, Elite Combat), each with its own payload (×1/×4/×16 rewards) and capture point (×1/×5/×25 CP). Payloads pay Cargo, capture points pay CP on completion, and WANTED bots pay Bounty Marks.")
    payload = f"""<div class="prose"><p>Stand within 14 studs of the cart to push it (2.4 studs/s, +0.5 per extra escort). Defenders try to stop it; if nobody escorts it for 15 s, it rolls back to the last checkpoint. The checkpoint at the halfway mark and the delivery at the gate both pay Cargo, Credits and Rank XP; deliveries pay 3× and raise the cart's level (+25% rewards per level, up to 10).</p>
      <p>Payloads are personal: you (or your group) have your own copy. The Rune of Fortune's Royal tier makes carts creep forward on their own, and Treasure makes them escort themselves at half speed.</p></div>
      {table(["Sector", "Defenders", "Rewards"], C.PAYLOADS)}"""
    control = f"""<div class="prose"><p>Stand inside the ring (10 studs) to fill it at 1% per second (+0.5% per extra player). Defender waves arrive every 22 s, and the point drains when nobody holds it. A capture pays only when it reaches 100%: CP, Credits (60 kills' worth) and 600 Rank XP. The point then relocks for 2.5 minutes.</p>
      <p>Fortified Points (Command) fills faster; Auto-Capture (Skill Rating) lets open points fill themselves at 25% speed.</p></div>
      {table(["Point", "Location", "Defenders", "Multiplier", "Base CP"], C.CONTROL_POINTS)}"""
    marks = ", ".join(f"{b['id']} {b['marks']}" for b in C.BOTS)
    bounty = f'<div class="prose"><p>Every 2.5 minutes a WANTED bot appears with 5× health. It lasts 90 s and pays 10× Credits plus Bounty Marks to everyone who deals at least 10% of its damage. Marks by bot: {marks}. Broker gets +25% Marks, and Bounty Scope adds up to +200%.</p></div>'
    turrets = """<div class="prose"><p>Bots drop Scrap 45% of the time: Bronze (×1), Silver (×2.5) or Gold (×6) pieces. Spend it on turrets at the 9 glowing sockets (3 per sector; Advanced sockets cost 4×, Elite 15×). Turrets fire every second at 60% of your damage, gain +35% per level (max 15) and have 55 studs of range.</p>
      <p>Building your first turret opens the Command tree's Scrap branch: Salvage Crews (turret damage), Rune Engine (roll anywhere) and Engineers (auto-upgrade, and keep turrets through rank up). Turrets reset on rank up until Engineers Lv2. Rivet's passive adds +30% Scrap and faster turrets.</p></div>"""
    heat = ", ".join(f"{b['id']} {b['heat']}" for b in C.BOTS)
    onfire = f"""<div class="prose"><p>Every kill adds heat ({heat}). Heat multiplies kill Credits: 25 = ×1.25, 50 = ×1.5, 75 = ×2, 100 = ×2.5 (ON FIRE). It starts draining 3 s after your last kill, and taking damage knocks a big chunk off. Fuel Line (Cargo Bay), Ember's Kindling and Hot Hands (SR) keep it higher for longer.</p></div>"""
    mxp = ", ".join(f"{b['id']} {b['mxp']}" for b in C.BOTS)
    mastery = f"""<div class="prose"><p>Kills level up the hero you're playing ({mxp} XP each). Levels land at 40, 200, 800 and 2,500 XP. At <b>Mastery 2</b> pick one of two minor perks, at <b>Mastery 3</b> one of two major perks (HEROES > MASTERY). Mastery 4 and 5 are prestige levels. Each hero's perks are on their <a href="{BASE}heroes/">hero page</a>, and Mastery Tomes (Bounty shop) give +250 XP.</p></div>"""
    contracts = """<div class="prose"><p>From Bronze 5 you hold 3 contracts at a time, like "Kill 100 Training bots" or "Land 40 critical hits". Each pays Credits sized to your rank (and Redeploy points on some), and a fresh set rolls every 15 minutes.</p></div>"""
    faq = [
        ("How do payloads work in Hero Incremental?", "Stand next to your sector's cart to push it along the track. Checkpoints and the delivery pay Cargo, Credits and Rank XP; the Advanced Combat cart pays 4× and the Elite cart 16×. Carts roll back if left alone for 15 seconds."),
        ("Why didn't my capture point pay anything?", "Capture points only pay when they reach 100%. Leaving the ring lets it drain. After a capture the point relocks for 2.5 minutes."),
        ("How often do bounties spawn?", "Every 2.5 minutes a WANTED bot appears for 90 seconds. Deal at least 10% of its damage to get the Marks."),
        ("Do turrets keep working when I leave?", "Turrets fight for you while you're anywhere in the game, not while you're offline. They reset on rank up until you own Engineers level 2 in the Command tree."),
    ]
    faq_html, faq_ld = faq_block(faq, "Objectives FAQ")
    body = f"""<section class="wrap page">
  {head}
  {toc([("payload", "Payload"), ("control", "Capture points"), ("bounties", "Bounties"), ("turrets", "Scrap & turrets"), ("on-fire", "On Fire"), ("mastery", "Mastery"), ("contracts", "Contracts")])}
  {sec("payload", "Payloads", "Payload", "From Bronze 4 · three carts, one per sector", payload)}
  {sec("control", "Capture points", "CP", "From Bronze 2 · A, B and C", control, "#be78ff")}
  {sec("bounties", "Bounties", "Marks", "From Bronze 3 · WANTED bots", bounty, "var(--damage)")}
  {sec("turrets", "Scrap & turrets", "Turrets", "From Bronze 3", turrets, "var(--sky)")}
  {sec("on-fire", "On Fire", "OnFire", "From the start · kill streak heat", onfire)}
  {sec("mastery", "Hero Mastery", "Mastery", "From Bronze 3 · perks per hero", mastery, "var(--warn)")}
  {sec("contracts", "Contracts", "Guide", "From Bronze 5", contracts, "var(--sky)")}
  {faq_html}
</section>"""
    add("objectives/", "Hero Incremental Objectives: Payload, Capture Points & Bounties",
        "How Hero Incremental's payloads, capture points, bounties, turrets, On Fire, hero mastery and contracts work, with every reward and multiplier.",
        body, [bc, faq_ld], "objectives")


# ---- sturmfeste ---------------------------------------------------------------------------
def build_sturmfeste():
    head, bc = page_head("Silver", "Sturmfeste",
                         "Silver's storm-lashed castle town: getting there, its zones and bots, the Siege Push, parkour, the Research Lab and Trials.", [("Sturmfeste", "sturmfeste/")],
                         "Promote to Silver 5, then board the dropship behind the Armory (or press T). Sturmfeste's Sentinels, Knights and Wardens pay far more than the Facility. Escort the siege robot for Crowns, run parkour for Momentum, research in the Lab and clear Trials for Honor.")
    zones = [["Sturmfeste Village", "Silver 5", "Sentinel", "The Sturmhorn Tavern (spawn), the Rune Sanctum and the Siege Push start"],
             ["Castle Grounds", "Silver 4", "Knight", "Courtyard, parkour courses and the Stormfield (World Boss)"],
             ["The Keep", "Silver 2", "Warden", "The gatehouse, Great Hall and Throne Room"]]
    push = f"""<div class="prose"><p>Escort the siege robot from the town square toward the throne: stay within 18 studs (3.6 studs/s, +0.6 per extra escort). Defender squads spawn 60 studs ahead every 32 s (never more than 3 at once), and the robot rolls back if left alone. Each checkpoint pays Crowns the first time you pass it on a run; how far you can go depends on your rank. Your <b>best distance is a permanent Credits multiplier</b>.</p>
      <p>Anchor's Heavy Hauler makes the robot 50% faster; Siege Drive, Siege Engineering and Steam Winch speed it up too. Like payloads, the siege is personal (or shared by your group).</p></div>
      {table(["Checkpoint", "Opens at", "Crowns"], C.PUSH_CHECKPOINTS, right=(2,))}"""
    parkour = f"""<div class="prose"><p>Three timed courses pay Momentum for the Mobility tree. Pass through every ring; beat par for up to 1.8× Momentum. A first clear pays 3×, and a new best time +50%. Kestrel gets +20% Momentum, and the Parkour Kit pass gives Double Jump and Dash from the start.</p></div>
      {table(["Course", "Route", "Par (s)", "Momentum", "Needs"], C.PARKOUR, right=(2, 3))}"""
    research = f"""<div class="prose"><p>Spend Crowns on projects that finish in real time and keep running while you're offline (up to 8 hours each). You start with one workbench; Second Workbench, Third Workbench (Honor Hall) and the Master Researcher pass add more. Each level costs more and takes longer.</p></div>
      {table(["Project", "Effect", "Levels", "First cost (Crowns)", "First time"], C.RESEARCH, right=(2, 3))}"""
    trials = f"""<div class="prose"><p>Challenge runs at the Tourney Yard (K). Pick a trial, play under its handicap, and hit the Bronze, Silver or Gold goal for a permanent reward per tier plus 10 Honor. Clears also unlock automation: <b>3 clears</b> auto-buys Redeploy upgrades, <b>6 clears</b> auto ranks you up.</p></div>
      {table(["Trial", "Handicap", "Reward per tier"], C.TRIALS)}"""
    travel = table(["Destination", "Opens", "What's there"], C.TRAVEL)
    faq = [
        ("How do I get to Sturmfeste?", "Promote from Bronze 1 to Silver 5. The door at the back of the Armory opens onto the dropship pad; board the dropship, or use fast travel (T) any time after your first visit."),
        ("How do I get Crowns?", "Escort the Siege Push robot: Grounds Courtyard pays 20 Crowns, Gatehouse 45, Great Hall 80 and Throne Room 150. Crown Press, Crown Tithe, Crown Minting and the 2× Crowns pass all increase it."),
        ("Does research continue offline?", "Yes. Research Lab timers keep counting down while you're offline. It's the only thing in the game that does."),
        ("How do I unlock double jump?", "Buy Spring Greaves then Double Jump in the Mobility tree (Silver 4) with Momentum. Kestrel has double jump and wall-run from the start, and the Parkour Kit pass gives Double Jump and Dash immediately."),
    ]
    faq_html, faq_ld = faq_block(faq, "Sturmfeste FAQ")
    body = f"""<section class="wrap page">
  {head}
  {toc([("zones", "Zones"), ("push", "Siege Push"), ("parkour", "Parkour"), ("research", "Research Lab"), ("trials", "Trials"), ("travel", "Fast travel")])}
  {sec("zones", "Zones &amp; bots", "Island", "Each Silver rank opens more of the town", table(["Zone", "Opens", "Bot", "Landmarks"], zones) + f'<p class="note" style="margin-top:10px;">Bot stats: <a href="{BASE}bots/">bots page</a>.</p>')}
  {sec("push", "Siege Push", "Crowns", "From Silver 5 · pays Crowns", push)}
  {sec("parkour", "Parkour", "Momentum", "From Silver 4 · pays Momentum", parkour, "var(--sky)")}
  {sec("research", "Research Lab", "Research", "From Silver 3 · spends Crowns", research, "var(--good)")}
  {sec("trials", "Trials", "Trials", "From Silver 2 · pays Honor", trials, "var(--warn)")}
  {sec("travel", "Fast travel", "Travel", "Press T · 4 s cooldown", travel)}
  {faq_html}
</section>"""
    add("sturmfeste/", "Hero Incremental Sturmfeste: Siege Push, Parkour, Research & Trials",
        "Hero Incremental's Silver zone: how to reach Sturmfeste, its zones and bots, Siege Push checkpoints and Crowns, parkour courses, Research Lab projects and Trials.",
        body, [bc, faq_ld], "sturmfeste")


# ---- events -------------------------------------------------------------------------------
def build_events():
    head, bc = page_head("Live", "Hero Incremental events",
                         "The hourly World Boss, weekly boards, the Hall of Fame, titles, daily rewards, groups and Rune Rush.", [("Events", "events/")],
                         "The Storm Colossus World Boss spawns at the top of every hour (Silver 5+). Weekly boards pay up to 500 Tickets. The Hall of Fame gives titles to the top 10 of 8 all-time boards. Log in daily for a 7-day streak ending in a Skin Token.")
    boss = """<div class="prose"><p>The <b>Storm Colossus</b> rises on the Stormfield at the top of every hour, with warnings 5 minutes, 1 minute and 10 seconds before. You have 5 minutes to take it down. It has at least 2M health, scaling up with the number of players. Dodge its slams (30 damage), missile volleys and shock rings at 66% and 33% health; it enrages at 25%.</p>
      <p>Everyone who deals at least 1% of its health earns <b>15 Tickets</b> (+10 for the top damage dealer), <b>500 Season XP</b> and, from Silver 1, <b>Storm Essence</b> for the Tempest Forge.</p></div>"""
    weekly = table(["Board", "Counts"], C.WEEKLY) + '<h3 style="margin:16px 0 8px;font-size:20px;">Rewards (each board)</h3>' + table(["Place", "Tickets", "Title"], C.WEEKLY_REWARDS)
    hall_rows = [[b[0], b[1], " / ".join(b[2])] for b in C.HALL]
    hall = ('<p class="lede-sm" style="margin-bottom:10px;">All-time boards in the Hall of Fame wing east of the Hub. #1 gets a statue; the top 10 hold a title while they stay there.</p>'
            + table(["Board", "Ranked by", "Titles (#1 / top 3 / top 10)"], hall_rows))
    title_secs = "".join(f'<div class="card"><h3>{cat}</h3>' + "".join(
        f'<p><b style="color:{C.RARITY_COLORS[r]}">{e(n)}</b> · {e(req)}</p>' for n, req, r in rows) + "</div>" for cat, rows in C.TITLES.items())
    daily = ('<p class="lede-sm" style="margin-bottom:10px;">Claim once per day in a safe zone. Missing a day restarts the streak; after day 7 it repeats. VIP doubles every daily reward.</p>'
             + table(["Streak", "Reward"], C.DAILY))
    groups = """<div class="prose"><p>Open the Menu (V) and choose <b>GROUP</b> to invite up to 3 players (invites last 60 s). A group gets <b>+10% per member, up to +30%</b>, shares its own payloads, capture points and siege robot, and splits kill Credits by damage dealt, so assists pay. Bot waves grow with the group.</p>
      <p>On top of that, every friend in your server adds the <b>Squad Bonus</b> (+10% Credits each, up to 3; Vesper doubles it), and Roblox Premium members get +10% on every currency.</p></div>"""
    rush = """<div class="prose"><p>When anyone buys Global Runes, every player in the server gets the Rune of Unity rolls and a <b>Rune Rush</b>: ×1.5 rune Luck for 5 minutes (stacking up to 30).</p>
      <p><b>No AFK kick:</b> the game quietly rejoins you before Roblox's 20-minute idle kick, so rune altars and payload creep keep working while you're away from the keyboard.</p></div>"""
    faq = [
        ("When does the World Boss spawn in Hero Incremental?", "At the top of every hour, on the Stormfield in Sturmfeste. You need Silver 5 to fight it, and you have 5 minutes to defeat it."),
        ("What do weekly leaderboards reward?", "Each of the three weekly boards (runes rolled, bots defeated, boss damage) pays 500 Tickets and the Weekly Champion title for #1, 300 and Weekly Podium for the top 3, then 150, 80 and 40 Tickets for the top 10, 25 and 100."),
        ("How do I get titles?", "Titles unlock from playtime, bots defeated, Season Pass tiers, weekly boards, the Hall of Fame and supporting the game. Equip one in your Profile (J) to show it over your head."),
        ("What does a group give?", "+10% per member up to +30%, shared objectives, and kill Credits split by damage so everyone gets paid."),
    ]
    faq_html, faq_ld = faq_block(faq, "Events FAQ")
    body = f"""<section class="wrap page">
  {head}
  {toc([("world-boss", "World Boss"), ("weekly", "Weekly boards"), ("hall-of-fame", "Hall of Fame"), ("titles", "Titles"), ("daily", "Daily streak"), ("groups", "Groups"), ("rush", "Rune Rush & AFK")])}
  {sec("world-boss", "World Boss: Storm Colossus", "WorldBoss", "Every hour · Silver 5+", boss, "var(--damage)")}
  {sec("weekly", "Weekly boards", "HallOfFame", "Reset every week (B)", weekly, "var(--warn)")}
  {sec("hall-of-fame", "Hall of Fame", "HallOfFame", "8 all-time boards", hall)}
  {sec("titles", "Titles", "Promotion", "Equip in your Profile (J)", f'<div class="grid2">{title_secs}</div>', "#be78ff")}
  {sec("daily", "Daily streak", "Daily", "7-day cycle", daily, "var(--sky)")}
  {sec("groups", "Groups &amp; bonuses", "Group", "Up to 4 players", groups, "var(--sky)")}
  {sec("rush", "Rune Rush &amp; AFK", "GlobalRunes", "", rush)}
  {faq_html}
</section>"""
    add("events/", "Hero Incremental Events: World Boss, Weekly Boards, Titles & Daily",
        "Hero Incremental's live events: the hourly Storm Colossus World Boss, weekly leaderboards and rewards, Hall of Fame boards, titles, daily streak, groups and Rune Rush.",
        body, [bc, faq_ld], "events")


# ---- skins + season -----------------------------------------------------------------------
def build_skins():
    S = C.SEASON
    total = sum(len(v) for v in C.SKINS.values())
    head, bc = page_head("Cosmetics", "Hero Incremental skins &amp; Season Pass",
                         f"All {total} hero skins and the Season {S['number']} pass ({S['name']}): every reward, how to earn Season XP and how to get skins for free.", [("Skins & Season", "skins/")],
                         f"There are {total} skins, 2 or 3 per hero. Each costs 600 Tickets or one Skin Token. Skin Tokens come free from day 7 of the daily streak, Skin Vouchers (Bounty shop) and the Season Pass. Season {S['number']} has 30 tiers and ends on {S['ends']}.")
    by_hero = []
    for hid, skins in C.SKINS.items():
        cards = "".join(
            f'<div class="skin" style="--sc:{sk[3]}"><div class="pic"><img src="{img("Hero_" + hid)}" alt="" width="64" height="64" loading="lazy"></div>'
            f'<div><b>{e(sk[0])}</b><span class="rar" style="color:{C.RARITY_COLORS[sk[1]]}">{sk[1]}{" · Season 1" if len(sk) > 4 else ""}</span><span>{e(sk[2])}</span></div></div>' for sk in skins)
        by_hero.append(f'<h3 style="margin:14px 0 8px;font-size:22px;"><a href="{BASE}heroes/{slug(hid)}/" style="color:{HERO[hid]["c"]};text-decoration:none;">{hid}</a></h3><div class="skin-grid">{cards}</div>')
    track = [[i + 1, e(f), e(p)] for i, (f, p) in enumerate(C.SEASON_REWARDS)]
    xp = [[e(a), e(fmt(b)) if not isinstance(b, str) else e(b)] for a, b in C.SEASON_XP]
    faq = [
        ("How do I get free skins in Hero Incremental?", "Skin Tokens are free from day 7 of the daily streak, Skin Vouchers in the Bounty shop (Marks) and tiers 10, 20 and 30 of the free Season Pass track. You can also buy any skin for 600 Tickets."),
        ("What's in the Season 1 pass?", f"{S['tiers']} tiers of Tickets, potions and Skin Tokens on both tracks. The premium track ({S['price']} Robux) adds three exclusive skins: Storm Baron (Broker, tier 10), Stormward Seraph (Solace, tier 20) and Stormbreaker (Vanguard, tier 30), each with a title."),
        ("How do I earn Season XP?", "World Boss fights (500), daily rewards (300), payload deliveries (250), captures and siege checkpoints (150), contracts (120), Tickets (60 each), new rune tiers, rune rolls and kills. Each tier needs 1,500 XP."),
        ("Do skins change stats?", "No. Skins are cosmetic only."),
    ]
    faq_html, faq_ld = faq_block(faq, "Skins FAQ")
    body = f"""<section class="wrap page">
  {head}
  {toc([("season", f"Season {S['number']}"), ("xp", "Season XP"), ("track", "Reward track"), ("skins", "All skins"), ("faq", "FAQ")])}
  {sec("season", f"Season {S['number']}: {S['name']}", "Season", e(S['tagline']), f'<div class="prose"><p>{S["tiers"]} tiers at {fmt(S["xp_per_tier"])} XP each. Every tier has a free reward, and the Season Pass ({S["price"]} Robux) unlocks the premium track too, including three exclusive skins and titles. The season ends on <b>{S["ends"]}</b>. Open it with <kbd>P</kbd>.</p></div>')}
  {sec("xp", "Earning Season XP", "Promotion", "", table(["Activity", "Season XP"], xp, right=(1,)), "var(--sky)")}
  {sec("track", "Reward track", "Ticket", "Free and premium rewards per tier", table(["Tier", "Free", "Premium"], track, "season-track", right=(0,)), "var(--warn)")}
  {sec("skins", f"All {total} skins", "SkinToken", "600 Tickets or 1 Skin Token each", "".join(by_hero), "#ff78c8")}
  {faq_html}
</section>"""
    add("skins/", f"Hero Incremental Skins & Season {S['number']} Pass: All Rewards",
        f"All {total} Hero Incremental skins by hero and rarity, how to get Skin Tokens free, and every Season {S['number']} ({S['name']}) reward and Season XP source.",
        body, [bc, faq_ld], "skins")


# ---- shop ---------------------------------------------------------------------------------
def build_shop():
    head, bc = page_head("Store", "Hero Incremental shop &amp; game passes",
                         "Every game pass and product with its price, what the ticket shop sells, and which bonuses stack.", [("Shop", "shop/")],
                         "Everything in Hero Incremental can be earned by playing, including heroes (Hero Tokens every rank up), skins (Tickets) and automation. Passes speed things up: VIP I–III multiply damage, fire rate and every currency, 2× passes double one currency, and rune passes boost rolling.")
    passes = [[f'<img src="{img(i)}" alt="" width="28" height="28" style="width:28px;height:28px;vertical-align:middle;margin-right:8px;display:inline-block;">{e(n)}', fmt(p) + " R$", e(b)] for n, p, b, i in C.PASSES]
    products = [[e(n), (fmt(p) if not isinstance(p, str) else p) + " R$", e(b)] for n, p, b in C.PRODUCTS]
    boosts = table(["Boost", "Per level (max 10)"], [[a, b] for a, b in C.BOOSTS])
    potions = table(["Potion", "Effect (15 min)"], [[a, b] for a, b in C.POTIONS])
    faq = [
        ("Is Hero Incremental pay to win?", "No purchase is required to see any content. Heroes come from rank ups, skins from Tickets and Skin Tokens, and automation from the upgrade trees. Passes make progress faster."),
        ("Which VIP should I buy?", "VIP I (249 Robux) is ×1.5 damage, fire rate and every currency, plus double daily rewards and a VIP tag. VIP II (799) is ×2 and VIP III (2,499) is ×4. Only your highest tier applies, and VIP II and III aren't in the Game Pass Bundle."),
        ("How do I get Tickets?", "1 Ticket every 5 minutes you're in the game, 15 per World Boss, 40–500 from weekly boards, Season Pass tiers, Ticket Bundles in the Bounty shop and the rune index. They can also be bought."),
        ("What stacks with what?", "Almost everything multiplies: VIP, 2× passes, Credit Surge, runes, Cargo Bay and SR boosts, Premium (+10%), the Squad Bonus (+10% per friend, up to 3) and a group (+10% per member, up to 30%)."),
    ]
    faq_html, faq_ld = faq_block(faq, "Shop FAQ")
    body = f"""<section class="wrap page">
  {head}
  {sec("passes", "Game passes", "HallOfFame", "Permanent · bought once", table(["Pass", "Price", "What it does"], passes, right=(1,)))}
  {sec("products", "Products", "Credits", "Buy any time", table(["Product", "Price", "What it does"], products, right=(1,)), "var(--sky)")}
  {sec("tickets", "Ticket shop", "Ticket", "1 Ticket every 5 minutes in game", f'<div class="grid2"><div><h3 style="font-size:20px;margin-bottom:8px;">Boosts</h3><p class="lede-sm" style="margin-bottom:8px;">Permanent levels. Each level costs 3 Tickets more than the last (165 Tickets to max one boost).</p>{boosts}</div><div><h3 style="font-size:20px;margin-bottom:8px;">Potions</h3><p class="lede-sm" style="margin-bottom:8px;">20 Tickets for 10. Using more stacks the time.</p>{potions}</div></div><p class="note" style="margin-top:10px;">Skins cost 600 Tickets. Plan your spending with the <a href="{BASE}calculator/#tickets">ticket planner</a>.</p>', "var(--warn)")}
  {faq_html}
</section>"""
    add("shop/", "Hero Incremental Shop: Game Passes, VIP, Prices & Tickets",
        "Every Hero Incremental game pass and product with prices: VIP I–III, 2× Credits/Redeploy/Cargo/Crowns, rune passes, Season Pass, tickets, boosts and potions.",
        body, [bc, faq_ld], "shop")


# ---- calculator ---------------------------------------------------------------------------
def build_calculator():
    head, bc = page_head("Calculators", "Hero Incremental calculators",
                         "Plan rune farming, rank ups, Redeploys and ticket spending with the game's own formulas.", [("Calculators", "calculator/")])
    data = json.dumps({"RANKS": C.RANKS, "ALTARS": C.ALTARS, "TIER_COLORS": C.TIER_COLORS, "MIN": C.REDEPLOY_MIN}, separators=(",", ":"))

    def rng(id_, label, mx, val, step=1):
        return f'<div class="field"><label for="{id_}">{label}</label><div class="range-row"><input type="range" id="{id_}" min="0" max="{mx}" step="{step}" value="{val}"><output id="{id_}-o">{val}</output></div></div>'
    body = f"""<section class="wrap page">
  {head}
  {toc([("runes", "Rune odds"), ("rank", "Rank-up"), ("redeploy", "Redeploy & SR"), ("tickets", "Tickets")])}
  <div class="panel tool altar-sec" id="runes">
    <div class="form">
      <h2 style="margin: 0;">Rune odds</h2>
      <div class="field"><label for="ro-altar">Altar</label><select id="ro-altar"></select></div>
      {rng("ro-cluck", "Rune Luck (Credit tab)", 15, 3)}
      {rng("ro-rluck", "Rune Luck (Redeploy tab)", 15, 2)}
      {rng("ro-cspeed", "Rune Speed (Credit tab)", 15, 3)}
      {rng("ro-rspeed", "Rune Speed (Redeploy tab)", 15, 2)}
      {rng("ro-cbulk", "Rune Bulk (Credit tab)", 12, 1)}
      {rng("ro-rbulk", "Rune Bulk (Redeploy tab)", 12, 1)}
      {rng("ro-field", "Field Command (Command)", 25, 3)}
      {rng("ro-attune", "Rune Attunement (Cargo Bay)", 3, 0)}
      {rng("ro-shop", "Ticket boosts (each)", 10, 0)}
      <div class="field"><label for="ro-tierluck">Luck from owned runes and index (×)</label><input type="number" id="ro-tierluck" min="1" step="0.05" value="1"></div>
      <div class="field"><span class="lbl">Passes &amp; potions</span>
        <label class="check"><input type="checkbox" id="ro-pass-luck"> Rune Luck pass (×1.5)</label>
        <label class="check"><input type="checkbox" id="ro-pass-speed"> Rune Speed pass (×1.5)</label>
        <label class="check"><input type="checkbox" id="ro-pass-bulk"> Rune Bulk pass (×1.5)</label>
        <label class="check"><input type="checkbox" id="ro-pass-clone"> Rune Clone pass (+1)</label>
        <label class="check"><input type="checkbox" id="ro-pots"> Luck, Speed and Bulk potions (×2 each)</label>
        <label class="check"><input type="checkbox" id="ro-rush"> Rune Rush (×1.5 Luck)</label>
      </div>
    </div>
    <div class="results">
      <div class="readout" id="ro-readout"></div>
      <div class="table-scroll"><table><thead><tr><th>Tier</th><th class="r">Base</th><th class="r">Your odds</th><th class="r">First pull in</th><th class="r">Per hour</th><th class="r">[MAX] in</th></tr></thead><tbody id="ro-table"></tbody></table></div>
      <p class="note">Example build shown. Times are averages; rare tiers can land much sooner or later. Rune bonuses themselves (like Glimmer's Luck) aren't included unless you add them in "Luck from owned runes".</p>
    </div>
  </div>
  <div class="panel tool altar-sec" id="rank" style="--accent: var(--sky);">
    <div class="form">
      <h2 style="margin: 0;">Rank-up</h2>
      <div class="field"><label for="rk-rank">Current rank</label><select id="rk-rank"></select></div>
      <div class="field"><label for="rk-credits">Credits you have</label><input type="number" id="rk-credits" min="0" step="1000" value="12000"></div>
      <div class="field"><label for="rk-income">Credits per minute</label><input type="number" id="rk-income" min="1" step="1000" value="9000"></div>
    </div>
    <div class="results">
      <div class="readout" id="rk-readout"></div>
      <div class="table-scroll"><table><thead><tr><th>Next rank</th><th class="r">Cost</th><th class="r">Still needed</th><th class="r">Time at this income</th></tr></thead><tbody id="rk-table"></tbody></table></div>
      <p class="note">Example numbers shown. Income jumps after every rank up and Redeploy, so later ranks arrive much sooner than this.</p>
    </div>
  </div>
  <div class="panel tool altar-sec" id="redeploy" style="--accent: var(--warn);">
    <div class="form">
      <h2 style="margin: 0;">Redeploy &amp; SR</h2>
      <div class="field"><label for="rd-rank">Current rank</label><select id="rd-rank"></select></div>
      <div class="field"><label for="rd-credits">Credits you'd cash in</label><input type="number" id="rd-credits" min="0" step="1000" value="2000000"></div>
      {rng("rd-rm", "Redeploy Multiplier level", 12, 3)}
      {rng("rd-ft", "Fast Track level (SR)", 25, 0)}
      <div class="field"><label for="rd-boost">Other Redeploy boosts (×)</label><input type="number" id="rd-boost" min="1" step="0.1" value="1"></div>
      <div class="field"><label for="rd-earned">Redeploy points earned this tier</label><input type="number" id="rd-earned" min="0" step="100" value="50000"></div>
    </div>
    <div class="results">
      <div class="readout" id="rd-readout"></div>
      <div class="prose"><p class="lede-sm">RP = √(Credits ÷ 150) × 2<sup>Redeploy Multiplier</sup> × (1 + 10% × Fast Track) × other boosts (Logistics Network, runes, VIP, 2× Redeploy pass). SR at promotion = √(RP earned this tier ÷ 2), rounded down.</p></div>
    </div>
  </div>
  <div class="panel tool altar-sec" id="tickets" style="--accent: var(--good);">
    <div class="form">
      <h2 style="margin: 0;">Ticket planner</h2>
      <div class="field"><label for="tk-hours">Hours played per day</label><div class="range-row"><input type="range" id="tk-hours" min="0.5" max="8" step="0.5" value="2"><output id="tk-hours-o">2</output></div></div>
      <div class="field"><label for="tk-have">Tickets you have</label><input type="number" id="tk-have" min="0" value="40"></div>
      <div class="field"><label for="tk-boost">Plan for</label><select id="tk-boost"></select></div>
    </div>
    <div class="results">
      <div class="readout" id="tk-readout"></div>
      <div class="table-scroll"><table><thead><tr><th>Level</th><th class="r">Ticket cost</th><th class="r">Running total</th><th class="r">Bonus</th><th class="r">Ready in</th></tr></thead><tbody id="tk-table"></tbody></table></div>
      <p class="note">Counts only the 1 Ticket per 5 minutes you get for playing; bosses, weekly boards and the Season Pass make it faster.</p>
    </div>
  </div>
</section>
<script type="application/json" id="hi-data">{data}</script>"""
    add("calculator/", "Hero Incremental Calculators: Rune Odds, Rank-Up, Redeploy & Tickets",
        "Free Hero Incremental calculators: rune odds and time to [MAX] for every altar, time to your next rank, Redeploy points and SR, and ticket boost planning.",
        body, [bc], "calculator")


# ---- bots ---------------------------------------------------------------------------------
def build_bots():
    head, bc = page_head("Enemy database", "Hero Incremental bots",
                         "Every bot type: health, armor, damage, payout and everything else a kill gives you.", [("Bots", "bots/")],
                         "Training Drones (50 HP, 10 Credits) fill the Main Hall. Armored Mechs (Bronze 3, 1M gate) pay 100 and Elite Androids (Bronze 1, 5B gate) 1,500. In Sturmfeste, Sentinels pay 12K, Knights 60K and Wardens 350K. All payouts are multiplied by your rank and upgrades.")
    top = math.log10(max(b["hp"] for b in C.BOTS))
    cards = []
    for b in C.BOTS:
        note = f'<p class="note">{e(b["note"])}</p>' if b.get("note") else ""
        cards.append(f"""<div class="panel bot" style="--accent:var(--damage)"><div><h2 class="bot-h">{b['name']}</h2><div class="where">{b['zone']} · {b['rank']}</div></div>
      <div class="hp-bar" title="Health (log scale)"><i style="width:{math.log10(b['hp']) / top * 100:.1f}%"></i></div>
      <dl><div><dt>Health</dt><dd>{fmt(b['hp'])}</dd></div><div><dt>Armor</dt><dd>{round(b['armor'] * 100)}%</dd></div><div><dt>Hit</dt><dd>{b['dmg']}</dd></div>
      <div><dt>Credits</dt><dd style="color:var(--orange)">{fmt(b['credits'])}</dd></div><div><dt>Respawn</dt><dd>{b['respawn']}s</dd></div><div><dt>Credits / HP</dt><dd>{b['credits'] / b['hp']:.2f}</dd></div></dl>{note}</div>""")
    per = [[b["name"], fmt(b["credits"]), b["heat"], b["scrap"], b["marks"], b["mxp"], b["ult"], b["sxp"]] for b in C.BOTS]
    faq = [
        ("Which bot gives the most Credits per health?", "Training Drones (0.2 Credits per HP) and Elite Androids (0.15) are the most efficient in the Facility; in Sturmfeste, Wardens (0.88) and Knights (0.67) pay the most per HP."),
        ("What does armor do?", "Armor cuts the damage bots take: Armored Mechs 10%, Sentinels 15%, Elite Androids and Knights 25%, Wardens 35%. Bulwark's hammer ignores Armored Mech armor."),
        ("How many bots spawn?", "Each zone starts with 5 bots, +2 for every 5 Damage levels you own, plus your turrets, up to a cap (14 in the Main Hall). More players in a zone scale it up to 2.8×."),
    ]
    faq_html, faq_ld = faq_block(faq, "Bot FAQ")
    body = f"""<section class="wrap page">
  {head}
  <div class="bot-grid">{''.join(cards)}</div>
  <div class="panel"><h2>What each kill gives</h2>{table(["Bot", "Credits", "Heat", "Scrap", "Bounty Marks", "Mastery XP", "Ult charge", "Season XP"], per, right=(1, 2, 3, 4, 5, 6, 7))}
    <p class="note" style="margin-top:10px;">Scrap drops 45% of the time. Bounty Marks only come from WANTED bots, which have 5× health and pay 10× Credits.</p></div>
  <div class="panel" style="--accent:var(--damage);"><div class="sec-h"><img src="{img('WorldBoss')}" alt="" width="44" height="44"><div><h2>Storm Colossus (World Boss)</h2><small>Stormfield · every hour · Silver 5+</small></div></div>
    <p class="lede-sm">At least 2M health, scaling with players. Slams for 30, fires 5-missile volleys, and sends shock rings at 66% and 33% health; enrages at 25%. <a href="{BASE}events/#world-boss">Rewards and timing</a>.</p></div>
  {faq_html}
</section>"""
    add("bots/", "Hero Incremental Bots: Health, Armor, Credits & Drops",
        "Every Hero Incremental bot from Training Drones to Wardens and the Storm Colossus: health, armor, damage, Credits, heat, Scrap, Marks and Season XP per kill.",
        body, [bc, faq_ld], "bots")


# ---- updates ------------------------------------------------------------------------------
def build_updates():
    head, bc = page_head("Patch notes", "Hero Incremental updates", "What changed in each update of Hero Incremental, newest first.", [("Updates", "updates/")])
    arts = []
    for i, p in enumerate(C.PATCHES):
        latest = '<span class="chip pill-active"><span>Latest</span></span>' if i == 0 else ""
        items = "".join(f"<li>{e(x)}</li>" for x in p["items"])
        arts.append(f'<article class="patch"><div class="patch-side"><b>{e(p["tag"])}</b><span class="pill">{p["date"]}</span>{latest}</div><div><h2 class="patch-h">{e(p["title"])}</h2><ul>{items}</ul></div></article>')
    body = f"""<section class="wrap page">
  {head}
  <div class="panel">{''.join(arts)}</div>
</section>"""
    add("updates/", "Hero Incremental Updates & Patch Notes",
        f"Hero Incremental patch notes and update log. Latest: {C.PATCHES[0]['title']}.", body, [bc], "updates")


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
    <a class="btn btn-ghost" href="{BASE}guide/"><span>Guide</span></a>
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


BUILDERS = (build_home, build_codes, build_guide, build_faq, build_heroes, build_tiers, build_ranks, build_currencies, build_upgrades,
            build_runes, build_objectives, build_sturmfeste, build_events, build_skins, build_shop, build_calculator, build_bots, build_updates, build_404)


def main():
    for f in BUILDERS:
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
    # alternates for Search Console: a plain-text URL list and a sitemap index (fresh URLs if sitemap.xml gets stuck)
    urls = [f"{SITE}/{p['path']}" for p in PAGES if p["path"] != "404.html"]
    (OUT / "sitemap.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")
    newest = max(v["date"] for v in manifest.values())
    (OUT / "sitemap-index.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                           f"  <sitemap><loc>{SITE}/sitemap.xml</loc><lastmod>{newest}</lastmod></sitemap>\n</sitemapindex>\n", encoding="utf-8")
    print(f"built {len(PAGES)} pages -> {OUT} ({len(sitemap)} in sitemap)")


if __name__ == "__main__":
    main()

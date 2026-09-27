# Hero Incremental Wiki

Codes, heroes, tier list, ranks, runes, every upgrade tree and calculators for **Hero Incremental** on Roblox.

Live site: https://daschen.github.io/hero-incremental-wiki/

## How it works

- `src/content.py`: **all game data and page text** (heroes, tier list, unlock order, codes, ranks, currencies,
  upgrade trees, runes, bots, objectives, events, skins, season, shop, FAQ, patch notes). Edit this.
- `build.py`: page templates. Generates every page into `docs/` (served by GitHub Pages) plus `sitemap.xml`.
- `src/site.css`, `src/site.js`: shared styles and the small script (copy buttons, hero filter, calculators).
- `src/img/`: portraits and icons. `src/assets/`: share image and favicons (`make_images.py`).

## Updating the site

```
python build.py
git add -A
git commit -m "Update codes"
git push
```

GitHub Pages redeploys in about a minute. Each page's "Updated" date and sitemap date only change when that
page's content changes (`src/lastmod.json`).

Not affiliated with or endorsed by Roblox Corporation.

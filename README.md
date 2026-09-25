# Hero Incremental Wiki

Codes, heroes, tier list, rank guide, rune odds and calculators for **Hero Incremental** on Roblox.

Live site: https://daschen.github.io/hero-incremental-wiki/

## How it works

- `src/data.json`: all game data (codes, heroes, ranks, systems, runes, bots, tier list, patch notes). **Edit this.**
- `src/site.css`, `src/site.js`: shared styles and the small script (copy buttons, hero filter, calculators).
- `src/img/`: hero portraits and icons. `src/assets/`: share image and favicons (made by `make_images.py`).
- `build.py`: generates every page into `docs/` (served by GitHub Pages), plus `sitemap.xml`.

## Updating the site

```
python build.py
git add -A
git commit -m "Update codes"
git push
```

GitHub Pages redeploys in about a minute. Each page's "Updated" date and sitemap date only change when that page's content changes (`src/lastmod.json`).

Not affiliated with or endorsed by Roblox Corporation.

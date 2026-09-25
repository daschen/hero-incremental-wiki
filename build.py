"""Wrap page.html (the Artifact-preview version) into a full index.html for any free static host."""
import re, pathlib
here = pathlib.Path(__file__).parent
src = (here / "page.html").read_text(encoding="utf-8")
title = re.search(r"<title>(.*?)</title>", src).group(1)
# everything up to </style> belongs in <head>; the rest is the body
cut = src.index("</style>") + len("</style>")
head, body = src[:cut], src[cut:]
meta = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Codes, heroes, tier list, rank guide, rune odds and calculators for Hero Incremental on Roblox.">
<meta property="og:title" content="Hero Incremental">
<meta property="og:description" content="Codes, heroes, tier list, rank guide, rune odds and calculators for Hero Incremental on Roblox.">
<meta property="og:image" content="img/Hero_Solace.webp">
<meta name="theme-color" content="#0a1224">
<meta name="google-site-verification" content="FJ00bImACFERceqv10BLJuMgPNszUCqIstSLtMqbvSM" />
<link rel="icon" href="img/HeroToken.webp">
"""
out = "<!doctype html>\n<html lang=\"en\">\n<head>\n" + meta + head + "\n</head>\n<body>" + body + "\n</body>\n</html>\n"
(here / "index.html").write_text(out, encoding="utf-8")
print("index.html", len(out), "bytes, title:", title)

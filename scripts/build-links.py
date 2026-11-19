#!/usr/bin/env python3
"""Build the link hub and podcast directories from one approved link registry."""
import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "data/presence.json").read_text())
CONFIG = json.loads((ROOT / "data/link-pages.json").read_text())
esc = lambda value: html.escape(str(value), quote=True)

def destination(key):
    if key in CONFIG["pages"]:
        return "/links/" + key + "/"
    value = REGISTRY["links"][key]
    assert urlparse(value).scheme == "https", "Expected HTTPS destination: " + key
    return value

def card(item, compact=False):
    url = esc(destination(item["key"]))
    title = esc(item["title"])
    icon = esc(item.get("icon", "↗"))
    color = esc(item.get("color", "purple"))
    assert color in ("purple", "red", "teal", "green", "ink", "gold")
    description = "" if compact else '<span class="d">' + esc(item["description"]) + '</span>'
    arrow = "" if compact else '<span class="arrow" aria-hidden="true">→</span>'
    return '<a class="link" href="' + url + '"><span class="ic bg-' + color + '" aria-hidden="true">' + icon + '</span><span class="txt"><span class="t">' + title + '</span>' + description + '</span>' + arrow + '</a>'

def groups(items):
    output = []
    for index, group in enumerate(items):
        label = "links-group-" + str(index)
        parts = ['<section class="group" aria-labelledby="' + label + '">', '<h2 class="group-label" id="' + label + '">' + esc(group["title"]) + '</h2>']
        if group.get("description"):
            parts.append('<p class="section-note">' + esc(group["description"]) + '</p>')
        if group.get("compact"):
            parts.append('<div class="podcast-actions">')
        parts.extend(card(item, group.get("compact", False)) for item in group["items"])
        if group.get("compact"):
            parts.append('</div>')
        parts.append('</section>')
        output.append("\n".join(parts))
    return "\n\n".join(output)

def subpage(slug, page):
    title = esc(page["title"])
    description = esc(page["description"])
    canonical = "https://alexagriffith.com/links/" + slug + "/"
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Alexa Griffith</title>
<meta name="description" content="{description}">
<meta name="author" content="Alexa Griffith">
<link rel="canonical" href="{canonical}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{title} · Alexa Griffith">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
<meta property="og:image" content="https://alexagriffith.com/assets/img/keynote-talking.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&amp;family=JetBrains+Mono:wght@500;700&amp;display=swap">
<link rel="stylesheet" href="/links/links.css">
</head>
<body class="subpage">
<div class="stripe"></div>
<div class="wrap">
<a class="back" href="/links/">← All Alexa’s links</a>
<header><h1>{title}</h1><p class="intro">{description}</p></header>
<main id="main-content">
{groups(page["groups"])}
</main>
<footer><a href="/links/">Back to all links</a> · <a href="/">Alexa Griffith</a></footer>
</div>
</body>
</html>
'''

def build():
    path = ROOT / "links/index.html"
    source = path.read_text()
    start, end = "<!-- links:start -->", "<!-- links:end -->"
    assert source.count(start) == source.count(end) == 1, "Link hub needs one generated region"
    root = source.split(start)[0] + start + "\n" + groups(CONFIG["root"]) + "\n" + end + source.split(end)[1]
    pages = {"links/index.html": root}
    for slug, page in CONFIG["pages"].items():
        pages["links/" + slug + "/index.html"] = subpage(slug, page)
    return pages

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, rendered in build().items():
        path = ROOT / name
        if args.check:
            assert path.exists() and path.read_text() == rendered, "Run python3 scripts/build-links.py: " + name
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered)
    assert len(CONFIG["root"][0]["items"]) == 3, "Podcast entry must stay compact"
    print("Link hub and three podcast directories match the shared registry.")

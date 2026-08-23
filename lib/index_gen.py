#!/usr/bin/env python3
"""
Generate the blog landing page (index.html) and feed.xml from posts/.

A post is any directory named  posts/YYYY-MM-DD-slug/  containing src.txt.
  - date and slug come from the directory name
  - title    = first line of src.txt
  - subtitle = third line of src.txt
  - summary / tags / draft come from the optional meta.txt

Posts with "draft: true" are built but left out of the index and the feed.
"""
import re, html, pathlib, datetime

ROOT = pathlib.Path(".")
POSTS = ROOT / "posts"
SITE_TITLE = "Ice Lakes Labs"
SITE_TAGLINE = "Notes from an over-instrumented house."
SITE_URL = "https://blog.icelakeslabs.com"   # must match the CNAME file + DNS

def read_meta(d):
    meta = {}
    f = d / "meta.txt"
    if f.exists():
        for line in f.read_text(encoding="utf-8").split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, _, v = line.partition(":")
            meta[k.strip().lower()] = v.strip()
    return meta

def collect():
    out = []
    for d in sorted(POSTS.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+)$", d.name)
        src = d / "src.txt"
        if not m or not src.exists():
            print(f"index: skipping {d.name} (needs YYYY-MM-DD-slug/ and src.txt)")
            continue
        lines = src.read_text(encoding="utf-8").split("\n")
        meta = read_meta(d)
        out.append({
            "dir": d,
            "date": datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))),
            "slug": m.group(4),
            "title": lines[0].strip() if lines else d.name,
            "subtitle": lines[2].strip() if len(lines) > 2 else "",
            "summary": meta.get("summary", ""),
            "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
            "draft": meta.get("draft", "").lower() == "true",
            "words": len(src.read_text(encoding="utf-8").split()),
        })
    return out

posts = collect()
live = [p for p in posts if not p["draft"]]

# ---------- index.html ------------------------------------------------------
items = []
for p in live:
    tags = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in p["tags"])
    items.append(f'''  <article class="post-entry">
    <p class="post-date"><time datetime="{p['date']}">{p['date'].strftime('%d %B %Y')}</time>
       &middot; {p['words']:,} words</p>
    <h2><a href="posts/{p['dir'].name}/">{html.escape(p['title'])}</a></h2>
    <p class="post-sub">{html.escape(p['subtitle'])}</p>
    <p class="post-summary">{html.escape(p['summary'])}</p>
    <p class="post-tags">{tags}</p>
  </article>''')

(ROOT / "index.html").write_text(f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(SITE_TITLE)}</title>
<link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_TITLE)}" href="feed.xml">
<link rel="stylesheet" href="style.css">
</head>
<body class="index-page">
<header class="site-header">
  <h1>{html.escape(SITE_TITLE)}</h1>
  <p class="tagline">{html.escape(SITE_TAGLINE)}</p>
</header>
<main>
{chr(10).join(items)}
</main>
<footer class="site-footer">
  <p><a href="feed.xml">RSS</a></p>
</footer>
</body>
</html>
''', encoding="utf-8")

# ---------- feed.xml --------------------------------------------------------
entries = []
for p in live:
    link = f"{SITE_URL}/posts/{p['dir'].name}/"
    pub = datetime.datetime.combine(p["date"], datetime.time(12, 0))
    entries.append(f'''  <item>
    <title>{html.escape(p['title'])}</title>
    <link>{link}</link>
    <guid isPermaLink="true">{link}</guid>
    <pubDate>{pub.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
    <description>{html.escape(p['summary'] or p['subtitle'])}</description>
  </item>''')

(ROOT / "feed.xml").write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{html.escape(SITE_TITLE)}</title>
  <link>{SITE_URL}/</link>
  <description>{html.escape(SITE_TAGLINE)}</description>
{chr(10).join(entries)}
</channel>
</rss>
''', encoding="utf-8")

drafts = len(posts) - len(live)
print(f"index: {len(live)} post(s) listed"
      + (f", {drafts} draft(s) hidden" if drafts else ""))
if SITE_URL == "https://example.com":
    print("index: WARNING — set SITE_URL in lib/index_gen.py before publishing "
          "(feed.xml links are wrong until you do)")

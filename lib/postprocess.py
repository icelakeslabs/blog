#!/usr/bin/env python3
"""
Post-process a built post's index.html:
  - move the TOC below the title and subtitle (pandoc puts it above everything)
  - unwrap the TOC's outer <li>, which otherwise repeats the title
  - add a "back to all posts" link
  - verify every internal anchor resolves
Run from inside a post directory.
"""
import re, pathlib, sys

f = pathlib.Path("index.html")
h = f.read_text(encoding="utf-8")

m = re.search(r'<nav id="TOC".*?</nav>\n?', h, re.S)
if m:
    original = m.group(0)
    toc = original
    a_end = toc.find("</a>")
    inner_start = toc.find("<ul>", a_end) if a_end != -1 else -1
    inner_end = toc.rfind("</li>")
    if 0 < inner_start < inner_end:
        toc = ('<nav id="TOC" role="doc-toc">\n'
               + toc[inner_start:inner_end].rstrip() + "\n</nav>\n")
    h = h.replace(original, "")
    anchor = re.search(r'<h1[^>]*>.*?</h1>\s*<p>.*?</p>', h, re.S)
    if anchor:
        h = h[:anchor.end()] + "\n" + toc + h[anchor.end():]
    else:
        print("  postprocess: WARNING — title block not found; TOC left at top")
        h = h.replace("<body>", "<body>\n" + toc, 1)

nav = '<p class="back-link"><a href="../../">&larr; all posts</a></p>\n'
if 'class="back-link"' not in h:
    h = h.replace("<body>", "<body>\n" + nav, 1)
    h = h.replace("</body>", nav + "</body>", 1)

f.write_text(h, encoding="utf-8")

unresolved = [a for a in re.findall(r'href="#([^"]+)"', h) if f'id="{a}"' not in h]
if unresolved:
    print(f"  postprocess: WARNING — unresolved anchors: {unresolved}")
loose = h.count("<li><p>")
if loose:
    print(f"  postprocess: WARNING — {loose} loose list item(s)")

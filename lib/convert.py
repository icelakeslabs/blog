#!/usr/bin/env python3
"""
Convert the annotated plain-text draft into Markdown.

Conventions handled (all confirmed by Craig):
  *word*            -> bold
  /i text/i         -> italic
  -Word-            -> strikethrough (headings only; explicit list)
  =-= ...           -> image placeholder or TL;DR nav link
  line + ---- rule  -> H2 section
  dash-ruled grids  -> real Markdown tables
  other indent      -> fenced code block

Anything the converter is unsure about is written to review.txt rather than
guessed at.
"""
import re, sys, pathlib

SRC = pathlib.Path("src.txt")
IMGDIR = "images"          # your existing directory — not renamed

# slot -> real filename, from images/manifest.csv when it exists
IMAGES = {}
_mf = pathlib.Path(IMGDIR) / "manifest.csv"
if _mf.exists():
    import csv as _csv
    with _mf.open(newline="", encoding="utf-8") as _f:
        for _r in _csv.DictReader(_f):
            if _r.get("your_file", "").strip():
                IMAGES[_r["slot"]] = _r["your_file"].strip()
OUT = pathlib.Path("post.md")
REVIEW = pathlib.Path("review.txt")

STRIKE = {"-Neurio-": "~~Neurio~~", "-D-o-w-n-": "~~Down~~"}

lines = SRC.read_text(encoding="utf-8").split("\n")
review = []
review_images = []
out = []
img_n = 0

# ---------- pass 1: locate structure ----------
section_at = {}          # line index -> heading text
for i in range(len(lines) - 1):
    if re.fullmatch(r"-{4,}", lines[i + 1].strip()) and lines[i].strip():
        section_at[i] = lines[i].strip()

tldr_at = [i for i, l in enumerate(lines) if l.strip().lower().startswith("tl;dr")]

def next_tldr_slug(idx):
    """Slug of the first TL;DR heading after idx, for nav links."""
    for t in tldr_at:
        if t > idx:
            # find the enclosing section to make the slug unique
            sec = max([s for s in section_at if s < t], default=None)
            if sec is not None:
                return slug(section_at[sec]) + "-tldr"
    return None

def slug(text):
    s = text.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    # pandoc 2.x REJECTS an identifier starting with a digit: it leaves the
    # literal "{#1-foo}" in the heading text and auto-generates its own id, so
    # every nav link silently 404s. pandoc 3.x accepts it. Section headings here
    # are numbered ("1. So Many Photons..."), so the slug starts with a digit.
    # Prefix it to stay valid on BOTH pandoc majors. Both the anchor definition
    # and the nav link route through this function, so they stay in sync.
    if s and s[0].isdigit():
        s = "s" + s
    return s

# ---------- inline formatting ----------
def inline(t):
    for k, v in STRIKE.items():
        t = t.replace(k, v)
    # Paired slash tags: /i ... /i, /strikeout ... /strikeout, /b ... /b.
    # Parked behind sentinels so the bold rule below can't re-match them.
    # Only these exact tags are recognised, so URL paths like /vitals and
    # /tesla are left alone.
    t = re.sub(r"/strikeout\s*(.+?)\s*/strikeout", "\x05\\1\x06", t)
    # /m ... /m -> monospace inline, no code-block background
    t = re.sub(r"/m\s+(.+?)\s*/m\b",
               lambda m: f'<span class="mono">{m.group(1)}</span>', t)
    t = re.sub(r"/b\s+(.+?)\s*/b\b", "\x03\\1\x04", t)
    t = re.sub(r"/i\s*(.+?)\s*/i", "\x01\\1\x02", t)
    # *word or phrase* -> **bold**   (skip the lone footnote marker "(*)")
    t = re.sub(r"(?<!\()\*([^*\n]+?)\*(?!\))", r"**\1**", t)
    t = (t.replace("\x01", "*").replace("\x02", "*")
          .replace("\x03", "**").replace("\x04", "**")
          .replace("\x05", "~~").replace("\x06", "~~"))
    # bare URLs -> links
    # Skip only genuine Markdown links "](url)" and already-autolinked <url>.
    # A URL in ordinary prose parentheses still becomes clickable.
    t = re.sub(r"(?<!\]\()(?<!<)\bhttps?://[^\s\)<>]+",
               lambda m: f"<{m.group(0)}>", t)
    return t

# ---------- table parsing ----------
def parse_table(start):
    """start points at the header line; start+1 is the dash rule."""
    rule = lines[start + 1]
    spans = [(m.start(), m.end()) for m in re.finditer(r"-{3,}", rule)]
    if len(spans) < 2:
        return None, start
    bounds = [s for s, _ in spans] + [10**6]

    def cells(l, allow_fallback=True):
        cut = [l[bounds[c]:bounds[c + 1]].strip() for c in range(len(spans))]
        # If a boundary landed inside a word, the row is misaligned in the
        # source; fall back to splitting on runs of 2+ spaces. Never do this
        # for continuation lines — their text legitimately sits in one column.
        if allow_fallback:
            for b in bounds[1:-1]:
                if 0 < b < len(l) and l[b - 1] != " " and l[b] != " ":
                    alt = re.split(r"\s{2,}", l.strip())
                    return (alt + [""] * len(spans))[:len(spans)]
        return cut

    header = cells(lines[start])
    rows, i = [], start + 2
    while i < len(lines):
        l = lines[i].replace("\t", " " * 8)
        if not l.strip():
            # Blank lines appear *inside* these tables (spacing between rows
            # and before wrapped cells). The table really ends at the first
            # non-blank line that starts at column 0 — e.g. the next
            # "Query: ..." header or ordinary prose.
            k = i + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            # Continue only if the next non-blank line still looks like a
            # table row: indented AND containing a column gap (3+ spaces).
            # Indented prose after a table has no such gap, so it ends here.
            if (k < len(lines) and lines[k][:1].isspace()
                    and re.search(r"\S\s{3,}\S", lines[k])):
                i = k
                continue
            break
        # A row starts only when the first column has content. Anything else
        # is a wrapped continuation of the row above.
        is_cont = not l[:bounds[1]].strip()
        if not is_cont:
            rows.append(cells(l))
        elif rows:
            # A continuation line may wrap in several columns at once. If every
            # column boundary lands on whitespace, slicing is safe and each
            # column is merged separately. Otherwise the row is misaligned in
            # the source, so append the whole line to the column its text
            # starts in rather than cutting words in half.
            # Slicing is safe only when the character *before* every boundary
            # is whitespace. Checking l[b] too was too lax: a word starting one
            # column early ("I can't read...") got sliced in half.
            safe = all(b >= len(l) or l[b - 1] == " " for b in bounds[1:-1])
            if safe:
                for k, part in enumerate(cells(l, allow_fallback=False)):
                    if part:
                        rows[-1][k] = (rows[-1][k] + " " + part).strip()
            else:
                text_col = len(l) - len(l.lstrip())
                col = max([k for k in range(len(spans))
                           if bounds[k] <= text_col + 3] or [len(spans) - 1])
                rows[-1][col] = (rows[-1][col] + " " + l.strip()).strip()
        i += 1
    ragged = [r for r in rows if sum(1 for c in r if c) < 2]
    if ragged:
        sec = max([x for x in section_at if x < start], default=None)
        review.append(
            f"src.txt line {start+1}  |  in: "
            f"{section_at[sec] if sec is not None else '(before section 1)'}\n"
            f"    table parsed but {len(ragged)} row(s) look ragged — the source\n"
            f"    grid is misaligned here. Check these against src.txt:\n"
            + "".join(f"      {r[0][:60]}\n" for r in ragged))
    return (header, rows), i

def emit_table(header, rows):
    w = len(header)
    out.append("| " + " | ".join(inline(h) for h in header) + " |")
    out.append("|" + "|".join([" --- "] * w) + "|")
    for r in rows:
        r = (r + [""] * w)[:w]
        out.append("| " + " | ".join(inline(c) for c in r) + " |")
    out.append("")

# ---------- main pass ----------
i = 0
in_script = False
while i < len(lines):
    raw = lines[i]
    l = raw.strip()

    # the JS email obfuscation block -> replacement sentence
    if 'id="email-link"' in l or l.startswith("<script"):
        in_script = True
    if in_script:
        if l.startswith("</script>"):
            in_script = False
            out.append("This blog is written by a human — namely, me.")
            out.append("")
        i += 1
        continue

    # title / subtitle
    if i == 0:
        out.append("# " + inline(l))
        out.append("")
        i += 1
        continue

    # section heading
    if i in section_at:
        head = section_at[i]
        num = re.match(r"\s*(\d+)\.", head)
        anchor = f" {{#section-{num.group(1)}}}" if num else ""
        head_md = inline(head)
        # A lone "*" (the footnote marker) anywhere in the heading stops pandoc
        # from parsing the trailing {#section-N} as an attribute block — it ends
        # up printed literally in the heading AND the TOC, and the anchor is
        # lost. Escaping it renders identically, "(*)", and lets the attribute
        # parse. Only the bare marker is touched; *bold* has already been turned
        # into **bold** by inline() above and must not be escaped.
        if anchor:
            head_md = head_md.replace("(*)", r"(\*)")
        out.append("## " + head_md + anchor)
        out.append("")
        i += 2
        continue

    # TL;DR heading
    if l.lower().startswith("tl;dr"):
        sec = max([s for s in section_at if s < i], default=None)
        anchor = (slug(section_at[sec]) + "-tldr") if sec is not None else slug(l)
        out.append(f'### {inline(l)} {{#{anchor}}}')
        out.append("")
        i += 1
        continue

    # annotations. These usually sit on their own line, but sometimes trail
    # prose ("And here's the first one: =-= insert hyperlink..."), so split
    # the prose off first and let the annotation be handled below.
    if "=-=" in l and not l.startswith("=-="):
        head, _, tail = l.partition("=-=")
        if head.strip():
            out.append(inline(head.strip()))
            out.append("")
        l = "=-=" + tail

    if l.startswith("=-="):
        body = l[3:].strip()
        if "hyperlink" in body.lower():
            sec = re.search(r"section\s+(\d+)", body, re.I)
            if sec:
                # Same label as every other nav link: what's being skipped is
                # the long text, not a jump "to" a TL;DR.
                out.append(f"[Skip ahead — DR the next TL →]"
                           f"(#section-{sec.group(1)})")
            else:
                tgt = next_tldr_slug(i)
                if tgt:
                    out.append(f"[Skip ahead — DR the next TL →](#{tgt})")
                else:
                    review.append(
                        f"src.txt line {i+1}  |  nav marker with no resolvable "
                        f"target: {body[:60]}")
            out.append("")
        else:
            img_n += 1
            slot = f"IMG-{img_n:02d}"
            fname = IMAGES.get(slot)
            out.append(f'<!-- {slot} (src line {i+1}): {body} -->')
            if fname:
                out.append(f'![{body}]({IMGDIR}/{fname})')
            else:
                out.append(f'![{slot} — UNASSIGNED: {body}]({IMGDIR}/{slot}.png)')
                review_images.append(f"{slot}  src line {i+1}  |  {body}")
            out.append("")
        i += 1
        continue

    # dash-ruled table
    if (i + 1 < len(lines) and re.search(r"-{3,}\s+-{3,}", lines[i + 1])
            and raw.startswith(" ")):
        parsed, nxt = parse_table(i)
        if parsed:
            emit_table(*parsed)
            i = nxt
            continue

    # indented dash-bulleted reference block -> nested Markdown list.
    # Top-level "  - item", with deeper-indented lines (URLs, asides) as
    # sub-bullets. Must be tested before the code-fence branch, or these
    # end up in a <pre> where links aren't clickable.
    if re.match(r"^\s{1,4}-\s+\S", raw):
        j = i
        items = []
        while j < len(lines):
            cur = lines[j]
            if not cur.strip():
                nxt = next((lines[k] for k in range(j + 1, len(lines))
                            if lines[k].strip()), "")
                if nxt[:1].isspace():
                    j += 1
                    continue
                break
            if not cur[:1].isspace():
                break
            m = re.match(r"^\s{1,4}-\s+(.*)$", cur)
            if m:
                items.append(("top", m.group(1).strip()))
            else:
                items.append(("sub", cur.strip()))
            j += 1
        # If the previous emitted block was already a list, these indented
        # items belong to it as sub-bullets. Emitting them as a separate list
        # after a blank line makes pandoc fuse the two into one loose list.
        prev = next((o for o in reversed(out) if o.strip()), "")
        continues_list = prev.lstrip().startswith("- ")
        if continues_list:
            while out and not out[-1].strip():
                out.pop()
        for kind, text in items:
            if continues_list:
                prefix = "    - " if kind == "top" else "        - "
            else:
                prefix = "- " if kind == "top" else "    - "
            out.append(prefix + inline(text))
        out.append("")
        i = max(j, i + 1)
        continue

    # unindented bullet run ("+ item") -> tight Markdown list. Emitting the
    # items contiguously matters: a blank line between them makes pandoc
    # treat the list as "loose" and wrap every item in <p>, which is what
    # produced the extra vertical space.
    if re.match(r"^[-+*]\s+\S", raw):
        j, items = i, []
        while j < len(lines):
            cur = lines[j]
            if not cur.strip():
                k = j + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1
                if k < len(lines) and re.match(r"^[-+*]\s+\S", lines[k]):
                    j = k
                    continue
                break
            m = re.match(r"^[-+*]\s+(.*)$", cur)
            if not m:
                break
            items.append(m.group(1).strip())
            j += 1
        if items:
            for it in items:
                out.append("- " + inline(it))
            out.append("")
            i = max(j, i + 1)
            continue

    # numbered list, indented or not -> tight ordered list. Wrapped
    # continuation lines are folded into the item above them.
    if re.match(r"^\s{0,4}\d+\.\s+\S", raw) and not raw.startswith("    "):
        j, items = i, []
        base = len(raw) - len(raw.lstrip())
        while j < len(lines):
            cur = lines[j]
            if not cur.strip():
                k = j + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1
                if k < len(lines) and re.match(r"^\s{0,4}\d+\.\s+\S", lines[k]):
                    j = k
                    continue
                break
            m = re.match(r"^\s{0,4}(\d+)\.\s+(.*)$", cur)
            if m:
                items.append([m.group(1), m.group(2).strip()])
            elif items and (len(cur) - len(cur.lstrip())) >= base:
                items[-1][1] += " " + cur.strip()
            else:
                break
            j += 1
        if items:
            for num, text in items:
                out.append(f"{num}. " + inline(text))
            out.append("")
            i = max(j, i + 1)
            continue

    # indented block -> code fence
    if raw.startswith("    ") or raw.startswith("\t"):
        block = []
        j = i
        while j < len(lines) and (lines[j].startswith("  ") or not lines[j].strip()):
            block.append(lines[j])
            j += 1
        while block and not block[-1].strip():
            block.pop()
            j -= 1
        if block:
            dedent = min((len(b) - len(b.lstrip()) for b in block if b.strip()),
                         default=0)
            out.append("```")
            out.extend(b[dedent:] if len(b) > dedent else b for b in block)
            out.append("```")
            out.append("")
            if any(re.search(r"\s{3,}\S", b) for b in block):
                sec = max([x for x in section_at if x < i], default=None)
                where = section_at[sec] if sec is not None else "(before section 1)"
                first = next((b.strip() for b in block if b.strip()), "")
                review.append(
                    f"src.txt lines {i+1}-{j}  |  in: {where}\n"
                    f"    aligned block kept as code block — should it be a table?\n"
                    f"    first line: {first[:70]}\n")
        i = max(j, i + 1)
        continue

    # subheading: short, standalone, ending in ":" or "-".
    # A colon line that introduces an indented block ("So now I have:") is a
    # lead-in sentence, not a heading — keep it as prose, colon and all.
    nxt = next((lines[k] for k in range(i + 1, len(lines)) if lines[k].strip()), "")
    introduces_block = l.endswith(":") and (
        nxt[:1].isspace() or nxt.strip().startswith("=-="))
    if (re.search(r"[:\-]$", l) and len(l) < 60 and not introduces_block and
            (i == 0 or not lines[i - 1].strip()) and
            (i + 1 >= len(lines) or not lines[i + 1].strip())):
        out.append("### " + inline(l.rstrip(" :-")))
        out.append("")
        i += 1
        continue

    if l:
        out.append(inline(l))
        out.append("")
    i += 1

# collapse runs of blank lines
text = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
OUT.write_text(text, encoding="utf-8")
pathlib.Path("images-todo.txt").write_text(
    ("Image slots with no file assigned in images/manifest.csv:\n\n"
     + "\n".join(review_images)) if review_images
    else "All image slots have a file assigned.\n", encoding="utf-8")
print(f"wrote {OUT} ({len(text.split())} words), {img_n} image slots, "
      f"{len(review)} items flagged for review")

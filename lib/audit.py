#!/usr/bin/env python3
"""
Build review.txt: the SUPERSET of every monospace/aligned block and every
table in the document, whether or not the converter had a question about it.

Each entry gets a stable ID derived from its content, NOT its position, so
the same block keeps the same ID across rebuilds even as other entries are
added or removed. Refer to entries by ID, never by ordinal.
"""
import re, hashlib, pathlib

SRC = pathlib.Path("src.txt")
MD = pathlib.Path("post.md")
OUT = pathlib.Path("review.txt")

src = SRC.read_text(encoding="utf-8").split("\n")
md = MD.read_text(encoding="utf-8").split("\n")

# --- map section headings in src -------------------------------------------
sections = {}
for i in range(len(src) - 1):
    if re.fullmatch(r"-{4,}", src[i + 1].strip()) and src[i].strip():
        sections[i] = src[i].strip()

def section_of(idx):
    k = max([s for s in sections if s < idx], default=None)
    return sections[k] if k is not None else "(before section 1)"

def stable_id(body):
    # Hash the WHOLE block: several tables share the same header row, so
    # hashing only the first line collides.
    norm = re.sub(r"\s+", " ", " ".join(body).strip()).lower()
    return "R-" + hashlib.md5(norm.encode()).hexdigest()[:5].upper()

# --- collect blocks as they appear in the OUTPUT ----------------------------
entries = []
i = 0
while i < len(md):
    l = md[i]
    if l.startswith("```"):
        j = i + 1
        body = []
        while j < len(md) and not md[j].startswith("```"):
            body.append(md[j])
            j += 1
        if body:
            entries.append(("CODE BLOCK", body))
        i = j + 1
        continue
    if l.startswith("| ") and i + 1 < len(md) and md[i + 1].startswith("| ---"):
        body = []
        j = i
        while j < len(md) and md[j].startswith("|"):
            body.append(md[j])
            j += 1
        entries.append(("TABLE", body))
        i = j
        continue
    i += 1

# --- locate each block back in src, for line numbers -------------------------
def find_in_src(first):
    key = re.sub(r"\s+", " ", re.sub(r"^\|\s*", "", first).split("|")[0].strip())
    if not key:
        return None
    for n, s in enumerate(src):
        if key[:28] and key[:28] in re.sub(r"\s+", " ", s):
            return n
    return None

lines_out = [
    "REVIEW — superset of every code block and table in the document.",
    "",
    "IDs are derived from content and are STABLE across rebuilds.",
    "Refer to an entry by its ID (e.g. R-A1B2C), never by position.",
    "'RENDERS AS' is how it currently appears in the finished page.",
    "=" * 74,
    "",
]
seen = {}
for kind, body in entries:
    sid = stable_id(body)
    # Two blocks can be byte-identical (the Goal grid appears twice). Suffix
    # repeats so each occurrence is separately addressable.
    seen[sid] = seen.get(sid, 0) + 1
    if seen[sid] > 1:
        sid = f"{sid}-{seen[sid]}"
    # Locate using the first DATA row — header rows are not distinctive.
    if kind == "TABLE":
        probe = next((b for b in body[2:] if b.strip()), body[0])
    else:
        # "{" or "```" style openers are not distinctive enough to locate;
        # use the first line with real content.
        probe = next((b for b in body if len(b.strip()) >= 12), body[0])
    n = find_in_src(probe)
    where = section_of(n) if n is not None else "(unlocated)"
    loc = f"src.txt ~line {n+1}" if n is not None else "src.txt line unknown"
    lines_out.append(f"{sid}   RENDERS AS: {kind}")
    lines_out.append(f"        {loc}  |  in: {where[:64]}")
    for b in body[:10]:
        lines_out.append("        " + b[:96])
    if len(body) > 10:
        lines_out.append(f"        ... ({len(body)-10} more lines)")
    lines_out.append("")

OUT.write_text("\n".join(lines_out), encoding="utf-8")
print(f"review.txt: {len(entries)} entries "
      f"({sum(1 for k,_ in entries if k=='TABLE')} tables, "
      f"{sum(1 for k,_ in entries if k=='CODE BLOCK')} code blocks)")

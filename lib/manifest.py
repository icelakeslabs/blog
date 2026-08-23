#!/usr/bin/env python3
"""
Build/refresh images/manifest.csv, which maps each image slot in the draft to
a real file in images/.

- Scans images/ for actual files and matches them against the filename hint
  parsed from each "=-=" annotation (case-insensitive, extension-agnostic).
- PRESERVES anything already in the your_file column — your edits are never
  overwritten, only blank rows get auto-filled.
- Leaves your_file blank when nothing matches, so you can fill it in by hand.

Run via ./build.sh, or on its own after adding files to images/.
"""
import csv, re, pathlib

SRC = pathlib.Path("src.txt")
IMGDIR = pathlib.Path("images")
MANIFEST = IMGDIR / "manifest.csv"
EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".PNG", ".JPG"}

IMGDIR.mkdir(exist_ok=True)

# existing choices, so we never clobber manual entries
existing = {}
if MANIFEST.exists():
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("your_file", "").strip():
                existing[row["slot"]] = row["your_file"].strip()

# Drop preserved entries whose file is no longer in images/ — a manifest
# pointing at a deleted file is worse than a blank one.

on_disk = [p.name for p in IMGDIR.iterdir()
           if p.is_file() and p.suffix in EXTS]
lower = {n.lower(): n for n in on_disk}

# Entries naming a file that is not (yet) in images/ are KEPT and reported.
# Deleting them would silently destroy hand-typed values — e.g. a name entered
# before the file was copied in, or a typo you would rather see than lose.
missing = sorted(k for k, v in existing.items() if v not in on_disk)
if missing:
    print("manifest: WARNING — assigned file not found in images/ for: "
          + ", ".join(f"{k} -> {existing[k]}" for k in missing))

def match(hint):
    """Find a real file for a hint, ignoring case and extension."""
    if not hint:
        return ""
    for h in hint.split(";"):
        h = h.strip().lower()
        if not h:
            continue
        stem = h.rsplit(".", 1)[0]
        for name_l, name in lower.items():
            if name_l.rsplit(".", 1)[0] == stem:
                return name
        for name_l, name in lower.items():       # looser: substring
            if stem and stem in name_l:
                return name
    return ""

rows, n = [], 0
for i, line in enumerate(SRC.read_text(encoding="utf-8").split("\n")):
    s = line.strip()
    if s.startswith("=-=") and "hyperlink" not in s.lower():
        n += 1
        slot = f"IMG-{n:02d}"
        body = s[3:].strip()
        hint = ";".join(re.findall(r"[0-9]{8}[_A-Za-z0-9]*|MAX485_[A-Za-z]+", body))
        chosen = existing.get(slot) or match(hint)
        rows.append([slot, i + 1, body, hint, chosen])

with MANIFEST.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["slot", "src_line", "annotation", "filename_hint", "your_file"])
    w.writerows(rows)

if missing:
    pathlib.Path("images-missing.txt").write_text(
        "Assigned in manifest.csv but NOT present in images/:\n\n"
        + "\n".join(f"{k}  ->  {existing[k]}" for k in missing) + "\n",
        encoding="utf-8")
else:
    pathlib.Path("images-missing.txt").write_text(
        "Every assigned file is present in images/.\n", encoding="utf-8")

filled = sum(1 for r in rows if r[4])
print(f"manifest: {len(rows)} slots, {filled} matched to files in images/, "
      f"{len(rows)-filled} still unassigned")

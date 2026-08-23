#!/usr/bin/env bash
# Scaffold a new blog post so you never copy a directory by hand.
# Creates posts/YYYY-MM-DD-slug/ with a template src.txt, meta.txt, and images/.
#
# Usage:
#   ./new-post.sh "My Post Title"              # dated today
#   ./new-post.sh "My Post Title" 2026-09-01   # explicit date
#
# Then: edit src.txt, drop figures in images/, run  ./build.sh <slug>,
# and flip meta.txt  draft: true -> false  when ready to publish.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TITLE="${1:-}"
if [ -z "$TITLE" ]; then
  echo "usage: ./new-post.sh \"Post Title\" [YYYY-MM-DD]" >&2
  exit 1
fi
DATE="${2:-$(date +%F)}"
echo "$DATE" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' || {
  echo "error: date must be YYYY-MM-DD (got '$DATE')" >&2; exit 1; }

# slug: lowercase, runs of non-alphanumerics -> single dash, trim dashes
SLUG="$(printf '%s' "$TITLE" | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
[ -n "$SLUG" ] || { echo "error: could not derive a slug from the title" >&2; exit 1; }

DIR="$ROOT/posts/$DATE-$SLUG"
[ -e "$DIR" ] && { echo "error: already exists: posts/$DATE-$SLUG" >&2; exit 1; }

mkdir -p "$DIR/images"
: > "$DIR/images/.gitkeep"   # keep the empty dir in git until images land

cat > "$DIR/src.txt" <<EOF
$TITLE

Or - a subtitle (this is line 3; edit it or delete the line)

1. First Section
----------------

Write your post here. See ../../README.md for the markup conventions:
headings, *bold*, /i italic/i, /m monospace/m, tables, 4-space code blocks,
lists, and  =-= <filename or description>  to place an image from images/.
EOF

cat > "$DIR/meta.txt" <<EOF
# Post metadata. Date and slug come from the directory name (YYYY-MM-DD-slug).
# Title and subtitle are read from the first and third lines of src.txt.
summary: One-sentence summary for the landing page and RSS feed.
tags: tag1, tag2
draft: true
EOF

echo "created posts/$DATE-$SLUG/"
echo "  next: edit its src.txt, add images/, then  ./build.sh $SLUG"
echo "  it stays hidden (draft: true) until you set draft: false in meta.txt"
cat <<'REMINDER'

  ── BEFORE YOU PUBLISH IMAGES ── (this repo is public; git history is forever)
  1. ./strip-exif.sh <slug>   removes metadata you CANNOT see (GPS, camera, serial)
  2. LOOK AT EVERY SCREENSHOT  for what IS visible, then ./redact.sh to black it out:
       device serial numbers   app/site names (often your street)
       Wi-Fi SSID             account email      street address
       QR codes               browser URL bars / hostnames
     An identifier usually appears in MORE THAN ONE screenshot — check them all,
     and scroll the whole image, not just the title bar.
  Do this BEFORE the first commit: redacting later leaves the original in history.
REMINDER

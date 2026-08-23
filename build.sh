#!/usr/bin/env bash
# Build the whole blog: every post under posts/, then the landing page + feed.
# Usage: ./build.sh            build everything
#        ./build.sh <slug>     build just one post (substring match)
set -euo pipefail

LIB="$(cd "$(dirname "$0")/lib" && pwd)"
ROOT="$(cd "$(dirname "$0")" && pwd)"
FILTER="${1:-}"

for dir in "$ROOT"/posts/*/; do
  name="$(basename "$dir")"
  [ -f "$dir/src.txt" ] || continue
  if [ -n "$FILTER" ] && [[ "$name" != *"$FILTER"* ]]; then continue; fi

  echo "=== $name ==="
  (
    cd "$dir"
    python3 "$LIB/manifest.py"
    python3 "$LIB/convert.py"

    pandoc post.md \
      --from=markdown+smart+pipe_tables+strikeout+header_attributes \
      --to=html5 \
      --standalone --wrap=none \
      --toc --toc-depth=2 \
      --css=../../style.css \
      --variable pagetitle="$(head -1 src.txt)" \
      --output=index.html

    python3 "$LIB/postprocess.py"
    python3 "$LIB/audit.py"
  )
done

python3 "$LIB/index_gen.py"

# Passive privacy guard: catch images that never went through strip-exif.sh.
# Only sees METADATA — it cannot tell whether a serial is legible in the pixels.
# That half is your eyes plus ./redact.sh; see README "Before publishing images".
if command -v exiftool >/dev/null 2>&1; then
  dirty="$(exiftool -q -r -ext jpg -ext jpeg -ext png -ext gif \
    -if '$GPSLatitude or $GPSLongitude or $Make or $Model or $SerialNumber' \
    -p '$FilePath' "$ROOT"/posts/*/images/ 2>/dev/null || true)"
  if [ -n "$dirty" ]; then
    echo "WARNING — these images still carry GPS/camera metadata; run ./strip-exif.sh:" >&2
    echo "$dirty" >&2
  fi
fi

echo "built."

#!/usr/bin/env bash
# Strip identifying metadata (GPS, camera make/model, serial, timestamps) from
# every image under posts/*/images/ BEFORE publishing. Phone photos embed your
# home GPS location and device info in EXIF — publishing them leaks it. Screen-
# shots usually don't, but this is cheap insurance. Orientation is preserved so
# photos don't rotate.
#
# Usage:  ./strip-exif.sh            # all posts
#         ./strip-exif.sh <slug>     # one post (substring match on its dir name)
#
# Requires exiftool:
#   macOS:  brew install exiftool
#   Debian: apt-get install libimage-exiftool-perl
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
FILTER="${1:-}"

if ! command -v exiftool >/dev/null 2>&1; then
  echo "error: exiftool not found. Install it:  brew install exiftool" >&2
  exit 1
fi

targets=()
for d in "$ROOT"/posts/*/images/; do
  [ -d "$d" ] || continue
  post="$(basename "$(dirname "$d")")"
  if [ -n "$FILTER" ] && [[ "$post" != *"$FILTER"* ]]; then continue; fi
  targets+=("$d")
done
[ ${#targets[@]} -gt 0 ] || { echo "no image directories matched"; exit 0; }

echo "stripping metadata (Orientation kept) in:"
printf '  %s\n' "${targets[@]}"
exiftool -q -overwrite_original -all= -tagsFromFile @ -Orientation \
  -r -ext jpg -ext jpeg -ext png -ext gif "${targets[@]}"

echo "=== verify: any GPS / camera identity remaining? ==="
leftovers="$(exiftool -q -r -ext jpg -ext jpeg -ext png -ext gif \
  -if '$GPSLatitude or $GPSLongitude or $Make or $Model or $SerialNumber' \
  -p '$FilePath' "${targets[@]}" 2>/dev/null || true)"
if [ -n "$leftovers" ]; then
  echo "WARNING — these still carry identifying tags:" >&2
  echo "$leftovers" >&2
  exit 1
fi
echo "clean — no GPS/Make/Model/Serial remain."

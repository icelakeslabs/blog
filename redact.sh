#!/usr/bin/env bash
# Black out regions of an image, permanently, then re-strip its metadata.
#
# WHY THIS EXISTS: strip-exif.sh removes metadata you cannot see. It does NOT
# touch what is VISIBLE IN THE PIXELS — a device serial in a screenshot, the
# site name in an app's title bar, a Wi-Fi SSID, an account email. Publishing a
# screenshot leaks whatever is legible in it. This is the tool for that half.
#
# Usage:
#   ./redact.sh <image> <x1,y1,x2,y2> [<x1,y1,x2,y2> ...]
#
# Example (two regions in one pass):
#   ./redact.sh posts/2026-08-19-solar-charging/images/wc.png \
#       430,270,770,325  190,522,625,580
#
# Coordinates are pixels in the ORIGINAL image, top-left origin. To find them:
#   identify -format '%wx%h\n' <image>              # full size
#   convert <image> -crop 1206x140+0+220 +repage /tmp/band.png   # inspect a band
# then measure within that band and add the crop's +y offset back.
#
# The fill is opaque and the file is re-encoded, so the original pixels are
# GONE — not covered by a layer someone can peel off, and no embedded thumbnail
# of the original survives (exiftool -all= runs afterward).
#
# Requires: ImageMagick (convert), exiftool.
set -euo pipefail

IMG="${1:-}"
shift || true
if [ -z "$IMG" ] || [ $# -eq 0 ]; then
  sed -n '4,18p' "$0" >&2
  echo >&2
  echo "usage: ./redact.sh <image> <x1,y1,x2,y2> [...]" >&2
  exit 1
fi
[ -f "$IMG" ] || { echo "error: no such file: $IMG" >&2; exit 1; }
command -v convert  >/dev/null 2>&1 || { echo "error: ImageMagick not found (apt-get install imagemagick / brew install imagemagick)" >&2; exit 1; }
command -v exiftool >/dev/null 2>&1 || { echo "error: exiftool not found (apt-get install libimage-exiftool-perl / brew install exiftool)" >&2; exit 1; }

args=()
for box in "$@"; do
  IFS=, read -r x1 y1 x2 y2 <<< "$box"
  for v in "$x1" "$y1" "$x2" "$y2"; do
    echo "$v" | grep -Eq '^[0-9]+$' || {
      echo "error: bad region '$box' — want x1,y1,x2,y2 as integers" >&2; exit 1; }
  done
  [ "$x2" -gt "$x1" ] && [ "$y2" -gt "$y1" ] || {
    echo "error: bad region '$box' — need x2>x1 and y2>y1" >&2; exit 1; }
  args+=(-draw "rectangle $x1,$y1 $x2,$y2")
  echo "  blacking out ${x1},${y1} -> ${x2},${y2}"
done

TMP="$(mktemp "${TMPDIR:-/tmp}/redact.XXXXXX")"
trap 'rm -f "$TMP"' EXIT
convert "$IMG" -fill black "${args[@]}" "${IMG##*.}:$TMP"
cp "$TMP" "$IMG"

# ImageMagick writes fresh metadata on save — strip it again, or the redacted
# file ships with new EXIF even though the pre-redaction file was clean.
exiftool -q -overwrite_original -all= -tagsFromFile @ -Orientation "$IMG"

echo "redacted: $IMG"
echo "VERIFY BY EYE before committing — a box in the wrong place hides nothing:"
echo "  open '$IMG'    (or crop the band and look at it)"

#!/bin/bash
# render_demos.sh - render every SNES demo song with a given Furnace build
# and write SHA-256 hashes of the output, so two builds can be compared.
#
# usage: render_demos.sh <furnace executable> <output dir>
# then:  diff <dirA>/hashes.txt <dirB>/hashes.txt

set -u
FURNACE="$1"
OUT="$2"
DEMOS="$(cd "$(dirname "$0")/../../demos/snes" && pwd)"

mkdir -p "$OUT"
: > "$OUT/hashes.txt"
for f in "$DEMOS"/*.fur; do
  name="$(basename "$f" .fur)"
  "$FURNACE" -loglevel error --output "$OUT/$name.wav" "$f" > /dev/null 2>&1
  if [ -f "$OUT/$name.wav" ]; then
    echo "$(sha256sum "$OUT/$name.wav" | cut -d' ' -f1)  $name" >> "$OUT/hashes.txt"
  else
    echo "RENDER-FAILED  $name" >> "$OUT/hashes.txt"
  fi
done
cat "$OUT/hashes.txt"

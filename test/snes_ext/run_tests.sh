#!/bin/bash
# run_tests.sh - tests for the SNES extended sample memory mode.
#
# usage: run_tests.sh <new furnace executable> [<baseline furnace executable>]
#
# - renders generated songs with 320/600 distinct samples (~5.8MB/~10.8MB of BRR)
#   with extendedMem on, and checks every row plays its own sample.
# - with a baseline executable (built from the commit before this feature),
#   also checks that every demo in demos/snes and the 320-sample song with the
#   flag OFF render byte-for-byte the same as the baseline.
#
# needs python3 with numpy. output goes to ./snes_ext_out.
# note: each Furnace run writes to its normal log/config folder.

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
NEW="$1"
BASE="${2:-}"
OUT="snes_ext_out"
FAIL=0
mkdir -p "$OUT"

render() {
  "$1" -loglevel error --output "$2" "$3" > /dev/null 2>&1
}

python3 "$HERE/make_test_song.py" --ext "$OUT/test320_on.fur" || exit 1
python3 "$HERE/make_test_song.py" --ext --echo "$OUT/test320_on_echo.fur" || exit 1
python3 "$HERE/make_test_song.py" --ext --count 600 "$OUT/test600_on.fur" || exit 1
python3 "$HERE/make_test_song.py" "$OUT/test320_off.fur" || exit 1

for t in test320_on test320_on_echo; do
  echo "== $t"
  render "$NEW" "$OUT/$t.wav" "$OUT/$t.fur"
  python3 "$HERE/check_mapping.py" "$OUT/$t.wav" || FAIL=1
done
echo "== test600_on"
render "$NEW" "$OUT/test600_on.wav" "$OUT/test600_on.fur"
python3 "$HERE/check_mapping.py" --count 600 "$OUT/test600_on.wav" || FAIL=1

echo "== unaligned loop (37-137), flag ON"
python3 "$HERE/make_test_song.py" --loop-test --ext "$OUT/loop_on.fur" > /dev/null || exit 1
render "$NEW" "$OUT/loop_on.wav" "$OUT/loop_on.fur"
python3 "$HERE/check_loop.py" --max-db -35 "$OUT/loop_on.wav" || FAIL=1
echo "== unaligned loop (37-137), flag OFF (expected to be distorted)"
python3 "$HERE/make_test_song.py" --loop-test "$OUT/loop_off.fur" > /dev/null || exit 1
render "$NEW" "$OUT/loop_off.wav" "$OUT/loop_off.fur"
python3 "$HERE/check_loop.py" "$OUT/loop_off.wav"
if [ -n "$BASE" ]; then
  render "$BASE" "$OUT/loop_off_base.wav" "$OUT/loop_off.fur"
  if cmp -s "$OUT/loop_off.wav" "$OUT/loop_off_base.wav"; then
    echo "identical to baseline"
  else
    echo "DIFFERENT from baseline"; FAIL=1
  fi
fi

if [ -n "$BASE" ]; then
  echo "== flag OFF: 320-sample song vs baseline"
  render "$NEW" "$OUT/test320_off_new.wav" "$OUT/test320_off.fur"
  render "$BASE" "$OUT/test320_off_base.wav" "$OUT/test320_off.fur"
  if cmp -s "$OUT/test320_off_new.wav" "$OUT/test320_off_base.wav"; then
    echo "identical"
  else
    echo "DIFFERENT"; FAIL=1
  fi
  echo "== flag OFF: demos/snes vs baseline"
  bash "$HERE/render_demos.sh" "$BASE" "$OUT/demos_base" > /dev/null
  bash "$HERE/render_demos.sh" "$NEW" "$OUT/demos_new" > /dev/null
  if diff "$OUT/demos_base/hashes.txt" "$OUT/demos_new/hashes.txt"; then
    echo "all $(wc -l < "$OUT/demos_new/hashes.txt") demos identical"
  else
    FAIL=1
  fi
fi

if [ $FAIL -ne 0 ]; then
  echo "FAILED"
  exit 1
fi
echo "all tests passed"

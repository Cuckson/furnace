#!/usr/bin/env python3
# check_mapping.py - verify a render of a make_test_song.py song.
#
# row N of the song plays sample N, a sine at 300+20*N Hz, for 0.25 seconds.
# for each row this finds the strongest frequency and maps it back to a
# sample number. a row is "silent" if its RMS is negligible.
#
# usage: check_mapping.py <render.wav> [--count N] [--expect-loaded K]
#   --expect-loaded K: expect rows 0..K-1 to match and the rest to NOT play
#                      their own sample (silence or garbage; flag OFF behaviour)
#                      (default: expect every row to match)

import argparse
import sys
import wave

import numpy as np

ROW_TIME = 0.25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--count", type=int, default=320)
    ap.add_argument("--expect-loaded", type=int, default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    with wave.open(args.wav, "rb") as w:
        rate = w.getframerate()
        chans = w.getnchannels()
        width = w.getsampwidth()
        frames = w.readframes(w.getnframes())
    if width != 2:
        sys.exit("expected 16-bit WAV")
    data = np.frombuffer(frames, dtype="<i2").astype(np.float64).reshape(-1, chans).mean(axis=1)

    expect = args.count if args.expect_loaded is None else args.expect_loaded
    matched = 0
    silent = 0
    wrong = []
    first_silent = None
    for n in range(args.count):
        a = int((n * ROW_TIME + 0.05) * rate)
        b = int((n * ROW_TIME + 0.20) * rate)
        seg = data[a:b]
        if len(seg) < (b - a):
            wrong.append((n, "past end of render"))
            continue
        rms = float(np.sqrt(np.mean(seg * seg)))
        if rms < 50.0:
            silent += 1
            if first_silent is None:
                first_silent = n
            got = None
        else:
            win = seg * np.hanning(len(seg))
            pad = 1 << 16
            spec = np.abs(np.fft.rfft(win, pad))
            peak = int(np.argmax(spec[1:])) + 1
            freq = peak * rate / pad
            got = int(round((freq - 300.0) / 20.0))
        ok_expected = (got == n) if n < expect else (got != n)
        if got == n:
            matched += 1
        if not ok_expected:
            wrong.append((n, got))
        if args.verbose:
            print("row %3d: rms %8.1f -> %s" % (n, rms, got))

    print("rows: %d, matched: %d, silent: %d, first silent row: %s" % (
        args.count, matched, silent, first_silent))
    if wrong:
        print("UNEXPECTED rows (row, detected sample): %s" % wrong[:20])
        sys.exit(1)
    print("OK: rows 0-%d play the correct sample%s" % (
        expect - 1, "" if expect == args.count else ", rows %d-%d do not" % (expect, args.count - 1)))


if __name__ == "__main__":
    main()

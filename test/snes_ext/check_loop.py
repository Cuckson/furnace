#!/usr/bin/env python3
# check_loop.py - measure how clean a looped sine is in a render of
# make_test_song.py --loop-test (a 320Hz sine whose loop isn't aligned to 16).
#
# prints THD+N: the share of energy outside the fundamental, in dB.
# a cleanly looped sine is far below -30dB; a broken loop (wrong period,
# phase jumps) is much higher.
#
# usage: check_loop.py <render.wav> [--max-db D]

import argparse
import sys
import wave

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--max-db", type=float, default=None, help="fail if THD+N is above this")
    args = ap.parse_args()

    with wave.open(args.wav, "rb") as w:
        rate = w.getframerate()
        chans = w.getnchannels()
        frames = w.readframes(w.getnframes())
    data = np.frombuffer(frames, dtype="<i2").astype(np.float64).reshape(-1, chans).mean(axis=1)
    seg = data[int(0.25 * rate):int(1.75 * rate)]
    seg = seg - seg.mean()
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    freqs = np.fft.rfftfreq(len(seg), 1.0 / rate)
    peak = freqs[int(np.argmax(spec))]
    fund = spec[(freqs > peak - 10) & (freqs < peak + 10)].sum()
    total = spec.sum()
    thdn = 10.0 * np.log10(max(total - fund, 1e-12) / total)
    print("peak %.1f Hz, THD+N %.1f dB" % (peak, thdn))
    if args.max_db is not None and thdn > args.max_db:
        print("FAIL: above %.1f dB" % args.max_db)
        sys.exit(1)


if __name__ == "__main__":
    main()

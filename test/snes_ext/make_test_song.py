#!/usr/bin/env python3
# make_test_song.py - generate a SNES .fur with many distinct samples
# used to test the SNES "extended sample memory" mode.
#
# each sample N is a 1-second sine at freq(N) Hz (16-bit, 32000Hz).
# the song plays sample 0, 1, 2, ... one per row (0.25s per row) on channel 1.
# samples are reached through instrument note maps (180 notes per instrument),
# because a song may have at most 256 instruments.
#
# usage: make_test_song.py <out.fur> [--count N] [--ext]

import argparse
import math
import struct

RATE = 32000
SAMPLE_LEN = RATE  # 1 second
NOTE_C4 = 108  # 0 is C-(-5), 60 is C-0
ROW_SPEED = 15  # ticks per row at 60Hz -> 0.25s per row
PAT_LEN = 64
NOTES_PER_INS = 120
VERSION = 256
CHANS = 8


def freq_of(n):
    return 300.0 + 20.0 * n


def cstr(s):
    return s.encode("utf-8") + b"\0"


class Block:
    def __init__(self, magic):
        self.magic = magic
        self.data = bytearray()

    def c(self, v):
        self.data += struct.pack("<B", v & 0xff)

    def s(self, v):
        self.data += struct.pack("<H", v & 0xffff)

    def i(self, v):
        self.data += struct.pack("<I", v & 0xffffffff)

    def f(self, v):
        self.data += struct.pack("<f", v)

    def str(self, v):
        self.data += cstr(v)

    def raw(self, b):
        self.data += b

    def bytes(self):
        return self.magic + struct.pack("<I", len(self.data)) + bytes(self.data)


def make_sample(n, length=SAMPLE_LEN, freq=None, loop=None):
    f = freq_of(n) if freq is None else freq
    b = Block(b"SMP2")
    b.str("sine %d (%.0fHz)" % (n, f))
    b.i(length)
    b.i(RATE)  # compat rate
    b.i(RATE)  # C-4 rate
    b.c(16)  # 16-bit PCM
    b.c(0)  # loop direction
    b.c(0)  # flags
    b.c(0)  # flags 2
    b.i(-1 if loop is None else loop[0])  # loop start
    b.i(-1 if loop is None else loop[1])  # loop end
    for _ in range(4):
        b.i(0xffffffff)
    pcm = bytearray()
    for k in range(length):
        pcm += struct.pack("<h", int(round(16000.0 * math.sin(2.0 * math.pi * f * k / RATE))))
    b.raw(bytes(pcm))
    return b.bytes()


def make_instrument(index, base, count):
    b = Block(b"INS2")
    b.s(VERSION)
    b.s(29)  # SNES
    name = cstr("samples %d-%d" % (base, base + count - 1))
    b.raw(b"NA" + struct.pack("<H", len(name)) + name)
    sm = bytearray()
    sm += struct.pack("<h", base)
    sm += struct.pack("<B", 3)  # use sample + use sample map
    sm += struct.pack("<B", 0)
    for note in range(180):
        if note < count:
            sm += struct.pack("<hh", NOTE_C4, base + note)
        else:
            sm += struct.pack("<hh", NOTE_C4, -1)
    b.raw(b"SM" + struct.pack("<H", len(sm)) + bytes(sm))
    b.raw(b"EN")
    return b.bytes()


def make_subsong(order_len):
    b = Block(b"SNG2")
    b.f(60.0)
    b.c(1)  # arp speed
    b.c(1)  # effect divider
    b.s(PAT_LEN)
    b.s(order_len)
    b.c(4)
    b.c(16)
    b.s(150)
    b.s(150)
    b.c(1)
    for k in range(16):
        b.s(ROW_SPEED if k == 0 else 0)
    b.str("")
    b.str("")
    for ch in range(CHANS):
        for o in range(order_len):
            b.c(o if ch == 0 else 0)
    for ch in range(CHANS):
        b.c(1)
    for ch in range(CHANS):
        b.c(3)
    for ch in range(CHANS):
        b.c(0)
    for ch in range(CHANS):
        b.str("")
    for ch in range(CHANS):
        b.str("")
    for ch in range(CHANS):
        b.i(0)
    return b.bytes()


def make_pattern(index, rows):
    # rows: list of (note, ins) or None, length PAT_LEN; last pattern gets FF00 after the last note
    b = Block(b"PATN")
    b.c(0)  # subsong
    b.c(0)  # channel
    b.s(index)
    b.str("")
    for r in rows:
        if r is None:
            b.c(0)  # skip 1 row
            continue
        note, ins, stop = r
        mask = 1 | 2
        if stop:
            mask |= 8 | 16
        b.c(mask)
        b.c(note)
        b.c(ins)
        if stop:
            b.c(0xff)
            b.c(0)
    b.c(0xff)
    return b.bytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--count", type=int, default=320)
    ap.add_argument("--ext", action="store_true", help="enable extended sample memory flag")
    ap.add_argument("--echo", action="store_true", help="enable echo on channel 1 at maximum delay")
    ap.add_argument("--loop-test", action="store_true",
                    help="instead: one looped 320Hz sine whose loop (37-137) isn't aligned to 16, held for 2 seconds")
    args = ap.parse_args()
    count = 1 if args.loop_test else args.count
    hold = 8 if args.loop_test else 1

    ins_count = (count + NOTES_PER_INS - 1) // NOTES_PER_INS
    # one row per sample, plus one final row that holds the stop effect
    total_rows = count * hold + 1
    order_len = (total_rows + PAT_LEN - 1) // PAT_LEN

    rows = []
    for n in range(count):
        rows.append((n % NOTES_PER_INS, n // NOTES_PER_INS, False))
        rows += [None] * (hold - 1)
    # final row: retrigger nothing, just stop
    rows.append(None)
    while len(rows) < order_len * PAT_LEN:
        rows.append(None)

    blocks = []  # (element type, bytes)
    blocks.append((1, make_subsong(order_len)))
    flags = "extendedMem=true\n" if args.ext else ""
    if args.echo:
        flags += "echo=true\nechoDelay=15\nechoMask=1\nechoFeedback=32\nechoVolL=40\nechoVolR=40\n"
    fb = Block(b"FLAG")
    fb.str(flags)
    blocks.append((2, fb.bytes()))
    for k in range(ins_count):
        base = k * NOTES_PER_INS
        blocks.append((4, make_instrument(k, base, min(NOTES_PER_INS, count - base))))
    for n in range(count):
        if args.loop_test:
            blocks.append((6, make_sample(n, length=137, freq=320.0, loop=(37, 137))))
        else:
            blocks.append((6, make_sample(n)))
    for p in range(order_len):
        pr = rows[p * PAT_LEN:(p + 1) * PAT_LEN]
        # place the stop effect on the row after the last note
        stop_row = count * hold
        if p * PAT_LEN <= stop_row < (p + 1) * PAT_LEN:
            pr = list(pr)
            pr[stop_row - p * PAT_LEN] = "STOP"
        out_rows = []
        for r in pr:
            if r == "STOP":
                out_rows.append((180, 0, True))  # note off + FF00
            else:
                out_rows.append(r)
        blocks.append((7, make_pattern(p, out_rows)))

    # info block layout: we need element pointers, so lay out sizes first
    elem_types = []
    for t, _ in blocks:
        if t not in elem_types:
            elem_types.append(t)

    def info_block(ptrs):
        b = Block(b"INF2")
        b.str("SNES ext test (%d samples)" % count)
        b.str("make_test_song.py")
        for _ in range(6):
            b.str("")
        b.f(440.0)
        b.c(0)  # auto system name
        b.f(1.0)
        b.s(CHANS)
        b.s(1)
        b.s(0x87)
        b.s(CHANS)
        b.f(1.0)
        b.f(0.0)
        b.f(0.0)
        b.i(0)  # patchbay connections
        b.c(1)  # auto patchbay
        for t in elem_types:
            lst = ptrs.get(t, [])
            b.c(t)
            b.i(len(lst))
            for p in lst:
                b.i(p)
        b.c(0)
        return b.bytes()

    header_len = 32
    dummy = {t: [0] * sum(1 for tt, _ in blocks if tt == t) for t in elem_types}
    info_len = len(info_block(dummy))
    pos = header_len + info_len
    ptrs = {t: [] for t in elem_types}
    for t, data in blocks:
        ptrs[t].append(pos)
        pos += len(data)
    info = info_block(ptrs)
    assert len(info) == info_len

    header = b"-Furnace module-" + struct.pack("<HHI", VERSION, 0, header_len) + b"\0" * 8
    with open(args.out, "wb") as f:
        f.write(header)
        f.write(info)
        for _, data in blocks:
            f.write(data)
    total_pcm = count * SAMPLE_LEN
    print("wrote %s: %d samples, %d instruments, %d patterns, ~%d bytes of BRR" % (
        args.out, count, ins_count, order_len, total_pcm // 16 * 9))


if __name__ == "__main__":
    main()

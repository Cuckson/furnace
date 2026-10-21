# SNES extended sample memory tests

tests for the SNES `extendedMem` chip flag ("Extended sample memory (not hardware-accurate)").

- `make_test_song.py`: writes a SNES .fur with N distinct samples. sample N is a 1-second sine at 300+20×N Hz. row N of the song plays sample N for 0.25 seconds. samples are reached through instrument sample maps, because a song can have at most 256 instruments.
- `check_mapping.py`: finds the strongest frequency in each row of a render and checks it matches that row's sample.
- `render_demos.sh`: renders every song in `demos/snes` and writes SHA-256 hashes, so two builds can be compared.
- `run_tests.sh`: runs all of the above.

```
bash test/snes_ext/run_tests.sh path/to/new/furnace.exe path/to/baseline/furnace.exe
```

the baseline is a build of the commit before this feature. it is used to check that with the flag off, rendered audio is byte-for-byte the same.

with the flag off, a song with more sample data than fits in 64KB keeps the original behaviour: "out of BRR memory for sample N!" is logged, and samples that didn't fit play garbage from address 0.

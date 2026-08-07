#!/usr/bin/env python3
"""
test_filter_on_stills.py -- try a filter chain on a handful of frames before
committing to a full video render.

A full render (even chunked) takes minutes. Testing a filter chain change on
a still frame takes about a second. Always iterate here first: tweak the
filter chain file, rerun this script, look at the output frames, repeat.
Only run render_graded.py once the stills look right across every kind of
shot in the footage (bright/dark, skin tones, any near-white surfaces,
anything you flagged as a possible color cast).

Usage:
    python3 test_filter_on_stills.py INPUT.mp4 FILTER_CHAIN.txt \\
        --times 1 8 22 29 43 64 --outdir ./_stills_test

    If --times is omitted, it samples 8 evenly-spaced points across the video.

For each timestamp this saves both the original and the graded frame so you
can flip between them (original_<t>.jpg / graded_<t>.jpg).
"""
import argparse
import subprocess
from pathlib import Path


def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("filter_chain_file")
    ap.add_argument("--times", type=float, nargs="*", default=None,
                     help="timestamps in seconds to sample (default: 8 evenly spaced)")
    ap.add_argument("--outdir", default="./_stills_test")
    args = ap.parse_args()

    video = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    filter_chain = Path(args.filter_chain_file).read_text().strip()

    times = args.times
    if not times:
        duration = ffprobe_duration(video)
        n = 8
        times = [round(duration * (i + 0.5) / n, 2) for i in range(n)]

    for t in times:
        orig = outdir / f"original_{t:07.2f}.jpg"
        graded = outdir / f"graded_{t:07.2f}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(video),
                         "-frames:v", "1", "-q:v", "2", str(orig)], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(orig),
                         "-vf", filter_chain, "-q:v", "2", str(graded)], check=True)
        print(f"t={t:.2f}s -> {orig}  |  {graded}")

    print(f"\n{len(times)} pairs saved to {outdir}/ -- view both original_* and graded_* for each timestamp.")
    print("Look specifically for: skin tone accuracy, whether near-white/gray surfaces stayed")
    print("neutral, whether shadows still have detail, and whether any flat/graphic frame")
    print("(see analyze_footage.py output) picked up banding or blocky artifacts.")


if __name__ == "__main__":
    main()

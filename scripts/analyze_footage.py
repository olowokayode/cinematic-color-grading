#!/usr/bin/env python3
"""
analyze_footage.py -- diagnostic pass over a video, BEFORE you write any grade.

Why this exists: guessing a color grade from memory or from a single frame
is how you end up amplifying problems you didn't know were there (a color
cast that only shows up on near-white surfaces, a "flat" title card that
looks fine until you push contrast on it). This script gives you numbers
and sample frames to look at first.

Usage:
    python3 analyze_footage.py INPUT.mp4 [--interval 2] [--outdir ./_analysis]

What it does:
  1. Prints an ffprobe technical summary (resolution, fps, codec, color tags,
     duration, has-audio).
  2. Extracts a frame every `--interval` seconds across the whole timeline.
  3. For each frame computes:
       - mean luma (overall brightness, 0-255)
       - a spatial-detail score (std of luma across the frame) -- very low
         values mean a flat/graphic frame (title card, solid color, smooth
         gradient), which should usually get little or NO photographic grade
       - per-channel means (R,G,B) -- lets you spot a global color cast
         directly from numbers instead of eyeballing it
  4. Flags likely non-photographic frames (titles, logo cards, pure
     black/white) so you don't blindly apply the same grade everywhere.
  5. Saves every sampled frame as a JPEG in the output directory so you can
     `view` them and actually look before deciding anything.

This does NOT modify your video. It's read-only diagnostics.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def ffprobe_json(path):
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def extract_frame(video, t, out_path):
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(video),
        "-frames:v", "1", "-q:v", "2", str(out_path),
    ]
    subprocess.run(cmd, check=True)


def frame_stats(path):
    from PIL import Image
    import numpy as np

    img = Image.open(path).convert("RGB")
    arr = np.array(img).astype(float)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return {
        "mean_luma": round(float(luma.mean()), 1),
        "luma_std": round(float(luma.std()), 1),
        "mean_r": round(float(r.mean()), 1),
        "mean_g": round(float(g.mean()), 1),
        "mean_b": round(float(b.mean()), 1),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--interval", type=float, default=2.0, help="seconds between sampled frames (default 2)")
    ap.add_argument("--outdir", default="./_analysis", help="where to save sampled frames + report")
    args = ap.parse_args()

    video = Path(args.video)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    probe = ffprobe_json(video)
    vstream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    astreams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
    duration = float(probe["format"]["duration"])

    print("=== Technical summary ===")
    print(f"file:        {video}")
    print(f"duration:    {duration:.2f}s")
    print(f"resolution:  {vstream.get('width')}x{vstream.get('height')}")
    print(f"fps:         {vstream.get('r_frame_rate')}")
    print(f"codec:       {vstream.get('codec_name')}")
    print(f"pix_fmt:     {vstream.get('pix_fmt')}")
    print(f"color tags:  primaries={vstream.get('color_primaries')} "
          f"trc={vstream.get('color_transfer')} space={vstream.get('color_space')}")
    print(f"has audio:   {'yes (' + astreams[0]['codec_name'] + ')' if astreams else 'no'}")
    print()

    # Main pass at the requested interval, plus a denser pass over the first
    # and last few seconds. Title cards, logo stings, and transitions are
    # usually short (1-3s) and sit right at the start or end -- a coarse
    # interval can jump clean over them (ask me how I know). Stay a hair
    # short of the true duration so we never seek past the last frame.
    safe_end = max(0.0, duration - 0.05)
    sample_times = set()
    t = 0.0
    while t < safe_end:
        sample_times.add(round(t, 2))
        t += args.interval

    edge_window = min(3.0, duration / 3)
    t = 0.0
    while t < min(edge_window, safe_end):
        sample_times.add(round(t, 2))
        t += 0.5
    t = max(0.0, safe_end - edge_window)
    while t < safe_end:
        sample_times.add(round(t, 2))
        t += 0.5

    # Merge near-duplicates that can happen where the dense edge pass
    # overlaps the main interval (common on short clips) -- no need to
    # extract essentially the same frame twice.
    merged_times = []
    for t in sorted(sample_times):
        if merged_times and t - merged_times[-1] < 0.2:
            continue
        merged_times.append(t)

    print(f"=== Sampling every {args.interval}s (+ a denser pass over the first/last "
          f"{edge_window:.1f}s where titles/logos usually live) ===")
    rows = []
    for t in merged_times:
        fname = outdir / f"t_{t:07.2f}.jpg"
        try:
            extract_frame(video, t, fname)
            stats = frame_stats(fname)
            stats["t"] = round(t, 2)
            stats["file"] = str(fname)
            rows.append(stats)
        except Exception as e:
            print(f"  [skip] t={t:.2f}s: {e}", file=sys.stderr)

    print(f"{'t(s)':>7} {'luma':>6} {'detail':>7} {'R':>6} {'G':>6} {'B':>6}  flag")
    for row in rows:
        is_flat = row["luma_std"] < 12
        flag = "<- flat/graphic? (title card, solid color, smooth gradient)" if is_flat else ""
        cast = max(row["mean_r"], row["mean_g"], row["mean_b"]) - min(row["mean_r"], row["mean_g"], row["mean_b"])
        # Only call out "cast" on frames that look photographic (some spatial
        # detail) -- a flagged flat/graphic frame is often an intentionally
        # colorful design element, not a white-balance problem to fix.
        if not is_flat and cast > 15 and row["mean_luma"] > 20:
            flag += f"  channel spread {cast:.0f} -- possible color cast (sample a believed-neutral area with check_neutral_patch.py to confirm)"
        print(f"{row['t']:>7.2f} {row['mean_luma']:>6.1f} {row['luma_std']:>7.1f} "
              f"{row['mean_r']:>6.1f} {row['mean_g']:>6.1f} {row['mean_b']:>6.1f}  {flag}")

    report_path = outdir / "report.json"
    report_path.write_text(json.dumps({
        "video": str(video),
        "duration": duration,
        "resolution": [vstream.get("width"), vstream.get("height")],
        "fps": vstream.get("r_frame_rate"),
        "has_audio": bool(astreams),
        "samples": rows,
    }, indent=2))

    flat_regions = [r["t"] for r in rows if r["luma_std"] < 12]
    print()
    print(f"Sampled frames saved to: {outdir}/")
    print(f"Full report saved to:    {report_path}")
    if flat_regions:
        print()
        print("NOTE: frames at these timestamps look flat/low-detail (possible title cards,")
        print("logo cards, transitions, or solid backgrounds). Look at them before deciding")
        print("whether to grade them the same as the rest of the footage -- pushing contrast")
        print("or saturation on a flat graphic can reveal ugly compression/banding artifacts")
        print("that are invisible at low contrast. See references/grading_pitfalls.md.")
        print("Timestamps:", ", ".join(f"{t:.1f}s" for t in flat_regions))


if __name__ == "__main__":
    main()

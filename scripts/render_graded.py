#!/usr/bin/env python3
"""
render_graded.py -- apply an ffmpeg color-grade filter chain to a video
safely in a sandboxed/tool-limited environment, then stitch it back together.

WHY THIS EXISTS
A single ffmpeg command encoding a heavy filter chain (curves, colorbalance,
selectivecolor, vibrance, deband, unsharp, noise...) at good quality over a
full-length clip can easily take longer than one command is allowed to run.
Backgrounding the process with `&` does not help either, because in many
sandboxed tool environments a background process is killed the moment the
command that launched it returns. The fix is boring but reliable: render in
short chunks (each comfortably inside the time limit), concatenate them
losslessly, then remux the original audio back in.

WHY --graded-range EXISTS
Title cards, logo stings, and other graphic (non-photographic) elements
often live at the very start or end of a video. Pushing a photographic
contrast/saturation grade onto a flat design graphic can drag hidden
compression artifacts (chroma-subsampling blocking, gradient banding) out
into plain sight -- see references/grading_pitfalls.md for a worked example.
Run analyze_footage.py first; if it flags a flat/graphic region, exclude it
here rather than grading it and hoping for the best.

USAGE
    python3 render_graded.py INPUT.mp4 FILTER_CHAIN.txt OUTPUT.mp4 \\
        [--preset veryfast] [--crf 16] [--chunk-seconds 11] \\
        [--graded-start 0] [--graded-end END] \\
        [--workdir ./_grade_work] [--keep-work]

    FILTER_CHAIN.txt contains a single line: an ffmpeg -vf filter chain
    string (e.g. what you built and tested with test_filter_on_stills.py).

    --graded-start / --graded-end restrict the grade to a time window (in
    seconds). Footage outside that window is re-encoded with the same
    codec settings but NO filter, so it stitches back together cleanly
    without picking up the creative grade. Default is the whole video.

EXAMPLE
    python3 render_graded.py my_video.mp4 my_grade.txt my_video_GRADED.mp4 \\
        --graded-end 65.0
    (grades everything up to 65s, leaves the last few seconds -- a logo
    card, say -- untouched)

After it finishes, it prints QC frame paths at every chunk boundary plus a
handful of points across the timeline. Look at those before calling it done
-- especially the boundary frames, to make sure there's no visible seam.
"""
import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def has_audio(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return bool(out.stdout.strip())


def build_segments(duration, graded_start, graded_end, chunk_seconds):
    """Return a list of (start, end, graded: bool) covering [0, duration)."""
    cut_points = sorted(set([0.0, duration]) | {
        p for p in (graded_start, graded_end) if 0.0 < p < duration
    })
    ranges = list(zip(cut_points[:-1], cut_points[1:]))

    segments = []
    for seg_start, seg_end in ranges:
        graded = seg_start >= graded_start - 1e-6 and seg_end <= graded_end + 1e-6
        span = seg_end - seg_start
        if span <= chunk_seconds:
            segments.append((seg_start, seg_end, graded))
            continue
        n = max(1, round(span / chunk_seconds))
        step = span / n
        t = seg_start
        for i in range(n):
            nxt = seg_end if i == n - 1 else t + step
            segments.append((t, nxt, graded))
            t = nxt
    return segments


def render_segment(input_video, start, end, graded, filter_chain, preset, crf, out_path):
    duration = end - start
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", str(input_video)]
    if duration > 0:
        cmd += ["-t", f"{duration:.3f}"]
    if graded:
        cmd += ["-vf", filter_chain]
    else:
        cmd += ["-vf", "format=yuv420p"]
    cmd += [
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-an", str(out_path),
    ]
    t0 = time.time()
    run(cmd)
    elapsed = time.time() - t0
    return elapsed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("filter_chain_file", help="text file containing one line: the -vf filter chain")
    ap.add_argument("output")
    ap.add_argument("--preset", default="veryfast", help="x264 preset (default veryfast -- see notes below)")
    ap.add_argument("--crf", type=int, default=16, help="x264 CRF, lower = higher quality (default 16)")
    ap.add_argument("--chunk-seconds", type=float, default=11.0,
                     help="max length of any single ffmpeg render call (default 11s; tune down "
                          "if your environment's timeout is tighter, up if you've confirmed it's roomier)")
    ap.add_argument("--graded-start", type=float, default=0.0)
    ap.add_argument("--graded-end", type=float, default=None,
                     help="default: end of video (grade everything)")
    ap.add_argument("--workdir", default="./_grade_work")
    ap.add_argument("--keep-work", action="store_true", help="don't delete the chunk/work directory when done")
    args = ap.parse_args()

    input_video = Path(args.input)
    output = Path(args.output)
    filter_chain = Path(args.filter_chain_file).read_text().strip()
    if not filter_chain:
        print("error: filter chain file is empty", file=sys.stderr)
        sys.exit(1)

    workdir = Path(args.workdir)
    chunks_dir = workdir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    duration = ffprobe_duration(input_video)
    graded_end = args.graded_end if args.graded_end is not None else duration
    audio_present = has_audio(input_video)

    print(f"input duration: {duration:.3f}s   grading window: "
          f"[{args.graded_start:.2f}s, {graded_end:.2f}s]   audio: {'yes' if audio_present else 'no'}")

    segments = build_segments(duration, args.graded_start, graded_end, args.chunk_seconds)
    print(f"rendering {len(segments)} segment(s):")
    for i, (s, e, g) in enumerate(segments):
        print(f"  [{i}] {s:.3f}s - {e:.3f}s  ({'GRADED' if g else 'ungraded passthrough'}, {e - s:.2f}s)")

    chunk_paths = []
    total_start = time.time()
    for i, (s, e, g) in enumerate(segments):
        out_path = chunks_dir / f"c{i:03d}.mp4"
        elapsed = render_segment(input_video, s, e, g, filter_chain, args.preset, args.crf, out_path)
        print(f"  [{i}] done in {elapsed:.0f}s -> {out_path}")
        chunk_paths.append(out_path)
    print(f"all segments rendered in {time.time() - total_start:.0f}s total")

    concat_list = workdir / "concat_list.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in chunk_paths))
    concat_video = workdir / "concat_video.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(concat_list), "-c", "copy", str(concat_video)])

    if audio_present:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(concat_video), "-i", str(input_video),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
             "-movflags", "+faststart", str(output)])
    else:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(concat_video),
             "-c", "copy", "-movflags", "+faststart", str(output)])

    out_duration = ffprobe_duration(output)
    print(f"\noutput: {output}  ({out_duration:.3f}s, input was {duration:.3f}s)")
    if abs(out_duration - duration) > 0.5:
        print("WARNING: output duration differs from input by more than 0.5s -- check for a dropped/duplicated segment.")

    # QC frames: right around every internal seam, plus a handful spread across the timeline.
    qc_dir = workdir / "qc"
    qc_dir.mkdir(exist_ok=True)
    seam_times = sorted({round(e, 2) for (_, e, _) in segments[:-1]})
    spread_times = [round(duration * f, 2) for f in (0.05, 0.25, 0.5, 0.75, 0.95)]
    qc_times = sorted(set(seam_times + spread_times))
    print(f"\nQC frames (check these before calling it done -- seams especially):")
    for t in qc_times:
        for offset, label in ((-0.08, "before"), (0.08, "after")):
            tt = max(0.0, min(out_duration - 0.02, t + offset))
            fname = qc_dir / f"seam_{t:07.2f}_{label}.jpg"
            try:
                run(["ffmpeg", "-y", "-v", "error", "-ss", f"{tt:.3f}", "-i", str(output),
                     "-frames:v", "1", "-q:v", "2", str(fname)])
                print(f"  {fname}")
            except subprocess.CalledProcessError:
                pass

    if not args.keep_work:
        # keep the qc frames, drop the (large) intermediate chunk files
        import shutil
        shutil.rmtree(chunks_dir, ignore_errors=True)
        concat_video.unlink(missing_ok=True)
        print(f"\n(intermediate chunks cleaned up; QC frames kept in {qc_dir})")


if __name__ == "__main__":
    main()

# Cinematic Color Grading

Command-line video color grading powered by `ffmpeg`. Turns flat, hazy,
washed-out, or low-contrast footage into a rich, cinematic grade — while
keeping skin tones natural and title cards/logos clean. No NLE, no GUI, no
paid plugins: four Python scripts wrapping tuned `ffmpeg` filter chains.

It was built by actually grading a short film start to finish, hitting real
problems along the way (a color cast that made things worse the more it was
corrected, a logo card that fell apart under saturation, renders that got
killed by execution-time limits in a sandboxed environment) and fixing each
one. Those fixes are baked into the scripts and written up in
[`references/grading_pitfalls.md`](references/grading_pitfalls.md) so you
don't have to rediscover them.

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Script reference](#script-reference)
  - [`analyze_footage.py`](#analyze_footagepy)
  - [`check_neutral_patch.py`](#check_neutral_patchpy)
  - [`test_filter_on_stills.py`](#test_filter_on_stillspy)
  - [`render_graded.py`](#render_gradedpy)
- [The base filter chain](#the-base-filter-chain)
- [Grading a new video, end to end](#grading-a-new-video-end-to-end)
- [Tuning tips](#tuning-tips)
- [Common pitfalls](#common-pitfalls)
- [Project structure](#project-structure)
- [Notes for CI and long-running environments](#notes-for-ci-and-long-running-environments)
- [License](#license)

## Requirements

- `ffmpeg` and `ffprobe` on your `PATH` (version 6.x+ recommended — the
  filter chain uses `selectivecolor`, `vibrance`, `deband`, and `chromanr`,
  which are all standard in recent ffmpeg builds but worth confirming with
  `ffmpeg -filters | grep -E "vibrance|selectivecolor|deband|chromanr"`)
- Python 3.8+
- `Pillow` and `numpy` (used by the analysis/QC scripts, not by rendering
  itself — rendering is pure `ffmpeg`)

## Installation

```bash
git clone <this-repo-url> cinematic-color-grading
cd cinematic-color-grading
pip install pillow numpy   # add --break-system-packages if your distro requires it

# sanity check
ffmpeg -version
python3 scripts/analyze_footage.py -h
```

Nothing needs to be "installed" beyond that — every script is run directly
with `python3 scripts/<name>.py`.

## Quick start

```bash
# 1. Look at the footage before touching it
python3 scripts/analyze_footage.py my_video.mp4 --outdir ./_analysis

# 2. Copy the starting filter chain and tune it (see "Tuning tips" below)
cp assets/base_grade_chain.txt my_grade.txt

# 3. Iterate fast on stills, not full renders
python3 scripts/test_filter_on_stills.py my_video.mp4 my_grade.txt \
  --times 5 20 45 90 --outdir ./_stills_test

# 4. Render the full video once the stills look right
python3 scripts/render_graded.py my_video.mp4 my_grade.txt my_video_GRADED.mp4

# 5. Check the QC frames it prints out, especially the seams
```

That's the whole loop. The rest of this document explains each step in
more depth.

## How it works

1. **Diagnose first.** `analyze_footage.py` samples the video at regular
   intervals (plus a denser pass at the very start/end, where titles and
   logos usually live) and reports brightness, spatial detail, and RGB
   channel means per sample — flagging likely graphic/title frames and
   possible color casts automatically, with numbers instead of guesses.
2. **Quantify any color cast.** `check_neutral_patch.py` samples a region
   you believe should be neutral (paper, sky, a wall) and tells you exactly
   which channel is elevated and by how much.
3. **Build the grade.** Start from `assets/base_grade_chain.txt` — a tuned
   `ffmpeg` filter chain covering white-balance neutralization, a filmic
   contrast curve, subtle split-toning, skin/hair warmth, smart saturation,
   and a debanding/chroma-smoothing safety net — and retune the numbers
   against what step 1 showed you.
4. **Iterate on stills.** `test_filter_on_stills.py` applies your filter
   chain to a handful of frames in about a second each, so you can tune
   without waiting on a full render.
5. **Render safely.** `render_graded.py` renders the graded video in short,
   time-boxed chunks, concatenates them losslessly, and remuxes the
   original audio back in untouched. It also supports excluding a time
   range from the grade entirely (`--graded-start`/`--graded-end`), for
   title cards and logo stings that shouldn't get a photographic grade.
6. **QC before you call it done.** Every internal seam (chunk boundary,
   graded/ungraded boundary) gets a before/after frame pair automatically,
   plus a handful of frames spread across the timeline.

## Script reference

### `analyze_footage.py`

Read-only diagnostics. Doesn't touch your video.

```bash
python3 scripts/analyze_footage.py INPUT.mp4 [--interval SECONDS] [--outdir DIR]
```

| Flag | Default | Description |
|---|---|---|
| `--interval` | `2.0` | Seconds between sampled frames across the main timeline. |
| `--outdir` | `./_analysis` | Where sampled frames and `report.json` are saved. |

Always also samples a denser pass (every 0.5s) over the first/last few
seconds of the video, since short title/logo segments can fall entirely
between two samples of a coarse interval otherwise.

Output: a printed table (timestamp, mean luma, a spatial-detail score, R/G/B
means, and flags), a `report.json` with the same data, and every sampled
frame saved as a JPEG for you to `view`/open directly.

### `check_neutral_patch.py`

```bash
python3 scripts/check_neutral_patch.py FRAME.jpg --box X Y W H
```

`X Y` is the top-left corner of a rectangle (in pixel coordinates) you
believe should be neutral gray/white; `W H` is its size. Prints the patch's
mean R/G/B, the deltas needed to neutralize it, and a starting
`colorbalance` correction. Re-check a patch on your *graded* output too —
later filters in the chain (especially contrast curves) will shift the
balance again.

### `test_filter_on_stills.py`

```bash
python3 scripts/test_filter_on_stills.py INPUT.mp4 FILTER_CHAIN.txt \
  [--times T1 T2 ...] [--outdir DIR]
```

| Flag | Default | Description |
|---|---|---|
| `--times` | 8 points evenly spread across the video | Timestamps (seconds) to sample. Pick ones covering every distinct lighting situation in the footage. |
| `--outdir` | `./_stills_test` | Where `original_<t>.jpg` / `graded_<t>.jpg` pairs are saved. |

`FILTER_CHAIN.txt` is a plain text file containing a single line: an
`ffmpeg -vf` filter chain string.

### `render_graded.py`

```bash
python3 scripts/render_graded.py INPUT.mp4 FILTER_CHAIN.txt OUTPUT.mp4 [options]
```

| Flag | Default | Description |
|---|---|---|
| `--preset` | `veryfast` | x264 encoder preset. Quality at a fixed CRF is fairly preset-independent for normal footage; go slower only if you've confirmed your environment tolerates the extra time (see [pitfalls #3](references/grading_pitfalls.md) for a case where a *slower* preset made an artifact worse, not better — that was a real-signal issue, not an encoder shortcut, so don't reach for `slow` as a default fix). |
| `--crf` | `16` | x264 quality (lower = higher quality/bigger file). |
| `--chunk-seconds` | `11.0` | Max length of any single render call. Lower this if your environment's command-timeout is tighter; raise it if you've confirmed it's roomier (see [below](#notes-for-ci-and-long-running-environments)). |
| `--graded-start` | `0.0` | Start of the time range (seconds) to apply the grade to. |
| `--graded-end` | end of video | End of the grade window. Footage outside `[--graded-start, --graded-end]` is re-encoded with the same codec settings but no filter — for title cards/logos that shouldn't get a photographic grade. |
| `--workdir` | `./_grade_work` | Scratch directory for chunks and QC frames. |
| `--keep-work` | off | Keep intermediate per-chunk files (large) instead of deleting them after the final concat. QC frames are always kept regardless. |

Prints per-segment render time as it goes, then a QC frame pair
(`<workdir>/qc/seam_<t>_before.jpg` / `_after.jpg`) for every internal cut
point plus five points spread across the whole timeline. **Look at these
before treating the output as final** — especially the seams.

## The base filter chain

`assets/base_grade_chain.txt` is one `ffmpeg -vf` chain, applied in this
order (order matters — see
[pitfalls #1](references/grading_pitfalls.md)):

1. **`chromanr`** — chroma-only smoothing. A safety net against
   chroma-subsampling block artifacts becoming visible later in the chain,
   particularly on large flat/gradient areas.
2. **`selectivecolor` (whites/neutrals)** — neutralizes a color cast on
   near-white/gray surfaces specifically, without touching skin.
3. **`curves` (master)** — filmic contrast S-curve: deepens the black
   point, adds midtone contrast, softens the highlight rolloff.
4. **`colorbalance`** — a subtle creative split-tone (cool shadows, warm
   mid/highlights), applied *after* the base cast is already neutral.
5. **`selectivecolor` (reds/yellows)** — targeted skin/hair warmth.
6. **`eq`** — a little extra contrast/gamma/brightness on top of the curve.
7. **`vibrance`** — saturation that protects skin tones by design, instead
   of a blanket saturation boost.
8. **`deband`** — removes gradient banding introduced by the stack of
   curve/level operations above.
9. **`unsharp`** — very mild clarity, not sharpening in the halo-inducing
   sense.
10. **`noise`** — a very light temporal grain for texture.

This is a **starting point, not a universal constant.** Every source has a
different cast and exposure; retune the numbers per video using
`analyze_footage.py` and `check_neutral_patch.py` rather than reusing the
values unchanged.

## Grading a new video, end to end

```bash
# Step 1: diagnose
python3 scripts/analyze_footage.py my_video.mp4 --interval 3 --outdir ./_analysis
# -> read the printed table, view a few _analysis/t_*.jpg frames covering
#    the brightest/darkest/most-skin-heavy moments, note any flagged
#    flat/graphic timestamps

# (optional) quantify a suspected cast
python3 scripts/check_neutral_patch.py _analysis/t_0032.00.jpg --box 400 100 300 150

# Step 2: build your grade from the template
cp assets/base_grade_chain.txt my_grade.txt
# edit my_grade.txt based on what step 1 showed you

# Step 3: iterate on stills until every lighting situation looks right
python3 scripts/test_filter_on_stills.py my_video.mp4 my_grade.txt \
  --times 3 30 60 90 120 --outdir ./_stills_test
# -> view original_*/graded_* pairs, edit my_grade.txt, repeat

# Step 4: render, excluding any title/logo range you found in step 1
python3 scripts/render_graded.py my_video.mp4 my_grade.txt my_video_GRADED.mp4 \
  --graded-start 0 --graded-end 118.5

# Step 5: QC
# -> view every _grade_work/qc/seam_*.jpg pair printed at the end
```

## Tuning tips

- **Fix white balance before contrast.** Contrast curves amplify whatever
  channel imbalance already exists. Get the cast close to neutral first,
  then add contrast on top of a balanced image — not the other way around.
- **Use `selectivecolor` for whites/neutrals, `colorbalance` for creative
  split-tone.** A blanket `colorbalance` shift can't satisfy "make this
  white surface neutral" and "keep this skin tone warm" at the same time if
  they fall in the same tonal range — hue-selective correction can.
- **Don't grade graphics like photography.** Logo cards and transitions can
  hide chroma-subsampling artifacts that only become visible once you push
  contrast/saturation. If `analyze_footage.py` flags a segment as
  flat/graphic, look at it before assuming it needs the same treatment as
  the rest of the footage — often the right answer is `--graded-end` right
  before it starts.
- **Test on every distinct lighting situation**, not just one flattering
  frame — a grade that looks great on a bright exterior can crush a dim
  interior shot in the same video.

Full detail and worked examples: [`references/grading_pitfalls.md`](references/grading_pitfalls.md).

For the creative side — what a finished grade should actually look and feel
like, independent of the ffmpeg mechanics — see
[`references/colorist_principles.md`](references/colorist_principles.md).
Worth a read-through as a checklist after your stills look technically
clean but before you render the full video.

## Common pitfalls

The short version (full write-up in
[`references/grading_pitfalls.md`](references/grading_pitfalls.md)):

| Symptom | Likely cause | Fix |
|---|---|---|
| Grading a white/gray surface also tints skin an odd color | Blanket `colorbalance` shift applied to fix a cast | Use `selectivecolor` targeting `whites`/`neutrals` instead |
| A cast gets *worse* after adding contrast | Curves amplify existing per-channel imbalance | Neutralize white balance before applying the contrast curve, not after |
| Blocky/banded artifacts on a logo card or gradient, invisible in the original | Contrast/saturation dragging out chroma-subsampling or gradient-banding that was sub-visible before grading | Exclude that range with `--graded-end`/`--graded-start`, or add `chromanr`+`deband` and re-test — don't just crank the encoder preset, that can make it worse |
| A long render gets killed partway through | Single command exceeded your environment's execution-time limit | Lower `--chunk-seconds` in `render_graded.py` |
| Output duration doesn't match input | A dropped or duplicated segment during chunked rendering | Check the warning `render_graded.py` prints, inspect `<workdir>/qc/` seam frames around each cut |

## Project structure

```
cinematic-color-grading/
├── README.md                          <- this file
├── SKILL.md                           <- Claude-skill definition (for AI coding assistants)
├── assets/
│   └── base_grade_chain.txt           <- starting ffmpeg -vf filter chain
├── references/
│   ├── grading_pitfalls.md            <- technical gotchas, worked examples
│   └── colorist_principles.md         <- creative review checklist
└── scripts/
    ├── analyze_footage.py             <- diagnostics
    ├── check_neutral_patch.py         <- quantify a color cast
    ├── test_filter_on_stills.py       <- fast filter-chain iteration
    └── render_graded.py               <- chunked, safe full-video render + QC
```

## Notes for CI and long-running environments

`render_graded.py`'s chunking exists specifically for sandboxed
environments where a single command has a wall-clock execution limit and
background processes don't survive past the command that launched them
(common in AI coding assistant sandboxes). If you're running this from a
normal CI job, a dedicated machine, or anywhere else without that
constraint, chunking is harmless but not necessary — you can pass a much
larger `--chunk-seconds` (e.g. `36000`, effectively "one chunk") to render
in a single `ffmpeg` pass, or skip the script and call `ffmpeg` directly
with the filter chain from your `.txt` file.

## License

No license file is included. Add one appropriate to your use case (e.g.
MIT) before publishing this publicly or sharing it outside your own use.

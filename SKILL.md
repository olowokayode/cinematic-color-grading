---
name: cinematic-color-grading
description: Professionally color grade video footage (.mp4/.mov) using ffmpeg -- turns flat, washed-out, hazy, or low-contrast footage into a rich, cinematic, "expensive-looking" grade while keeping skin tones natural. Use this whenever the user wants their video color graded, color corrected, made to look "cinematic"/"premium"/"professional", or asks to fix footage that looks flat, dull, gray, milky, hazy, desaturated, or washed out. Also use it if the user mentions a colorist, LUTs, white balance correction, or matching shots/scenes for consistent color. Trigger even if they just upload a video and ask you to "make it look better" or "punch it up" -- that's a color grading request. Handles long videos safely by rendering in time-boxed chunks so it doesn't get killed by execution-time limits, and knows to leave logo cards/title graphics ungraded so they don't pick up compression artifacts.
---

# Cinematic Video Color Grading

A workflow (plus scripts) for grading real footage with ffmpeg: diagnose
first, build the grade in the right order, test on stills before committing
to a full render, then render safely and QC it. This came out of actually
grading a short film start to finish, hitting real problems (a color cast
that fought itself, a logo card that fell apart under saturation, renders
that got killed by execution-time limits), and fixing each one -- the
scripts and the two reference docs encode those fixes so you don't have to
rediscover them.

## Before you start

Check ffmpeg is available: `ffmpeg -version` and `ffprobe -version`. It's
present in most sandboxed dev environments already. If it's missing, tell
the user their environment needs it installed (or check network settings if
package installation is blocked) -- don't try to grade without it.

Every script below is self-documented -- run `python3 scripts/<name>.py -h`
for the full usage if these summaries aren't enough, and read the header
docstring in the script itself for the *why*, not just the *how*.

## Step 1 -- Look at the footage before touching it

Don't guess a grade from a single glance or from memory of "what footage
usually needs." Run the diagnostic pass:

```bash
python3 scripts/analyze_footage.py INPUT.mp4 --interval 3 --outdir ./_analysis
```

This prints a technical summary (resolution, fps, codec, color tags,
duration) and a table of brightness/detail/RGB-mean stats sampled across the
whole timeline, plus flags for:
- **flat/graphic frames** -- likely title cards, logo stings, transitions.
  Note their timestamps; you'll probably want to exclude them from the
  grade later (see Step 4 and `references/grading_pitfalls.md` #3).
- **possible color cast** -- a channel spread big enough to be worth
  investigating on a photographic frame.

Then actually `view` several of the saved sample frames -- pick ones that
cover the range of lighting in the piece (brightest, darkest, any indoor
scene, any scene with a lot of skin/faces, any scene with something that
should read as pure white or gray). Numbers point you in the right
direction; your eyes make the final call.

If a frame's color cast is unclear from the numbers, sample a specific
patch you believe should be neutral (a wall, paper, overcast sky, a white
shirt):

```bash
python3 scripts/check_neutral_patch.py _analysis/t_0029.00.jpg --box 900 50 400 100
```

This reports the actual R/G/B imbalance and a starting correction, instead
of you eyeballing "does this look a bit warm."

## Step 2 -- Build the filter chain

Start from `assets/base_grade_chain.txt`. It's a working, previously-tuned
chain (selective white-balance neutralization, filmic contrast curve,
subtle split-tone, skin/hair warmth, smart saturation, deband + chroma
smoothing safety net, light clarity and grain) -- but it is a **starting
point, not a universal constant**. Every piece of footage has a different
cast and exposure; retune the numbers against what Step 1 actually showed
you, especially:
- the white-balance neutralization values (from `check_neutral_patch.py`'s
  suggestion)
- how much contrast lift the footage needs (a genuinely flat/log-like
  source needs more; footage that's merely a bit dull needs less)
- whether any scene is *deliberately* low-key/moody -- don't flatten it to
  match the rest

Read `references/grading_pitfalls.md` #1 and #2 before you start tuning --
the order you apply corrections in changes the result, and a blanket
white-balance shift can fix a white surface while breaking skin tones in
the same shot.

Iterate on stills, not full renders -- this is fast (seconds, not minutes):

```bash
python3 scripts/test_filter_on_stills.py INPUT.mp4 my_grade.txt \
  --times 1 8 22 29 43 64 --outdir ./_stills_test
```

Pick timestamps that cover every distinct lighting situation you saw in
Step 1. View the `original_*`/`graded_*` pairs. Keep adjusting
`my_grade.txt` and rerunning until every one of those stills looks right --
particularly skin tones, any near-white surface, and shadow detail.

## Step 3 -- Cross-check against the creative standard

Once the stills look technically clean, read back through
`references/colorist_principles.md` against what you're seeing. It's a
review checklist (skin tones, color separation, depth, shot matching,
restraint) for catching things that are correct but not yet *good* --
technically-neutral-but-lifeless is a common failure mode a purely
numerical process can produce.

## Step 4 -- Decide what NOT to grade

Cross-reference the flat/graphic timestamps from Step 1 against what you
saw when you viewed those frames. If any of them are logo cards, title
text, or transitions rather than photographic content, plan to exclude that
range from the grade entirely -- see `references/grading_pitfalls.md` #3
for why pushing a photographic grade onto a flat graphic tends to reveal
ugly compression artifacts that are invisible at low contrast. Note the
start/end timestamps of the range you actually want graded.

## Step 5 -- Render

```bash
python3 scripts/render_graded.py INPUT.mp4 my_grade.txt OUTPUT.mp4 \
  --graded-start 0 --graded-end 65.0
```

Omit `--graded-start`/`--graded-end` to grade the whole video. This renders
in short chunks automatically (so it survives execution-time limits common
in sandboxed tool environments), concatenates losslessly, and remuxes the
original audio back in untouched. See `references/grading_pitfalls.md` #4
if you want to understand why chunking is necessary here rather than just
running one long ffmpeg command.

If a render is taking implausibly long or the environment's time limit is
tighter than expected, lower `--chunk-seconds` (default 11) and re-run --
each individual chunk needs to comfortably finish inside one command's time
budget.

## Step 6 -- QC before calling it done

`render_graded.py` automatically extracts frame pairs immediately before
and after every internal seam (chunk boundary, and the graded/ungraded
boundary if you used one), plus a handful of frames spread across the whole
timeline, into `<workdir>/qc/`. View them. You're checking for:
- **seams**: the two sides of every cut should look identical in exposure
  and color (same scene, no jump)
- **the graded/ungraded boundary** (if used): should be visually
  unremarkable -- often placed during a fade or a cut, where a small
  difference wouldn't read as jarring anyway
- **the full-timeline spread frames**: re-run the section 19 checklist from
  `colorist_principles.md` one more time, now against the actual rendered
  output rather than test stills

Only hand the file back once every seam frame looks clean and nothing on
the checklist is flagged.

## Adapting this for different footage

This workflow was built grading a single handheld short film, but the
approach generalizes:
- **Very clean, already well-graded footage**: you may only need a light
  touch -- skip straight to a much gentler version of Step 2, or tell the
  user it doesn't need much.
- **Footage shot in wildly different lighting across scenes** (bright
  exterior intercut with a dim interior): a single global grade may not
  serve both well. Consider multiple `render_graded.py` passes with
  different filter chains for different `--graded-start`/`--graded-end`
  windows, each rendered separately and concatenated -- read
  `references/grading_pitfalls.md` #6 first.
- **Footage with no audio track**: `render_graded.py` detects this
  automatically and skips the audio remux step.
- **Very long footage** (many minutes): the chunked render will simply
  produce more chunks; nothing about the workflow changes, but consider
  raising `--chunk-seconds` if you've confirmed the environment tolerates
  longer single commands, to cut down total chunk count and re-encode
  overhead.

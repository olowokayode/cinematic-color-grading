# Grading pitfalls (learned the hard way)

These are specific, non-obvious failure modes discovered while building and
QC-ing this skill. Each one cost real iteration time to diagnose. Read this
before you start tuning a filter chain -- it'll save you the same detours.

## 1. Fix white balance BEFORE adding contrast, not after

Contrast curves amplify whatever color imbalance already exists, because
ffmpeg's `curves` filter applies the same nonlinear function to R, G, and B
independently. If a "neutral" surface starts at R=112, G=97, B=100, pushing
those three numbers through an S-curve doesn't just make the image punchier
-- it stretches the *gap* between them too, so a mild cast becomes a
noticeably worse one.

Order that works: neutralize the cast first (see #2), then apply your
contrast/creative curve on top of an already-balanced image. If you tune
white balance after the contrast curve, you're chasing a moving target --
every time you touch the curve, the cast shifts again.

## 2. Use hue-selective correction for whites/neutrals, not a blanket shift

`colorbalance` shifts a whole tonal range (shadows/midtones/highlights)
regardless of hue. The problem: a near-white surface (paper, sky, a wall)
and warm skin tone often sit in the *same* luma band. Push `colorbalance`
hard enough to neutralize the white surface, and you'll tint skin the wrong
direction (we turned a hand green trying to fix a pink-tinted passport photo
this way).

`selectivecolor` targeting the `whites` and `neutrals` ranges is
hue-aware -- it only pulls on pixels that are already close to
desaturated/neutral, so it fixes the paper without touching the skin at all.
Reserve `colorbalance` for a deliberate, gentle creative split-tone once the
base cast is already handled; use `selectivecolor reds`/`yellows` for skin
and hair warmth specifically.

Quantify before you guess: `check_neutral_patch.py` on a patch you believe
should be neutral tells you exactly which channel is off and by how much,
rather than eyeballing "does this look warm."

## 3. Graphics and title cards are not photographic footage -- don't grade them the same way

Logo cards, color-wipe transitions, lower thirds, text cards: these are
flat, often gently-animated gradients with almost no spatial detail. A
strong contrast/saturation grade that looks great on skin and asphalt can
drag out artifacts that are completely invisible at low contrast:

- **Chroma-subsampling blocking.** Video is normally stored 4:2:0 (color
  resolution is half of luma resolution). On a smooth colorful gradient,
  that coarser color sampling is usually invisible -- until you push
  saturation and contrast hard, at which point you can see the actual
  color blocks.
- **Gradient banding.** Multiple sequential curve/levels operations in 8-bit
  can turn a smooth gradient into visible steps.

How to tell which one you're looking at: check the *original* frame at the
same timestamp. If it's clean there and only shows artifacts after your
filter chain, your grade is amplifying something that was already present
but sub-visible -- not introducing new corruption. Confirm by testing at a
*stronger* encoder preset (`slow` instead of `veryfast`); if the artifact
gets *worse* with a more faithful encode, that confirms it's real signal in
the pixels being amplified, not an encoder shortcut.

Fixes, in order of preference:
1. **Best: don't grade it.** Use `render_graded.py --graded-start/--graded-end`
   to exclude the graphic segment entirely. A logo card should look like the
   designer delivered it, not like a movie still.
2. If you do need to grade it (e.g. a title card that's meant to match the
   footage's color palette), add `chromanr` (chroma-only smoothing) early in
   the chain and `deband` after the color operations, before sharpening/grain.
   This helps but doesn't always fully eliminate the artifact on
   heavily-pushed gradients -- test on the actual frame, don't assume it's fixed.
3. Never fix this by cranking the encoder preset alone (`slow`/`slower`).
   That makes it worse, not better, per the diagnostic above.

`analyze_footage.py` flags likely graphic frames automatically (very low
luma_std = very little spatial detail) so you don't have to eyeball the
whole timeline looking for them.

## 4. Long renders need chunking in tool-limited environments

A full-quality x264 encode (crf ~16, preset medium/slow) of even a one
minute clip with a heavy filter chain can take 8-12 minutes. If you're
running this from an environment where a single command has a wall-clock
limit (many agent sandboxes do), that one command will get killed partway
through -- and backgrounding it with `&` does not reliably help, because the
background process is often killed too when the launching command returns.

`render_graded.py` handles this by rendering in short chunks (default 11s,
tune `--chunk-seconds` down if your environment's limit is tighter), then
concatenating losslessly (`-c copy`, no re-encode) and remuxing the original
audio back in. If you're running this from a normal terminal/CI job with no
such limit, you can pass a much larger `--chunk-seconds` (or just don't
worry about it -- the chunking is harmless either way, just slightly less
efficient than one long encode).

## 5. Always QC at chunk seams and at every kind of shot, not just the "hero" frame

It's tempting to tune a filter chain by looking at one flattering frame,
declare victory, and render the whole thing. Two things that one frame
won't catch:

- A seam artifact at a chunk boundary (wrong timestamp math, an off-by-one
  in duration, a dropped frame). Check a frame immediately before and after
  every internal cut point -- `render_graded.py` does this automatically and
  saves the pairs to `<workdir>/qc/`.
- A grade that looks great on the shot you tuned it on but does something
  bad on a different shot (blows out a bright exterior, crushes a dark
  interior, tints a different skin tone). Test on stills from every
  *distinct* lighting situation in the footage before rendering the full
  video -- `test_filter_on_stills.py` with timestamps spread across the
  whole piece.

## 6. A single global grade is a reasonable default, not a universal law

The "grade every shot individually" ideal from professional color work is
hard to fully automate without an NLE and shot-level masking. In practice, one
well-built global filter chain, applied uniformly, works well for most
short-form footage shot in consistent conditions (same day, similar
lighting). Reach for per-segment treatment (via `--graded-start`/`--graded-end`,
or multiple `render_graded.py` passes with different filter chains stitched
together) specifically when:
- there's a graphic/title element (see #3), or
- a scene is deliberately shot in a very different lighting register (e.g.
  a low-key intimate scene intercut with bright daylight exteriors) where a
  single contrast curve will either crush the dark scene or wash out the
  bright one.

#!/usr/bin/env python3
"""
check_neutral_patch.py -- quantify a color cast instead of eyeballing it.

The fastest way to tune a white-balance correction is to sample a patch of
something that SHOULD be neutral (white paper, an overcast sky, a gray wall,
a shirt you know is white) and look at the actual R/G/B numbers. If they're
not close to equal, that gap tells you exactly which channel is elevated
and by roughly how much -- far more reliable than judging "does this look
warm or cool" by eye, especially on a screen that isn't color-calibrated.

Usage:
    python3 check_neutral_patch.py FRAME.jpg --box X Y W H

    X,Y is the top-left corner of a rectangle you believe is neutral,
    W,H is its width/height, in pixel coordinates (use an image viewer or
    just eyeball it against the frame's resolution).

Example:
    python3 check_neutral_patch.py frames/t_29.00.jpg --box 900 50 400 100

Output: the patch's mean R/G/B, which channel is highest/lowest, and a
suggested starting point for ffmpeg's `colorbalance` filter to neutralize it.
Treat the suggestion as a starting value, not gospel -- always re-check a
patch on the GRADED output afterward, because later filters in your chain
(contrast curves especially) will shift the balance again. See
references/grading_pitfalls.md for why order of operations matters here.
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--box", nargs=4, type=int, metavar=("X", "Y", "W", "H"), required=True)
    args = ap.parse_args()

    from PIL import Image
    import numpy as np

    x, y, w, h = args.box
    img = np.array(Image.open(args.image).convert("RGB")).astype(float)
    if y + h > img.shape[0] or x + w > img.shape[1]:
        print(f"warning: box goes outside the image ({img.shape[1]}x{img.shape[0]}); clamping", file=sys.stderr)
    patch = img[max(0, y):y + h, max(0, x):x + w]
    if patch.size == 0:
        print("error: box is entirely outside the image", file=sys.stderr)
        sys.exit(1)

    r, g, b = patch[..., 0].mean(), patch[..., 1].mean(), patch[..., 2].mean()
    mean = (r + g + b) / 3
    print(f"patch mean RGB: R={r:.1f}  G={g:.1f}  B={b:.1f}   (target neutral: {mean:.1f} each)")

    dr, dg, db = mean - r, mean - g, mean - b
    spread = max(r, g, b) - min(r, g, b)
    if spread < 4:
        print("This patch is already close to neutral (spread < 4). No correction needed here.")
        return

    print(f"deltas needed: R{dr:+.1f}  G{dg:+.1f}  B{db:+.1f}   (spread: {spread:.1f})")
    scale = 255.0
    print()
    print("Rough starting point for ffmpeg colorbalance (pick the tonal range this")
    print("patch's brightness falls into -- shadows ~0-85, midtones ~85-170, highlights ~170-255):")
    print(f"  midtones:  rm={dr/scale:+.3f}:gm={dg/scale:+.3f}:bm={db/scale:+.3f}")
    print()
    print("If this patch is meant to be a clean white/gray (paper, sky, wall) rather than")
    print("skin or another warm subject, selectivecolor targeting 'whites'/'neutrals' is")
    print("usually safer than a blanket colorbalance shift -- see references/grading_pitfalls.md")
    print("for why (a flat shift that fixes a white surface can tint skin the wrong way).")


if __name__ == "__main__":
    main()

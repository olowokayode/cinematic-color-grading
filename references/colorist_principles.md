# Colorist principles (creative checklist)

This is the master prompt you originally wrote, describing how a
professional colorist thinks about a grade. Keep it as the *creative*
checklist -- what to look for and what "done" should feel like. Pair it
with `grading_pitfalls.md`, which covers the *technical* traps specific to
doing this with ffmpeg in a tool-limited environment.

Use this as a review checklist after you've built a filter chain and before
you call a grade finished: read back through the numbered sections below
against your actual test stills, not from memory.

---

## Primary objective

Transform footage into an exceptionally beautiful, cinematic, expensive
looking final grade -- not a generic LUT slapped on top. Every decision
should be intentional. Preserve: natural skin tones, realistic textures,
accurate product colors, highlight detail, shadow detail, depth, consistent
exposure, and color continuity between shots. The viewer should feel the
quality of the image before consciously noticing the grade.

## 1. Analyze the footage first

Before grading, determine: camera characteristics, exposure, white balance,
dynamic range, contrast, highlight rolloff, shadow behavior, skin tones,
dominant/environmental colors, lighting direction and quality, mixed-lighting
problems, noise/compression, clipping, color casts, lens characteristics,
overall mood, and gamma/color space. Don't apply a look before you know what
the footage actually needs -- if different shots need different corrections,
grade them individually.

## 2. Build a clean technical base before the creative look

- **Exposure**: correct recoverable under/overexposure, protect highlights,
  preserve shadow detail, avoid crushed blacks unless stylistically justified.
- **White balance**: neutralize unwanted casts while preserving intentional
  environmental lighting.
- **Contrast**: strong but elegant -- avoid flat images, crushed blacks,
  harsh digital contrast, or an artificial HDR look. Aim for smooth,
  cinematic tonal separation.
- **Highlights**: smooth rolloff, not harsh/clipped/digital.
- **Shadows**: maintain detail and create depth, don't just push to black.
- **Midtones**: enough density/separation for a rich image.

## 3. Skin tones are sacred

Natural, healthy, believable, consistent. Never orange, oversaturated, red,
magenta, gray, plastic, or over-smoothed. Isolate and correct independently
if needed. Should feel dimensional, with realistic variation across
highlight/midtone/shadow on the face.

## 4. Cinematic color separation

Build relationships (skin vs. background, subject vs. environment,
highlight vs. shadow, warm vs. cool) rather than just raising saturation.
Subtle complementary relationships are fine when they genuinely improve the
image -- don't force a teal-and-orange look onto footage that doesn't call
for it.

## 5. Create depth

Tonal separation, color separation, local contrast, controlled saturation,
highlight/shadow shaping. The subject should naturally draw the eye.
Vignettes, if used at all, should be extremely subtle.

## 6. Control saturation like a colorist, not a slider

Protect skin tones, control over-saturated colors, increase color density
selectively, keep neutrals believable, let important colors stand out,
reduce distracting background color, keep whites neutral unless
intentionally stylized. Richness usually comes from better color
*relationships*, not from turning everything up.

## 7-8. Highlights and shadows should have character

Highlights: soft, controlled, organic, texture-preserving (skin, hair,
fabric, product, windows, practicals). Shadows: rich rather than crushed,
with whatever restrained color (blue/cyan/green/neutral/warm brown)
naturally complements the scene.

## 9-10. Curves and color science over effects

A refined tonal curve beats a generic LUT, heavy film filter, excessive
grain/halation/bloom, overdone teal-orange, or artificial HDR. If film
character is added, keep it subtle -- the goal is "why does this look so
good," not "that's a film filter."

## 11. Film character (if appropriate)

Gentle highlight rolloff, slightly softened digital harshness, organic tonal
compression, natural color density, very subtle grain, slight per-channel
response variation.

## 12. Shot matching

Every shot should feel like it belongs to the same production: match
exposure, white balance, contrast, skin tone, saturation, color temperature,
shadow density, and highlight behavior across cuts, unless a change is
intentional.

## 13. Subject priority

Identify the most important element in each shot and subtly guide attention
to it via exposure, contrast, color, saturation, and background control --
never so obviously that the audience notices the technique.

## 14. Product shots

Keep products color-accurate, clean, premium, legible, dimensional, and
separated from the environment. They should look better because of lighting
and grading, not because their actual color was changed.

## 15. Animals/pets (if present)

Preserve realistic fur color/texture. Don't let fur oversaturate, white fur
clip, black fur go featureless, or brown fur turn orange. Eyes should keep
natural detail and life.

## 16. Image quality

No artificial sharpness -- avoid oversharpening, haloing, crunchy textures,
excessive clarity, digital edge enhancement. Preserve existing sharpness;
improve perceived detail carefully on soft footage without making it look
processed.

## 17-18. Creative direction, scene by scene

Target feel: premium, cinematic, modern, emotional, natural, sophisticated,
expensive, immersive. Different scenes may need different treatment -- for
each one, ask what emotion it should create, what the subject is, what
colors already exist vs. should dominate/recede, where the viewer should
look, what should read warm vs. cool, and how much contrast/saturation it
actually needs.

## 19. Final quality control

Before calling it done, check the whole thing start to finish for: skin
tone consistency, exposure jumps, white-balance shifts, color contamination,
clipped highlights, crushed blacks, excessive saturation, product/fur color
accuracy, noise, **banding**, artificial sharpening, inconsistent contrast,
scene-to-scene mismatch, distracting colors, and unintentional color casts.

## 20. The standard: beautiful, not just correct

Ask: "if this were being finished for a real commercial budget, what would
a senior colorist still improve?" Then make those improvements, with
restraint -- professional grading is often about knowing what *not* to
change.

---

## Important override

Don't blindly follow a checklist if the footage demands something
different. The footage is the source of truth: make decisions based on the
actual lighting, camera response, subject, environment, and intended
emotional impact. Where "cinematic" and "natural" conflict, favor whichever
looks more sophisticated and believable. If a creative effect makes the
image look processed, don't use it.

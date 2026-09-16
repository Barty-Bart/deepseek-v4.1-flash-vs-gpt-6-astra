# Asset plan — MERIDIAN

All product imagery is generated, not recoloured. One master reference controls every shot.

## Product truth (identical in every asset)

40 mm brushed stainless-steel round case, narrow polished bezel, midnight-blue dial, silver baton
indices, two silver hands plus a fine champagne seconds hand, date window at 3 o'clock, crown at
3 o'clock, integrated three-link brushed-steel bracelet, concealed folding clasp. Hands at 10:10.
No extra crowns, no dial-marking drift, no lug-geometry drift.

## Reference plan

| ID | Purpose | Model | Ratio |
|---|---|---|---|
| `hero-identity-sheet` | front / three-quarter / side-crown / bracelet-clasp / back | gpt_image_2_5 | 1:1 |
| `hero-still-tq` | assembled hero beauty still (text-safe negative space) | nano_banana_2 | 16:9 |
| `hero-still-portrait` | assembled hero, portrait composition | nano_banana_2 | 9:16 |
| `exploded-landscape` | exploded construction axis, end-frame anchor for clip 2 | nano_banana_2 | 16:9 |
| `exploded-portrait` | exploded construction, portrait safe area | nano_banana_2 | 9:16 |
| `variant-ivory` | M01 Ivory on steel bracelet | nano_banana_2 | 4:5 |
| `variant-forest` | M01 Forest on steel bracelet | nano_banana_2 | 4:5 |
| `variant-eclipse` | M01 Eclipse, coated case + bracelet | nano_banana_2 | 4:5 |
| `variant-atelier` | M02 Atelier, cognac leather strap | nano_banana_2 | 4:5 |
| `craft-macro` | movement macro, polished gear + bridge | nano_banana_2 | 3:2 |
| `lifestyle-arcade` | worn watch, architectural city walkway | nano_banana_2 | 16:9 |

## Film plan (per aspect ratio, 4 connected clips, 6 s each = 24 s)

| Clip | Beat | Copy in frame? |
|---|---|---|
| 1 | assembled beauty, three-quarter, slow move | no (HTML overlay) |
| 2 | exploded construction along one axis | no |
| 3 | macro into gear/bridge, deliberate defocus | **no copy at all** |
| 4 | pull out of blur, wrist enters, clasp closes, wrist beauty | no (HTML overlay) |

Landscape 16:9 first, then portrait 9:16 recomposed independently. Chaining: last frame of clip N
becomes `start_image` of clip N+1. Identity references re-sent on every clip.

## Budget envelope

Estimated 250-320 credits for the full first pass (16 video clips at 6 s = 192, ~11 stills = ~25,
plus retry headroom).

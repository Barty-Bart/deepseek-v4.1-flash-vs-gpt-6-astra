# MERIDIAN — STORYBOARD

Fictional brand concept demonstration. Generated cinematic media on a scroll-controlled page; this
is not a manipulable real-time 3D model and the site does not claim that it is.

## Approved sequence — 4 beats, 4 connected clips per aspect ratio

Total generated runtime: **24 s per aspect ratio** (4 clips x 6 s), within `minimax_h3` duration
capabilities. Native scrolling drives frame position; the page never intercepts the wheel.

| Scene | Visual story | Website copy |
|---|---|---|
| 1. Assembled beauty shot | The complete closed M01 Midnight floats in a dark seamless studio, three-quarter dial view, bracelet elegantly curved. A slow controlled move catches the brushed steel. No wrist in frame. | “Every part, a purpose.” — supporting line “Mechanical craft. Made for the hours that matter.” — CTA “Explore M01” |
| 2. Exploded construction | The same watch separates cleanly along one deliberate axis into crystal, bezel, dial, hands, movement, case and back. A limited set of smaller visible gears sits within the movement layer. Parts stay recognizable and aligned; no random debris, no duplicated watches, no liquid metal. No wrist in frame. | “Considered, down to the smallest detail.” — supporting line “A complete world of precision, working as one.” |
| 3. Macro transition | The camera travels into the movement components until a selected polished gear and bridge fill the frame, then pulls focus into a soft abstract blur. The deliberate blur is the transition, not a defect. The next clip opens on the matching blurred frame and matching colour and light. | *(no copy during this beat, by design)* |
| 4. Wrist resolution | Pulling back out of the blur, the components return into the same assembled watch. A natural adult wrist and hand enter the composition; the bracelet wraps the wrist and the clasp closes visibly and plausibly. Ends on a composed wrist-worn beauty shot, correct anatomy, unchanged product design. The finished frame holds briefly before ordinary sections resume. | “Made to become part of your day.” — CTA “Find your Meridian” |

## Aspect ratio treatments

- **Desktop 16:9** — landscape clips, composition holds negative space for text overlays.
- **Mobile 9:16** — independently generated stills and clips, recomposed for portrait rather than
  cropped from the landscape footage. Exploded parts stay inside the portrait central safe area;
  the background runs to all four edges; the top third stays clear for fixed navigation; the final
  wrist composition leaves readable CTA space.

## Production rules applied

1. Dependent clips are generated in order. The selected ending frame of clip N is extracted and
   passed as the actual `start_image` of clip N+1.
2. Hero identity references are re-sent on every clip.
3. Outgoing and incoming frames are inspected together as a contact sheet before the seam is accepted.
4. Visible changes of product geometry or wrist anatomy are corrected with bounded, targeted retries
   (at most one corrective regeneration per asset).
5. The site is silent by default. No voiceover.

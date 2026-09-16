# MERIDIAN

A local fictional watch-store demonstration built from `PROMPT.md`, with React, Vite, Higgsfield product photography and native scroll-controlled cinematic media. The five-watch collection, variant selection, persistent demo bag, checkout summary and local trade-in preview are implemented. Film production and final acceptance are recorded in `ASSETS.json` and `BUILD-NOTES.md`.

The latest revision shortens the exploded/blur transitions and adds five generated wrist photographs on collection-image hover or keyboard focus. Product image paths are editable in `src/content.js`. The original card image remains visible while the supplementary image loads; touch keeps the existing one-tap detail interaction.

**The film is an unfinished cinematic study.** Both generated wrist scenes failed the required reassembly/clasp mechanics after their permitted corrective retries. The preview uses clean wrist footage and preserves the rejected attempts; it is not marked storyboard-approved.

## Run

Requires Node.js 22.12+ (built with Node 24).

```sh
npm ci
npm run dev -- --port 5174 --strictPort
```

Open **http://127.0.0.1:5174/**. The style tile is **http://127.0.0.1:5174/style-tile.html**.

```sh
npm run build
npm run preview -- --port 4174 --strictPort
npm test
```

Tests use locally installed Google Chrome through Playwright. The test runner starts the production preview on 4174 when needed. No service, database or environment secret is required.

## Edit

- `src/content.js`: product names, copy, prices, specifications, founding story and statistics.
- `src/styles.css`: responsive layouts, motion preferences and design tokens.
- `src/main.jsx`: navigation, collection, bag, product panel, trade form and footer.
- `src/Intro.jsx` and `src/sequence.js`: native scroll timeline and bounded frame transport.
- `public/media/manifest.json`: actual responsive sequence dimensions, counts, posters, timing and acceptance state.
- `public/assets/generated/`: accepted optimized Higgsfield photography; PNG originals are in `masters/`.
- `public/media/originals/`: original generated clips and documented local finishing versions.
- `scripts/watch-scene.js`: editable provisional watch model; `npm run assets` renders eight separate assets via local Chrome and the dev server on 5174. Original PNG renders stay in `public/assets/masters/`.
- `STORYBOARD.md`, `ASSET-PLAN.md`, `ASSETS.json`: approved story, generation estimates, prompts, dependencies and provenance ledger.
- `BUILD-NOTES.md`: checks, decisions, limitations and handoff.
- `artifacts/`: viewport screenshots and measured browser-test results.

Bag state uses `meridian-bag-v1` in local storage. Reset it from the bag drawer. The valuation form does not store its fields, upload its selected image, or issue network writes. Demo checkout creates a local summary and never requests payment.

## Media integration

Generation was explicitly authorized for this session. The asset ledger preserves exact prompts, job IDs, reference dependencies, inspected versions and local finishing provenance. Subsequent clips use uploaded frames extracted from the accepted preceding clip. Originals are retained alongside locally finished versions. No API keys are required to run the finished site.

The reproducible media tools are `extract-endpoints.mjs`, `compare-seam.mjs`, `media-contact-sheet.mjs`, `assemble-film.mjs` and `extract-sequence.mjs`. The extraction script preserves the original, writes versioned WebP frames and updates real counts/dimensions. It checks decodability separately from visual acceptance. The manifest enables reviewed `preview` films or fully `accepted` films; the current status is deliberately `preview`. Optional Python finishing dependencies are listed in `scripts/media-requirements.txt`.

The renderer keeps at most 13 decoded frames and three requests in flight, closes evicted ImageBitmaps, aborts obsolete work on breakpoint changes, and displays its poster beneath failed loads. Reduced motion uses a poster in ordinary flow without sequence requests. The application loads no runtime Three.js: it is used only to author the provisional static assets.

`scripts/shorten-transitions.mjs` records the one-time v1 → v2 timing edit and refuses to overwrite existing versions. The v2 MP4s are review exports from the selected WebP frames; their JSON sidecars retain every selected source-frame index. `audit-media.mjs` checks the active version without replacing its authored timing or acceptance status. Revision prompts, costs, timing measurements and browser evidence are in `docs/hover-images-v1.json` and `artifacts/repair-v3/`.

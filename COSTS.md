# DeepSeek versus Astra — costs, tokens and build times, version by version

Compiled 15 Sep 2026 from the harness run logs of each build session. Times are Melbourne local (AEST). Dollar figures are OpenRouter API spend in USD; Higgsfield credits are listed separately.

## Grand totals

| | Astra | DeepSeek |
|---|---|---|
| API spend (USD) | **$118.41** (OpenRouter account total; matches the sum of the four dedicated-key totals ($118.4112)) | **$20.03** (OpenRouter account total. The run logs only account for $18.01, so about $2.02 is the unreconciled DeepSeek watch V3 spend on the expired key) |
| Total tokens (OpenRouter account) | 58.6 million | 301 million |
| API requests (OpenRouter account) | 511 | 1,120 |
| Higgsfield credits | 339.25 (watch 148.5 + Blender 190.75) | unresolved (Blender 252 video verified + references unresolved; watch at least 222 + 46 with the full V1 total unresolved) |
| Recorded build time | 5 h 25 min | 14 h 52 min (wall clock 31 h 0 min) |
| Input tokens from run logs (cached) | 57,973,242 (55,132,675) | 290,761,212 (240,190,164) |
| Output tokens from run logs (reasoning) | 540,202 (190,930) | 1,159,538 (471,851) |

## Per-test totals

| Test | Model | Versions | Status | API USD | Higgsfield credits | Recorded time | Input tokens | Output tokens |
|---|---|---|---|---|---|---|---|---|
| 1. Age of Empires | Astra | 2 | Complete | 12.254011 (Current dedicated key total) | 0 | 46.6 min | 5,234,483 | 92,884 |
| 1. Age of Empires | DeepSeek | 3 | Complete (cost is a historical checkpoint; final balance unavailable) | 3.287446365 (Historical checkpoint; final balance unavailable) | 0 | 253.8 min | 44,172,658 | 278,646 |
| 2. Watch website (MERIDIAN) | Astra | 3 | Complete | 48.634141 (Current dedicated key total) | 148.5 (ASSETS.json ledger, matches balance decrease) | 129.7 min | 23,577,054 | 167,196 |
| 2. Watch website (MERIDIAN) | DeepSeek | 4 | Complete with remaining visual defects (clasp attachment not fully proven; portrait opening cuts to a separately generated exploded plate) | 7.739505378 known + unknown (Old key last verified $4.30766475 + replacement key $3.431840628; old-key remainder (V3) unknown) | unresolved; known pieces: at least 222 (V1 interim) + 46 (V4) | 446.5 min (wall clock 963.1 min) | 155,094,721 | 323,198 |
| 3. Booking app (Northline Barber) | Astra | 2 | Complete | 17.880175 (Current dedicated key total) | 0 | 40.7 min | 7,302,575 | 109,860 |
| 3. Booking app (Northline Barber) | DeepSeek | 2 | Complete | 2.32652778 (Current dedicated key total) | 0 | 59.5 min | 20,731,414 | 152,369 |
| 4. Blender pickup truck | Astra | 3 | Complete | 39.6428705 (Current dedicated key total) | 190.75 (video 186.75 + references 4) | 107.6 min | 21,859,130 | 170,262 |
| 4. Blender pickup truck | DeepSeek | 4 | Complete | 4.658526894 (Current dedicated key total) | 252 video (verified) + reference images unresolved | 132.4 min (wall clock 583.2 min) | 70,762,419 | 405,325 |

## Test 1 — Age of Empires

Browser real-time-strategy game (villagers, resources, buildings, enemy raids). Same PROMPT.md for both models.

### Astra — GPT-6 Astra (openai/gpt-6-astra via OpenRouter, Codex CLI, high reasoning)

Status: Complete.

| Version | What was asked | When (AEST) | Recorded time | Input tokens (cached) | Output tokens (reasoning) | API cost this version | Key total after | Higgsfield | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** Original build | Read PROMPT.md and build it. | 14 Sep 18:06 to 18:36 | 30.5 min | 2,256,248 (2,146,284) | 61,524 (11,387) | $6.8079 — Key total after V1; includes earlier connection tests and failed launch attempts. | $6.8079 | none | task_complete | `aoe-astra-iteration-1-20260914-184852` |
| **V2** Civilization ages, watchtowers, fog of war | Level up the civilization, add watchtowers, add map discovery (dark until explored, faint once explored) like Age of Empires 2. | 14 Sep 18:50 to 19:06 | 16.1 min | 2,978,235 (2,899,967) | 31,360 (11,259) | $5.4462 — Final key total minus V1 checkpoint. | $12.2540 | none | task_complete | `Age of Empires/astra (same as Versions/aoe-astra-snapshot-20260914-195139)` |
| **Total** | | | 46.6 min | 5,234,483 (5,046,251) | 92,884 (22,646) | **12.254011** (Current dedicated key total) | | 0 | | |

### DeepSeek — DeepSeek V4.1 Flash (deepseek/deepseek-v4.1-flash via OpenRouter, Codex CLI, high reasoning)

Status: Complete (cost is a historical checkpoint; final balance unavailable).

| Version | What was asked | When (AEST) | Recorded time | Input tokens (cached) | Output tokens (reasoning) | API cost this version | Key total after | Higgsfield | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** Original build | Read PROMPT.md and build it. | 14 Sep 14:42 to 16:20 | 97.1 min | 16,406,129 (13,306,752) | 164,181 (68,257) | $1.3383 — Key total after V1. Bart recalls about $0.05 of pre-build usage, so the build itself is about $1.29 (estimate). | $1.3383 | none | task_complete | `aoe-iteration-1-20260914-165354` |
| **V2** AoE2 look, farms fixed, formations, upgrades | Icons and visuals more like Age of Empires 2; add the civilization upgrade button; fix villagers not working farms; better gathering visuals; military formations; watchtowers. | 14 Sep 17:15 to 18:53 | 98.0 min | 17,058,623 (13,632,256) | 81,312 (31,209) | $1.2566 — Checkpoint read during V2 (not at its exact end): $2.5948. Increment shown is since the V1 checkpoint and is provisional. | $2.5948 | none | task_complete | `aoe-deepseek-iteration-2-20260914-185220` |
| **V3** 3D-style visuals, selection rings, fog of war, start menu | Make visuals more 3D-like; selection ring on click; dark undiscovered map, grey explored map; nicer UI with a start menu. | 14 Sep 18:53 to 19:52 | 58.8 min | 10,707,906 (8,726,400) | 33,153 (13,549) | $0.6926 — Final key total minus the mid-V2 checkpoint, so this increment also contains the tail of V2. V2 + V3 together = $1.9492. | $3.2874 | none | task_complete | `Age of Empires/deepseek (same as Versions/aoe-deepseek-v3-20260914-200651)` |
| **Total** | | | 253.8 min | 44,172,658 (35,665,408) | 278,646 (113,015) | **3.287446365** (Historical checkpoint; final balance unavailable) | | 0 | | |

## Test 2 — Watch website (MERIDIAN)

Fictional luxury watch studio site: scroll-driven film, five products, bag, trade-in form, desktop and mobile. Images and video generated through the Higgsfield MCP (paid in Higgsfield credits, separate from API dollars).

### Astra — GPT-6 Astra (openai/gpt-6-astra via OpenRouter, Codex CLI, high reasoning)

Status: Complete.

| Version | What was asked | When (AEST) | Recorded time | Input tokens (cached) | Output tokens (reasoning) | API cost this version | Key total after | Higgsfield | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** Local build, media withheld | Read PROMPT.md and build it. (The brief required a credit limit before generating; none was given, so Astra built the site with provisional local artwork and 0 credits.) | 14 Sep 18:35 to 18:56 | 21.1 min | 3,185,995 (3,034,218) | 54,027 (8,913) | unknown — No API checkpoint was saved at V1; its cost is inside the V2 figure. | unknown | 0 credits (estimated 87 for the planned batch, not submitted) | task_complete, 15 browser checks | `watch-astra-iteration-1-20260914-185912` |
| **V2** Generated media integrated | Proceed with Higgsfield MCP and generate images and videos as you see fit; seek no further approval. | 14 Sep 19:01 to 20:38 | 96.6 min | 18,650,866 (17,936,439) | 91,443 (37,014) | $39.1741 — Key total after V2. Covers V1 + V2 (V1 not separable). | $39.1741 | 138.5 credits (25 jobs: 16 image, 9 video) | task_complete, 20 browser checks; wrist reassembly/clasp beat unfinished, films labelled previews | `watch-astra-v2-20260914-225024` |
| **V3** Shorter transitions, wrist hover images | Two transition scenes linger too long, shorten them. Add a hover image per product showing the watch on a wrist. | 14 Sep 22:49 to 22:58 (stopped by OpenRouter 402 out of credits), resumed 23:15 to 23:18 | 12.0 min | 1,740,193 (1,173,534) | 21,726 (5,358) | $9.4600 — Final key total minus V2 checkpoint. | $48.6341 | 10 credits (5 images). Project total 148.5 | task_complete, 26 browser checks | `Watch website/astra (same as Versions/watch-astra-variation-2-20260914-234920)` |
| **Total** | | | 129.7 min | 23,577,054 (22,144,191) | 167,196 (51,285) | **48.634141** (Current dedicated key total) | | 148.5 (ASSETS.json ledger, matches balance decrease) | | |

### DeepSeek — DeepSeek V4.1 Flash (deepseek/deepseek-v4.1-flash via OpenRouter, Codex CLI, high reasoning)

Status: Complete with remaining visual defects (clasp attachment not fully proven; portrait opening cuts to a separately generated exploded plate).

| Version | What was asked | When (AEST) | Recorded time | Input tokens (cached) | Output tokens (reasoning) | API cost this version | Key total after | Higgsfield | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** Original build (ended in an API error) | Read PROMPT.md and build the complete watch website, desktop and mobile; make all creative decisions; give me the local preview URL. | 14 Sep 15:38 to 19:26 | 228.5 min | 33,198,789 (28,235,648) | 136,379 (21,957) | $1.8919 — Nearest checkpoint: $1.8919 read at 23:02 on 14 Sep, after V1 finished and before V2 work. Includes setup and a short aborted recovery turn. | $1.8919 | at least 222 credits (interim balance decrease read before the later video jobs; the full V1 total was never reconciled) | Turn ended with OpenRouter 413 (an image over 30 MB); site built, film heavy and choppy, collection grid uneven | `watch-deepseek-v1-20260914-194400 (rebuilt from its source for this kit; the snapshot's own dist folder was stale). Versions/watch-deepseek-recovery-20260914-230256 has identical site source, so it is not served separately` |
| **V2** Lighter film, even collection grid | Film is too heavy and choppy, fix it. Five watch cards are misplaced, fix the grid. Use existing media, no new paid generation. | 14 Sep 23:07 to 15 Sep 09:26 (recorded 102.3 min inside a 618.9 min wall-clock span) | 102.3 min (wall clock 618.9 min) | 30,765,542 (26,912,768) | 62,202 (14,037) | $2.4157 — Checkpoint after V2 minus the post-V1 checkpoint. This was the last reading on the original key. | $4.3077 | 0 new credits | task_complete; 60 fps measured, bag buttons fixed | `watch-deepseek-before-hover-20260915-113310` |
| **V3** Consistent frames, wrist hover images, centring, form | Hero frames jump (116 to 166 to 216), make the frame rate consistent. Generate wrist hover images for every watch. Centre the M01 Midnight image, the stats columns and the form. | 15 Sep 11:33 to 11:57 | 24.3 min | 16,519,147 (10,111,488) | 27,574 (5,851) | unknown — UNKNOWN. The original OpenRouter key expired (401) before this turn's spend could be read; the remainder above $4.3077 is unreconciled. | unknown | 0 new credits (wrist images derived locally from an existing frame) | task_complete | `watch-deepseek-before-final-repair-20260915-175731` |
| **V4** Final repair: pull-back, hover match, clasp | Opening does not zoom out before the exploded view, repair the motion. Wrist hover images are cut off and do not match their products (grey, brown), fix them. Clasp attaches implausibly, fix where feasible. Higgsfield authorised for targeted repairs. | 15 Sep 17:58 to 17:59 (failed, key expired), then 18:07 to 19:37 on a replacement key | 91.0 min | 74,611,243 (64,857,088) | 97,043 (20,968) | $3.4318 — Replacement key started at $0, so this is a clean per-revision figure. | $3.4318 | 46 credits (10 image, 36 video) | task_complete with two honest defects left (clasp, portrait cut) | `Watch website/deepseek (installed from DeepSeek-Astra-Final-Update). The mid-repair checkpoint collected at 18:31 is kept at Versions/watch-deepseek-provisional-mid-final-repair-20260915-183100` |
| **Total** | | | 446.5 min (wall clock 963.1 min) | 155,094,721 (130,116,992) | 323,198 (62,813) | **7.739505378 known + unknown** (Old key last verified $4.30766475 + replacement key $3.431840628; old-key remainder (V3) unknown) | | unresolved; known pieces: at least 222 (V1 interim) + 46 (V4) | | |

## Test 3 — Booking app (Northline Barber)

Local haircut appointment booking site with an admin dashboard: Flask + SQLite, customer booking and cancellation, double-booking protection. Same PROMPT.md for both models.

### Astra — GPT-6 Astra (openai/gpt-6-astra via OpenRouter, Codex CLI, high reasoning)

Status: Complete.

| Version | What was asked | When (AEST) | Recorded time | Input tokens (cached) | Output tokens (reasoning) | API cost this version | Key total after | Higgsfield | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** Original build | Read PROMPT.md and build it. Use the PORT environment variable for the local preview. | 15 Sep 14:47 to 15:04 | 16.6 min | 2,045,573 (1,948,290) | 56,177 (9,374) | $6.0797 — Key total after V1 (key started at $0). | $6.0797 | none | task_complete; independent re-run of its test suite: 65 passed | `booking-v1-20260915-165832/astra` |
| **V2** Sticky header, tap-to-open pickers, phone layout | Sticky header on desktop and mobile; clicking anywhere on a date/time field opens its picker; responsive iPhone layout with a hamburger menu; verify booking, cancellation and double-booking. | 15 Sep 16:59 to 17:09 (stopped by OpenRouter 402, credits topped up), resumed 17:58 to 18:12 | 24.1 min | 5,257,002 (4,921,385) | 53,683 (24,782) | $11.8005 — Final key total minus V1 checkpoint. | $17.8802 | none | task_complete | `Booking app/astra` |
| **Total** | | | 40.7 min | 7,302,575 (6,869,675) | 109,860 (34,156) | **17.880175** (Current dedicated key total) | | 0 | | |

### DeepSeek — DeepSeek V4.1 Flash (deepseek/deepseek-v4.1-flash via OpenRouter, Codex CLI, high reasoning)

Status: Complete.

| Version | What was asked | When (AEST) | Recorded time | Input tokens (cached) | Output tokens (reasoning) | API cost this version | Key total after | Higgsfield | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** Original build | Read PROMPT.md and build it. Use the PORT environment variable for the local preview. | 15 Sep 12:45 to 13:07 | 22.0 min | 8,997,900 (7,193,088) | 87,680 (19,390) | $0.6787 — Key total after V1 (key started at $0). | $0.6787 | none | task_complete; independent re-run of its tests: 48 passed / 3 failed (date-dependent tests), 51 passed with a fixed clock | `booking-v1-20260915-165832/deepseek` |
| **V2** Sticky header, tap-to-open pickers, phone layout | Same revision brief as Astra. | 15 Sep 16:59 to 17:36 | 37.6 min | 11,733,514 (6,632,192) | 64,689 (26,610) | $1.6478 — Final key total minus V1 checkpoint. | $2.3265 | none | task_complete | `Booking app/deepseek` |
| **Total** | | | 59.5 min | 20,731,414 (13,825,280) | 152,369 (46,000) | **2.32652778** (Current dedicated key total) | | 0 | | |

## Test 4 — Blender pickup truck

Model and rig a pickup truck in Blender with a mechanical inspection animation (suspension, drivetrain), then render it as an AI video through Higgsfield (Seedance 2.5) using reference images. Blender files and MP4s are files, not web pages.

### Astra — GPT-6 Astra (openai/gpt-6-astra via OpenRouter, Codex CLI, high reasoning)

Status: Complete.

| Version | What was asked | When (AEST) | Recorded time | Input tokens (cached) | Output tokens (reasoning) | API cost this version | Key total after | Higgsfield | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** Scene and animation built | Read PROMPT.md and build it. Save the Blender scene and animation; do not render yet. | 15 Sep 11:35 to 12:02 | 26.7 min | 2,909,908 (2,794,658) | 65,297 (26,716) | $7.6115 — Checkpoint read at 12:24; may include the first minutes of V2. | $7.6115 | none | task_complete (pickup_truck.blend, 240 frames) | `blender-astra-v1-20260915-122456` |
| **V2** Engine bay opening, extra rear-suspension hold | Before the end, hold 2 to 3 s on the rear suspension while driving; show all components moving. Start in the engine bay, pan out, close the hood, then continue. | 15 Sep 12:24 to 12:45 (stopped by OpenRouter 402 out of credits), resumed 12:46 to 12:51 | 26.1 min | 3,079,742 (2,772,324) | 61,410 (34,046) | $9.6853 — Checkpoint after V2 minus V1 checkpoint. | $17.2969 | none | task_complete (pickup_truck_v2.blend, 498 frames, 20.75 s) | `blender-astra-v2-20260915-131558` |
| **V3** Higgsfield Seedance 2.5 render | Use the Higgsfield <> Blender MCP to render the animation with Seedance 2.5, supplying two reference images (red truck, background). | 15 Sep 13:24 to 13:59 (stopped by OpenRouter 402), resumed 14:40 to 15:00 | 54.9 min | 15,869,480 (15,505,576) | 43,555 (22,081) | $22.3460 — Final key total minus V2 checkpoint. | $39.6429 | 190.75 credits (186.75 video + 4 for two reference images) | task_complete: 20.7 s 1080p H.264 clip | `Blender truck/astra (same as Versions/blender-final-renders-20260915-151604/astra)` |
| **Total** | | | 107.6 min | 21,859,130 (21,072,558) | 170,262 (82,843) | **39.6428705** (Current dedicated key total) | | 190.75 (video 186.75 + references 4) | | |

### DeepSeek — DeepSeek V4.1 Flash (deepseek/deepseek-v4.1-flash via OpenRouter, Codex CLI, high reasoning)

Status: Complete.

| Version | What was asked | When (AEST) | Recorded time | Input tokens (cached) | Output tokens (reasoning) | API cost this version | Key total after | Higgsfield | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** Scene and animation built | Read PROMPT.md and build it. | 14 Sep 20:05 to 20:32 | 26.8 min | 25,768,958 (24,333,524) | 299,782 (180,011) | $1.0440 — Key total after V1 (includes setup and retries). | $1.0440 | none | task_complete (462 objects, 240 frames, 60/60 verification checks) | `blender-deepseek-v1-20260914-231601` |
| **V2** Longer scene, 5 s undercarriage hold, axle-line view | Make it 2 to 3 times longer; stay about five seconds centred under the truck with things moving; before the end, look along the axle into the wheel with detailed suspension and drivetrain. | 14 Sep 23:17 to 15 Sep 07:39 (recorded 50.8 min inside a 501.6 min wall-clock span) | 50.8 min (wall clock 501.6 min) | 4,483,932 (3,369,472) | 45,300 (35,731) | unknown — No checkpoint at the end of V2; V2 + V3 together = $1.6810 (see V3). | unknown | none | Turn ended with a stream-disconnect network error; scene extended to 28 s | `no separate snapshot` |
| **V3** Local render plus Higgsfield reference images | Render with Seedance 2.5 in Higgsfield; first generate reference images of a red truck and outback scenery. (The Higgsfield connector was not yet loaded, so this turn rendered locally in Blender.) | 15 Sep 11:28 to 12:04 | 36.0 min | 19,329,486 (17,735,680) | 34,662 (19,762) | $1.6810 — Checkpoint after V3 minus V1 checkpoint (covers V2 + V3). | $2.7250 | 0 credits for the local render; reference-image credits unresolved | task_complete: local Blender + ffmpeg render, 19.7 min | `blender-deepseek-render-run (log only)` |
| **V4** Higgsfield Seedance 2.5 render | You are now connected to Higgsfield MCP and can use the Blender scene as discussed. Complete the task. | 15 Sep 12:59 to 13:18 | 18.8 min | 21,180,043 (15,143,808) | 25,581 (14,519) | $1.9335 — Final key total minus V3 checkpoint. | $4.6585 | 252 video credits verified; reference-image credits unresolved | task_complete: pickup_truck_seedance25_1080p.mp4 | `Blender truck/deepseek (same as Versions/blender-final-renders-20260915-151604/deepseek)` |
| **Total** | | | 132.4 min (wall clock 583.2 min) | 70,762,419 (60,582,484) | 405,325 (250,023) | **4.658526894** (Current dedicated key total) | | 252 video (verified) + reference images unresolved | | |

## How to read these numbers

- Costs are cumulative per test and model as read from each dedicated OpenRouter API key. Per-version figures are checkpoint differences, not request-level invoices, and some checkpoints were read mid-turn (noted per row).
- Input tokens include cached input; output tokens include reasoning tokens. Do not add the subsets twice.
- Time is the harness-recorded turn duration (from the user's message to the model's completion). It includes tool runs, approvals and waits, so it is not pure model inference time. Where a turn spanned a long idle gap, the wall-clock span is shown separately.
- Higgsfield media credits are separate from API dollars. The credit-to-dollar rate was never recorded, so no dollar value is given for credits.
- Several Astra turns were interrupted by OpenRouter 402 (out of credits) and resumed after a top-up; both parts are counted.
- Unknowns are shown as unknown. The DeepSeek watch website changed API keys mid-project; spend on the expired key after its last reading is unrecoverable.

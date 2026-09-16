# DeepSeek V4.1 Flash vs GPT-6 Astra

Four identical build briefs, two coding models, every final result in this repo.

Both models ran through OpenRouter inside the Codex CLI at high reasoning effort:

- **Astra** — `openai/gpt-6-astra`
- **DeepSeek** — `deepseek/deepseek-v4.1-flash`

Each model received the same `PROMPT.md`, built the first version, then got the same follow-up feedback rounds. Media (images and video) was generated through the Higgsfield MCP and is paid in Higgsfield credits, tracked separately from API dollars.

## Headline numbers

| | Astra | DeepSeek |
|---|---|---|
| API spend (OpenRouter) | $118.41 | $20.03 |
| Tokens | 58.6 million | 301 million |
| API requests | 511 | 1,120 |
| Recorded build time | 5 h 25 min | 14 h 52 min |
| Higgsfield credits | 339.25 | 298+ (not fully reconciled) |

Full version-by-version breakdown, with tokens and time per revision: [COSTS.md](COSTS.md).

## The four tests

| # | Test | Astra | DeepSeek |
|---|---|---|---|
| 1 | **Age of Empires** — browser real-time strategy game | [`Age of Empires/astra`](Age%20of%20Empires/astra) · [brief](Age%20of%20Empires/astra/PROMPT.md) | [`Age of Empires/deepseek`](Age%20of%20Empires/deepseek) · [brief](Age%20of%20Empires/deepseek/PROMPT.md) |
| 2 | **Watch website** — luxury watch studio site with AI-generated film and photos | [`Watch website/astra`](Watch%20website/astra) · [brief](Watch%20website/astra/PROMPT.md) | [`Watch website/deepseek`](Watch%20website/deepseek) · [brief](Watch%20website/deepseek/PROMPT.md) |
| 3 | **Booking app** — barber appointment booking with an admin dashboard | [`Booking app/astra`](Booking%20app/astra) · [brief](Booking%20app/astra/PROMPT.md) | [`Booking app/deepseek`](Booking%20app/deepseek) · [brief](Booking%20app/deepseek/PROMPT.md) |
| 4 | **Blender pickup truck** — rigged truck and inspection animation, rendered as AI video | [`Blender truck/astra`](Blender%20truck/astra) · [brief](Blender%20truck/astra/PROMPT.md) | [`Blender truck/deepseek`](Blender%20truck/deepseek) · [brief](Blender%20truck/deepseek/PROMPT.md) |

Each project folder is the model's final version and has its own README with run instructions.

## Running them

**Age of Empires, Astra** (Vite): `cd "Age of Empires/astra" && npm ci && npm run dev`

**Age of Empires, DeepSeek** (plain static files): `cd "Age of Empires/deepseek" && node serve.mjs`

**Watch website, Astra** (Vite + React): `cd "Watch website/astra" && npm ci && npm run dev`

**Watch website, DeepSeek** (Vite): `cd "Watch website/deepseek" && npm ci && npm run dev`

**Booking apps** (Flask + SQLite, Python 3.12): each folder has a `start.sh` that creates a virtualenv and starts the server. Seed the demo data first with the command in that folder's README. Demo admin login is `admin` with the password shown in each README.

**Blender**: open `Blender truck/astra/pickup_truck_v2.blend` or `Blender truck/deepseek/pickup_truck.blend` in Blender 5.2. The AI renders are the MP4 files under each `renders` folder.

## What is not here

Conversation transcripts, API keys, local databases, the Higgsfield generation ledgers and account details, intermediate versions, and build artifacts. The numbers in COSTS.md come from the harness run logs of each session.

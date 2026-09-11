# rdspan

Mobile-first Spanish practice using the Ranieri–Dowling method: memorize verb tables by reciting them aloud toward a scorecard target, then transcribe phrases (scriptorium). Progress is reps and completed pages — not streaks of opening the app.

v0 is **verb tables + phrase transcription**. Forms are loaded only from curated JSON. The app never asks an LLM (or any generator) for a conjugation.

## Method (what the app enforces)

**Paradigms (`verb_table`)**

`idle → preview (see + hear the table) → recite (say without looking) → scored`

A scorecard rep is counted only when the recite step **passes** (exact token match, punctuation/case ignored, accents kept). Repeat recite until `reps >= target` (default **100**) → `mastered`. Listen is acknowledgement only. Write is optional practice and does **not** add reps.

**Scriptorium (`phrase_transcription`)**

`idle → listen → say → write → done`

A page is complete only when **listen, say, and write** are all true. Listen is ack-only. Say and write must match the phrase tokens.

## Run with Podman

```sh
cp .env.example .env   # change BASIC_AUTH_PASS
podman compose up --build
```

Then open [http://localhost:8080](http://localhost:8080) and sign in with HTTP Basic (`rdspan` / `changeme` unless you changed them).

Named volumes:

- `rdspan_data` — SQLite file (`DATABASE_PATH=/data/rdspan.db`)
- `rdspan_audio` — Piper voice + pre-generated WAV/OGG

The container seeds paradigms on boot, then pre-generates audio with **Piper** (`es_ES-davefx-medium`, slightly slow `PIPER_LENGTH_SCALE=1.35`). First boot downloads the voice into `rdspan_audio` and synthesizes every cell and phrase. Later boots skip files that already exist. TTS is **never** called during a drill.

### Seed / regenerate without rebuilding

```sh
# Load curated JSON into SQLite (idempotent)
podman compose exec rdspan python -m rdspan seed

# Rebuild WAV/OGG from the current database (only missing files)
podman compose exec rdspan python -m rdspan generate-audio

# Force regenerate everything
podman compose exec rdspan python -m rdspan generate-audio --force
```

## Local (no container)

Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/). Piper needs `espeak-ng` on the host (the container image already installs it).

```sh
uv sync
export BASIC_AUTH_USER=rdspan BASIC_AUTH_PASS=changeme
export DATABASE_PATH=./var/rdspan.db AUDIO_PATH=./var/audio
uv run python -m rdspan seed
uv run python -m rdspan generate-audio   # downloads the Spanish voice on first run
uv run python -m rdspan serve            # http://127.0.0.1:8080
```

Useful env vars: `BASIC_AUTH_USER`, `BASIC_AUTH_PASS`, `DATABASE_PATH`, `AUDIO_PATH`, `SCORECARD_TARGET`, `PIPER_VOICE`, `PIPER_LENGTH_SCALE`, `HOST`, `PORT`.

## Data rules

Curated files:

- `data/paradigms.json` — regular *-ar / -er / -ir* presente + pretérito, plus irregulars **ser, estar, ir, haber, tener, hacer, decir, poder, querer, venir**. Every paradigm has `source`, `license`, `verified_at`.
- `data/phrases.json` — original scriptorium sentences, same provenance fields.

`python -m rdspan seed` copies those files into SQLite. It does not inflect verbs.

Schema lives in `migrations/` and is applied on startup.

## Tests

```sh
uv run pytest
```

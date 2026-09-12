# rdspan

Mobile-first Spanish practice using the Ranieri–Dowling method: memorize verb tables by reciting them aloud toward a scorecard target. Progress is reps — not streaks of opening the app.

v0 is **verb tables only**. Forms are loaded from curated JSON. The app never asks an LLM (or any generator) for a conjugation.

## Method (what the app enforces)

**Paradigms (`verb_table`)**

`hear → repeat → next`

Open a table, play the audio, say the six forms aloud, tap **Siguiente**. That counts one rep and opens the next table. No typing. Repeat until `reps >= target` (default **100**) → `mastered`.

Tense names on each table link to `/tiempos`, which explains every tense used in the seed.

## Run with Podman

```sh
cp .env.example .env   # change BASIC_AUTH_PASS
podman compose up --build
```

Then open [http://localhost:8080](http://localhost:8080) and sign in with HTTP Basic (`rdspan` / `changeme` unless you changed them).

If the host already has something on 8080 (`bind: address already in use`), set `RDSPAN_PORT` in `.env` (or the environment) to a free port:

```sh
RDSPAN_PORT=5783 podman compose up --build
```

Then open `http://localhost:5783`. `PORT` is inside the container (leave it at 8080); `RDSPAN_PORT` is the port on your Mac.

Named volumes:

- `rdspan_data` — SQLite file (`DATABASE_PATH=/data/rdspan.db`)

Pre-generated full-table OGG files ship in `data/audio/` (copied into the image). TTS is **not** run on boot. `generate-audio` is only for missing full tracks after you add paradigms.

### Seed / regenerate without rebuilding

```sh
# Load curated JSON into SQLite (idempotent)
podman compose exec rdspan python -m rdspan seed

# Synthesize any missing full-table OGG (downloads the Piper voice if needed)
podman compose exec rdspan python -m rdspan generate-audio
```

## Local (no container)

Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/). Piper needs `espeak-ng` on the host only if you regenerate audio.

```sh
uv sync
export BASIC_AUTH_USER=rdspan BASIC_AUTH_PASS=changeme
export DATABASE_PATH=./var/rdspan.db
uv run python -m rdspan seed
uv run python -m rdspan serve            # http://127.0.0.1:8080
```

Audio defaults to `./data/audio` (the committed OGG files). Override with `AUDIO_PATH` if needed.

Useful env vars: `BASIC_AUTH_USER`, `BASIC_AUTH_PASS`, `DATABASE_PATH`, `AUDIO_PATH`, `SCORECARD_TARGET`, `PIPER_VOICE`, `PIPER_LENGTH_SCALE`, `FULL_AUDIO_PAUSE_MS`, `HOST`, `PORT`.

## Data rules

Curated files:

- `data/paradigms.json` — finite tables from Butt, Benjamin and Moreira Rodríguez, *A New Reference Grammar of Modern Spanish*, 6th ed., chapter 16. Regular models **hablar, comer, vivir**, then every usable headword in the 16.12 irregular list (compounds and radical-changing verbs included; obsolete parenthetical defectives omitted). Each lemma has presente, imperfecto, pretérito, futuro, and condicional (indicative) plus presente and imperfecto *-ra* (subjunctive). Compound tenses, the future subjunctive, and *-se* imperfect subjunctive are omitted (predictable or obsolete). Every paradigm has `source`, `license`, `verified_at`.
- `data/lemma_en.json` — English glosses for every lemma (shown on the home list and each table). Tense names are translated in the UI (`present indicative`, and so on).
- `data/phrases.json` — empty. Scriptorium is not seeded.
- `data/audio/` — Piper OGG full-table tracks (pause between forms). Per-form clips, WAV intermediates, and voice models are not kept.

Regenerate the JSON from the authoring tables with `uv run python scripts/build_paradigms.py`. `python -m rdspan seed` copies JSON into SQLite. It does not inflect verbs.

Schema lives in `migrations/` and is applied on startup.

## Tests

```sh
uv run pytest
```

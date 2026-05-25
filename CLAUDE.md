# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this app does

Festival Match is a Flask web app that authenticates a user via Spotify OAuth, fetches their top 50 artists (medium-term), looks up genre tags for each artist via the Last.fm API, then scores every artist in `festival_lineup.csv` by how many of their Last.fm tags appear in the user's genre list. Results are rendered server-side and shown ranked by score.

## Running locally

```bash
pip install -r requirements.txt
# Set required env vars (see .env), then:
python src/app.py
```

## Deploying (Railway)

Production start command (from `railway.toml`):
```
gunicorn --chdir src app:app
```

## Required environment variables

| Variable | Purpose |
|---|---|
| `SPOTIPY_CLIENT_ID` | Spotify app client ID |
| `SPOTIPY_CLIENT_SECRET` | Spotify app client secret |
| `SPOTIPY_REDIRECT_URI` | Must match Spotify dashboard (prod: `https://festivef23-production.up.railway.app/callback`) |
| `FM_API_KEY` | Last.fm API key |
| `FLASK_SECRET_KEY` | Flask session secret |

## Architecture

**`src/app.py`** — Flask entry point. Handles Spotify OAuth flow (`/login` → `/callback`) and stores the access token in the Flask session. The `/results` route orchestrates everything: fetches top artists from Spotify, calls into `SpotifyCall.py` for genre matching, then renders `results.html` with the sorted matches.

**`src/SpotifyCall.py`** — All external API logic:
- `compile_genres(list_of_artists)` — calls Last.fm `artist.getTopTags` for each artist, returns a flat list of genre tag strings (top 5 per artist, duplicates preserved for weighting)
- `compare_genres_to_CSV(genres)` — reads `festival_lineup.csv`, fetches Last.fm tags for each festival artist, counts how many appear in the user's genre list (using `list.count()` for frequency weighting), returns `["ArtistName:score", ...]`

**`festival_lineup.csv`** — Source of truth for the festival lineup. Must have an `"Artist Name"` column. Editing this file changes which artists appear in results.

**`src/templates/`** — Jinja2 templates rendered by Flask. `results.html` uses `top_score` (the max score) to compute per-artist color intensity via inline `style` attributes.

## Scoring logic

Score for a festival artist = sum of `genres.count(tag)` for each of their Last.fm tags that appears in the user's compiled genre list. Frequency in the user list amplifies the score, so artists whose genres the user listens to repeatedly rank higher.

## Known quirks

- `index.html` contains a dead `fetch('/results')` JavaScript block that was an earlier SPA approach; it is never executed in the current flow since `/results` is server-side rendered.
- `results.html` has Jinja template tags inside a `<style>` block (lines ~76–93) — this is intentional inline styling, not a bug; the CSS class rules above it are unused dead code.
- `src/SpotComp.py`, `src/Main.py`, and `src/side.py` are legacy scripts not used by the Flask app.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Flask web app that fetches YouTube comments for a video (YouTube Data API v3), runs them through
sentiment/emoji/topic/summary analysis using several Hugging Face transformer models, renders
matplotlib charts as base64 images, and stores per-user results in Firebase Firestore. Deployed
as a Hugging Face Spaces Docker app.

## Running the app

A `requirements.txt` exists — install dependencies inside a venv rather than manually:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py   # serves on http://127.0.0.1:5001 locally (PORT env var, default 5001)
```

Requires a Firebase project (Firestore enabled) and a `.env` file (git-ignored) in the project
root with:

```
FLASK_SECRET_KEY=...
YOUTUBE_API_KEY=...
FIREBASE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}   # full service account JSON, single line
```

The app will not start without `FLASK_SECRET_KEY` (`app.py`) or `FIREBASE_SERVICE_ACCOUNT_JSON`
(`firebase_client.py`) — both are read directly from the environment via `os.environ[...]`, no
fallback. On Hugging Face Spaces these are set as Repository Secrets instead of a committed `.env`.

Also requires NLTK's `stopwords` corpus (`ternding_Topics.py` auto-downloads it on first use if
missing).

## Architecture

### Request flow

`app.py` is the only Flask app entry point; `auth.py` is a Blueprint registered onto it (no
`url_prefix`, so its routes live at the same top level as `app.py`'s routes). Both use a
process-wide `Database()` instance (`database.py`, backed by `firebase_admin`/`google-cloud-firestore`
via `firebase_client.get_firestore_client()`) — no ORM, direct collection access
(`db.users`, `db.video_analysis`).

The core pipeline lives in `analyses.py:perform_video_analysis`, called from `app.py`'s
`/analyze` route, and chains through these modules in order:

1. `extract_id.py` — parse a video ID out of a `youtube.com`/`youtu.be` URL
2. `fetch_comments.py` — async (`aiohttp`/`asyncio`) paginated fetch via YouTube Data API
   `commentThreads`/`videos` endpoints; filters to English only via `langid`, caps at 1000
   English comments, also fetches video title/channel/thumbnail (base64-encoded)
3. `separate_emojis_and_text.py` — splits each comment into emoji-only and text-only strings
4. `Model.py` — sentiment on the text portion via `nlptown/bert-base-multilingual-uncased-sentiment`
   (5-star output collapsed to -1/0/1); model/tokenizer are loaded once at **module import time**
5. `emoji_analyzer.py` — sentiment on comments containing emoji via
   `cardiffnlp/twitter-roberta-base-sentiment`; unlike `Model.py`, this pipeline is
   re-instantiated on every call (no caching) — expect it to be slow
6. `ternding_Topics.py` — top-N frequent words via `sklearn`'s `CountVectorizer` + NLTK stopwords
7. `key_insights.py` — abstractive summary via `facebook/bart-large-cnn`, with chunk/overlap
   splitting for long input and lazy-but-cached (`global_tokenizer`/`global_summarizer`) model
   loading, unlike `Model.py`'s eager load
8. `create_bar_chart.py` — renders sentiment/emoji distributions to base64 PNGs via matplotlib
   (`Agg` backend)

Results are packed into two dicts: one for immediate template rendering (`results_dict`, includes
HTML snippets built inline in `analyses.py`) and one for persistence (`analysis_data`, saved via
`db.save_analysis`). Re-analyzing a video already saved for the same user short-circuits the
pipeline and reads the cached Firestore document instead (see the `existing_data` branch in
`app.py:analyze`, backed by `db.get_analysis_for_user`).

### Auth & storage

- Passwords hashed with `werkzeug.security`; sessions store just the username in `session['user']`.
- `database.py`'s `Database` class wraps two Firestore collections: `users_data` (document ID is
  the username itself — see `auth.py`'s username validation in `register()`, which guards this
  boundary since Firestore document IDs can't be empty, `/`-containing, `.`/`..`, or match
  `__.*__`) and `video_analysis` (auto-generated document IDs, queried by `username`/`video_id`
  fields).
- Profile images and per-analysis chart images/thumbnails are stored as base64 strings directly
  inline on the Firestore documents — there is no Firebase Storage / GridFS in this stack, and
  that was a deliberate choice to avoid requiring a billing-enabled Firebase project.
- `login_required` (`auth.py`) redirects to `auth.login` when `session['user']` is absent.

## Known gotchas

- **Duplicate `/history` route**: both `app.py` (`@app.route('/history')`) and the `auth`
  blueprint (`@auth.route('/history')`) register a view for the same path, since the blueprint has
  no `url_prefix`. Only one is reachable depending on Werkzeug's rule matching order — if editing
  history behavior, check both and remove the redundant one rather than editing just one.
- Secrets (`app.secret_key`, the YouTube API key, the Firebase service account) are all read from
  environment variables (`.env` locally, HF Spaces Repository Secrets in deployment) — none are
  hardcoded in source.

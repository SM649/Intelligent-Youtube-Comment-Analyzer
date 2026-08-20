# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Flask web app that fetches YouTube comments for a video (YouTube Data API v3), runs them through
sentiment/emoji/topic/summary analysis using several Hugging Face transformer models, renders
matplotlib charts as base64 images, and stores per-user results in MongoDB.

## Running the app

There is no `requirements.txt`, `.gitignore`, `.env`, or test suite in this repo despite the
README describing them — install dependencies manually before running:

```bash
pip install flask pymongo gridfs werkzeug aiohttp langid transformers torch \
    emoji matplotlib numpy scikit-learn nltk
python app.py   # serves on http://127.0.0.1:5001 (debug=True)
```

Requires a running local MongoDB instance (`mongodb://localhost:27017/`, hardcoded in
`database.py`) and NLTK's `stopwords` corpus (`ternding_Topics.py` auto-downloads it on first
use if missing).

**The YouTube API key is hardcoded**, not read from an environment variable — set it directly in
`fetch_comments.py`:

```python
API_KEY = "Your API key here."
```

## Architecture

### Request flow

`app.py` is the only Flask app entry point; `auth.py` is a Blueprint registered onto it (no
`url_prefix`, so its routes live at the same top level as `app.py`'s routes). Both use a
process-wide `Database()` instance (`database.py`, `pymongo`) — no ORM, direct collection access
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
pipeline and reads the cached Mongo document instead (see the `existing_data` branch in
`app.py:analyze`).

### Auth & storage

- Passwords hashed with `werkzeug.security`; sessions store just the username in `session['user']`.
- Profile images are stored as base64 strings directly on the user document — `gridfs.GridFS` is
  initialized in `Database.__init__` (`self.fs`) but `save_image` is unused by any route; don't
  assume GridFS is actually in the write path.
- `login_required` (`auth.py`) redirects to `auth.login` when `session['user']` is absent.

## Known gotchas

- **`app.py` renders `'index.html'` but the file on disk is `templates/Index.html`** (capital I).
  This filesystem is case-sensitive (Linux), so every route that calls
  `render_template('index.html', ...)` will raise `TemplateNotFound` until the casing matches.
- **Duplicate `/history` route**: both `app.py` (`@app.route('/history')`) and the `auth`
  blueprint (`@auth.route('/history')`) register a view for the same path, since the blueprint has
  no `url_prefix`. Only one is reachable depending on Werkzeug's rule matching order — if editing
  history behavior, check both and remove the redundant one rather than editing just one.
- `app.secret_key` and the MongoDB URI are hardcoded, not environment-configured.

# Migrate persistence layer from local MongoDB to Firebase, host on Hugging Face Spaces

## Goal

Move off a local, unhosted MongoDB instance so the app can run entirely on free-tier
infrastructure: Firebase (Firestore + Storage) for persistence, Hugging Face Spaces for
app hosting. No paid tier of anything.

## Context / constraints that shaped this design

- The app loads three transformer models (`nlptown/bert-base-multilingual-uncased-sentiment`,
  `cardiffnlp/twitter-roberta-base-sentiment`, `facebook/bart-large-cnn`) at runtime, needing
  well over the RAM most free generic web hosts (Render/Fly.io/Railway free tiers) offer.
  Hugging Face Spaces' free CPU tier (2 vCPU / 16GB RAM) is sized for exactly this, so app
  hosting is decided: **Hugging Face Spaces**.
- HF Spaces containers are ephemeral — local disk does not persist across restarts/sleep — so
  an external database and external file storage are both required regardless of DB choice.
- Current data model is Mongo-shaped (loose documents, base64 blobs embedded inline). The
  actual free-tier storage risk is the base64 image blobs (chart PNGs, profile pictures), not
  the text/numeric fields — a `video_analysis` document without an embedded image is only a
  few KB, so tens of thousands of them fit inside any free tier's storage cap.
- Decision (via brainstorming, see conversation): **Firebase (Firestore + Storage)**, chosen
  over "stay on MongoDB Atlas + separate bucket" (smaller rewrite, but two providers) and over
  Supabase/Postgres (biggest rewrite — relational redesign — plus free-tier project pausing on
  inactivity, which would double up with HF Spaces' own idle-sleep).
- Keep the existing custom auth (werkzeug password hashing + Flask session), just backed by
  Firestore instead of Mongo — not switching to Firebase Authentication. Smallest change, no
  new auth concepts, and this app's session model already works.

## Data model

Firestore is document-based, like Mongo, so this is a driver swap rather than a schema
redesign.

| Collection | Document ID | Notes |
|---|---|---|
| `users_data` | **username** (not an auto ID) | Free uniqueness enforcement + O(1) lookup by username via `.document(username).get()`. Email uniqueness still requires a `.where('email', '==', email)` query, same shape as today's `find_one`. |
| `video_analysis` | auto-generated | Same fields as today (`username`, `video_id`, `Video_Title`, `Channel_Name`, counts, `trending_topics`, `key_insights`, chart/profile fields — see below for the URL change). Queried via `.where('username', '==', ...)`, `.where('video_id', '==', ...)`, or both combined (a composite index will be needed for the two-field query used by the "already analyzed by this user" check in `app.py:analyze` — Firestore will surface a console link to create it on first use; create it during setup, don't wait for it to fail in production). |

## Image / blob storage

Chart PNGs (`create_bar_chart.py`) and profile images currently get base64-encoded and
embedded directly in Mongo documents. New flow:

- `database.py` uploads the raw PNG/JPEG bytes to Firebase **Storage**, at paths like:
  - `charts/{username}/{video_id}/bar_chart.png`
  - `charts/{username}/{video_id}/emoji_chart.png`
  - `profile_images/{username}.jpg`
- Firestore documents store only the resulting download URL string (in place of today's
  base64 string in `bar_chart_id` / `emoji_chart_id` / `profile_image_b64` fields — field
  names can stay, their contents change from base64 to URL).
- `save_analysis()` takes the chart bytes, uploads them, writes the URLs to Firestore, **and
  returns those URLs** to the caller. This is important: today, a brand-new analysis renders
  its modal from the local base64 string built moments earlier, while a cached/re-analyzed
  video renders from whatever was saved — those must produce the same displayable value.
  Returning the URL from `save_analysis()` and using it in both `results_dict`/`modal_data`
  paths keeps fresh and cached renders identical.
- Storage access model: these specific paths (`charts/**`, `profile_images/**`) are marked
  world-readable via Firebase Storage Rules. Chart data isn't sensitive; profile pictures are
  a minor exposure but consistent with this app's existing security bar (hardcoded Flask
  secret key today, no CSRF protection) — flagged here as a known tradeoff, not silently
  assumed. Signed URLs were considered and rejected as unnecessary complexity at this scale.

### Template changes required

Three `<img>` tags currently hardcode the base64 data-URI prefix and must switch to a plain
URL `src`:

- `templates/Index.html` — profile picture in the nav (`src="data:image/png;base64,{{ profile }}"`)
- `templates/Index.html` — bar chart (`src="data:image/png;base64,{{ modal_data.bar_chart_id }}"`)
- `templates/Index.html` — emoji chart (`src="data:image/png;base64,{{ modal_data.emoji_chart_id }}"`)
- `templates/profile_settings.html` and `templates/History_model.html` — same profile-picture
  pattern, need the equivalent check/update.

The video thumbnail (`data:image/jpeg;base64,{{ modal_data.thumbnail }}`) is unaffected — it
comes from the YouTube API response each time, not from our storage, so it stays base64.

## Config & secrets

Fixing the hardcoded secrets flagged in `CLAUDE.md` is in scope here since credentials
handling is already being touched:

- `app.secret_key` (`app.py`) → `FLASK_SECRET_KEY` env var
- YouTube API key (`fetch_comments.py`) → `YOUTUBE_API_KEY` env var
- New: Firebase service-account key → `FIREBASE_SERVICE_ACCOUNT_JSON` env var, holding the
  full JSON content as a string, parsed with `json.loads()` and passed to
  `firebase_admin.credentials.Certificate(...)` — avoids writing a credentials file to disk.
- New: Firebase Storage bucket name → `FIREBASE_STORAGE_BUCKET` env var.

Loaded locally via `python-dotenv` reading the existing (currently empty) `.env` file.
In production, set as Hugging Face Spaces **Repository secrets** (same env var names, so no
code branches between local/prod).

## Code footprint

| File | Change |
|---|---|
| `database.py` | Rewritten: `pymongo`/`gridfs` calls → `firebase-admin` Firestore/Storage calls. `save_image`/`self.fs` (already dead code per CLAUDE.md) removed entirely rather than ported. |
| `requirements.txt` | *(does not currently exist — will be created as part of this work, since none exists today)* `pymongo` → `firebase-admin`; add `python-dotenv`. |
| `app.py` | Read `FLASK_SECRET_KEY` from env instead of the hardcoded string. |
| `auth.py` | Pass raw image bytes to the DB layer instead of pre-base64-encoding them (encoding now happens only if/when needed for display, not for storage). |
| `analyses.py` | Use the URL returned by `save_analysis()`/chart upload for the immediate `results_dict`, instead of the locally-built base64 string. |
| `fetch_comments.py` | Read `YOUTUBE_API_KEY` from env instead of the hardcoded constant. |
| Templates (see above) | `data:image/...;base64,{{ x }}` → `{{ x }}` in the 5 spots identified. |
| `Model.py`, `emoji_analyzer.py`, `ternding_Topics.py`, `key_insights.py`, `create_bar_chart.py`, `extract_id.py`, `separate_emojis_and_text.py` | Untouched — none of these talk to storage. |

New file: a `Dockerfile` (or HF Spaces' `README.md` SDK metadata, if using the Gradio/Docker
Space type) for HF Spaces deployment — exact shape decided during the implementation plan.

## Error handling

- Firestore/Storage calls can fail on network errors or missing/invalid credentials at
  startup — surfaced today's equivalent way: `Database.__init__` connecting to Mongo doesn't
  currently handle connection failure gracefully either, so this preserves existing behavior
  (fail loud at startup) rather than adding new fallback logic that wasn't there before.
- Duplicate-username/email checks (`register_user`) keep their current shape: a `.get()` /
  `.where()` existence check before write, same as today's `find_one` checks.

## Testing

No test suite exists in this repo today (per `CLAUDE.md`). This migration will be verified
manually against a real (free-tier) Firebase project: register a user, upload a profile
image, analyze a video, confirm charts render, re-analyze the same video and confirm the
cached path renders identically to the fresh path, log out/in, delete history. This matches
the project's current verification bar — introducing a test framework is out of scope for
this change.

## Out of scope (explicitly not doing)

- Switching to Firebase Authentication (keeping custom auth, see above).
- A Firestore emulator for local dev — this is a small personal project; using the same live
  Firebase project for local dev and production is acceptable and simpler (YAGNI).
- Signed/expiring URLs for Storage objects (see Storage Rules discussion above).
- Any other refactor to the analysis pipeline itself — this change is scoped strictly to the
  persistence layer and hosting.

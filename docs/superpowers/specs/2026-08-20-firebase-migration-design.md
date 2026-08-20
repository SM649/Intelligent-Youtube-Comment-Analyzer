# Migrate persistence layer from local MongoDB to Firebase, host on Hugging Face Spaces

## Goal

Move off a local, unhosted MongoDB instance so the app can run entirely on free-tier
infrastructure: Firebase (Firestore) for persistence, Hugging Face Spaces for app hosting.
No paid tier, and no billing card on file, for anything.

## Revision note (post-approval correction)

The original version of this spec used Firebase **Storage** for chart/profile images. That
was corrected after discovering Firebase Cloud Storage now requires enabling the Blaze
(pay-as-you-go) plan — a billing card on file — even to stay within its free quota. Since
that contradicts the no-card goal, images are instead kept inline in Firestore documents as
base64 strings, exactly like Mongo does today (see "Image storage" below). This removes
Storage, `storage_utils.py`, and all template changes from scope entirely.

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
| `video_analysis` | auto-generated | Same fields as today (`username`, `video_id`, `Video_Title`, `Channel_Name`, counts, `trending_topics`, `key_insights`, chart/profile fields, all unchanged in shape — see "Image storage" below). Queried via `.where('username', '==', ...)`, `.where('video_id', '==', ...)`, or both combined. Firestore does **not** require a manually-created composite index for a pure multi-field equality query like this (composite indexes are only needed once a range filter or `orderBy` on a different field is combined with an equality filter) — no index setup step needed. |

## Image storage

Chart PNGs (`create_bar_chart.py`) and profile images stay exactly as they are today:
base64-encoded strings embedded directly in the document (`bar_chart_id`, `emoji_chart_id`,
`profile_image_b64` fields — same names, same content, same encoding). This is a deliberate
choice after ruling out Firebase Storage (see revision note above):

- Firestore's per-document limit is 1MiB. A chart PNG from `create_bar_chart.py` (a 5×3"
  matplotlib figure) is typically 20-50KB — comfortably small. The risk is entirely on
  user-uploaded profile pictures, which can be arbitrary size.
- New validation (not present today): reject a profile picture upload over ~500KB raw
  (≈667KB once base64-encoded) in `auth.py`, in both `register()` and `profile_settings()`,
  with a clear error message. This is the one new piece of behavior this migration adds,
  and it's a real system-boundary check (Firestore's actual hard limit), not speculative
  validation.
- Because the encoding never changes, `create_bar_chart.py`, `auth.py`'s existing
  base64-encoding of uploads, and every template's `data:image/...;base64,{{ x }}` `<img>`
  pattern all stay exactly as they are today. **No template changes are required.**
- `save_analysis()` keeps its current signature and behavior (`bar_chart`/`emoji_chart` as
  base64 strings written straight into the document) — the "fresh vs. cached render
  consistency" concern from the original Storage-based design doesn't apply here, since both
  paths already produce identical base64 strings today.

## Config & secrets

Fixing the hardcoded secrets flagged in `CLAUDE.md` is in scope here since credentials
handling is already being touched:

- `app.secret_key` (`app.py`) → `FLASK_SECRET_KEY` env var
- YouTube API key (`fetch_comments.py`) → `YOUTUBE_API_KEY` env var
- New: Firebase service-account key → `FIREBASE_SERVICE_ACCOUNT_JSON` env var, holding the
  full JSON content as a string, parsed with `json.loads()` and passed to
  `firebase_admin.credentials.Certificate(...)` — avoids writing a credentials file to disk.

Loaded locally via `python-dotenv` reading the existing (currently empty) `.env` file.
In production, set as Hugging Face Spaces **Repository secrets** (same env var names, so no
code branches between local/prod).

## Code footprint

| File | Change |
|---|---|
| `database.py` | Rewritten: `pymongo`/`gridfs` calls → `firebase-admin` Firestore calls. `save_image`/`self.fs` (already dead code per CLAUDE.md) removed entirely rather than ported. Two new methods added (`get_analysis_by_video_id`, `get_analysis_for_user`) to replace `app.py`'s current direct `db.video_analysis.find_one(...)` calls — Firestore's `CollectionReference` has no `find_one`, so that direct-access pattern can no longer work and needs a proper method, same as every other query in this class. |
| `firebase_client.py` | New file: initializes the Firebase Admin app from `FIREBASE_SERVICE_ACCOUNT_JSON` and exposes a `get_firestore_client()` used by `database.py`. |
| `requirements.txt` | *(does not currently exist — will be created as part of this work, since none exists today)* `pymongo` → `firebase-admin`; add `python-dotenv`. |
| `app.py` | Read `FLASK_SECRET_KEY` from env instead of the hardcoded string; replace the two direct `db.video_analysis.find_one(...)` calls with the new `database.py` methods; read `PORT` from env for HF Spaces' expected listen port. |
| `auth.py` | Add the ~500KB profile-picture size guard described above. Otherwise unchanged — image handling (base64-encode on upload) stays exactly as it is today. |
| `fetch_comments.py` | Read `YOUTUBE_API_KEY` from env instead of the hardcoded constant. |
| `Model.py`, `emoji_analyzer.py`, `ternding_Topics.py`, `key_insights.py`, `create_bar_chart.py`, `extract_id.py`, `separate_emojis_and_text.py`, `analyses.py`, all templates | Untouched. |

New file: a `Dockerfile` and HF Spaces `README.md` SDK metadata (YAML frontmatter) for
deployment — exact shape decided during the implementation plan.

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
- Firebase Storage, or any object-storage provider, for images (see revision note above —
  ruled out specifically to avoid a billing card requirement).
- A Firestore emulator for local dev — this is a small personal project; using the same live
  Firebase project for local dev and production is acceptable and simpler (YAGNI).
- Any other refactor to the analysis pipeline itself — this change is scoped strictly to the
  persistence layer and hosting.

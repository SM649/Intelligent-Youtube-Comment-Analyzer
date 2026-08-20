# Firebase Migration + Hugging Face Spaces Hosting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the local, unhosted MongoDB persistence layer with Firebase Firestore (free Spark plan, no billing card), and prepare the app to run on Hugging Face Spaces (free CPU tier) so the whole project can be hosted for free.

**Architecture:** `database.py` is rewritten from `pymongo` calls to `firebase-admin` Firestore calls, with identical method signatures wherever possible so callers change minimally. Images (chart PNGs, profile pictures) stay exactly as base64 strings embedded in documents — no object storage, no new billing requirement, no template changes. Secrets (Flask secret key, YouTube API key, Firebase credentials) move from hardcoded values to environment variables loaded via `python-dotenv`, read identically in local dev and in a Hugging Face Space (via its Repository Secrets).

**Tech Stack:** Flask, `firebase-admin` (Firestore Admin SDK), `python-dotenv`, Docker (for the Hugging Face Space).

**Spec:** `docs/superpowers/specs/2026-08-20-firebase-migration-design.md`

## Global Constraints

- No paid tier and no billing card for any provider used in this migration (per spec Goal).
- Image data (chart PNGs, profile pictures) stays base64-encoded inline in Firestore documents — no object storage (per spec "Image storage" section, revised after discovering Firebase Storage now requires Blaze billing).
- Profile picture uploads must be rejected over ~500KB raw bytes, to keep every Firestore document under its 1MiB hard limit (per spec "Image storage").
- Keep the existing custom auth (werkzeug password hashing + Flask session) — do not introduce Firebase Authentication (per spec Context).
- No test framework is being introduced; this repo has none today and the spec explicitly scopes that out. Every task's "test" step is a manual verification command/action against a real (free-tier) Firebase project.
- Every other module not explicitly touched by a task below (`Model.py`, `emoji_analyzer.py`, `ternding_Topics.py`, `key_insights.py`, `create_bar_chart.py`, `extract_id.py`, `separate_emojis_and_text.py`, `analyses.py`, all templates) stays unmodified.

---

## Task 1: Provision the Firebase project and local secrets (manual — human only)

This task cannot be executed by a coding agent — it requires a browser and a Google account login. Whoever executes this plan should either do this task themselves before continuing, or hand it to the project owner and pause.

**Files:** None (external account setup + populating the existing `.env` file with real values).

- [ ] **Step 1: Create the Firebase project**

Go to https://console.firebase.google.com/, click "Add project", and create a new project. Stay on the free **Spark** plan — do not enable Blaze/billing (Firestore is fully free on Spark; this migration deliberately avoids Storage, which is the piece that would require Blaze).

- [ ] **Step 2: Create the Firestore database**

In the new project, go to Build → Firestore Database → "Create database". Choose "Start in production mode" (the Admin SDK used by this app authenticates as a service account and bypasses Firestore Security Rules entirely, so the mode chosen here only affects direct client-SDK access, which this app never uses). Pick any region.

- [ ] **Step 3: Generate a service account key**

Go to Project Settings (gear icon, top left) → "Service accounts" tab → "Generate new private key". This downloads a JSON file — treat it as a secret, never commit it.

- [ ] **Step 4: Minify the service account JSON into one line**

```bash
python3 -c "import json; print(json.dumps(json.load(open('/path/to/downloaded-key.json'))))"
```

Copy the single-line output.

- [ ] **Step 5: Populate the `.env` file**

Open the `.env` file at the repo root (already exists, currently empty) and add:

```
FLASK_SECRET_KEY=<output of: python3 -c "import secrets; print(secrets.token_hex(32))">
YOUTUBE_API_KEY=<the same YouTube Data API v3 key currently hardcoded in fetch_comments.py>
FIREBASE_SERVICE_ACCOUNT_JSON=<the single-line JSON from Step 4>
```

- [ ] **Step 6: Confirm `.env` is not tracked by git**

```bash
git check-ignore .env
```

Expected output: `.env` (confirms the existing `.gitignore` entry covers it). If this prints nothing, stop and fix `.gitignore` before continuing — do not proceed with real secrets in a file git would track.

---

## Task 2: Environment-based configuration foundation

**Files:**
- Create: `requirements.txt`
- Modify: `fetch_comments.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `YOUTUBE_API_KEY` read from `os.environ` in `fetch_comments.py` (consumed already by that module's own `fetch_page`/`fetch_video_details` functions — no external consumers).

- [ ] **Step 1: Write `requirements.txt`**

```
flask
firebase-admin
python-dotenv
werkzeug
aiohttp
langid
transformers
torch
emoji
matplotlib
numpy
scikit-learn
nltk
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 3: Add a safety-net entry to `.gitignore`**

Current contents are just `.env`. Append the raw downloaded service-account file name too, in case it's kept around locally for reference:

```
.env
firebase-service-account.json
```

- [ ] **Step 4: Read the YouTube API key from the environment in `fetch_comments.py`**

Replace:

```python
import aiohttp
import asyncio
from langid import classify  # Faster alternative to langdetect
import base64

API_KEY = "Your API key here."
```

with:

```python
import os
import aiohttp
import asyncio
from langid import classify  # Faster alternative to langdetect
import base64

API_KEY = os.environ["YOUTUBE_API_KEY"]
```

- [ ] **Step 5: Verify**

This module reads the env var at import time, so it can only be verified once `.env` is actually loaded before import — that wiring happens in Task 6 (`app.py`). For now, confirm the file has no syntax errors:

```bash
python3 -c "import ast; ast.parse(open('fetch_comments.py').read())"
```

Expected: no output (parses cleanly).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt fetch_comments.py .gitignore
git commit -m "Add requirements.txt, load YouTube API key from environment"
```

---

## Task 3: Firebase Admin SDK client module

**Files:**
- Create: `firebase_client.py`

**Interfaces:**
- Produces: `get_firestore_client() -> google.cloud.firestore.Client`, used by `database.py` (Task 4).
- Consumes: `FIREBASE_SERVICE_ACCOUNT_JSON` env var (set in Task 1).

- [ ] **Step 1: Write `firebase_client.py`**

```python
import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

_app = None


def _init_app():
    global _app
    if _app is None:
        cred_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
        cred = credentials.Certificate(cred_dict)
        _app = firebase_admin.initialize_app(cred)
    return _app


def get_firestore_client():
    _init_app()
    return firestore.client()
```

- [ ] **Step 2: Verify against the real Firebase project**

```bash
python3 -c "
from dotenv import load_dotenv
load_dotenv()
from firebase_client import get_firestore_client
client = get_firestore_client()
print(client.collection('users_data').document('_smoketest').set({'ok': True}))
print(client.collection('users_data').document('_smoketest').get().to_dict())
client.collection('users_data').document('_smoketest').delete()
"
```

Expected: prints a Firestore `WriteResult`, then `{'ok': True}`, with no exceptions. This confirms credentials are valid and the project is reachable. Then check the Firebase console's Firestore data tab to confirm the `_smoketest` document is gone after the delete.

- [ ] **Step 3: Commit**

```bash
git add firebase_client.py
git commit -m "Add Firebase Admin SDK client module"
```

---

## Task 4: Rewrite `database.py` for Firestore

**Files:**
- Modify: `database.py` (full rewrite of the `Database` class body; same class name, same import site in `app.py`/`auth.py`)

**Interfaces:**
- Consumes: `get_firestore_client()` from `firebase_client.py` (Task 3).
- Produces (all methods called by `app.py`/`auth.py`, Tasks 5-6):
  - `register_user(username: str, email: str, password: str, profile_image_b64: str = None) -> tuple[bool, str]`
  - `verify_user(email: str, password: str) -> tuple[bool, dict | None]`
  - `get_user_video_ids(username: str) -> tuple[list[str], list[str]]`
  - `save_analysis(username: str, video_id: str, analysis_data: dict, bar_chart: str, emoji_chart: str) -> None`
  - `get_user_analysis_history(username: str) -> list[dict]`
  - `delete_analysis(username: str, video_id: str) -> bool`
  - `get_user_profile_image(username: str) -> str | None`
  - `update_user_profile(old_username: str, new_username: str, new_password: str = None, profile_image_b64: str = None) -> tuple[bool, str]`
  - `get_analysis_by_video_id(video_id: str) -> dict | None` (new — replaces `app.py`'s direct `db.video_analysis.find_one({"video_id": video_id})`)
  - `get_analysis_for_user(username: str, video_id: str) -> dict | None` (new — replaces `app.py`'s direct `db.video_analysis.find_one({"video_id": video_id, "username": ...})`)

- [ ] **Step 1: Replace the full contents of `database.py`**

```python
from firebase_client import get_firestore_client
from werkzeug.security import generate_password_hash, check_password_hash


class Database:
    def __init__(self):
        self.db = get_firestore_client()
        self.users = self.db.collection('users_data')
        self.video_analysis = self.db.collection('video_analysis')

    def register_user(self, username: str, email: str, password: str, profile_image_b64: str = None) -> tuple[bool, str]:
        if self.users.document(username).get().exists:
            return False, "Username already taken"
        if list(self.users.where('email', '==', email).limit(1).stream()):
            return False, "Email already registered"

        user_doc = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
        }
        if profile_image_b64:
            user_doc['profile_image_b64'] = profile_image_b64

        self.users.document(username).set(user_doc)
        return True, "Registration successful"

    def verify_user(self, email, password):
        matches = list(self.users.where('email', '==', email).limit(1).stream())
        if not matches:
            return False, None
        user = matches[0].to_dict()
        if check_password_hash(user['password'], password):
            return True, user
        return False, None

    def get_user_video_ids(self, username):
        docs = [d.to_dict() for d in self.video_analysis.where('username', '==', username).stream()]
        video_ids = [d["video_id"] for d in docs]
        video_titles = [d.get("Video_Title", "No Title Found") for d in docs]
        return video_ids, video_titles

    def save_analysis(self, username, video_id, analysis_data, bar_chart, emoji_chart):
        """Save analysis results in Firestore along with chart images (as base64 strings)."""
        analysis_data.update({
            "username": username,
            "video_id": video_id,
            "bar_chart_id": bar_chart,
            "emoji_chart_id": emoji_chart
        })
        self.video_analysis.add(analysis_data)

    def get_user_analysis_history(self, username):
        return [d.to_dict() for d in self.video_analysis.where('username', '==', username).stream()]

    def delete_analysis(self, username, video_id):
        docs = list(
            self.video_analysis
                .where('username', '==', username)
                .where('video_id', '==', video_id)
                .stream()
        )
        for d in docs:
            d.reference.delete()
        return len(docs) > 0

    def get_user_profile_image(self, username: str) -> str | None:
        doc = self.users.document(username).get()
        if doc.exists:
            return doc.to_dict().get('profile_image_b64')
        return None

    def update_user_profile(self,
                        old_username: str,
                        new_username: str,
                        new_password: str = None,
                        profile_image_b64: str = None
                        ) -> tuple[bool, str]:
        old_ref = self.users.document(old_username)
        old_doc = old_ref.get()
        if not old_doc.exists:
            return False, "User not found"

        if new_username != old_username and self.users.document(new_username).get().exists:
            return False, "Username already taken"

        update_fields = {}
        if new_password:
            update_fields['password'] = generate_password_hash(new_password)
        if profile_image_b64:
            update_fields['profile_image_b64'] = profile_image_b64

        if not update_fields and new_username == old_username:
            return True, "No changes made"

        if new_username != old_username:
            # Document ID is the username, so a rename is copy-then-delete, not an update.
            user_data = old_doc.to_dict()
            user_data.update(update_fields)
            user_data['username'] = new_username
            self.users.document(new_username).set(user_data)
            old_ref.delete()
        else:
            old_ref.update(update_fields)

        return True, "Profile updated successfully"

    def get_analysis_by_video_id(self, video_id):
        matches = list(self.video_analysis.where('video_id', '==', video_id).limit(1).stream())
        return matches[0].to_dict() if matches else None

    def get_analysis_for_user(self, username, video_id):
        matches = list(
            self.video_analysis
                .where('username', '==', username)
                .where('video_id', '==', video_id)
                .limit(1)
                .stream()
        )
        return matches[0].to_dict() if matches else None
```

- [ ] **Step 2: Verify the full user + analysis lifecycle against the real Firebase project**

```bash
python3 -c "
from dotenv import load_dotenv
load_dotenv()
from database import Database

db = Database()

# Register
ok, msg = db.register_user('plantest', 'plantest@example.com', 'hunter2')
print('register:', ok, msg)
assert ok

# Duplicate checks
ok, msg = db.register_user('plantest', 'other@example.com', 'x')
print('dup username:', ok, msg)
assert not ok
ok, msg = db.register_user('other', 'plantest@example.com', 'x')
print('dup email:', ok, msg)
assert not ok

# Login
ok, user = db.verify_user('plantest@example.com', 'hunter2')
print('login:', ok, user['username'])
assert ok

# Save + fetch an analysis
db.save_analysis('plantest', 'vid123', {'Video_Title': 'Test Video', 'total_fetched': 10}, 'BASE64BARCHART', 'BASE64EMOJICHART')
ids, titles = db.get_user_video_ids('plantest')
print('video ids:', ids, titles)
assert ids == ['vid123']

hit = db.get_analysis_for_user('plantest', 'vid123')
print('get_analysis_for_user:', hit['Video_Title'])
assert hit['bar_chart_id'] == 'BASE64BARCHART'

hit2 = db.get_analysis_by_video_id('vid123')
assert hit2['video_id'] == 'vid123'

history = db.get_user_analysis_history('plantest')
assert len(history) == 1

deleted = db.delete_analysis('plantest', 'vid123')
print('deleted:', deleted)
assert deleted

# Cleanup
db.users.document('plantest').delete()
print('ALL PASSED')
"
```

Expected: prints each step and ends with `ALL PASSED`, no assertion errors. Check the Firebase console's Firestore tab to confirm no leftover `plantest` user or `vid123` analysis document remains after this runs.

- [ ] **Step 3: Commit**

```bash
git add database.py
git commit -m "Rewrite database.py to use Firestore instead of MongoDB"
```

---

## Task 5: Add a profile-picture size guard to `auth.py`

**Files:**
- Modify: `auth.py`

**Interfaces:**
- Consumes: `db.register_user(...)`, `db.update_user_profile(...)` from `database.py` (Task 4) — signatures unchanged from before this task.

- [ ] **Step 1: Add the size constant near the top of `auth.py`**

Add right after the existing imports (after `import base64`):

```python
MAX_PROFILE_IMAGE_BYTES = 500_000  # keeps base64-encoded field comfortably under Firestore's 1MiB/doc limit
```

- [ ] **Step 2: Guard the upload in `register()`**

Replace:

```python
        # 2) handle optional profile image
        image_file = request.files.get('profile_image')
        image_b64  = None
        if image_file and image_file.filename:
            raw_bytes = image_file.read()
            image_b64 = base64.b64encode(raw_bytes).decode('utf-8')
```

with:

```python
        # 2) handle optional profile image
        image_file = request.files.get('profile_image')
        image_b64  = None
        if image_file and image_file.filename:
            raw_bytes = image_file.read()
            if len(raw_bytes) > MAX_PROFILE_IMAGE_BYTES:
                return render_template('register.html', error="Profile image too large — please use an image under 500KB.")
            image_b64 = base64.b64encode(raw_bytes).decode('utf-8')
```

- [ ] **Step 3: Guard the upload in `profile_settings()`**

Replace:

```python
        image_file = request.files.get('profile_image')
        profile_b64 = None
        if image_file and image_file.filename:
            profile_b64 = base64.b64encode(image_file.read()).decode('utf-8')
```

with:

```python
        image_file = request.files.get('profile_image')
        profile_b64 = None
        if image_file and image_file.filename:
            raw_bytes = image_file.read()
            if len(raw_bytes) > MAX_PROFILE_IMAGE_BYTES:
                return render_template(
                    'profile_settings.html',
                    username=username,
                    profile=db.get_user_profile_image(username),
                    error="Profile image too large — please use an image under 500KB."
                )
            profile_b64 = base64.b64encode(raw_bytes).decode('utf-8')
```

- [ ] **Step 4: Verify with a syntax check**

```bash
python3 -c "import ast; ast.parse(open('auth.py').read())"
```

Expected: no output. Full behavioral verification (an actual oversized upload through the browser) happens in Task 8's end-to-end pass, once `app.py` is wired up in Task 6.

- [ ] **Step 5: Commit**

```bash
git add auth.py
git commit -m "Reject profile picture uploads over 500KB (Firestore 1MiB doc limit)"
```

---

## Task 6: Update `app.py` — env-based secret key, Firestore method calls, PORT for deployment

**Files:**
- Modify: `app.py`

**Interfaces:**
- Consumes: `db.get_analysis_by_video_id(video_id)`, `db.get_analysis_for_user(username, video_id)` from `database.py` (Task 4).
- Consumes: `FLASK_SECRET_KEY` env var (Task 1).

- [ ] **Step 1: Load `.env` before any other import, and read the secret key from the environment**

Replace the top of `app.py`:

```python
from flask import Flask, render_template, request, session, jsonify
from auth import auth, login_required
from database import Database
from analyses import perform_video_analysis  # helper function in a separate module
from extract_id import extract_video_id  # needed to extract video id

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key
app.register_blueprint(auth)
db = Database()
```

with:

```python
from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask, render_template, request, session, jsonify
from auth import auth, login_required
from database import Database
from analyses import perform_video_analysis  # helper function in a separate module
from extract_id import extract_video_id  # needed to extract video id

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.register_blueprint(auth)
db = Database()
```

`load_dotenv()` must run before the `from auth import ...` / `from database import ...` lines, because importing those modules transitively imports `firebase_client.py`, whose module-level code (via `Database()` a few lines down) reads `FIREBASE_SERVICE_ACCOUNT_JSON` — and `fetch_comments.py` reads `YOUTUBE_API_KEY` at its own import time via the `analyses` import chain.

- [ ] **Step 2: Replace the direct Mongo-style lookup in `fetch_analysis`**

Replace:

```python
    """Get analysis data from the database for a given video"""
    analysis_data = db.video_analysis.find_one({"video_id": video_id})
```

with:

```python
    """Get analysis data from the database for a given video"""
    analysis_data = db.get_analysis_by_video_id(video_id)
```

- [ ] **Step 3: Replace the direct Mongo-style lookup in `analyze`**

Replace:

```python
    # Check if the user has already analyzed this video
    existing_data = db.video_analysis.find_one({"video_id": video_id, "username": session.get('user')})
```

with:

```python
    # Check if the user has already analyzed this video
    existing_data = db.get_analysis_for_user(session.get('user'), video_id)
```

- [ ] **Step 4: Read the port from the environment for deployment**

Replace:

```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)
```

with:

```python
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true')
```

- [ ] **Step 5: Verify the app boots and serves the dashboard route**

```bash
FLASK_DEBUG=true python3 app.py &
sleep 2
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/
kill %1
```

Expected: `200` (the landing page route). This confirms `.env` loads correctly, Firestore connects, and Flask starts without the old hardcoded secret key.

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "Read secrets from environment, use Database methods instead of direct collection access"
```

---

## Task 7: Hugging Face Spaces deployment files

**Files:**
- Create: `Dockerfile`
- Modify: `README.md` (prepend HF Spaces YAML frontmatter — existing content below it is untouched)

**Interfaces:** None (deployment configuration only, no code interfaces).

- [ ] **Step 1: Write the `Dockerfile`**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=7860
EXPOSE 7860

CMD ["python", "app.py"]
```

(Hugging Face Spaces' Docker SDK expects the container to listen on port 7860; `app.py`'s `PORT` env var handling from Task 6 already respects this.)

- [ ] **Step 2: Prepend HF Spaces metadata to `README.md`**

Add this block as the very first lines of `README.md`, above the existing content:

```markdown
---
title: Intelligent YouTube Comment Analyzer
emoji: 📊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

```

- [ ] **Step 3: Verify the Docker image builds locally**

```bash
docker build -t yt-comment-analyzer-test .
```

Expected: build completes without errors (this will take a while the first time — `torch`/`transformers` are large). This does not require a running container or real Firebase credentials to pass; it only confirms the image builds.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile README.md
git commit -m "Add Hugging Face Spaces Docker deployment files"
```

- [ ] **Step 5: Create the Space and push (manual — human only)**

This sub-step needs a browser + Hugging Face account and cannot be done by a coding agent:

1. Go to https://huggingface.co/new-space, create a new Space with SDK "Docker".
2. Add it as a git remote and push this repo's `main` branch to it (`git remote add space <space-git-url>`, `git push space main`).
3. In the Space's Settings → "Repository secrets", add `FLASK_SECRET_KEY`, `YOUTUBE_API_KEY`, and `FIREBASE_SERVICE_ACCOUNT_JSON` with the same values used locally in `.env`.
4. Wait for the Space to build and start; open its URL to confirm the landing page loads.

---

## Task 8: End-to-end manual verification

**Files:** None (verification only, matches the spec's "Testing" section).

- [ ] **Step 1: Register a new user with a normal-sized profile picture.** Confirm redirect to login and no error.

- [ ] **Step 2: Attempt to register a second user with a profile picture over 500KB.** Confirm the "Profile image too large" error renders instead of a crash.

- [ ] **Step 3: Log in as the first user.** Confirm the dashboard loads with the profile picture visible in the nav (base64 `<img>`, unchanged from before this migration).

- [ ] **Step 4: Analyze a new YouTube video link.** Confirm the modal shows sentiment counts, the bar chart, the emoji chart, trending topics, and the key-insights summary.

- [ ] **Step 5: Submit the same video link again.** Confirm it takes the cached path (near-instant, no re-run of the ML pipeline) and displays the same data as Step 4.

- [ ] **Step 6: Visit `/history`.** Confirm the analyzed video appears with its charts rendering correctly.

- [ ] **Step 7: Delete the history entry.** Confirm it disappears from `/history` and from the dashboard's video list.

- [ ] **Step 8: Log out and log back in.** Confirm the session round-trips correctly against Firestore-backed auth.

- [ ] **Step 9: Check the Firebase console's Firestore data tab.** Confirm `users_data` and `video_analysis` reflect exactly the operations performed above — no orphaned test documents left over from earlier task verification steps (Tasks 3-4).

# Structure & UX Redesign — Design Spec

**Date:** 2026-08-22
**Status:** Draft, pending user review

## Goal

Follow up on the shipped visual redesign (PR #4, "clay+3D" palette/dark-mode) with actual
structural/UX improvements: how pages are organized, how the app feels to interact with, and the
user journey — not just color/shape. Decided through visual brainstorming
(`.superpowers/brainstorm/` mockups, not committed).

This spec covers five changes. The first four are template/CSS/JS-only, matching the previous
redesign's scope. The fifth (History page) is the one piece that touches the backend.

## 1. Dashboard/analyze page — progressive staged reveal

`templates/index.html` keeps its current section order (search → video info → 3 stat tiles →
2 charts → insights/emoji table) — no layout change. Two additions:

- **Staged loading indicator.** Replace the current full-screen spinner (`#loadingSpinner` in
  `index.html`'s `{% block scripts %}`) with a multi-stage progress strip cycling through labeled
  steps: "Fetching comments" → "Analyzing sentiment" → "Extracting topics" → "Summarizing". Since
  the backend performs these steps synchronously in one request/response
  (`analyses.py:perform_video_analysis`) with no intermediate progress signal available, the
  stages are **time-based, not real progress** — a fixed CSS/JS animation cycling through the
  labels every ~1.5s while the request is in flight, purely to make the wait feel structured
  rather than a literal progress bar. This requires no backend change.
- **Staged section reveal.** Once the page reloads with `modal_data` populated, the four result
  blocks (video info, stat tiles, charts, insights) fade/slide in sequentially (~150ms stagger)
  instead of appearing simultaneously — a CSS `animation-delay` per block, triggered on page load.

## 2. Sidebar — grouped links + Recent Analyses

`templates/_navbar_dashboard.html` restructures its link list under two group labels: **Main**
(Dashboard, History) and **Account** (Profile Settings) — visual grouping only, `_flash.html`/URLs
unchanged. Below Main, a new **Recent** section lists the user's last 3 analyzed videos as
one-click links straight into that video's history detail page (see §5 for that route).

Backend addition required: there's currently no timestamp on saved analyses, so "last 3" can't be
ordered reliably. `database.py`'s `save_analysis` adds an `analyzed_at` field
(`datetime.utcnow().isoformat()`) to `analysis_data` before writing. A new
`Database.get_recent_analyses(username, limit=3)` method queries
`video_analysis.where(username == X).order_by('analyzed_at', direction=DESCENDING).limit(3)`. This
sidebar data needs to be available on every dashboard-shell page (index, history, profile), so
`app.py` adds a Flask `context_processor` that calls `get_recent_analyses` and injects
`recent_analyses` into every template render when `session.get('user')` is set — avoiding having
to thread this through `render_dashboard`, `history()`, and `auth.profile_settings()` individually.
**Deployment note:** if Firestore rejects the `where` + `order_by` combination for lack of an
index, the fix is creating the composite index Firestore's error message links to — no code
change, an infra step to flag if it comes up.

## 3. Landing hero — interactive looping preview

`templates/landing.html`'s hero (already re-themed with clay blobs) gains a small looping
animation, fake data only, no backend involvement: a mock URL bar "typing" a YouTube link,
sentiment bars animating from 0 to their target widths, then 2-3 keyword chips popping in — full
loop ~6s, pure CSS keyframes + a `setInterval`-driven class toggle in a small inline script, sitting
inside or beside the hero text (not replacing it).

## 4. Landing page — sample results showcase

A new `<section>` in `templates/landing.html`, inserted after Features and before How It Works
(keeping every existing section otherwise unchanged): a static mockup of a finished analysis
report — sample video title/channel, sample sentiment stat tiles, sample chart images (styled
divs or a pre-rendered illustrative image, not live data) — giving visitors a concrete look at the
payoff before signing up. No backend involvement; static content baked into the template.

## 5. History page — rich cards + summary strip + search (backend-touching)

### Card redesign

Each analysis in `templates/History_model.html` becomes a compact card: thumbnail, title,
channel, comment count, sentiment shown as two colored chips (positive %, negative %) instead of
today's full stat-tile row, and two actions — **View full report** and **Delete** (existing delete
route/form, unchanged). The chart images and full insight/emoji-table detail move OFF this card.

### New detail route

A new page shows the full report for one analysis: `GET /history/<video_id>`, added to `app.py`,
reusing the existing `Database.get_analysis_for_user(username, video_id)` method (already used by
the re-analysis short-circuit in `app.py:analyze`) rather than adding a new query. Renders a new
template, `templates/history_detail.html` (extends `base_dashboard.html`), containing the exact
markup `History_model.html` currently renders per-card (video info, 3 stat tiles, 2 charts,
trend/insight block) — that markup moves from the loop in `History_model.html` into this new
template, parameterized by the single fetched record instead of looping. 404/redirect-to-history
if `get_analysis_for_user` returns `None` (e.g. stale link, deleted analysis, or someone else's
video_id).

### List page additions

`app.py`'s `history()` view computes three aggregate numbers from the existing `history_data`
list — total count, average positive percentage, and count where `analyzed_at` falls within the
last 7 days — and passes them to the template as a small dict, rendered as a stats strip above the
list. A client-side search box (title/channel substring match, filtering the already-rendered
cards via JS — no new query, no pagination) sits below the stats strip; no server-side filtering
is added since the existing dataset per user is small and already fully rendered.

## Backend change summary (everything outside templates/CSS/JS)

- `database.py`: `save_analysis` gains `analyzed_at` timestamp; new `get_recent_analyses(username, limit=3)` method.
- `app.py`: new `context_processor` injecting `recent_analyses`; new `GET /history/<video_id>` route; `history()` view gains a small aggregation step (3 numbers) before rendering.
- No change to `auth.py`, `analyses.py`, `Model.py`, `emoji_analyzer.py`, `ternding_Topics.py`, `key_insights.py`, `create_bar_chart.py`, `fetch_comments.py`, `extract_id.py`, `separate_emojis_and_text.py`, `firebase_client.py`.

## Testing

- Manual pass covering: analyze a video and watch the staged loading + staged reveal; confirm the
  sidebar's Recent list appears and links work on index/history/profile pages; confirm the landing
  hero's loop animation runs and loops cleanly; confirm the sample-results section renders between
  Features and How It Works; on History, confirm the stats strip numbers are correct against a
  known set of saved analyses, confirm search filters the visible cards, confirm "View full
  report" opens the new detail route with full charts/insights, confirm "Delete" still works from
  the list.
- Both light and dark mode, since this all sits on top of the existing clay+3D theme.

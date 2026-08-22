# Structure & UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real structural/UX improvements on top of the already-shipped clay+3D visual redesign — staged reveal on the analyze page, a smarter sidebar, an animated landing hero, a sample-results showcase, and a reworked History page with a detail route.

**Architecture:** Four of five changes are template/CSS/JS-only, following the same token/class conventions established in the prior redesign. The fifth (History) adds a small, focused backend surface: one new `Database` method + one new field, one Flask `context_processor`, and one new route + template — nothing else in the Python layer changes.

**Tech Stack:** Flask + Jinja2, Tailwind CSS (compiled via the existing `.tailwindcss-cli` binary), Alpine.js, vanilla JS, `firebase_admin.firestore` for the one new query.

**Spec:** `docs/superpowers/specs/2026-08-22-structure-ux-redesign-design.md`

## Global Constraints

- No new build tooling — keep using `./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify`, and rebuild+commit `static/tailwind.css` after every task that adds a class not already compiled (check with grep first; skip the rebuild if nothing new was added, as established in the prior redesign's tasks).
- No test suite exists in this project (confirmed: no `pytest.ini`, no `tests/` dir) and Firestore requires live credentials to query — verification in every task is grep/curl-based against a running `python app.py` instance, the same convention used throughout this project's prior redesign tasks.
- Existing routes/endpoints keep their exact names: `landing`, `index` (mounted at `/dashboard`), `about`, `analyze`, `history`, `delete_history`. Do not rename any of them — `url_for('index')`/`url_for('history')` calls already exist in templates and must keep resolving.
- `positive`/`negative`/`neutral` Tailwind color tokens and every `bg-surface`/`bg-app-bg`/`text-text-dark`/`text-text-muted`/`.clay-blob` class from the prior redesign are already compiled and correct — reuse them, do not reintroduce hardcoded colors.
- The dashboard sidebar (`_navbar_dashboard.html`) must stay visually flat (no `shadow-card-base`/`.clay-blob` on it) — only its structure (grouping, new Recent section) changes in this plan, not its "flat exception" visual treatment.

---

### Task 1: `Database.get_recent_analyses` + `analyzed_at` timestamp

**Files:**
- Modify: `database.py`

**Interfaces:**
- Produces: `Database.get_recent_analyses(self, username, limit=3)` → `list[dict]`, each dict being a Firestore document's fields (same shape as `get_user_analysis_history`'s items) ordered newest-first by `analyzed_at`. Task 2 calls this by exact name.
- Produces: every `save_analysis` call now stamps a string field `analyzed_at` (ISO-8601 UTC, via `datetime.now(timezone.utc).isoformat()`) on the saved document. Task 4 reads `entry.get('analyzed_at')` on history entries — entries saved before this change won't have the field, and code reading it must treat that as "unknown/not this week", never crash.

- [ ] **Step 1: Add the `analyzed_at` timestamp to `save_analysis`**

In `database.py`, add this import near the top (alongside the existing `from werkzeug.security import ...` line):

```python
from datetime import datetime, timezone
from firebase_admin import firestore
```

Change:
```python
    def save_analysis(self, username, video_id, analysis_data, bar_chart, emoji_chart):
        """Save analysis results in Firestore along with chart images (as base64 strings)."""
        analysis_data.update({
            "username": username,
            "video_id": video_id,
            "bar_chart_id": bar_chart,
            "emoji_chart_id": emoji_chart
        })
        self.video_analysis.add(analysis_data)
```
to:
```python
    def save_analysis(self, username, video_id, analysis_data, bar_chart, emoji_chart):
        """Save analysis results in Firestore along with chart images (as base64 strings)."""
        analysis_data.update({
            "username": username,
            "video_id": video_id,
            "bar_chart_id": bar_chart,
            "emoji_chart_id": emoji_chart,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        })
        self.video_analysis.add(analysis_data)
```

- [ ] **Step 2: Add `get_recent_analyses`**

Add this method directly below `get_user_analysis_history` in `database.py`:

```python
    def get_recent_analyses(self, username, limit=3):
        """Returns the user's most recently analyzed videos, newest first.

        Entries saved before the `analyzed_at` field existed are excluded by
        Firestore's order_by (a doc missing the ordered field never matches),
        which is an accepted limitation, not a bug.
        """
        query = (
            self.video_analysis
                .where(filter=FieldFilter('username', '==', username))
                .order_by('analyzed_at', direction=firestore.Query.DESCENDING)
                .limit(limit)
        )
        return [d.to_dict() for d in query.stream()]
```

- [ ] **Step 3: Verify by inspection and a live save/fetch check**

Run:
```bash
grep -n "analyzed_at\|get_recent_analyses\|from datetime import\|from firebase_admin import firestore" database.py
```
Expected: all four strings present, matching the code above.

Start the dev server (`python app.py`), log in, analyze one video (or re-use an already-analyzed one — re-analysis short-circuits to `get_analysis_for_user` and does NOT call `save_analysis`, so use a video you have not analyzed with this account before, to actually exercise the new `analyzed_at` write path), then open a Python shell in the same environment and confirm the new field exists:
```bash
python3 -c "
from database import Database
db = Database()
recent = db.get_recent_analyses('<your-test-username>', limit=3)
print(len(recent), [r.get('analyzed_at') for r in recent])
"
```
Expected: prints a count ≥ 1 and a list of non-`None` ISO timestamp strings. If Firestore raises an index-related error here, that's expected and documented in the spec (§2's deployment note) — report it in your task report rather than trying to work around it in code; the fix is creating the composite index Firestore's error message links to, not a code change.

- [ ] **Step 4: Commit**

```bash
git add database.py
git commit -m "Add analyzed_at timestamp and get_recent_analyses for sidebar Recent list"
```

---

### Task 2: Sidebar — grouped links + Recent Analyses, via a context processor

**Files:**
- Modify: `app.py`
- Modify: `templates/_navbar_dashboard.html`

**Interfaces:**
- Consumes: `Database.get_recent_analyses(username, limit=3)` from Task 1.
- Produces: every template rendered by this app can reference `recent_analyses` (a list, possibly empty) without any view function passing it explicitly — Task 2 is the only place this context processor is defined.

- [ ] **Step 1: Add a context processor to `app.py`**

Add this directly below `db = Database()` in `app.py`:

```python
@app.context_processor
def inject_recent_analyses():
    """Makes `recent_analyses` available to every template without threading it through each view."""
    user_id = session.get('user')
    if not user_id:
        return {'recent_analyses': []}
    try:
        return {'recent_analyses': db.get_recent_analyses(user_id, limit=3)}
    except Exception:
        # A missing Firestore composite index (or any other transient query failure) must not
        # break every page render — degrade to an empty sidebar list instead of a 500.
        return {'recent_analyses': []}
```

- [ ] **Step 2: Restructure `templates/_navbar_dashboard.html`** to add group labels and the Recent section

Replace the file's `<div class="flex-1 py-3">...</div>` block (everything between `<div class="flex-1 py-3">` and its matching `</div>`) with:

```html
  <div class="flex-1 py-3">
    <p class="px-5 pt-2 pb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Main</p>
    <ul class="list-none m-0 p-0">
      <li class="my-1">
        <a href="{{ url_for('index') }}"
           class="flex items-center gap-2 px-5 py-3 text-sm border-l-4 transition
                  {{ 'border-[var(--clay-coral)] text-[var(--clay-coral)] font-semibold' if request.endpoint == 'index' else 'border-transparent text-text-muted hover:text-text-dark' }}">
          <i class="bi bi-house-fill"></i> Dashboard
        </a>
      </li>
      <li class="my-1">
        <a href="{{ url_for('history') }}"
           class="flex items-center gap-2 px-5 py-3 text-sm border-l-4 transition
                  {{ 'border-[var(--clay-coral)] text-[var(--clay-coral)] font-semibold' if request.endpoint in ('history', 'history_detail') else 'border-transparent text-text-muted hover:text-text-dark' }}">
          <i class="bi bi-clock-history"></i> History
        </a>
      </li>
    </ul>

    {% if recent_analyses %}
    <p class="px-5 pt-4 pb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Recent</p>
    <ul class="list-none m-0 p-0">
      {% for entry in recent_analyses %}
      <li class="my-1">
        <a href="{{ url_for('history_detail', video_id=entry.video_id) }}"
           class="flex items-center gap-2 px-5 py-2 text-xs text-text-muted hover:text-text-dark transition truncate">
          <i class="bi bi-play-circle"></i> <span class="truncate">{{ entry.Video_Title or 'Untitled video' }}</span>
        </a>
      </li>
      {% endfor %}
    </ul>
    {% endif %}

    <p class="px-5 pt-4 pb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">Account</p>
    <ul class="list-none m-0 p-0">
      <li class="my-1">
        <a href="{{ url_for('auth.profile_settings') }}"
           class="flex items-center gap-2 px-5 py-3 text-sm border-l-4 transition
                  {{ 'border-[var(--clay-coral)] text-[var(--clay-coral)] font-semibold' if request.endpoint == 'auth.profile_settings' else 'border-transparent text-text-muted hover:text-text-dark' }}">
          <i class="bi bi-gear-fill"></i> Profile Settings
        </a>
      </li>
    </ul>
  </div>
```

Note this references `url_for('history_detail', ...)` — that endpoint doesn't exist until Task 3. This is expected: Task 2's own verification (Step 3) only needs to confirm the template contains the class attributes, not fully render (`url_for` for a not-yet-registered endpoint raises at render time). If you need to sanity-check a real render before Task 3 lands, temporarily comment out the `{% if recent_analyses %}...{% endif %}` block's `<a href="{{ url_for('history_detail', ...">` line only for that manual check, then restore it — do not leave it commented out in the commit.

- [ ] **Step 3: Verify the template edit and the context processor by inspection**

```bash
grep -n "context_processor\|inject_recent_analyses" app.py
grep -n "Main\|Recent\|Account\|history_detail" templates/_navbar_dashboard.html
```
Expected: both greps show the expected strings from the code above.

- [ ] **Step 4: Commit**

```bash
git add app.py templates/_navbar_dashboard.html
git commit -m "Add recent_analyses context processor and grouped sidebar with Recent section"
```

---

### Task 3: History detail route + template

**Files:**
- Modify: `app.py`
- Create: `templates/history_detail.html`

**Interfaces:**
- Consumes: `Database.get_analysis_for_user(username, video_id)` (already exists, used by `analyze()`'s re-analysis short-circuit).
- Produces: a `history_detail` endpoint at `GET /history/<video_id>`, rendering `templates/history_detail.html` with context `analysis` (a dict, same field names as `History_model.html`'s loop variable today: `Video_Title`, `Channel_Name`, `video_id`, `total_fetched`, `total_english`, `thumbnail`, `positive_count`, `negative_count`, `neutral_count`, `bar_chart_id`, `emoji_chart_id`, `trending_topics`, `key_insights`), plus `username`/`profile` like every other dashboard page. Task 2's sidebar `url_for('history_detail', video_id=...)` calls resolve once this task lands. Task 4's "View full report" links also call `url_for('history_detail', video_id=analysis.video_id)`.

- [ ] **Step 1: Add the route to `app.py`**

Add this directly below the existing `history()` view (before `delete_history`):

```python
@app.route('/history/<video_id>')
def history_detail(video_id):
    """Displays the full report (charts + insights) for one saved analysis."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    user_id = session.get('user')
    analysis = db.get_analysis_for_user(user_id, video_id)
    if not analysis:
        flash('That analysis could not be found.', 'error')
        return redirect(url_for('history'))
    profile_image_b64 = db.get_user_profile_image(user_id)
    return render_template('history_detail.html', analysis=analysis, username=user_id, profile=profile_image_b64)
```

- [ ] **Step 2: Create `templates/history_detail.html`**

This is today's `History_model.html` per-card markup (video info, 3 stat tiles, 2 charts, trending topics/insights, emoji table), de-looped and pointed at `analysis` instead of a loop variable, plus a back link and the existing delete form:

```html
{% extends "base_dashboard.html" %}

{% block title %}{{ analysis.Video_Title }} – Intelligent YouTube Comment Analyzer{% endblock %}

{% block content %}
<a href="{{ url_for('history') }}" class="inline-flex items-center gap-1 text-sm text-text-muted hover:text-text-dark mb-4">
  <i class="bi bi-arrow-left"></i> Back to History
</a>

<div class="rounded-brand-lg shadow-card-base bg-surface p-4 mb-6">
  <div class="grid sm:grid-cols-[auto_1fr] gap-4 items-start">
    <div class="sm:w-40 text-center">
      {% if analysis.thumbnail %}
      <img src="data:image/jpeg;base64,{{ analysis.thumbnail }}" alt="Thumbnail" class="rounded-brand-md w-full">
      {% else %}
      <img src="https://via.placeholder.com/160x90?text=No+Thumbnail" alt="No Thumbnail" class="rounded-brand-md w-full">
      {% endif %}
    </div>
    <div>
      <h1 class="font-semibold text-xl">{{ analysis.Video_Title }}</h1>
      <p class="text-sm mb-1"><strong>Channel:</strong> {{ analysis.Channel_Name }}</p>
      <p class="text-sm mb-1"><strong>Video ID:</strong> {{ analysis.video_id }}</p>
      <p class="text-sm mb-1"><strong>Total Comments:</strong> {{ analysis.total_fetched }}</p>
      <p class="text-sm mb-3"><strong>English Comments:</strong> {{ analysis.total_english }}</p>

      <div class="grid grid-cols-3 gap-3 mb-4">
        <div class="rounded-brand-md bg-positive/10 p-3 text-center">
          <h6 class="text-positive font-semibold text-sm mb-1">Positive</h6>
          <p class="text-2xl font-bold m-0">{{ analysis.positive_count }}</p>
        </div>
        <div class="rounded-brand-md bg-negative/10 p-3 text-center">
          <h6 class="text-negative font-semibold text-sm mb-1">Negative</h6>
          <p class="text-2xl font-bold m-0">{{ analysis.negative_count }}</p>
        </div>
        <div class="rounded-brand-md bg-neutral/10 p-3 text-center">
          <h6 class="text-neutral font-semibold text-sm mb-1">Neutral</h6>
          <p class="text-2xl font-bold m-0">{{ analysis.neutral_count }}</p>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-3 mb-3">
        {% if analysis.bar_chart_id %}
        <div class="rounded-brand-md border border-border-lighter overflow-hidden">
          <div class="bg-surface px-3 py-2 border-b border-border-lighter">
            <h6 class="font-semibold text-sm m-0">Comments Chart</h6>
          </div>
          <div class="p-3 text-center">
            <img src="data:image/png;base64,{{ analysis.bar_chart_id }}" alt="Comments Chart" class="max-w-full mx-auto" loading="lazy">
          </div>
        </div>
        {% endif %}
        {% if analysis.emoji_chart_id %}
        <div class="rounded-brand-md border border-border-lighter overflow-hidden">
          <div class="bg-surface px-3 py-2 border-b border-border-lighter">
            <h6 class="font-semibold text-sm m-0">Emoji Chart</h6>
          </div>
          <div class="p-3 text-center">
            <img src="data:image/png;base64,{{ analysis.emoji_chart_id }}" alt="Emoji Chart" class="max-w-full mx-auto" loading="lazy">
          </div>
        </div>
        {% endif %}
      </div>

      {% if analysis.trending_topics %}
      <div class="flex flex-wrap gap-2 mb-3">
        {% for topic in analysis.trending_topics %}
        <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">{{ topic }}</span>
        {% endfor %}
      </div>
      {% endif %}

      {% if analysis.key_insights %}
      <div class="text-sm text-text-dark mb-3">{{ analysis.key_insights }}</div>
      {% endif %}

      <div class="text-right">
        <form method="post" action="{{ url_for('delete_history', video_id=analysis.video_id) }}" onsubmit="return confirm('Are you sure you want to delete this Analyses?');">
          <button type="submit" class="inline-flex items-center gap-1 text-sm text-white bg-negative hover:bg-negative/90 px-3 py-1.5 rounded-brand-md transition">
            <i class="bi bi-trash"></i> Delete
          </button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -n "history_detail\|history/<video_id>" app.py
```
Expected: the route decorator and function name both present.

Start the dev server, log in, analyze a video (or use one already saved), then visit `/history/<that-video-id>` directly in the browser (or `curl -b <session-cookie-jar> http://127.0.0.1:5001/history/<video_id>`) and confirm it renders the full report with a working "Back to History" link. Then go back to `/history` (Task 2's sidebar Recent links now resolve — click one and confirm it lands here).

- [ ] **Step 4: Commit**

```bash
git add app.py templates/history_detail.html
git commit -m "Add history detail route and template"
```

---

### Task 4: History list — rich cards, stats strip, client-side search

**Files:**
- Modify: `app.py`
- Modify: `templates/History_model.html`

**Interfaces:**
- Consumes: `history_detail` endpoint from Task 3 (for each card's "View full report" link).
- Produces: `history()` now passes a `stats` dict (`{'total': int, 'avg_positive': int, 'this_week': int}`) to the template — no other task consumes this, it's rendered directly.

- [ ] **Step 1: Add percentage pre-computation and stats aggregation to `app.py`**

Add this helper function directly above the `history()` view:

```python
def _annotate_and_summarize_history(history_data):
    """Adds positive_pct/negative_pct to each entry and returns (entries, stats dict)."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    positive_pcts_for_avg = []
    this_week = 0

    for entry in history_data:
        pos = entry.get('positive_count', 0)
        neg = entry.get('negative_count', 0)
        neu = entry.get('neutral_count', 0)
        denom = pos + neg + neu
        entry['positive_pct'] = round(pos / denom * 100) if denom else 0
        entry['negative_pct'] = round(neg / denom * 100) if denom else 0
        if denom:
            positive_pcts_for_avg.append(entry['positive_pct'])

        analyzed_at = entry.get('analyzed_at')
        if analyzed_at:
            try:
                analyzed_dt = datetime.fromisoformat(analyzed_at)
                if now - analyzed_dt <= timedelta(days=7):
                    this_week += 1
            except ValueError:
                pass

    stats = {
        'total': len(history_data),
        'avg_positive': round(sum(positive_pcts_for_avg) / len(positive_pcts_for_avg)) if positive_pcts_for_avg else 0,
        'this_week': this_week,
    }
    return history_data, stats
```

Change the `history()` view from:
```python
@app.route('/history')
def history():
    """Displays the analysis history for the logged-in user."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    user_id = session.get('user')
    history_data = db.get_user_analysis_history(user_id)
    profile_image_b64 = db.get_user_profile_image(user_id)
    return render_template('History_model.html', history_data=history_data, username=user_id, profile=profile_image_b64)
```
to:
```python
@app.route('/history')
def history():
    """Displays the analysis history for the logged-in user."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    user_id = session.get('user')
    history_data = db.get_user_analysis_history(user_id)
    history_data, stats = _annotate_and_summarize_history(history_data)
    profile_image_b64 = db.get_user_profile_image(user_id)
    return render_template('History_model.html', history_data=history_data, username=user_id, profile=profile_image_b64, stats=stats)
```

- [ ] **Step 2: Replace `templates/History_model.html`'s content block** with the stats strip, search box, and rich cards

```html
{% extends "base_dashboard.html" %}

{% block title %}History – Intelligent YouTube Comment Analyzer{% endblock %}

{% block content %}
<h1 class="text-2xl font-bold mb-4">Analysis History</h1>

{% if history_data %}
<div class="grid grid-cols-3 gap-3 mb-4">
  <div class="rounded-brand-lg shadow-card-base bg-surface p-3 text-center">
    <p class="text-2xl font-bold m-0">{{ stats.total }}</p>
    <p class="text-xs text-text-muted m-0">Total analyses</p>
  </div>
  <div class="rounded-brand-lg shadow-card-base bg-surface p-3 text-center">
    <p class="text-2xl font-bold m-0">{{ stats.avg_positive }}%</p>
    <p class="text-xs text-text-muted m-0">Avg. positive</p>
  </div>
  <div class="rounded-brand-lg shadow-card-base bg-surface p-3 text-center">
    <p class="text-2xl font-bold m-0">{{ stats.this_week }}</p>
    <p class="text-xs text-text-muted m-0">This week</p>
  </div>
</div>

<input type="text" id="historySearch" placeholder="Search by video title or channel..."
       class="w-full mb-4 px-4 py-2 rounded-brand-md border border-border-light outline-none">

<div id="historyList">
{% for analysis in history_data %}
<div class="video-card rounded-brand-lg shadow-card-base hover:shadow-card-hover transition p-4 mb-4 bg-surface"
     data-title="{{ (analysis.Video_Title or '')|lower }}" data-channel="{{ (analysis.Channel_Name or '')|lower }}">
  <div class="flex flex-col sm:flex-row items-center sm:items-start gap-4">
    <div class="sm:w-32 shrink-0 text-center">
      {% if analysis.thumbnail %}
      <img src="data:image/jpeg;base64,{{ analysis.thumbnail }}" alt="Thumbnail" class="rounded-brand-md w-full" loading="lazy">
      {% else %}
      <img src="https://via.placeholder.com/160x90?text=No+Thumbnail" alt="No Thumbnail" class="rounded-brand-md w-full" loading="lazy">
      {% endif %}
    </div>
    <div class="flex-1">
      <h5 class="font-semibold text-lg">{{ analysis.Video_Title }}</h5>
      <p class="text-sm text-text-muted mb-2">{{ analysis.Channel_Name }} · {{ analysis.total_fetched }} comments</p>
      <div class="flex flex-wrap gap-2 mb-3">
        <span class="px-3 py-1 rounded-full bg-positive/10 text-positive text-xs font-semibold">😊 {{ analysis.positive_pct }}% positive</span>
        <span class="px-3 py-1 rounded-full bg-negative/10 text-negative text-xs font-semibold">😞 {{ analysis.negative_pct }}% negative</span>
      </div>
      <div class="flex gap-2">
        <a href="{{ url_for('history_detail', video_id=analysis.video_id) }}"
           class="inline-flex items-center gap-1 text-sm text-white bg-primary hover:bg-primary/90 px-3 py-1.5 rounded-brand-md transition">
          <i class="bi bi-file-earmark-text"></i> View full report
        </a>
        <form method="post" action="{{ url_for('delete_history', video_id=analysis.video_id) }}" onsubmit="return confirm('Are you sure you want to delete this Analyses?');">
          <button type="submit" class="inline-flex items-center gap-1 text-sm text-white bg-negative hover:bg-negative/90 px-3 py-1.5 rounded-brand-md transition">
            <i class="bi bi-trash"></i> Delete
          </button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endfor %}
</div>
{% else %}
<p class="text-text-muted">No analysis history available.</p>
{% endif %}
{% endblock %}

{% block scripts %}
<script>
  document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('historySearch');
    if (!searchInput) return;
    searchInput.addEventListener('input', function () {
      const term = searchInput.value.trim().toLowerCase();
      document.querySelectorAll('#historyList .video-card').forEach(function (card) {
        const matches = card.dataset.title.includes(term) || card.dataset.channel.includes(term);
        card.style.display = matches ? '' : 'none';
      });
    });
  });
</script>
{% endblock %}
```

- [ ] **Step 3: Rebuild CSS if needed, then verify**

```bash
grep -o 'bg-primary\b' static/tailwind.css | head -1
```
If that prints nothing, rebuild: `./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify` (this class was already used elsewhere in the prior redesign, so it should already be compiled — confirm before deciding whether to rebuild).

```bash
grep -n "historySearch\|stats.total\|stats.avg_positive\|stats.this_week\|history_detail" templates/History_model.html
grep -n "_annotate_and_summarize_history" app.py
```
Expected: all present.

Start the dev server, log in, view `/history` with at least one saved analysis: confirm the stats strip shows correct numbers, typing in the search box filters cards live, "View full report" opens the Task 3 detail page, "Delete" still works.

- [ ] **Step 4: Commit**

```bash
git add app.py templates/History_model.html
git commit -m "Redesign History page: rich cards, stats strip, client-side search"
```

---

### Task 5: Dashboard/analyze page — staged loading + staged reveal

**Files:**
- Modify: `static/tailwind-input.css`
- Modify: `templates/index.html`
- Modify: `static/myjs.js`

**Interfaces:**
- Produces: CSS classes `.reveal-stage` (used with an inline `style="animation-delay:…"` per block) in `static/tailwind-input.css`'s plain-CSS section (alongside `.clay-blob`). Produces a `#loadingStageText` element id that `static/myjs.js` writes to.

- [ ] **Step 1: Add the reveal-stage animation to `static/tailwind-input.css`**

Add this directly after the existing `.clay-blob` rule inside the `@layer components` block:

```css
  .reveal-stage {
    opacity: 0;
    animation: reveal-fade 0.5s ease forwards;
  }
```

And add this keyframe definition outside any `@layer` block (same place `:root`/`.dark` live, i.e. at the top level of the file):

```css
@keyframes reveal-fade {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
```

- [ ] **Step 2: Apply `.reveal-stage` to the four result blocks in `templates/index.html`**

Add `reveal-stage` to the class list and an inline delay to each of these four top-level blocks inside the `{% if modal_data %}` branch (do not change any other class already on these elements):

1. The video-info card (`<div class="rounded-brand-lg shadow-card-base bg-surface p-4 mb-6">`) → add `reveal-stage` to its class list and `style="animation-delay:0ms"`.
2. The 3-stat-tile grid (`<div class="grid md:grid-cols-3 gap-4 mb-6" id="Comments-summary" ...>`) → add `reveal-stage` and `style="animation-delay:150ms"` (merge with the existing `data-positive`/etc. attributes already on this element — don't remove them).
3. The 2-chart grid (`<div class="grid md:grid-cols-2 gap-4 mb-6">` directly below the stat tiles) → add `reveal-stage` and `style="animation-delay:300ms"`.
4. The insights/emoji-table grid (`<div class="grid lg:grid-cols-12 gap-4">`) → add `reveal-stage` and `style="animation-delay:450ms"`.

For example, block 1 changes from:
```html
<div class="rounded-brand-lg shadow-card-base bg-surface p-4 mb-6">
```
to:
```html
<div class="rounded-brand-lg shadow-card-base bg-surface p-4 mb-6 reveal-stage" style="animation-delay:0ms">
```
Apply the same pattern (add `reveal-stage` to the class attribute, add the matching `style="animation-delay:…ms"`) to the other three blocks using their respective delays (150ms, 300ms, 450ms).

- [ ] **Step 3: Add the staged loading label to the spinner and cycle it in `static/myjs.js`**

In `templates/index.html`'s `{% block scripts %}`, change:
```html
<div class="fixed inset-0 bg-black/70 z-50 items-center justify-center" id="loadingSpinner" style="display: none;">
  <div class="text-center">
    <div class="animate-spin h-12 w-12 border-4 border-white/30 border-t-white rounded-full mx-auto"></div>
    <p class="mt-3 text-white">Analyzing comments...</p>
  </div>
</div>
```
to:
```html
<div class="fixed inset-0 bg-black/70 z-50 items-center justify-center" id="loadingSpinner" style="display: none;">
  <div class="text-center">
    <div class="animate-spin h-12 w-12 border-4 border-white/30 border-t-white rounded-full mx-auto"></div>
    <p class="mt-3 text-white" id="loadingStageText">Fetching comments...</p>
  </div>
</div>
```

Change `static/myjs.js` from:
```js
document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form');
  const loadingSpinner = document.getElementById('loadingSpinner');

  if (form && loadingSpinner) {
      form.addEventListener('submit', function (e) {
          // Keep the spinner logic, actual submission is handled by the browser/backend
          loadingSpinner.style.display = 'flex';
          // The spinner will hide when the new page loads or via backend response handling
      });
  }


});
```
to:
```js
document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form');
  const loadingSpinner = document.getElementById('loadingSpinner');
  const loadingStageText = document.getElementById('loadingStageText');
  const loadingStages = ['Fetching comments...', 'Analyzing sentiment...', 'Extracting topics...', 'Summarizing...'];

  if (form && loadingSpinner) {
      form.addEventListener('submit', function (e) {
          // Keep the spinner logic, actual submission is handled by the browser/backend
          loadingSpinner.style.display = 'flex';
          // The spinner will hide when the new page loads or via backend response handling
          if (loadingStageText) {
              let stageIndex = 0;
              loadingStageText.textContent = loadingStages[stageIndex];
              setInterval(function () {
                  stageIndex = (stageIndex + 1) % loadingStages.length;
                  loadingStageText.textContent = loadingStages[stageIndex];
              }, 1500);
              // No clearInterval call: the page navigates away on the form's normal
              // submit/response cycle, which discards this interval along with the page.
          }
      });
  }


});
```

- [ ] **Step 4: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
grep -c "reveal-fade\|reveal-stage" static/tailwind.css
grep -c "reveal-stage" templates/index.html
grep -c "loadingStages\|loadingStageText" static/myjs.js
```
Expected: first command ≥ 1, second command `4`, third command ≥ 2.

Start the dev server, log in, analyze a video, and watch: the spinner's label cycles through the 4 stage texts while waiting, and once the page reloads with results, the four blocks fade/slide in with a visible stagger rather than all appearing instantly.

- [ ] **Step 5: Commit**

```bash
git add static/tailwind-input.css templates/index.html static/myjs.js static/tailwind.css
git commit -m "Add staged loading text and staggered reveal animation to the analyze page"
```

---

### Task 6: Landing hero — looping interactive preview

**Files:**
- Modify: `static/tailwind-input.css`
- Modify: `templates/landing.html`

**Interfaces:**
- Produces: CSS classes `.hero-demo`, `.hero-demo-url`, `.hero-demo-bar`, `.hero-demo-chip` in `static/tailwind-input.css` — no other task consumes these.

- [ ] **Step 1: Add the demo animation CSS**

Add this block to `static/tailwind-input.css`, at the top level (outside any `@layer`), directly after the `@keyframes reveal-fade` block added in Task 5:

```css
@keyframes hero-demo-url-type {
  0%, 10% { width: 0; }
  35%, 100% { width: 100%; }
}
@keyframes hero-demo-bar-fill {
  0%, 35% { width: 0; }
  60%, 100% { width: var(--fill-to, 70%); }
}
@keyframes hero-demo-chip-pop {
  0%, 55% { opacity: 0; transform: translateY(6px) scale(0.9); }
  70%, 100% { opacity: 1; transform: translateY(0) scale(1); }
}
.hero-demo-url {
  display: inline-block;
  overflow: hidden;
  white-space: nowrap;
  border-right: 2px solid var(--clay-muted);
  animation: hero-demo-url-type 6s ease-in-out infinite;
}
.hero-demo-bar {
  height: 100%;
  border-radius: 999px;
  width: 0;
  animation: hero-demo-bar-fill 6s ease-in-out infinite;
}
.hero-demo-chip {
  opacity: 0;
  animation: hero-demo-chip-pop 6s ease-in-out infinite;
}
```

- [ ] **Step 2: Add the demo markup to the landing hero**

In `templates/landing.html`, inside the hero's `<div class="relative max-w-3xl mx-auto px-4" ...>` wrapper, add this block directly after the "Start Analyzing Now" `<a>` link and before the wrapper's closing `</div>`:

```html
    <div class="mt-10 max-w-sm mx-auto rounded-brand-lg bg-surface shadow-card-base p-4 text-left">
      <div class="text-xs text-text-muted mb-2">youtube.com/watch?v=<span class="hero-demo-url">dQw4w9WgXcQ</span></div>
      <div class="flex items-center gap-2 mb-1">
        <span class="text-xs w-16 text-text-muted">Positive</span>
        <div class="flex-1 h-2 rounded-full bg-app-bg overflow-hidden"><div class="hero-demo-bar bg-positive" style="--fill-to:72%"></div></div>
      </div>
      <div class="flex items-center gap-2 mb-3">
        <span class="text-xs w-16 text-text-muted">Negative</span>
        <div class="flex-1 h-2 rounded-full bg-app-bg overflow-hidden"><div class="hero-demo-bar bg-negative" style="--fill-to:18%"></div></div>
      </div>
      <div class="flex flex-wrap gap-2">
        <span class="hero-demo-chip px-2 py-1 rounded-full bg-primary/10 text-primary text-xs">editing tips</span>
        <span class="hero-demo-chip px-2 py-1 rounded-full bg-primary/10 text-primary text-xs">great content</span>
      </div>
    </div>
```

- [ ] **Step 3: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
grep -c "hero-demo-url-type\|hero-demo-bar-fill\|hero-demo-chip-pop" static/tailwind.css
grep -c "hero-demo" templates/landing.html
```
Expected: first command ≥ 1, second command ≥ 5.

Start the dev server, visit `/`, and watch the hero: the fake URL "types" in, then two bars fill to 72%/18%, then two keyword chips pop in, looping every ~6s.

- [ ] **Step 4: Commit**

```bash
git add static/tailwind-input.css templates/landing.html static/tailwind.css
git commit -m "Add looping interactive preview animation to landing hero"
```

---

### Task 7: Landing page — sample results showcase section

**Files:**
- Modify: `templates/landing.html`

**Interfaces:**
- None — purely additive static content, no other task depends on this.

- [ ] **Step 1: Insert a new section between Features and How It Works**

In `templates/landing.html`, insert this new `<section>` directly after the Features section's closing `</section>` tag and before `<section class="py-20 bg-surface" id="how-it-works">`:

```html
<section class="py-20 bg-app-bg" id="sample-results">
  <div class="max-w-4xl mx-auto px-4">
    <div class="text-center max-w-2xl mx-auto mb-12" data-aos="fade-up">
      <h2 class="text-3xl font-bold mb-2">See It In Action</h2>
      <p class="text-text-muted">A real example of what your analysis report looks like</p>
    </div>
    <div class="rounded-brand-lg shadow-card-base bg-surface p-6" data-aos="fade-up" data-aos-delay="100">
      <h5 class="font-semibold text-lg mb-1">"10 Tips For Better Video Editing"</h5>
      <p class="text-sm text-text-muted mb-4">CreatorHub · 2,340 comments analyzed</p>
      <div class="grid grid-cols-3 gap-3 mb-4">
        <div class="rounded-brand-md bg-positive/10 p-3 text-center">
          <h6 class="text-positive font-semibold text-sm mb-1">Positive</h6>
          <p class="text-2xl font-bold m-0">76%</p>
        </div>
        <div class="rounded-brand-md bg-negative/10 p-3 text-center">
          <h6 class="text-negative font-semibold text-sm mb-1">Negative</h6>
          <p class="text-2xl font-bold m-0">14%</p>
        </div>
        <div class="rounded-brand-md bg-neutral/10 p-3 text-center">
          <h6 class="text-neutral font-semibold text-sm mb-1">Neutral</h6>
          <p class="text-2xl font-bold m-0">10%</p>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">editing software</span>
        <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">color grading</span>
        <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">audio quality</span>
      </div>
    </div>
  </div>
</section>
```

- [ ] **Step 2: Verify**

```bash
grep -c "sample-results" templates/landing.html
```
Expected: `2` (the `id="sample-results"` and the `href`-less section itself — confirm both the opening section tag and the id attribute are present by inspecting the file, since a plain count only proves the string occurs, not where).

Start the dev server, visit `/`, and confirm the new "See It In Action" section renders between Features and How It Works, styled consistently with the rest of the clay-themed page, in both light and dark mode.

- [ ] **Step 3: Commit**

```bash
git add templates/landing.html
git commit -m "Add sample results showcase section to landing page"
```

---

### Task 8: Full-site verification

**Files:**
- Test only — no file changes expected unless verification surfaces a real bug, in which case fix it in the specific file it belongs to and note the fix in the report.

**Interfaces:**
- None.

- [ ] **Step 1: Rebuild CSS one final time and confirm it's minified**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
wc -c static/tailwind.css
```
Expected: a single-line, minified file (confirm by checking it's not multi-line with comments — the un-minified-build regression from the prior redesign's process must not recur here).

- [ ] **Step 2: Full manual pass**

Start `python app.py`, and walk through, in both light and dark mode:
- `/` — hero demo animation loops, sample-results section appears between Features and How It Works, coral CTA still renders.
- `/dashboard` (after login) — sidebar shows Main/Recent/Account grouping, staged loading text cycles during an analysis, results fade in staggered.
- Sidebar's Recent list — click an entry, confirm it opens that video's `/history/<video_id>` detail page.
- `/history` — stats strip numbers are correct against what you know you've saved, search box filters cards live by typing part of a title or channel name, "View full report" opens the detail page, "Delete" still removes an entry and redirects back to `/history`.
- `/history/<video_id>` directly — full charts/insights render, "Back to History" returns to the list.

- [ ] **Step 3: Report results**

Write a short report noting: what was verified live vs. what environment limits prevented (e.g., if no Firestore credentials are available in this run, note exactly which checks were skipped and why — do not fabricate a "verified" claim for anything not actually observed).

- [ ] **Step 4: Commit** (only if Step 2 surfaced and required a fix; otherwise skip — there's nothing to commit for a clean verification pass)

```bash
git add -A
git commit -m "Fix issue found during full-site verification: <describe>"
```

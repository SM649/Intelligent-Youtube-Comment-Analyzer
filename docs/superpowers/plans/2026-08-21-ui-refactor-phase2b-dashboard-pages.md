# UI Refactor Phase 2B: Dashboard Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the last two remaining Bootstrap-era templates — `profile_settings.html` and `index.html` — onto `base_dashboard.html`, adopt `flash()` in `auth.py`'s `profile_settings()` view (matching the pattern already used by `login()`/`register()`), and rebuild `static/tailwind.css` as part of the plan itself (not an afterthought — Phase 2A's own final review caught that its predecessor plan skipped this).

**Architecture:** Same pattern as Phase 1/2A. `templates/index.html`'s own inline percentage-calculation script stays as a page-specific `{% block scripts %}` — Phase 1 already confirmed `static/myjs.js`'s copy of that same logic targets a `sentiment-summary` ID that never exists on this page (the real container is `Comments-summary`), so it's dead/unreachable there and always was; `index.html` has always supplied its own working copy inline, and that doesn't change here. `static/myjs.js`'s generic submit-spinner logic (`document.querySelector('form')` / `getElementById('loadingSpinner')`), by contrast, IS already active on every `base_dashboard.html` page (it's loaded there unconditionally) — `index.html` reuses it as-is rather than duplicating spinner-toggle code in its own script block, matching the inline-style `display: none` convention `myjs.js` already manipulates directly (not a Tailwind class toggle).

**Tech Stack:** Same as Phase 1/2A — no new libraries needed for this phase (no new Alpine components; the sidebar/topbar/flash chrome is already fully built by `base_dashboard.html`).

**Spec:** `docs/superpowers/specs/2026-08-20-ui-refactor-design.md` (original design). No new spec document.

## Global Constraints

- `templates/index.html` and `templates/profile_settings.html` must become genuinely Bootstrap-free (no Bootstrap CSS/JS bundle). Font Awesome, Bootstrap Icons (icon font) are expected and fine.
- `auth.py`'s `profile_settings()` view's TWO failure paths switch from `render_template(template, ..., error=...)` to `flash(message, 'error')` + `redirect(url_for('auth.profile_settings'))`, matching `login()`/`register()`'s already-established pattern. The success path (`session['user'] = new_username; ...` falling through to the final `return render_template(...)` at the end of the GET/POST-merged flow) changes to a `redirect` too, since flash-based feedback requires a redirect to display correctly (a flashed message set right before falling through to the same request's own render would never be consumed — Flask's flash queue is read on the NEXT request). The initial `if not username: return redirect(url_for('auth.login'))` guard is unchanged.
- `templates/index.html`'s `error_message` display (a pre-existing, different mechanism for surfacing analysis failures, e.g. an invalid YouTube URL) is NOT converted to `flash()` — it stays as an inline conditional block, unrelated to the auth-error flash pattern this plan otherwise follows.
- `static/myjs.js` is NOT modified by this plan — both templates rely on its existing (already-working, already-reviewed) sidebar-toggle and submit-spinner logic without any changes.
- `static/tailwind.css` MUST be rebuilt and verified to contain the new classes both templates introduce, as part of this plan's own tasks (see Task 3) — not deferred to a "someone will catch it in review" hope, per the lesson from Phase 2A.
- Verification is manual (real server + curl), same as every prior task in this project.

---

## File Structure

**Modify:**
- `templates/profile_settings.html` — full rewrite, `{% extends "base_dashboard.html" %}`.
- `auth.py` — `profile_settings()`'s two failure paths + the post-update success flow switch to `flash()` + `redirect()`.
- `templates/index.html` — full rewrite, `{% extends "base_dashboard.html" %}`.
- `static/tailwind.css` — regenerated (Task 3).

---

### Task 1: Migrate `profile_settings.html` + adopt `flash()` in `auth.py`'s `profile_settings()`

**Files:**
- Modify: `templates/profile_settings.html` (full rewrite)
- Modify: `auth.py:108-158` (the `profile_settings()` view)

**Interfaces:**
- Consumes: `base_dashboard.html` (Phase 1) — already includes the sidebar, topbar, `_flash.html`, and `myjs.js`.
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Replace `templates/profile_settings.html` in full**

```html
{% extends "base_dashboard.html" %}

{% block title %}Profile Settings – Intelligent YouTube Comment Analyzer{% endblock %}

{% block content %}
<h1 class="text-2xl font-bold mb-4">Profile Settings</h1>

<div class="rounded-brand-lg shadow-card-base bg-white p-6 max-w-2xl">
  <form method="POST" action="{{ url_for('auth.profile_settings') }}" enctype="multipart/form-data" class="space-y-5">
    <div class="flex justify-center">
      <div class="relative inline-block text-center cursor-pointer">
        <label for="profile_image" class="cursor-pointer">
          {% if profile %}
          <img id="profile_preview" class="h-28 w-28 rounded-full object-cover border-2 border-dashed border-primary mx-auto"
               src="data:image/png;base64,{{ profile }}" alt="Profile">
          {% else %}
          <img id="profile_preview" class="h-28 w-28 rounded-full object-cover border-2 border-dashed border-primary mx-auto bg-app-bg"
               src="{{ url_for('static', filename='img/default_profile.jpeg') }}" alt="Profile">
          {% endif %}
          <div class="mt-2 text-sm font-medium text-primary">Click to change picture</div>
        </label>
        <input type="file" id="profile_image" name="profile_image" accept="image/*" class="hidden">
      </div>
    </div>

    <div>
      <label for="username" class="block text-sm font-medium mb-1">Username</label>
      <input type="text" id="username" name="username" value="{{ username }}" required
             class="w-full px-3 py-2 rounded-brand-md border border-border-light outline-none">
    </div>

    <div>
      <label for="new_password" class="block text-sm font-medium mb-1">New Password</label>
      <input type="password" id="new_password" name="new_password" placeholder="Enter new password" minlength="5"
             class="w-full px-3 py-2 rounded-brand-md border border-border-light outline-none">
    </div>

    <button type="submit" class="w-full py-3 rounded-brand-lg bg-brand-gradient text-white font-semibold shadow-button-primary hover:shadow-button-primary-hover transition flex items-center justify-center gap-2">
      <i class="fas fa-save"></i> Save Changes
    </button>
  </form>
</div>
{% endblock %}

{% block scripts %}
<script>
  document.getElementById('profile_image').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = evt => {
      const img = document.getElementById('profile_preview');
      img.src = evt.target.result;
    };
    reader.readAsDataURL(file);
  });
</script>
{% endblock %}
```

- [ ] **Step 2: Switch `auth.py`'s `profile_settings()` to `flash()` + `redirect()`**

Read `auth.py` first — `profile_settings()` currently is:
```python
@auth.route('/profile_settings', methods=['GET', 'POST'])
def profile_settings():
    # 1) Must be logged in
    username = session.get('user')
    if not username:
        return redirect(url_for('auth.login'))

    # 2) Handle form submit
    if request.method == 'POST':
        # new username + optional image + new password
        new_username = request.form['username']
        new_password = request.form.get('new_password') or None

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

        # call your DB update function
        success, msg = db.update_user_profile(
            old_username=username,
            new_username=new_username,
            new_password=new_password,
            profile_image_b64=profile_b64
        )
        if not success:
            return render_template(
                'profile_settings.html',
                username=username,
                profile=profile_b64 or db.get_user_profile_image(username),
                error=msg
            )
        # if username changed, update the session
        session['user'] = new_username
        username = new_username

    # 3) On GET (or after successful POST) fetch current values
    profile_b64 = db.get_user_profile_image(username)
    return render_template(
        'profile_settings.html',
        username=username,
        profile=profile_b64
    )
```

Change it to:
```python
@auth.route('/profile_settings', methods=['GET', 'POST'])
def profile_settings():
    # 1) Must be logged in
    username = session.get('user')
    if not username:
        return redirect(url_for('auth.login'))

    # 2) Handle form submit
    if request.method == 'POST':
        # new username + optional image + new password
        new_username = request.form['username']
        new_password = request.form.get('new_password') or None

        image_file = request.files.get('profile_image')
        profile_b64 = None
        if image_file and image_file.filename:
            raw_bytes = image_file.read()
            if len(raw_bytes) > MAX_PROFILE_IMAGE_BYTES:
                flash("Profile image too large — please use an image under 500KB.", "error")
                return redirect(url_for('auth.profile_settings'))
            profile_b64 = base64.b64encode(raw_bytes).decode('utf-8')

        # call your DB update function
        success, msg = db.update_user_profile(
            old_username=username,
            new_username=new_username,
            new_password=new_password,
            profile_image_b64=profile_b64
        )
        if not success:
            flash(msg, "error")
            return redirect(url_for('auth.profile_settings'))
        # if username changed, update the session
        session['user'] = new_username
        username = new_username
        return redirect(url_for('auth.profile_settings'))

    # 3) On GET fetch current values
    profile_b64 = db.get_user_profile_image(username)
    return render_template(
        'profile_settings.html',
        username=username,
        profile=profile_b64
    )
```

(Note the added `return redirect(url_for('auth.profile_settings'))` after a successful POST — this is a new line, not present in the original, needed because the original fell through to re-render the same template inline after a successful update; since there's nothing to flash on success, this could technically stay a direct render, but redirecting keeps the POST-redirect-GET pattern consistent for all three outcomes of this view and avoids a form-resubmission browser warning on refresh, which the original code was vulnerable to.)

- [ ] **Step 3: Manually verify**

```bash
venv/bin/python app.py &
sleep 20
curl -s -c /tmp/pc.txt -b /tmp/pc.txt -o /dev/null -w "GET /profile_settings (logged out): %{http_code}\n" http://127.0.0.1:5001/profile_settings
curl -s -c /tmp/pc.txt -b /tmp/pc.txt http://127.0.0.1:5001/profile_settings | grep -o 'profile_preview\|tailwind.css'
kill %1
```
Expected: first curl `302` (redirected to login, since not authenticated in this test — confirms the `if not username` guard still works); note that a full authenticated round-trip (actually updating a profile) requires a real logged-in session, which isn't practical to fabricate via curl alone without a valid account — if you have a way to log in first (e.g. reuse a cookie jar from a successful `/login` POST against a known test account, if one exists in the dev DB), do a full round trip; otherwise, note in your report that only the unauthenticated-redirect path and the template's static rendering (via a direct Jinja `test_request_context` render with fabricated `username`/`profile` context, similar to how Phase 1's `History_model.html` task verified its populated-card branch without live DB data) were verified, and that a live authenticated POST wasn't exercised — this is an acceptable, documented verification gap consistent with this project's approach (Phase 2A's final review already accepted an analogous gap for `register()`'s DB-failure path).

- [ ] **Step 4: Commit**

```bash
git add templates/profile_settings.html auth.py
git commit -m "Migrate profile_settings.html to base_dashboard.html, adopt flash() for profile errors"
```

---

### Task 2: Migrate `index.html`

**Files:**
- Modify: `templates/index.html` (full rewrite)

**Interfaces:**
- Consumes: `base_dashboard.html` (Phase 1), `static/myjs.js`'s existing (unmodified) submit-spinner logic (targets `document.querySelector('form')` / `getElementById('loadingSpinner')` — both present on this page, matching by design).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Replace `templates/index.html` in full**

```html
{% extends "base_dashboard.html" %}

{% block title %}Intelligent YouTube Comment Analyzer{% endblock %}

{% block content %}
<div class="mb-6">
  <form action="/analyze" method="POST" class="max-w-2xl mx-auto">
    <div class="flex rounded-brand-lg overflow-hidden shadow-card-base">
      <input type="text" class="flex-1 px-4 py-3 outline-none" id="videoLinkInput" name="video_link"
             placeholder="Enter YouTube Video Link Here" required>
      <button type="submit" class="px-6 bg-brand-gradient text-white font-semibold flex items-center gap-2">
        <i class="fas fa-search"></i> Analyze
      </button>
    </div>
  </form>
</div>

{% if modal_data %}
<div class="rounded-brand-lg shadow-card-base bg-white p-4 mb-6">
  <div class="flex flex-col sm:flex-row items-center sm:items-start gap-4">
    <img src="data:image/jpeg;base64,{{modal_data.thumbnail}}" alt="Video Thumbnail" class="rounded-brand-md w-40">
    <div>
      <h5 class="font-semibold text-lg">{{ modal_data.Video_Title }}</h5>
      <p class="text-sm mb-1"><i class="fas fa-user-circle me-1"></i> {{ modal_data.Channel_Name }}</p>
      <p class="text-sm mb-2"><i class="fas fa-hashtag me-1"></i> {{ modal_data.video_id }}</p>
      <div class="flex flex-wrap gap-2">
        <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium"><i class="fas fa-comments me-1"></i> {{ modal_data.total_fetched }} comments</span>
        <span class="px-3 py-1 rounded-full bg-app-bg text-text-muted text-xs font-medium"><i class="fas fa-language me-1"></i> {{ modal_data.total_english }} English</span>
      </div>
    </div>
  </div>
</div>

<div class="grid md:grid-cols-3 gap-4 mb-6" id="Comments-summary"
     data-positive="{{ modal_data.positive_count | default(0) }}"
     data-negative="{{ modal_data.negative_count | default(0) }}"
     data-neutral="{{ modal_data.neutral_count | default(0) }}">
  <div class="rounded-brand-lg shadow-card-base bg-white p-5">
    <div class="flex justify-between items-center mb-2">
      <h5 class="font-semibold"><i class="fas fa-smile me-2"></i>Positive Comments</h5>
      <span class="h-10 w-10 rounded-full bg-positive/10 text-positive flex items-center justify-center"><i class="fas fa-smile"></i></span>
    </div>
    <h1 class="text-4xl font-bold" id="positive-percentage">0%</h1>
    <p class="text-sm text-text-muted" id="positive-count">{{ modal_data.positive_count }} Positive comments detected</p>
    <div class="h-2 rounded-full bg-app-bg overflow-hidden mt-2">
      <div class="h-full bg-positive" role="progressbar" id="positive-progress" style="width: {{ modal_data.positive_count }}%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
    </div>
  </div>

  <div class="rounded-brand-lg shadow-card-base bg-white p-5">
    <div class="flex justify-between items-center mb-2">
      <h5 class="font-semibold"><i class="fas fa-frown me-2"></i>Negative Comments</h5>
      <span class="h-10 w-10 rounded-full bg-negative/10 text-negative flex items-center justify-center"><i class="fas fa-frown"></i></span>
    </div>
    <h1 class="text-4xl font-bold" id="negative-percentage">0%</h1>
    <p class="text-sm text-text-muted" id="negative-count">{{ modal_data.negative_count }} Negative comments detected</p>
    <div class="h-2 rounded-full bg-app-bg overflow-hidden mt-2">
      <div class="h-full bg-negative" role="progressbar" id="negative-progress" style="width: {{ modal_data.negative_count }}%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
    </div>
  </div>

  <div class="rounded-brand-lg shadow-card-base bg-white p-5">
    <div class="flex justify-between items-center mb-2">
      <h5 class="font-semibold"><i class="fas fa-meh me-2"></i>Neutral Comments</h5>
      <span class="h-10 w-10 rounded-full bg-neutral/10 text-neutral flex items-center justify-center"><i class="fas fa-meh"></i></span>
    </div>
    <h1 class="text-4xl font-bold" id="neutral-percentage">0%</h1>
    <p class="text-sm text-text-muted" id="neutral-count">{{ modal_data.neutral_count }} Neutral comments detected</p>
    <div class="h-2 rounded-full bg-app-bg overflow-hidden mt-2">
      <div class="h-full bg-neutral" role="progressbar" id="neutral-progress" style="width: {{ modal_data.neutral_count }}%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
    </div>
  </div>
</div>

<div class="grid md:grid-cols-2 gap-4 mb-6">
  {% if modal_data.bar_chart_id %}
  <div class="rounded-brand-lg shadow-card-base bg-white overflow-hidden">
    <div class="px-4 py-3 border-b border-border-lighter">
      <h5 class="font-semibold m-0"><i class="fas fa-chart-bar me-2"></i>Comments Analysis</h5>
    </div>
    <div class="p-4 text-center">
      <img class="max-w-full mx-auto" src="data:image/png;base64,{{ modal_data.bar_chart_id }}" alt="Comments Bar Chart">
    </div>
  </div>
  {% endif %}

  {% if modal_data.emoji_chart_id %}
  <div class="rounded-brand-lg shadow-card-base bg-white overflow-hidden">
    <div class="px-4 py-3 border-b border-border-lighter">
      <h5 class="font-semibold m-0"><i class="far fa-laugh-beam me-2"></i>Emoji Analysis</h5>
    </div>
    <div class="p-4 text-center">
      <img class="max-w-full mx-auto" src="data:image/png;base64,{{ modal_data.emoji_chart_id }}" alt="Emoji Chart">
    </div>
  </div>
  {% endif %}
</div>

<div class="grid lg:grid-cols-12 gap-4">
  <div class="lg:col-span-8 rounded-brand-lg shadow-card-base bg-white p-4">
    <h5 class="font-semibold mb-3"><i class="fas fa-lightbulb me-2"></i>Trending Topics &amp; Key Insights</h5>
    <h6 class="text-sm font-semibold mb-2"><i class="fas fa-hashtag me-2"></i>Trending Topics:</h6>
    {% if modal_data.trending_topics %}
    <div class="flex flex-wrap gap-2 mb-4">
      {% for topic in modal_data.trending_topics %}
      <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm">{{ topic }}</span>
      {% endfor %}
    </div>
    {% else %}
    <p class="text-sm text-text-muted">No trending topics available.</p>
    {% endif %}

    <hr class="border-border-lighter my-4">
    <h6 class="text-sm font-semibold mb-2"><i class="fas fa-brain me-2"></i>Key Insights:</h6>
    <div class="text-sm text-text-dark">
      {% if modal_data.key_insights %}
      {{ modal_data.key_insights | safe }}
      {% else %}
      <p>No key insights available.</p>
      {% endif %}
    </div>
  </div>

  <div class="lg:col-span-4 rounded-brand-lg shadow-card-base bg-white p-4">
    <h5 class="font-semibold mb-3"><i class="far fa-grin-beam me-2"></i>Emoji Usage Summary</h5>
    <table class="w-full text-sm">
      <thead>
        <tr class="text-left border-b border-border-lighter">
          <th class="py-2">Sentiment Type</th>
          <th class="py-2">Emoji Count</th>
        </tr>
      </thead>
      <tbody>
        <tr class="border-b border-border-lighter">
          <td class="py-2"><i class="fas fa-smile text-positive me-2"></i>Positive</td>
          <td class="py-2">{{ modal_data.positive_emoji | default('N/A') }}</td>
        </tr>
        <tr class="border-b border-border-lighter">
          <td class="py-2"><i class="fas fa-frown text-negative me-2"></i>Negative</td>
          <td class="py-2">{{ modal_data.negative_emoji | default('N/A') }}</td>
        </tr>
        <tr>
          <td class="py-2"><i class="fas fa-meh text-neutral me-2"></i>Neutral</td>
          <td class="py-2">{{ modal_data.neutral_emoji | default('N/A') }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

{% else %}
<div class="text-center mt-16">
  <i class="fas fa-search text-4xl mb-3 text-text-muted"></i>
  <h4 class="font-semibold">Ready to analyze</h4>
  <p class="text-text-muted">Enter a YouTube video link above and click Analyze to see the results.</p>
</div>
{% endif %}

{% if error_message %}
<div class="mt-4">
  {{ error_message|safe }}
</div>
{% endif %}
{% endblock %}

{% block scripts %}
<div class="fixed inset-0 bg-black/70 z-50 items-center justify-center" id="loadingSpinner" style="display: none;">
  <div class="text-center">
    <div class="animate-spin h-12 w-12 border-4 border-white/30 border-t-white rounded-full mx-auto"></div>
    <p class="mt-3 text-white">Analyzing comments...</p>
  </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        const summaryContainer = document.getElementById('Comments-summary');

        if (summaryContainer) {
            const positiveCount = parseInt(summaryContainer.getAttribute('data-positive') || '0', 10);
            const negativeCount = parseInt(summaryContainer.getAttribute('data-negative') || '0', 10);
            const neutralCount = parseInt(summaryContainer.getAttribute('data-neutral') || '0', 10);
            const totalComments = positiveCount + negativeCount + neutralCount;

            function calculateAndUpdate(count, total, percentageElId, countElId, progressElId) {
                const percentageEl = document.getElementById(percentageElId);
                const countEl = document.getElementById(countElId);
                const progressEl = document.getElementById(progressElId);
                let percentage = 0;

                if (total > 0) {
                    percentage = Math.round((count / total) * 100);
                }

                if (percentageEl) percentageEl.textContent = `${percentage}%`;
                if (countEl) countEl.textContent = `${count} ${countElId.split('-')[0]} comments detected`;
                if (progressEl) {
                    progressEl.style.width = `${percentage}%`;
                    progressEl.setAttribute('aria-valuenow', percentage);
                }
            }

            calculateAndUpdate(positiveCount, totalComments, 'positive-percentage', 'positive-count', 'positive-progress');
            calculateAndUpdate(negativeCount, totalComments, 'negative-percentage', 'negative-count', 'negative-progress');
            calculateAndUpdate(neutralCount, totalComments, 'neutral-percentage', 'neutral-count', 'neutral-progress');
        } else {
            console.log("Could not find the Comments-summary container.");
        }
    });
</script>
{% endblock %}
```

Note: the loading spinner `<div id="loadingSpinner">` is placed inside `{% block scripts %}` at the top (before the `<script>` tag) rather than in `{% block content %}` — this matches `base_dashboard.html`'s block ordering (the `scripts` block renders at the very end of `<body>`, same as the original page's own structure, where the spinner overlay was also placed near the end of the document, after the main content div, for the same `position: fixed` full-viewport-overlay reason). Its initial-hidden state uses an inline `style="display: none;"` attribute — deliberately NOT a Tailwind `hidden` class — because `static/myjs.js`'s existing (unmodified) submit-spinner logic directly manipulates `loadingSpinner.style.display = 'flex'` on form submit; using a Tailwind class here would create the same class-vs-inline-style mismatch bug this project already hit and fixed once with the dashboard sidebar (see the `2026-08-21-dashboard-sidebar-alpine-fix` plan) — matching `myjs.js`'s actual manipulation method avoids repeating it.

- [ ] **Step 2: Manually verify**

```bash
venv/bin/python app.py &
sleep 20
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/
curl -s http://127.0.0.1:5001/ | grep -o 'bootstrap\.min\.css\|bootstrap\.bundle\.min\.js'
curl -s http://127.0.0.1:5001/ | grep -o 'Ready to analyze\|videoLinkInput\|loadingSpinner\|Comments-summary'
kill %1
```
Expected: first curl `200`; second finds nothing (genuinely Bootstrap-free); third finds all four markers (this request has no `modal_data`, so the empty-state branch and the always-present search form/spinner render — the `modal_data`-populated branch can't be exercised without a real analysis run, which requires a live YouTube API key and takes real processing time; note this as a documented verification gap in your report, same category as Task 1's).

- [ ] **Step 3: Commit**

```bash
git add templates/index.html
git commit -m "Migrate index.html to base_dashboard.html (Bootstrap-free)"
```

---

### Task 3: Rebuild `static/tailwind.css` and final verification

**Files:**
- Modify: `static/tailwind.css` (regenerated)

**Interfaces:**
- Consumes: the state after Tasks 1-2 — every new Tailwind class both templates introduced.

- [ ] **Step 1: Rebuild**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
```

If `.tailwindcss-cli` is missing or not exactly 42,958,276 bytes, re-download (network in this sandbox can be slow — `-C -` resumes safely, just re-run the same command if it times out partway):
```bash
curl -sSL -C - --connect-timeout 15 --retry 3 --retry-delay 2 -o .tailwindcss-cli "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64" && chmod +x .tailwindcss-cli
```

- [ ] **Step 2: Verify the new classes actually compiled in**

```bash
grep -o '\.animate-spin\|\.border-t-white\|\.lg\\:col-span-8\|\.lg\\:col-span-4\|\.rounded-full\b' static/tailwind.css | sort -u
```
Expected: matches for all of them (spot-checking classes unique to `index.html`'s new markup that weren't used by any previously-migrated page).

- [ ] **Step 3: Full-site sanity check — every migrated page still returns 200**

```bash
venv/bin/python app.py &
sleep 20
for path in / /about /login /register /history /profile_settings; do
  curl -s -o /dev/null -w "$path: %{http_code}\n" http://127.0.0.1:5001/$path
done
kill %1
```
Expected: `/`, `/about`, `/login`, `/register` all `200`; `/history` and `/profile_settings` `302` (both redirect to login when not authenticated — this is correct, expected behavior, not a bug).

- [ ] **Step 4: Commit**

```bash
git add static/tailwind.css
git commit -m "Rebuild static/tailwind.css for Phase 2B (index.html, profile_settings.html)"
```

---

## Self-Review Notes

- **Spec coverage:** both remaining templates migrated, `flash()` adopted for the third and final auth view, CSS rebuilt within this plan (not deferred).
- **Type/naming consistency:** all IDs referenced by `static/myjs.js` (`sidebar`, `content`, `sidebarClose` — via `base_dashboard.html`/`_navbar_dashboard.html`, unchanged — and the generic `form`/`loadingSpinner` pair, newly matched by `index.html`) are exactly what the unmodified `myjs.js` expects; no renaming.
- **No placeholders:** every task has literal, complete file contents.
- **Scope check:** after this plan, ALL 7 original templates are on the new base-layout system. The only remaining work is Phase 2C: deleting `static/auth.css` and `static/dashboard.css` (both now fully unreferenced) and any final dead-code sweep — a separate, final plan.

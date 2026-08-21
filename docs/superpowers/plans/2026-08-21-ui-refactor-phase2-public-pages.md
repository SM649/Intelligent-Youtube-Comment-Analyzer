# UI Refactor Phase 2A: Public Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish migrating the three remaining `base_public.html`-family templates (`landing.html`, `login.html`, `register.html`) off Bootstrap, adopt Flask's `flash()` in `auth.py` for login/register errors (replacing the ad-hoc `error=` template variable), convert the two remaining Bootstrap-JS-dependent interactions (the FAQ accordion, the password show/hide toggle) to Alpine.js, and delete `static/pages.css` once nothing references it anymore.

**Architecture:** Same pattern established in Phase 1 — each template becomes `{% extends "base_public.html" %}` with Tailwind utility classes replacing Bootstrap, reusing the design tokens already defined in `tailwind.config.js`. New in this phase: Alpine's official Collapse plugin (one more CDN script, loaded before Alpine core) for the FAQ accordion's expand/collapse animation, and `auth.py`'s error-handling switching from "re-render the template with an `error` kwarg" to "flash + redirect" (a proper POST-redirect-GET pattern), which `_flash.html` (built in Phase 1, currently inert) starts actually rendering once these two templates extend `base_public.html`.

**Tech Stack:** Same as Phase 1 (Tailwind CSS v3 standalone CLI, Alpine.js v3 CDN, Font Awesome 6 + Bootstrap Icons, AOS 2.3.4) plus `@alpinejs/collapse` (official Alpine plugin, CDN, no build step).

**Spec:** `docs/superpowers/specs/2026-08-20-ui-refactor-design.md` (original design — this plan implements the "Phase 2" work that spec's "Out of scope"/plan's own "Next Step" section deferred). No new spec document; this plan's own design was confirmed in chat with the user before writing it.

## Global Constraints

- No Node/npm — Alpine's Collapse plugin is added via CDN `<script>` tag exactly like Alpine core already is.
- Bootstrap CSS/JS must be fully absent from all three migrated pages (Font Awesome, Bootstrap Icons, AOS, and now `@alpinejs/collapse` are all expected and fine).
- `auth.py`'s `login()` error path and all three of `register()`'s error paths change from `render_template(template, error=...)` to `flash(message, 'error')` + `redirect(url_for(...))`. No other view logic in `auth.py` changes.
- `static/pages.css` is deleted at the end of this plan (Task 5) — it is safe to do so within this plan because `templates/about.html` already stopped using it in Phase 1, and `templates/landing.html` (this plan's Task 4) is the only other template that ever referenced it. `static/auth.css` and `static/dashboard.css` are NOT touched by this plan — `templates/profile_settings.html` (not yet migrated) still depends on `auth.css`... actually depends on `dashboard.css`, and `login.html`/`register.html` currently link `auth.css`, which becomes unreferenced by THIS plan's end too, but is left in place for this plan and removed later alongside `dashboard.css`'s removal in the Phase 2 cleanup plan, to keep this plan's file-deletion blast radius limited to the one file (`pages.css`) that is unambiguously fully dead after this plan and nothing else.
- Verification is manual (real server + curl), same as every prior task in this project — no automated test suite exists. Actual click interactivity (accordion expand/collapse, password toggle, mobile nav) remains unverifiable without a browser — say so explicitly rather than overclaiming, same discipline as Phase 1.

---

## File Structure

**Modify:**
- `templates/base_public.html` — add the Alpine Collapse plugin CDN script.
- `templates/login.html` — full rewrite, `{% extends "base_public.html" %}`.
- `templates/register.html` — full rewrite, `{% extends "base_public.html" %}`.
- `templates/landing.html` — full rewrite, `{% extends "base_public.html" %}`.
- `auth.py` — `login()` and `register()` error paths switch to `flash()` + `redirect()`.

**Delete:**
- `static/pages.css` (Task 5, once confirmed unreferenced).

---

### Task 1: Add Alpine Collapse plugin to `base_public.html`

**Files:**
- Modify: `templates/base_public.html`

**Interfaces:**
- Produces: the `x-collapse` Alpine directive, available to any template extending `base_public.html` — consumed by Task 4's FAQ accordion.

- [ ] **Step 1: Add the plugin script before Alpine's core script**

In `templates/base_public.html`, change:
```html
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
```
to:
```html
  <script defer src="https://cdn.jsdelivr.net/npm/@alpinejs/collapse@3/dist/cdn.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
```
(Alpine plugins must load before Alpine's core script — this is Alpine's own documented requirement for the CDN-script installation method, not a convention specific to this project.)

- [ ] **Step 2: Manually verify no rendering error**

Run:
```bash
venv/bin/python app.py &
sleep 20
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/about
curl -s http://127.0.0.1:5001/about | grep -o '@alpinejs/collapse@3'
kill %1
```
Expected: `200`, then a match for `@alpinejs/collapse@3` (confirms the new script tag renders; `/about` is used here only because it's the one already-migrated `base_public.html` page available to test against — this task doesn't change `/about`'s behavior).

- [ ] **Step 3: Commit**

```bash
git add templates/base_public.html
git commit -m "Add Alpine Collapse plugin to base_public.html"
```

---

### Task 2: Migrate `login.html` + adopt `flash()` in `auth.py`'s `login()`

**Files:**
- Modify: `templates/login.html` (full rewrite)
- Modify: `auth.py:43-55` (the `login()` view)

**Interfaces:**
- Consumes: `base_public.html` (Task 1), transitively `_flash.html` (Phase 1).
- Produces: no interface other tasks depend on — this task is self-contained.

- [ ] **Step 1: Replace `templates/login.html` in full**

```html
{% extends "base_public.html" %}

{% block title %}Login – Intelligent YouTube Comment Analyzer{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto px-4 py-12">
  <div class="rounded-brand-lg shadow-card-base overflow-hidden bg-white" data-aos="fade-up" data-aos-duration="1000">
    <div class="bg-brand-gradient text-white text-center py-10 px-6">
      <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Logo" class="mx-auto mb-4 h-16 w-16">
      <h2 class="text-2xl font-bold mb-2">Welcome Back!</h2>
      <p class="text-white/90">Sign in to your account to access your YouTube comment analytics dashboard</p>
    </div>

    <div class="grid lg:grid-cols-12">
      <div class="lg:col-span-7 p-8">
        <form method="POST" action="{{ url_for('auth.login') }}" class="space-y-5">
          <div>
            <label for="email" class="block text-sm font-medium mb-1">Email Address</label>
            <div class="flex items-center rounded-brand-md border border-border-light overflow-hidden">
              <span class="px-3 bg-app-bg text-text-muted"><i class="bi bi-envelope"></i></span>
              <input type="email" id="email" name="email" placeholder="name@example.com" required
                     class="flex-1 px-3 py-2 outline-none">
            </div>
          </div>

          <div x-data="{ showPassword: false }">
            <label for="password" class="block text-sm font-medium mb-1">Password</label>
            <div class="flex items-center rounded-brand-md border border-border-light overflow-hidden">
              <span class="px-3 bg-app-bg text-text-muted"><i class="bi bi-lock"></i></span>
              <input :type="showPassword ? 'text' : 'password'" id="password" name="password" required
                     class="flex-1 px-3 py-2 outline-none">
              <button type="button" @click="showPassword = !showPassword" class="px-3 text-text-muted" aria-label="Toggle password visibility">
                <i class="bi" :class="showPassword ? 'bi-eye-slash-fill' : 'bi-eye-fill'"></i>
              </button>
            </div>
          </div>

          <button type="submit" class="w-full py-3 rounded-brand-lg bg-brand-gradient text-white font-semibold shadow-button-primary hover:shadow-button-primary-hover transition flex items-center justify-center gap-2">
            Sign In <i class="bi bi-arrow-right"></i>
          </button>
        </form>

        <div class="text-center text-text-muted text-sm my-5">OR</div>

        <p class="text-center text-sm">
          Don't have an account yet?
          <a href="{{ url_for('auth.register') }}" class="font-medium text-primary hover:underline">Create an account</a>
        </p>
      </div>

      <div class="hidden lg:block lg:col-span-5 bg-app-bg p-8">
        <h4 class="font-bold text-lg mb-4">Why Choose Our Platform?</h4>
        <div class="space-y-5">
          <div class="flex gap-3">
            <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center shrink-0"><i class="bi bi-graph-up"></i></div>
            <div>
              <h5 class="font-semibold mb-1">Advanced Analytics</h5>
              <p class="text-sm text-text-muted">Get detailed insights from your YouTube comments with AI-powered analysis</p>
            </div>
          </div>
          <div class="flex gap-3">
            <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center shrink-0"><i class="bi bi-lightning"></i></div>
            <div>
              <h5 class="font-semibold mb-1">Fast Processing</h5>
              <p class="text-sm text-text-muted">Our system analyzes thousands of comments in seconds</p>
            </div>
          </div>
          <div class="flex gap-3">
            <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center shrink-0"><i class="bi bi-shield-check"></i></div>
            <div>
              <h5 class="font-semibold mb-1">Secure &amp; Reliable</h5>
              <p class="text-sm text-text-muted">Your data is protected with enterprise-grade security</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Switch `auth.py`'s `login()` to `flash()` + `redirect()`**

Read `auth.py` first — `login()` is currently:
```python
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, user = db.verify_user(email, password)
        if success:
            session['user'] = user['username']
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid email or password")
    
    return render_template('login.html')
```
Change the failure branch's `return` line from:
```python
        return render_template('login.html', error="Invalid email or password")
```
to:
```python
        flash("Invalid email or password", "error")
        return redirect(url_for('auth.login'))
```
(`flash` is already imported at the top of `auth.py` — `from flask import Blueprint, render_template, request, redirect, url_for, session, flash` — no new import needed.)

- [ ] **Step 3: Manually verify**

```bash
venv/bin/python app.py &
sleep 20
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/login
curl -s http://127.0.0.1:5001/login | grep -o 'bootstrap\|showPassword\|tailwind.css' | sort -u
# Submit a bad login and confirm the flash message survives the redirect:
curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt -X POST http://127.0.0.1:5001/login \
  -d "email=nonexistent@example.com&password=wrong" -L -o /tmp/login_after.html -w "%{http_code}\n"
grep -o "Invalid email or password" /tmp/login_after.html
kill %1
```
Expected: first curl `200`; second finds `showPassword` and `tailwind.css` but no `bootstrap` (aside from `bootstrap-icons`, which is expected — grep for the literal word "bootstrap" will also match "bootstrap-icons", that's fine, just confirm there's no `bootstrap.min.css`/`bootstrap.bundle.min.js` anywhere in the raw output if you want to double check); the login POST returns `200` (after following the redirect) and the final page contains "Invalid email or password" (proving the flash message survived the redirect and `_flash.html` rendered it).

- [ ] **Step 4: Commit**

```bash
git add templates/login.html auth.py
git commit -m "Migrate login.html to base_public.html, adopt flash() for login errors"
```

---

### Task 3: Migrate `register.html` + adopt `flash()` in `auth.py`'s `register()`

**Files:**
- Modify: `templates/register.html` (full rewrite)
- Modify: `auth.py:57-93` (the `register()` view)

**Interfaces:**
- Consumes: `base_public.html` (Task 1).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Replace `templates/register.html` in full**

```html
{% extends "base_public.html" %}

{% block title %}Register – Intelligent YouTube Comment Analyzer{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto px-4 py-12">
  <div class="rounded-brand-lg shadow-card-base overflow-hidden bg-white" data-aos="fade-up" data-aos-duration="1000">
    <div class="bg-brand-gradient text-white text-center py-10 px-6">
      <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Logo" class="mx-auto mb-4 h-16 w-16">
      <h2 class="text-2xl font-bold mb-2">Create an Account</h2>
      <p class="text-white/90">Join our platform to unlock powerful YouTube comment analytics</p>
    </div>

    <div class="grid lg:grid-cols-12">
      <div class="lg:col-span-7 p-8">
        <form method="POST" action="{{ url_for('auth.register') }}" enctype="multipart/form-data" class="space-y-5">
          <div class="flex justify-center">
            <div class="relative inline-block text-center cursor-pointer">
              <label for="profile_image" class="cursor-pointer">
                <img id="profile_preview" class="h-24 w-24 rounded-full object-cover bg-app-bg border-2 border-dashed border-primary mx-auto"
                     src="{{ url_for('static', filename='img/default_profile.png') }}" alt="Profile">
                <div class="mt-2 text-sm font-medium text-primary"><i class="bi bi-camera-fill me-1"></i> Upload Photo</div>
              </label>
              <input type="file" id="profile_image" name="profile_image" accept="image/*" class="hidden" required>
            </div>
          </div>

          <div>
            <label for="username" class="block text-sm font-medium mb-1">Username</label>
            <div class="flex items-center rounded-brand-md border border-border-light overflow-hidden">
              <span class="px-3 bg-app-bg text-text-muted"><i class="bi bi-person"></i></span>
              <input type="text" id="username" name="username" placeholder="Choose a username" required
                     class="flex-1 px-3 py-2 outline-none">
            </div>
          </div>

          <div>
            <label for="email" class="block text-sm font-medium mb-1">Email Address</label>
            <div class="flex items-center rounded-brand-md border border-border-light overflow-hidden">
              <span class="px-3 bg-app-bg text-text-muted"><i class="bi bi-envelope"></i></span>
              <input type="email" id="email" name="email" placeholder="name@example.com" required
                     class="flex-1 px-3 py-2 outline-none">
            </div>
          </div>

          <div x-data="{ showPassword: false }">
            <label for="password" class="block text-sm font-medium mb-1">Password</label>
            <div class="flex items-center rounded-brand-md border border-border-light overflow-hidden">
              <span class="px-3 bg-app-bg text-text-muted"><i class="bi bi-lock"></i></span>
              <input :type="showPassword ? 'text' : 'password'" id="password" name="password" required minlength="5"
                     class="flex-1 px-3 py-2 outline-none">
              <button type="button" @click="showPassword = !showPassword" class="px-3 text-text-muted" aria-label="Toggle password visibility">
                <i class="bi" :class="showPassword ? 'bi-eye-slash-fill' : 'bi-eye-fill'"></i>
              </button>
            </div>
            <p class="text-xs text-text-muted mt-1"><i class="bi bi-info-circle me-1"></i>Choose strong Password to be secure.</p>
          </div>

          <button type="submit" class="w-full py-3 rounded-brand-lg bg-brand-gradient text-white font-semibold shadow-button-primary hover:shadow-button-primary-hover transition flex items-center justify-center gap-2">
            Create Account <i class="bi bi-arrow-right"></i>
          </button>

          <p class="text-center text-sm">
            Already have an account?
            <a href="{{ url_for('auth.login') }}" class="font-medium text-primary hover:underline">Sign in here</a>
          </p>
        </form>
      </div>

      <div class="hidden lg:block lg:col-span-5 bg-app-bg p-8">
        <h4 class="font-bold text-lg mb-4">Get Started in Minutes</h4>
        <div class="space-y-5">
          <div class="flex gap-3">
            <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center shrink-0"><i class="bi bi-person-plus"></i></div>
            <div>
              <h5 class="font-semibold mb-1">Create Your Profile</h5>
              <p class="text-sm text-text-muted">Set up your personalized account with just a few clicks</p>
            </div>
          </div>
          <div class="flex gap-3">
            <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center shrink-0"><i class="bi bi-youtube"></i></div>
            <div>
              <h5 class="font-semibold mb-1">Connect YouTube Videos</h5>
              <p class="text-sm text-text-muted">Easily analyze comments from any YouTube video</p>
            </div>
          </div>
          <div class="flex gap-3">
            <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center shrink-0"><i class="bi bi-graph-up"></i></div>
            <div>
              <h5 class="font-semibold mb-1">Gain Valuable Insights</h5>
              <p class="text-sm text-text-muted">Discover what viewers are saying about your content</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
  const profileInput = document.getElementById('profile_image');
  const profilePreview = document.getElementById('profile_preview');
  profileInput.addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = evt => profilePreview.src = evt.target.result;
    reader.readAsDataURL(file);
  });
</script>
{% endblock %}
```

- [ ] **Step 2: Switch `auth.py`'s `register()` to `flash()` + `redirect()`**

Read `auth.py` first — `register()` currently has three failure `return`s. Change each:

From:
```python
            return render_template('register.html', error=username_error)
```
to:
```python
            flash(username_error, "error")
            return redirect(url_for('auth.register'))
```

From:
```python
                return render_template('register.html', error="Profile image too large — please use an image under 500KB.")
```
to:
```python
                flash("Profile image too large — please use an image under 500KB.", "error")
                return redirect(url_for('auth.register'))
```

From:
```python
        else:
            return render_template('register.html', error=message)
```
to:
```python
        else:
            flash(message, "error")
            return redirect(url_for('auth.register'))
```

Leave the success branch (`return redirect(url_for('auth.login'))`) unchanged.

- [ ] **Step 3: Manually verify**

```bash
venv/bin/python app.py &
sleep 20
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/register
curl -s http://127.0.0.1:5001/register | grep -o 'showPassword\|tailwind.css\|profile_preview' | sort -u
# Submit an invalid username and confirm the flash message survives the redirect:
curl -s -c /tmp/cookies2.txt -b /tmp/cookies2.txt -X POST http://127.0.0.1:5001/register \
  -F "username=../bad" -F "email=test@example.com" -F "password=password123" \
  -L -o /tmp/register_after.html -w "%{http_code}\n"
grep -o "Username may only contain" /tmp/register_after.html
kill %1
```
Expected: first curl `200`; second finds all three markers; the register POST returns `200` after following the redirect and the final page contains the username-validation error message (proving flash + redirect works for `register()` too).

- [ ] **Step 4: Commit**

```bash
git add templates/register.html auth.py
git commit -m "Migrate register.html to base_public.html, adopt flash() for register errors"
```

---

### Task 4: Migrate `landing.html` + convert FAQ accordion to Alpine

**Files:**
- Modify: `templates/landing.html` (full rewrite)

**Interfaces:**
- Consumes: `base_public.html` (Task 1, for the Collapse plugin).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Replace `templates/landing.html` in full**

```html
{% extends "base_public.html" %}

{% block title %}Intelligent YouTube Comment Analyzer | Professional Insights{% endblock %}

{% block content %}
<header class="bg-brand-gradient text-white text-center py-24 md:py-32" id="home">
  <div class="max-w-3xl mx-auto px-4" data-aos="fade-up" data-aos-duration="1000">
    <h1 class="text-4xl md:text-5xl font-bold mb-4">Transform YouTube Comments Into Valuable Insights</h1>
    <p class="text-lg md:text-xl mb-8 text-white/90">Harness the power of AI to analyze sentiment, identify trends, and gain actionable intelligence from your video comments.</p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-white text-primary-dark font-semibold px-8 py-3 rounded-brand-lg hover:bg-white/90 transition">
      Start Analyzing Now <i class="bi bi-arrow-right"></i>
    </a>
  </div>
</header>

<section class="py-20" id="features">
  <div class="max-w-6xl mx-auto px-4">
    <div class="text-center max-w-2xl mx-auto mb-12" data-aos="fade-up">
      <h2 class="text-3xl font-bold mb-2">Powerful Features</h2>
      <p class="text-text-muted">Comprehensive tools to help you understand your audience better</p>
    </div>
    <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div class="rounded-brand-lg p-6 shadow-card-base hover:shadow-card-hover transition" data-aos="fade-up" data-aos-delay="100">
        <i class="bi bi-emoji-smile text-3xl text-primary mb-3"></i>
        <h4 class="font-semibold mb-2">Advanced Sentiment Analysis</h4>
        <p class="text-sm text-text-muted">Our AI analyzes comments to determine positive, negative, or neutral sentiment with more than 85% accuracy.</p>
      </div>
      <div class="rounded-brand-lg p-6 shadow-card-base hover:shadow-card-hover transition" data-aos="fade-up" data-aos-delay="200">
        <i class="bi bi-graph-up text-3xl text-primary mb-3"></i>
        <h4 class="font-semibold mb-2">Topic Detection</h4>
        <p class="text-sm text-text-muted">Automatically identify recurring themes and trending topics in your video comments.</p>
      </div>
      <div class="rounded-brand-lg p-6 shadow-card-base hover:shadow-card-hover transition" data-aos="fade-up" data-aos-delay="300">
        <i class="bi bi-bar-chart text-3xl text-primary mb-3"></i>
        <h4 class="font-semibold mb-2">Interactive Visualizations</h4>
        <p class="text-sm text-text-muted">Comprehensive charts and graphs that make data interpretation intuitive and actionable.</p>
      </div>
      <div class="rounded-brand-lg p-6 shadow-card-base hover:shadow-card-hover transition" data-aos="fade-up" data-aos-delay="400">
        <i class="bi bi-clock-history text-3xl text-primary mb-3"></i>
        <h4 class="font-semibold mb-2">Historical Analysis</h4>
        <p class="text-sm text-text-muted">Track sentiment changes over time to understand audience engagement evolution.</p>
      </div>
      <div class="rounded-brand-lg p-6 shadow-card-base hover:shadow-card-hover transition" data-aos="fade-up" data-aos-delay="500">
        <i class="bi bi-file-earmark-text text-3xl text-primary mb-3"></i>
        <h4 class="font-semibold mb-2">Detailed Reports</h4>
        <p class="text-sm text-text-muted">Unlock deep insights from every comment — emojis included! Our AI analyzes Emojis and meaning independently, so you don't miss a thing.</p>
      </div>
      <div class="rounded-brand-lg p-6 shadow-card-base hover:shadow-card-hover transition" data-aos="fade-up" data-aos-delay="600">
        <i class="bi bi-grid text-3xl text-primary mb-3"></i>
        <h4 class="font-semibold mb-2">Interactive System</h4>
        <p class="text-sm text-text-muted">Turn complex data into clear, interactive graphs. Get measurable insights that make decision-making easier than ever.</p>
      </div>
    </div>
  </div>
</section>

<section class="py-20 bg-white" id="how-it-works">
  <div class="max-w-4xl mx-auto px-4">
    <div class="text-center mb-12" data-aos="fade-up">
      <h2 class="text-3xl font-bold mb-2">How It Works</h2>
      <p class="text-text-muted">Simple steps to start analyzing your YouTube comments</p>
    </div>
    <div class="space-y-6">
      <div class="flex gap-4 items-start rounded-brand-lg p-5 shadow-card-base" data-aos="fade-up" data-aos-delay="100">
        <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center font-bold shrink-0">1</div>
        <div>
          <h4 class="font-semibold mb-1">Create an Account</h4>
          <p class="text-sm text-text-muted">Register for free and set up your profile to get started with our platform.</p>
        </div>
      </div>
      <div class="flex gap-4 items-start rounded-brand-lg p-5 shadow-card-base" data-aos="fade-up" data-aos-delay="200">
        <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center font-bold shrink-0">2</div>
        <div>
          <h4 class="font-semibold mb-1">Enter YouTube Video URL</h4>
          <p class="text-sm text-text-muted">Simply paste the URL of the YouTube video you want to analyze.</p>
        </div>
      </div>
      <div class="flex gap-4 items-start rounded-brand-lg p-5 shadow-card-base" data-aos="fade-up" data-aos-delay="300">
        <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center font-bold shrink-0">3</div>
        <div>
          <h4 class="font-semibold mb-1">Process Comments</h4>
          <p class="text-sm text-text-muted">Our AI automatically fetches and processes all comments from the video.</p>
        </div>
      </div>
      <div class="flex gap-4 items-start rounded-brand-lg p-5 shadow-card-base" data-aos="fade-up" data-aos-delay="400">
        <div class="h-10 w-10 rounded-full bg-brand-gradient text-white flex items-center justify-center font-bold shrink-0">4</div>
        <div>
          <h4 class="font-semibold mb-1">Review Insights</h4>
          <p class="text-sm text-text-muted">Explore the comprehensive analysis dashboard with visualized data and actionable insights.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="py-20 bg-brand-gradient text-white text-center">
  <div class="max-w-3xl mx-auto px-4" data-aos="fade-up">
    <h2 class="text-3xl md:text-4xl font-bold mb-4">Ready to Unlock Insights from Your YouTube Comments?</h2>
    <p class="text-lg mb-8 text-white/90">Join thousands of content creators and marketers who are making better content decisions using our AI-powered analysis platform.</p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-white text-primary-dark font-semibold px-8 py-3 rounded-brand-lg hover:bg-white/90 transition">
      Get Started Free <i class="bi bi-arrow-right"></i>
    </a>
  </div>
</section>

<section class="py-20" id="faq">
  <div class="max-w-3xl mx-auto px-4">
    <div class="text-center mb-12" data-aos="fade-up">
      <h2 class="text-3xl font-bold mb-2">Frequently Asked Questions</h2>
      <p class="text-text-muted">Common questions about our YouTube Comment Analysis platform</p>
    </div>

    <div class="space-y-3" data-aos="fade-up" data-aos-delay="100" x-data="{ openFaq: null }">
      <div class="rounded-brand-md border border-border-light overflow-hidden">
        <button type="button" @click="openFaq = openFaq === 1 ? null : 1" :aria-expanded="(openFaq === 1).toString()"
                class="w-full text-left px-4 py-3 font-medium flex justify-between items-center">
          How accurate is the sentiment analysis?
          <i class="bi bi-chevron-down transition-transform" :class="openFaq === 1 ? 'rotate-180' : ''"></i>
        </button>
        <div x-show="openFaq === 1" x-collapse class="px-4 pb-4 text-sm text-text-muted">
          Our sentiment analysis algorithm has been trained on millions of comments and achieves over 92% accuracy in identifying positive, negative, and neutral sentiments. It can also detect nuanced emotions like excitement, disappointment, and confusion.
        </div>
      </div>

      <div class="rounded-brand-md border border-border-light overflow-hidden">
        <button type="button" @click="openFaq = openFaq === 2 ? null : 2" :aria-expanded="(openFaq === 2).toString()"
                class="w-full text-left px-4 py-3 font-medium flex justify-between items-center">
          Is there a limit to how many videos I can analyze?
          <i class="bi bi-chevron-down transition-transform" :class="openFaq === 2 ? 'rotate-180' : ''"></i>
        </button>
        <div x-show="openFaq === 2" x-collapse class="px-4 pb-4 text-sm text-text-muted">
          Free accounts can analyze up to 5 videos per month with a cap of 1,000 comments per video. Premium accounts have higher or unlimited limits depending on the subscription tier. Check our pricing page for more details.
        </div>
      </div>

      <div class="rounded-brand-md border border-border-light overflow-hidden">
        <button type="button" @click="openFaq = openFaq === 3 ? null : 3" :aria-expanded="(openFaq === 3).toString()"
                class="w-full text-left px-4 py-3 font-medium flex justify-between items-center">
          Can I export the analysis results?
          <i class="bi bi-chevron-down transition-transform" :class="openFaq === 3 ? 'rotate-180' : ''"></i>
        </button>
        <div x-show="openFaq === 3" x-collapse class="px-4 pb-4 text-sm text-text-muted">
          Yes, all users can export results in multiple formats including PDF reports, CSV data files, and image exports of visualization charts. Premium users get additional export options including editable PowerPoint presentations.
        </div>
      </div>

      <div class="rounded-brand-md border border-border-light overflow-hidden">
        <button type="button" @click="openFaq = openFaq === 4 ? null : 4" :aria-expanded="(openFaq === 4).toString()"
                class="w-full text-left px-4 py-3 font-medium flex justify-between items-center">
          Does it work with non-English comments?
          <i class="bi bi-chevron-down transition-transform" :class="openFaq === 4 ? 'rotate-180' : ''"></i>
        </button>
        <div x-show="openFaq === 4" x-collapse class="px-4 pb-4 text-sm text-text-muted">
          Absolutely! Our platform supports comment analysis in over 30 languages, with the most accurate results in English, Spanish, French, German, Japanese, Chinese, and Arabic. We're continuously expanding our language capabilities.
        </div>
      </div>
    </div>
  </div>
</section>
{% endblock %}
```

Note: this rewrite drops the dead "Stats Section" and "Testimonials Section" (both were already-empty HTML comments in the original — see Phase 1's duplication survey — carrying no content to preserve) and does not carry over the animated-counter JS / `IntersectionObserver` code that targeted them, since that code had no section left to observe even before this migration (confirmed dead in the original file). It also drops the scroll-triggered navbar background change and the smooth-scroll-for-anchor-links script — `_navbar_public.html` (Phase 1) already gives the navbar a solid background at all times rather than a transparent-until-scrolled one (a deliberate Phase 1 simplification, see that plan's design notes), so there is nothing left for a "scrolled" class to visually change, and anchor links (`#features`, `#how-it-works`, `#faq`) still work as normal same-page jumps via the browser's native behavior without the smooth-scroll script — only the animation is lost, not the navigation.

- [ ] **Step 2: Manually verify**

```bash
venv/bin/python app.py &
sleep 20
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/
curl -s http://127.0.0.1:5001/ | grep -o 'bootstrap\.min\.css\|bootstrap\.bundle\.min\.js'
curl -s http://127.0.0.1:5001/ | grep -o 'x-data="{ openFaq: null }"\|x-collapse' | sort -u
kill %1
```
Expected: first curl `200`; second curl finds nothing (confirms genuine absence of the Bootstrap framework bundle — `bootstrap-icons` is a different, still-expected string and isn't matched by this pattern); third curl finds both patterns.

- [ ] **Step 3: Commit**

```bash
git add templates/landing.html
git commit -m "Migrate landing.html to base_public.html, convert FAQ accordion to Alpine"
```

---

### Task 5: Delete `static/pages.css`

**Files:**
- Delete: `static/pages.css`

**Interfaces:**
- Consumes: the state after Tasks 2-4 — confirms nothing references this file anymore.

- [ ] **Step 1: Confirm nothing references `pages.css` anymore**

```bash
grep -rl "pages.css" templates/
```
Expected: no output (empty — every template that used to link `pages.css` has been migrated: `about.html` in Phase 1, `landing.html` in this plan's Task 4).

- [ ] **Step 2: Delete the file**

```bash
git rm static/pages.css
```

- [ ] **Step 3: Manually verify nothing broke**

```bash
venv/bin/python app.py &
sleep 20
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/about
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/login
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/register
kill %1
```
Expected: all four `200` (deleting an unreferenced static file cannot break server-side rendering, but Flask would 404 the specific asset if some page still tried to load it — this confirms the whole app still boots and serves cleanly).

- [ ] **Step 4: Commit**

```bash
git commit -m "Delete static/pages.css (fully unreferenced after Phase 2A migration)"
```

---

## Self-Review Notes

- **Spec coverage:** all four items this plan set out to do — migrate `landing.html`/`login.html`/`register.html`, adopt `flash()` in `auth.py`, convert the FAQ accordion and password toggle to Alpine, delete `pages.css` — are each covered by a task above.
- **Type/naming consistency:** `showPassword` (password toggle) and `openFaq` (accordion) are each used consistently within their own scope; no name collides with `sidebarOpen`/`open`/`mobileOpen` used elsewhere in the app's other Alpine components (different templates, different `x-data` scopes, no shared state).
- **No placeholders:** every task has literal, complete file contents or literal before/after diffs — no "add appropriate styling" shortcuts.
- **Scope check:** `static/auth.css` and `static/dashboard.css` are deliberately NOT deleted by this plan (still needed by `templates/profile_settings.html`, not yet migrated) — that's the follow-up Phase 2B (dashboard pages) and Phase 2C (final cleanup) plans' job, not this one.

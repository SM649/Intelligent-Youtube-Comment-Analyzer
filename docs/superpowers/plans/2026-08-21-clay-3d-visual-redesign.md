# Clay + 3D Visual Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-skin the whole app (colors, dark mode, Claymorphism + 3D visual language) without changing page structure, routes, or Python code.

**Architecture:** The app already centralizes theming in `tailwind.config.js` (color/shadow/radius tokens consumed by every template). Instead of rewriting classes on every element, this plan repoints the *existing* token values to CSS custom properties defined in `static/tailwind-input.css` (one set under `:root`, one set under `.dark`). That single change re-themes almost the entire site — including dark mode — with zero template edits, because every `bg-app-bg`, `shadow-card-base`, `text-primary`, `bg-positive`, etc. already appears throughout the templates. Only four categories of template edits remain, each its own task below: (1) literal `bg-white` (not a token, doesn't respond to the new system) → `bg-surface`, (2) the six full-bleed `bg-brand-gradient text-white` hero/CTA bands, which need the clay-base + floating-blob look instead of a solid color fill, (3) the dashboard sidebar and public navbar, which are the deliberate flat/non-clay exceptions, and (4) the dark-mode toggle control + anti-flash script.

**Tech Stack:** Flask + Jinja2 templates, Tailwind CSS v3.4.17 (compiled via the existing `.tailwindcss-cli` binary, not npm), Alpine.js (already loaded via CDN), vanilla JS in `static/myjs.js`.

**Spec:** `docs/superpowers/specs/2026-08-21-clay-3d-visual-redesign-design.md`

## Global Constraints

- No new build tooling — keep using `./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify`, exactly as established in `docs/superpowers/plans/2026-08-20-ui-refactor-phase1-foundation.md`.
- `static/tailwind.css` MUST be rebuilt and committed after every task that touches `tailwind.config.js` or `static/tailwind-input.css` or adds a new class to a template — a stale compiled file was a prior Critical finding in this project (`docs/superpowers/plans/2026-08-21-dashboard-sidebar-alpine-fix.md`).
- No change to page/section structure (landing's hero → features → how-it-works → CTA → FAQ order, etc.) — this is a visual/token-level redesign only.
- Dark-mode toggle is client-side only (`localStorage`), no server/profile persistence, per the spec.
- Dashboard sidebar (`_navbar_dashboard.html`) and public navbar (`_navbar_public.html`) stay flat/non-clay; every other surface gets the full clay + 3D dual-shadow treatment.
- Sentiment colors keep their existing token names (`positive`/`negative`/`neutral`) — only their hex values change, so every existing `bg-positive`, `text-negative`, etc. across `index.html`, `History_model.html`, `_flash.html` keeps working unmodified.

---

### Task 1: Color/shadow/dark-mode token foundation

**Files:**
- Modify: `tailwind.config.js`
- Modify: `static/tailwind-input.css`
- Test: manual grep against the rebuilt `static/tailwind.css`

**Interfaces:**
- Produces: CSS custom properties `--clay-base`, `--clay-surface`, `--clay-text`, `--clay-muted`, `--clay-shadow-dark`, `--clay-shadow-light`, `--clay-border`, `--clay-sidebar-bg`, `--clay-blue`, `--clay-coral`, `--clay-neutral` (defined on `:root` and overridden on `.dark`) — every later task's dark-mode work depends on toggling the `dark` class on `<html>` to swap these.
- Produces: Tailwind utility classes `bg-app-bg`, `bg-surface`, `text-text-dark`, `text-text-muted`, `border-border-light`, `border-border-lighter`, `bg-positive`/`text-positive`, `bg-negative`/`text-negative`, `bg-neutral`/`text-neutral`, `text-primary`/`text-primary-dark`, `bg-brand-gradient`, `shadow-navbar`, `shadow-card-base`, `shadow-card-hover`, `shadow-button-primary`, `shadow-button-primary-hover` — all now driven by the CSS variables above. Later tasks consume these by name; none of their values are hardcoded in later tasks.
- Produces: a `.clay-blob` component class (dual inset-shadow, absolutely positioned, no pointer events) — Tasks 5 and 6 apply it to decorative hero shapes, setting only `width`/`height`/`top or bottom`/`left or right`/`background` inline per instance.

- [ ] **Step 1: Add the CSS custom properties to `static/tailwind-input.css`**

Replace the full file content with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

[x-cloak] {
  display: none !important;
}

:root {
  --clay-base: #e9edf5;
  --clay-surface: #f3f6fb;
  --clay-text: #2b3550;
  --clay-muted: #5b6478;
  --clay-shadow-dark: #c9d1e0;
  --clay-shadow-light: #ffffff;
  --clay-border: #e2e8f0;
  --clay-sidebar-bg: #dfe4ee;
  --clay-blue: #2f6fed;
  --clay-coral: #ff7a72;
  --clay-neutral: #d69e00;
}

.dark {
  --clay-base: #1a2036;
  --clay-surface: #222b47;
  --clay-text: #e2e8f0;
  --clay-muted: #94a3b8;
  --clay-shadow-dark: #11152355;
  --clay-shadow-light: #2c3760;
  --clay-border: #26314f;
  --clay-sidebar-bg: #15192c;
  --clay-blue: #5ac8fa;
  --clay-coral: #ff7a72;
  --clay-neutral: #f0b429;
}

@layer components {
  .clay-blob {
    border-radius: 9999px;
    position: absolute;
    pointer-events: none;
    box-shadow: inset 10px 10px 20px var(--clay-shadow-dark), inset -10px -10px 20px var(--clay-shadow-light);
  }
}
```

- [ ] **Step 2: Rewrite `tailwind.config.js` to consume the variables and enable class-based dark mode**

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        primary: 'var(--clay-blue)',
        'primary-dark': 'var(--clay-blue)',
        positive: 'var(--clay-blue)',
        negative: 'var(--clay-coral)',
        // NOTE: this shadows Tailwind's built-in neutral-50..950 grayscale palette by design — used for sentiment badges (bg-neutral/text-neutral), not the gray scale.
        neutral: 'var(--clay-neutral)',
        surface: 'var(--clay-surface)',
        'app-bg': 'var(--clay-base)',
        'text-dark': 'var(--clay-text)',
        'text-muted': 'var(--clay-muted)',
        'border-light': 'var(--clay-border)',
        'border-lighter': 'var(--clay-border)',
        'footer-dark': '#1a2036',
        'sidebar-bg': 'var(--clay-sidebar-bg)',
      },
      spacing: {
        sidebar: '280px',
      },
      borderRadius: {
        'brand-sm': '8px',
        'brand-md': '15px',
        'brand-lg': '30px',
      },
      boxShadow: {
        navbar: '0 8px 20px var(--clay-shadow-dark), 0 -2px 6px var(--clay-shadow-light)',
        'card-base': '6px 6px 14px var(--clay-shadow-dark), -6px -6px 14px var(--clay-shadow-light)',
        'card-hover': '8px 8px 18px var(--clay-shadow-dark), -8px -8px 18px var(--clay-shadow-light)',
        'input-focus': '0 0 0 3px rgba(255, 122, 114, 0.35)',
        'button-primary': '6px 6px 14px var(--clay-shadow-dark), -4px -4px 10px var(--clay-shadow-light)',
        'button-primary-hover': '8px 8px 18px var(--clay-shadow-dark), -6px -6px 14px var(--clay-shadow-light)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, var(--clay-coral) 0%, var(--clay-coral) 100%)',
      },
      fontFamily: {
        sans: ['Poppins', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

Note what was removed versus the old config: `primary-darker`, `gradient-start`, `gradient-end`, `brand-gradient-h`, `brand-gradient-h-hover`, `text-medium` — confirmed unused across `templates/` by grep before this task was written; do not re-add them.

- [ ] **Step 3: Rebuild `static/tailwind.css`**

Run:
```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
```
If `.tailwindcss-cli` is missing, download it first (same binary used by every prior phase of this project):
```bash
curl -sSL -C - --connect-timeout 15 --retry 3 --retry-delay 2 -o .tailwindcss-cli "https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64" && chmod +x .tailwindcss-cli
```

- [ ] **Step 4: Verify the compiled CSS contains the new tokens**

Run:
```bash
grep -c -- "--clay-base" static/tailwind.css
grep -c "e9edf5\|1a2036" static/tailwind.css
```
Expected: both commands print a number ≥ 1 (the custom properties and their light/dark hex values are present in the compiled output).

- [ ] **Step 5: Commit**

```bash
git add tailwind.config.js static/tailwind-input.css static/tailwind.css
git commit -m "Add clay+3D color/shadow tokens and class-based dark mode"
```

---

### Task 2: Dark-mode toggle (anti-flash script + control + persistence)

**Files:**
- Modify: `templates/base_dashboard.html`
- Modify: `templates/base_public.html`
- Modify: `static/myjs.js`
- Test: manual browser check (documented in Task 9) + grep check below

**Interfaces:**
- Consumes: the `.dark` class contract from Task 1 (toggling `dark` on `<html>` swaps every `--clay-*` variable).
- Produces: a global `window.toggleClayTheme()` function in `static/myjs.js` that later tasks' toggle buttons call via `onclick="toggleClayTheme()"`.

- [ ] **Step 1: Add the anti-flash script to `templates/base_dashboard.html`**

In `templates/base_dashboard.html`, immediately after the opening `<head>` tag (before the `<meta charset>` line is fine too, but keep it the very first thing so no paint happens before it runs):

```html
<head>
  <script>
    (function () {
      var stored = localStorage.getItem('theme');
      if (stored === 'dark') document.documentElement.classList.add('dark');
    })();
  </script>
  <meta charset="utf-8">
```

- [ ] **Step 2: Add the same anti-flash script to `templates/base_public.html`**

Same snippet, same position, in `templates/base_public.html`.

- [ ] **Step 3: Add the toggle function to `static/myjs.js`**

Append to `static/myjs.js`:

```js
function toggleClayTheme() {
  var root = document.documentElement;
  var isDark = root.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}
```

- [ ] **Step 4: Add a toggle button to the dashboard topbar in `templates/base_dashboard.html`**

Find the topbar `<div class="flex items-center justify-between">` block (inside `<nav id="topbar">`). It currently has three direct children: the hamburger button, the title link, and the profile-dropdown `<div x-data="{ open: false }" ...>`. Wrap the toggle button and that profile-dropdown div together in a new flex container, so the toggle doesn't become a fourth item competing for `justify-between` spacing:

Change the entire profile-dropdown block from:
```html
          <div x-data="{ open: false }" class="relative" @click.outside="open = false">
            {% if username %}
            <button type="button" @click="open = !open" class="flex items-center gap-2">
              <img src="data:image/png;base64,{{ profile }}" class="h-9 w-9 rounded-full object-cover" alt="Profile">
              <span class="hidden md:inline text-sm font-medium">{{ username }}</span>
            </button>
            <ul x-show="open" x-cloak class="absolute right-0 mt-2 w-48 bg-white rounded-brand-lg shadow-navbar p-2 text-sm z-50">
              <li>
                <a href="{{ url_for('auth.profile_settings') }}" class="flex items-center gap-2 px-3 py-2 rounded-brand-md hover:bg-primary/10 transition">
                  <i class="fas fa-user-cog"></i> Profile Settings
                </a>
              </li>
              <li class="border-t border-border-lighter my-1"></li>
              <li>
                <a href="{{ url_for('auth.logout') }}" class="flex items-center gap-2 px-3 py-2 rounded-brand-md hover:bg-primary/10 transition">
                  <i class="fas fa-sign-out-alt"></i> Logout
                </a>
              </li>
            </ul>
            {% else %}
            <a href="{{ url_for('auth.login') }}" class="flex items-center gap-2 text-sm font-medium">
              <i class="fas fa-sign-in-alt"></i> Login
            </a>
            {% endif %}
          </div>
```
to (wraps it with the toggle button so both sit together as one topbar-right group, and swaps the dropdown's literal `bg-white` for the token-driven `bg-surface`):
```html
          <div class="flex items-center gap-1">
            <button type="button" onclick="toggleClayTheme()" aria-label="Toggle dark mode"
                    class="text-text-dark px-3 py-2 rounded-brand-md hover:bg-border-light transition">
              <i class="fas fa-circle-half-stroke"></i>
            </button>

            <div x-data="{ open: false }" class="relative" @click.outside="open = false">
              {% if username %}
              <button type="button" @click="open = !open" class="flex items-center gap-2">
                <img src="data:image/png;base64,{{ profile }}" class="h-9 w-9 rounded-full object-cover" alt="Profile">
                <span class="hidden md:inline text-sm font-medium">{{ username }}</span>
              </button>
              <ul x-show="open" x-cloak class="absolute right-0 mt-2 w-48 bg-surface rounded-brand-lg shadow-navbar p-2 text-sm z-50">
                <li>
                  <a href="{{ url_for('auth.profile_settings') }}" class="flex items-center gap-2 px-3 py-2 rounded-brand-md hover:bg-primary/10 transition">
                    <i class="fas fa-user-cog"></i> Profile Settings
                  </a>
                </li>
                <li class="border-t border-border-lighter my-1"></li>
                <li>
                  <a href="{{ url_for('auth.logout') }}" class="flex items-center gap-2 px-3 py-2 rounded-brand-md hover:bg-primary/10 transition">
                    <i class="fas fa-sign-out-alt"></i> Logout
                  </a>
                </li>
              </ul>
              {% else %}
              <a href="{{ url_for('auth.login') }}" class="flex items-center gap-2 text-sm font-medium">
                <i class="fas fa-sign-in-alt"></i> Login
              </a>
              {% endif %}
            </div>
          </div>
```

- [ ] **Step 5: Add a matching toggle button to `templates/_navbar_public.html`**

Inside the `<ul class="hidden md:flex md:items-center md:gap-2">` list, add as the first `<li>`:

```html
        <li>
          <button type="button" onclick="toggleClayTheme()" aria-label="Toggle dark mode" class="px-3 py-2">
            <i class="fas fa-circle-half-stroke"></i>
          </button>
        </li>
```

And in the mobile `<ul id="public-nav-links" ...>` list, add as the first `<li>`:

```html
      <li>
        <button type="button" onclick="toggleClayTheme()" aria-label="Toggle dark mode" class="block px-4 py-2 font-medium">
          <i class="fas fa-circle-half-stroke"></i> Toggle theme
        </button>
      </li>
```

`base_public.html` does not currently load `static/myjs.js` — add it right before `{% block scripts %}{% endblock %}`:

```html
  <script src="{{ url_for('static', filename='myjs.js') }}"></script>
  {% block scripts %}{% endblock %}
```

- [ ] **Step 6: Verify**

Run:
```bash
grep -c "toggleClayTheme" static/myjs.js templates/base_dashboard.html templates/base_public.html templates/_navbar_public.html
grep -c "bg-white" templates/base_dashboard.html
```
Expected: the first command reports ≥ 1 for every file; the second reports `0` (the profile-dropdown menu's literal `bg-white` is now `bg-surface`).

Start the dev server (`python app.py`) and manually confirm in a browser: clicking the toggle flips the page between light and dark instantly, and reloading the page keeps the chosen theme (no flash of the other theme).

- [ ] **Step 7: Commit**

```bash
git add templates/base_dashboard.html templates/base_public.html templates/_navbar_public.html static/myjs.js
git commit -m "Add persisted client-side dark-mode toggle"
```

---

### Task 3: Dashboard sidebar — flat exception

**Files:**
- Modify: `templates/_navbar_dashboard.html`

**Interfaces:**
- Consumes: `sidebar-bg`, `app-bg`, `text-dark`, `text-muted`, `primary` (coral is now `var(--clay-coral)` via... actually coral has no dedicated Tailwind color token in Task 1; this task adds inline `text-[var(--clay-coral)]` for the active-state accent since no `coral` utility color was defined) from Task 1's tokens.

- [ ] **Step 1: Replace the sidebar's gradient background and link styling with the flat clay-accent treatment**

Replace the full content of `templates/_navbar_dashboard.html`:

```html
<nav id="sidebar" class="fixed top-0 left-0 h-screen w-sidebar bg-sidebar-bg text-text-dark z-40 flex flex-col transition-all duration-300 overflow-y-auto -ml-sidebar md:ml-0" :class="sidebarOpen && '!ml-0'" @click.outside="sidebarOpen = false">
  <div class="relative px-5 py-5 border-b border-border-light">
    <button type="button" @click="sidebarOpen = false" aria-label="Close sidebar" class="md:hidden absolute right-4 top-4 text-2xl leading-none">&times;</button>
    <div class="flex items-center gap-2">
      <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Logo" class="h-8 w-8">
      <h5 class="text-base font-semibold m-0">Comment Analyzer</h5>
    </div>
  </div>

  <div class="flex-1 py-3">
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
                  {{ 'border-[var(--clay-coral)] text-[var(--clay-coral)] font-semibold' if request.endpoint in ('history', 'auth.history') else 'border-transparent text-text-muted hover:text-text-dark' }}">
          <i class="bi bi-clock-history"></i> History
        </a>
      </li>
      <li class="my-1">
        <a href="{{ url_for('auth.profile_settings') }}"
           class="flex items-center gap-2 px-5 py-3 text-sm border-l-4 transition
                  {{ 'border-[var(--clay-coral)] text-[var(--clay-coral)] font-semibold' if request.endpoint == 'auth.profile_settings' else 'border-transparent text-text-muted hover:text-text-dark' }}">
          <i class="bi bi-gear-fill"></i> Profile Settings
        </a>
      </li>
    </ul>
  </div>
</nav>
```

- [ ] **Step 2: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
grep -c "bg-sidebar-bg" static/tailwind.css
```
Expected: ≥ 1.

Start the dev server, log in, and manually confirm: the sidebar is a flat panel (no gradient, no puffy shadow), and the current page's nav item is coral-colored with a coral left border while the others are muted gray.

- [ ] **Step 3: Commit**

```bash
git add templates/_navbar_dashboard.html static/tailwind.css
git commit -m "Make dashboard sidebar flat (clay exception)"
```

---

### Task 4: Public navbar — flat exception

**Files:**
- Modify: `templates/_navbar_public.html`

**Interfaces:**
- Consumes: `surface`, `text-dark`, `border-light` tokens from Task 1. Already consumes `toggleClayTheme()` from Task 2 (added in that task).

- [ ] **Step 1: Swap the gradient background and white text for the flat surface treatment**

Replace `templates/_navbar_public.html` (keeping the toggle `<li>`s added in Task 2) with:

```html
<nav x-data="{ mobileOpen: false }" class="fixed top-0 inset-x-0 z-50 bg-surface border-b border-border-light">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between h-16 md:h-20">
      <a href="{{ url_for('landing') }}" class="flex items-center gap-2 text-text-dark font-semibold text-lg">
        <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Logo" class="h-8 w-8 md:h-10 md:w-10">
        <span class="hidden sm:inline">Intelligent YouTube Comments Analyzer</span>
      </a>

      <button
        type="button"
        @click="mobileOpen = !mobileOpen"
        class="md:hidden text-text-dark p-2 rounded-brand-sm hover:bg-border-light"
        :aria-expanded="mobileOpen.toString()"
        aria-controls="public-nav-links"
        aria-label="Toggle navigation"
      >
        <i class="bi" :class="mobileOpen ? 'bi-x-lg' : 'bi-list'" style="font-size: 1.5rem;"></i>
      </button>

      <ul class="hidden md:flex md:items-center md:gap-2">
        <li>
          <button type="button" onclick="toggleClayTheme()" aria-label="Toggle dark mode" class="px-3 py-2 text-text-dark">
            <i class="fas fa-circle-half-stroke"></i>
          </button>
        </li>
        <li><a href="{{ url_for('landing') }}" class="block px-4 py-2 font-medium text-text-dark hover:text-primary transition">Home</a></li>
        <li><a href="{{ url_for('about') }}" class="block px-4 py-2 font-medium {{ 'underline' if request.endpoint == 'about' else '' }} text-text-dark hover:text-primary transition">About</a></li>
        <li><a href="{{ url_for('auth.login') }}" class="block px-4 py-2 font-medium {{ 'underline' if request.endpoint == 'auth.login' else '' }} text-text-dark hover:text-primary transition"><i class="fas fa-sign-in-alt me-1"></i> Login</a></li>
        <li><a href="{{ url_for('auth.register') }}" class="block px-4 py-2 rounded-brand-lg bg-primary/10 font-medium text-primary hover:bg-primary/20 transition"><i class="fas fa-user-plus me-1"></i> Register</a></li>
      </ul>
    </div>

    <ul id="public-nav-links" x-show="mobileOpen" x-cloak class="md:hidden pb-4 space-y-1">
      <li>
        <button type="button" onclick="toggleClayTheme()" aria-label="Toggle dark mode" class="block px-4 py-2 font-medium text-text-dark">
          <i class="fas fa-circle-half-stroke"></i> Toggle theme
        </button>
      </li>
      <li><a href="{{ url_for('landing') }}" class="block px-4 py-2 font-medium text-text-dark hover:bg-border-light rounded-brand-sm">Home</a></li>
      <li><a href="{{ url_for('about') }}" class="block px-4 py-2 font-medium text-text-dark hover:bg-border-light rounded-brand-sm">About</a></li>
      <li><a href="{{ url_for('auth.login') }}" class="block px-4 py-2 font-medium text-text-dark hover:bg-border-light rounded-brand-sm"><i class="fas fa-sign-in-alt me-1"></i> Login</a></li>
      <li><a href="{{ url_for('auth.register') }}" class="block px-4 py-2 font-medium text-text-dark hover:bg-border-light rounded-brand-sm"><i class="fas fa-user-plus me-1"></i> Register</a></li>
    </ul>
  </div>
</nav>
```

Also update `templates/base_public.html`: the `<main>` element currently assumes a solid-color navbar of fixed height; no change needed there (padding-top classes `pt-16 md:pt-20` already match the navbar's height, which is unchanged).

- [ ] **Step 2: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
python app.py &
sleep 2
curl -s http://127.0.0.1:5001/ | grep -o 'bg-gradient-start\|bg-surface' | sort -u
kill %1
```
Expected output: only `bg-surface` (no `bg-gradient-start` — confirms the old gradient class is gone from the rendered page).

- [ ] **Step 3: Commit**

```bash
git add templates/_navbar_public.html
git commit -m "Make public navbar flat (clay exception)"
```

---

### Task 5: Landing page — clay hero + section re-theme

**Files:**
- Modify: `templates/landing.html`

**Interfaces:**
- Consumes: `app-bg`, `surface`, `border-light`, `brand-gradient` (now solid coral), `card-base`/`card-hover` shadow tokens, all from Task 1.

- [ ] **Step 1: Replace the hero `<header>` with the clay-base + floating-blob treatment**

Replace:
```html
<header class="bg-brand-gradient text-white text-center py-24 md:py-32" id="home">
  <div class="max-w-3xl mx-auto px-4" data-aos="fade-up" data-aos-duration="1000">
    <h1 class="text-4xl md:text-5xl font-bold mb-4">Transform YouTube Comments Into Valuable Insights</h1>
    <p class="text-lg md:text-xl mb-8 text-white/90">Harness the power of AI to analyze sentiment, identify trends, and gain actionable intelligence from your video comments.</p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-white text-primary-dark font-semibold px-8 py-3 rounded-brand-lg hover:bg-white/90 transition">
      Start Analyzing Now <i class="bi bi-arrow-right"></i>
    </a>
  </div>
</header>
```
with:
```html
<header class="relative overflow-hidden bg-app-bg text-center py-24 md:py-32" id="home">
  <div class="clay-blob" style="width:180px;height:180px;top:-60px;left:-60px;background:var(--clay-surface);"></div>
  <div class="clay-blob" style="width:120px;height:120px;bottom:-30px;right:5%;background:var(--clay-coral);opacity:0.2;"></div>
  <div class="relative max-w-3xl mx-auto px-4" data-aos="fade-up" data-aos-duration="1000">
    <h1 class="text-4xl md:text-5xl font-bold mb-4 text-text-dark">Transform YouTube Comments Into Valuable Insights</h1>
    <p class="text-lg md:text-xl mb-8 text-text-muted">Harness the power of AI to analyze sentiment, identify trends, and gain actionable intelligence from your video comments.</p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-brand-gradient text-white font-semibold px-8 py-3 rounded-brand-lg shadow-button-primary hover:shadow-button-primary-hover transition">
      Start Analyzing Now <i class="bi bi-arrow-right"></i>
    </a>
  </div>
</header>
```

- [ ] **Step 2: Re-theme the "how it works" alternating section background**

Change `<section class="py-20 bg-white" id="how-it-works">` to `<section class="py-20 bg-surface" id="how-it-works">`.

- [ ] **Step 3: Replace the final CTA band the same way as the hero**

Replace:
```html
<section class="py-20 bg-brand-gradient text-white text-center">
  <div class="max-w-3xl mx-auto px-4" data-aos="fade-up">
    <h2 class="text-3xl md:text-4xl font-bold mb-4">Ready to Unlock Insights from Your YouTube Comments?</h2>
    <p class="text-lg mb-8 text-white/90">Join thousands of content creators and marketers who are making better content decisions using our AI-powered analysis platform.</p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-white text-primary-dark font-semibold px-8 py-3 rounded-brand-lg hover:bg-white/90 transition">
      Get Started Free <i class="bi bi-arrow-right"></i>
    </a>
  </div>
</section>
```
with:
```html
<section class="relative overflow-hidden py-20 bg-app-bg text-center">
  <div class="clay-blob" style="width:150px;height:150px;top:-40px;right:-40px;background:var(--clay-surface);"></div>
  <div class="relative max-w-3xl mx-auto px-4" data-aos="fade-up">
    <h2 class="text-3xl md:text-4xl font-bold mb-4 text-text-dark">Ready to Unlock Insights from Your YouTube Comments?</h2>
    <p class="text-lg mb-8 text-text-muted">Join thousands of content creators and marketers who are making better content decisions using our AI-powered analysis platform.</p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-brand-gradient text-white font-semibold px-8 py-3 rounded-brand-lg shadow-button-primary hover:shadow-button-primary-hover transition">
      Get Started Free <i class="bi bi-arrow-right"></i>
    </a>
  </div>
</section>
```

- [ ] **Step 4: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
python app.py &
sleep 2
curl -s http://127.0.0.1:5001/ | grep -o 'bg-brand-gradient text-white text-center py-24\|bg-app-bg text-center py-24' | sort -u
kill %1
```
Expected: `bg-app-bg text-center py-24` present, `bg-brand-gradient text-white text-center py-24` absent.

- [ ] **Step 5: Commit**

```bash
git add templates/landing.html
git commit -m "Re-theme landing page hero and CTA band for clay+3D"
```

---

### Task 6: About page — clay hero + section re-theme

**Files:**
- Modify: `templates/about.html`

**Interfaces:**
- Consumes: same tokens as Task 5.

- [ ] **Step 1: Replace the hero `<section>`**

Replace:
```html
<section class="text-center py-24 md:py-32 bg-brand-gradient text-white">
  <div class="max-w-4xl mx-auto px-4" data-aos="fade-up">
    <h1 class="text-4xl md:text-5xl font-bold mb-4">About Our System</h1>
    <p class="text-lg md:text-xl mb-8 text-white/90">
      Intelligent YouTube Comment Analyzer turns raw comments into clear insights for creators and
      marketers alike. Discover what your audience truly thinks.
    </p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-white text-primary-dark font-semibold px-8 py-3 rounded-brand-lg hover:bg-white/90 transition">
      Get Started <i class="bi bi-arrow-right"></i>
    </a>
  </div>
</section>
```
with:
```html
<section class="relative overflow-hidden text-center py-24 md:py-32 bg-app-bg">
  <div class="clay-blob" style="width:180px;height:180px;top:-60px;left:-60px;background:var(--clay-surface);"></div>
  <div class="relative max-w-4xl mx-auto px-4" data-aos="fade-up">
    <h1 class="text-4xl md:text-5xl font-bold mb-4 text-text-dark">About Our System</h1>
    <p class="text-lg md:text-xl mb-8 text-text-muted">
      Intelligent YouTube Comment Analyzer turns raw comments into clear insights for creators and
      marketers alike. Discover what your audience truly thinks.
    </p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-brand-gradient text-white font-semibold px-8 py-3 rounded-brand-lg shadow-button-primary hover:shadow-button-primary-hover transition">
      Get Started <i class="bi bi-arrow-right"></i>
    </a>
  </div>
</section>
```

- [ ] **Step 2: Re-theme the three alternating `bg-white` sections**

Change all three occurrences of `<section class="py-20 bg-white">` in `templates/about.html` (the "Key Features", "System's Limitation", and "Meet the Team" sections) to `<section class="py-20 bg-surface">`.

- [ ] **Step 3: Replace the final CTA band**

Replace:
```html
<section class="py-20 bg-brand-gradient text-white text-center">
  <div class="max-w-3xl mx-auto px-4" data-aos="fade-up">
    <h2 class="text-3xl md:text-4xl font-bold mb-4">Ready to Understand Your Audience?</h2>
    <p class="text-lg mb-8 text-white/90">Join thousands of content creators who are using data to improve their videos.</p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-white text-primary-dark font-semibold px-8 py-3 rounded-brand-lg hover:bg-white/90 transition">
      Get Started Now <i class="fas fa-chevron-right"></i>
    </a>
  </div>
</section>
```
with:
```html
<section class="relative overflow-hidden py-20 bg-app-bg text-center">
  <div class="clay-blob" style="width:150px;height:150px;top:-40px;right:-40px;background:var(--clay-surface);"></div>
  <div class="relative max-w-3xl mx-auto px-4" data-aos="fade-up">
    <h2 class="text-3xl md:text-4xl font-bold mb-4 text-text-dark">Ready to Understand Your Audience?</h2>
    <p class="text-lg mb-8 text-text-muted">Join thousands of content creators who are using data to improve their videos.</p>
    <a href="{{ url_for('auth.register') }}" class="inline-flex items-center gap-2 bg-brand-gradient text-white font-semibold px-8 py-3 rounded-brand-lg shadow-button-primary hover:shadow-button-primary-hover transition">
      Get Started Now <i class="fas fa-chevron-right"></i>
    </a>
  </div>
</section>
```

- [ ] **Step 4: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
python app.py &
sleep 2
curl -s http://127.0.0.1:5001/about | grep -c 'bg-white"' 
kill %1
```
Expected: `0` (no literal `bg-white"` class left in the rendered page — the trailing quote ensures `bg-white/90`-style opacity classes, if any remained, wouldn't false-match, but none should remain here regardless).

- [ ] **Step 5: Commit**

```bash
git add templates/about.html
git commit -m "Re-theme about page hero, sections, and CTA band for clay+3D"
```

---

### Task 7: Login & Register pages — clay card re-theme

**Files:**
- Modify: `templates/login.html`
- Modify: `templates/register.html`

**Interfaces:**
- Consumes: `surface`, `app-bg`, `brand-gradient` tokens from Task 1.

- [ ] **Step 1: In `templates/login.html`, swap the card's `bg-white` and header band**

Change:
```html
  <div class="rounded-brand-lg shadow-card-base overflow-hidden bg-white" data-aos="fade-up" data-aos-duration="1000">
    <div class="bg-brand-gradient text-white text-center py-10 px-6">
```
to:
```html
  <div class="rounded-brand-lg shadow-card-base overflow-hidden bg-surface" data-aos="fade-up" data-aos-duration="1000">
    <div class="bg-brand-gradient text-white text-center py-10 px-6 rounded-t-brand-lg">
```
(The header band stays solid coral here — unlike the full-page heroes in Task 5/6, this is a small contained card header, not a full-bleed section, so a solid clay-coral fill reads as a clean accent rather than an overwhelming wash. `rounded-t-brand-lg` keeps the corners consistent with the card now that it's not implicitly clipped by a page-width section.)

Then change the "Why Choose Our Platform?" panel background:
```html
      <div class="hidden lg:block lg:col-span-5 bg-app-bg p-8">
```
Leave this line unchanged — `bg-app-bg` already resolves via the new tokens automatically.

- [ ] **Step 2: In `templates/register.html`, make the same two changes**

Change:
```html
  <div class="rounded-brand-lg shadow-card-base overflow-hidden bg-white" data-aos="fade-up" data-aos-duration="1000">
    <div class="bg-brand-gradient text-white text-center py-10 px-6">
```
to:
```html
  <div class="rounded-brand-lg shadow-card-base overflow-hidden bg-surface" data-aos="fade-up" data-aos-duration="1000">
    <div class="bg-brand-gradient text-white text-center py-10 px-6 rounded-t-brand-lg">
```

- [ ] **Step 3: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
python app.py &
sleep 2
curl -s http://127.0.0.1:5001/login | grep -o 'bg-white"\|bg-surface' | sort -u
curl -s http://127.0.0.1:5001/register | grep -o 'bg-white"\|bg-surface' | sort -u
kill %1
```
Expected: both show `bg-surface` and neither shows `bg-white"`.

- [ ] **Step 4: Commit**

```bash
git add templates/login.html templates/register.html
git commit -m "Re-theme login/register cards for clay+3D"
```

---

### Task 8: Dashboard analyze page & profile settings — clay card re-theme + lazy images

**Files:**
- Modify: `templates/index.html`
- Modify: `templates/profile_settings.html`

**Interfaces:**
- Consumes: `surface` token from Task 1.

- [ ] **Step 1: In `templates/index.html`, replace every literal `bg-white` with `bg-surface`**

There are 8 occurrences (the video-info card, the three sentiment stat cards, the two chart containers, and the two insight/table panels). Change each `bg-white` to `bg-surface` — e.g.:
```html
<div class="rounded-brand-lg shadow-card-base bg-white p-4 mb-6">
```
becomes:
```html
<div class="rounded-brand-lg shadow-card-base bg-surface p-4 mb-6">
```
Apply this same substitution to all 8 occurrences in the file (lines with `bg-white p-4 mb-6`, `bg-white p-5` ×3, `bg-white overflow-hidden` ×2, `bg-white p-4` ×2).

- [ ] **Step 2: Add `loading="lazy"` to the base64 image tags in `templates/index.html`**

Change:
```html
    <img src="data:image/jpeg;base64,{{modal_data.thumbnail}}" alt="Video Thumbnail" class="rounded-brand-md w-40">
```
to:
```html
    <img src="data:image/jpeg;base64,{{modal_data.thumbnail}}" alt="Video Thumbnail" class="rounded-brand-md w-40" loading="lazy">
```
Change both chart `<img>` tags:
```html
    <img class="max-w-full mx-auto" src="data:image/png;base64,{{ modal_data.bar_chart_id }}" alt="Comments Bar Chart">
```
```html
    <img class="max-w-full mx-auto" src="data:image/png;base64,{{ modal_data.emoji_chart_id }}" alt="Emoji Chart">
```
to add `loading="lazy"` to each.

- [ ] **Step 3: In `templates/profile_settings.html`, swap `bg-white`**

Change:
```html
<div class="rounded-brand-lg shadow-card-base bg-white p-6 max-w-2xl">
```
to:
```html
<div class="rounded-brand-lg shadow-card-base bg-surface p-6 max-w-2xl">
```

- [ ] **Step 4: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
grep -c 'bg-white' templates/index.html templates/profile_settings.html
grep -c 'loading="lazy"' templates/index.html
```
Expected: first command prints `0` for both files; second prints `3`.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html templates/profile_settings.html
git commit -m "Re-theme analyze/profile pages for clay+3D, lazy-load chart images"
```

---

### Task 9: History page — clay card re-theme + lazy images, then full-site verification

**Files:**
- Modify: `templates/History_model.html`
- Test: full-site manual check across light/dark mode

**Interfaces:**
- Consumes: `surface` token from Task 1.

- [ ] **Step 1: Replace the three `bg-white` occurrences in `templates/History_model.html`**

Change:
```html
<div class="video-card rounded-brand-lg shadow-card-base hover:shadow-card-hover transition p-4 mb-4 bg-white">
```
to:
```html
<div class="video-card rounded-brand-lg shadow-card-base hover:shadow-card-hover transition p-4 mb-4 bg-surface">
```
Change both:
```html
          <div class="bg-white px-3 py-2 border-b border-border-lighter">
```
occurrences (the "Comments Chart" and "Emoji Chart" header strips) to:
```html
          <div class="bg-surface px-3 py-2 border-b border-border-lighter">
```

- [ ] **Step 2: Add `loading="lazy"` to the thumbnail and both chart images**

Change:
```html
      <img src="data:image/jpeg;base64,{{ analysis.thumbnail }}" alt="Thumbnail" class="rounded-brand-md w-full">
```
to add `loading="lazy"`, and do the same for the placeholder `<img>` immediately below it (the `{% else %}` branch), and for both:
```html
            <img src="data:image/png;base64,{{ analysis.bar_chart_id }}" alt="Comments Chart" class="max-w-full mx-auto">
```
```html
            <img src="data:image/png;base64,{{ analysis.emoji_chart_id }}" alt="Emoji Chart" class="max-w-full mx-auto">
```

- [ ] **Step 3: Rebuild CSS and verify**

```bash
./.tailwindcss-cli -i static/tailwind-input.css -o static/tailwind.css --config tailwind.config.js --minify
grep -c 'bg-white' templates/History_model.html
grep -c 'loading="lazy"' templates/History_model.html
grep -rn 'bg-white"' templates/
```
Expected: first command prints `0`; second prints `4`; the repo-wide sweep in the third command prints nothing at all (no template anywhere still has a literal `bg-white` card background — every occurrence found before this plan started has been replaced by Tasks 2, 5, 6, 7, 8, and this task).

- [ ] **Step 4: Full-site manual verification (both themes)**

Start the dev server:
```bash
python app.py
```
In a browser, visit each of these pages in **both** light mode (default) and dark mode (after clicking the toggle), and confirm no page shows a stray white/purple box that breaks the theme:
- `/` (landing) — hero blobs visible, coral CTA buttons, "how it works" section visibly alternates shade from the page background
- `/about` — hero blobs visible, three alternating sections visibly shade-shifted, feature/team cards show the puffy dual-shadow
- `/login`, `/register` — card header is solid coral, form panel is puffy
- register/log in, then `/` (dashboard/analyze) — sidebar stays flat in both themes while the topbar and result cards are puffy
- `/history` (with at least one saved analysis) — cards are puffy, images lazy-load (check Network tab: thumbnail/chart requests fire only as they scroll into view)
- `/profile_settings` — panel is puffy
- Reload any dashboard page — dark-mode choice persists (no flash of the other theme)

- [ ] **Step 5: Commit**

```bash
git add templates/History_model.html
git commit -m "Re-theme history page for clay+3D, lazy-load thumbnail/chart images"
```

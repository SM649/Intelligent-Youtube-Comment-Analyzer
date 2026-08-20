# Refactor Jinja templates and CSS/JS, replace Bootstrap with Tailwind

## Goal

Optimize the UI across all three axes the user asked for: visual/UX polish, performance, and
code quality. The concrete driver is that none of the 7 templates use Jinja inheritance —
each is a fully standalone HTML document — so head boilerplate, navbars, footers, and inline
scripts are copy-pasted 2-5 times each, and the same CSS shell rules (`.navbar`,
`.footer-text`, `.spinner-container`) are redefined independently and inconsistently across
`auth.css`/`dashboard.css`/`pages.css`.

## Current state (confirmed via code survey)

- **Zero Jinja inheritance**: no `{% extends %}`, `{% block %}`, `{% include %}`, or
  `{% macro %}` anywhere in `templates/`.
- **Duplicated blocks**: identical `<head>` boilerplate (charset/viewport/fonts/Bootstrap/Font
  Awesome/Bootstrap Icons CDN links/favicon) in all 7 templates; the public navbar duplicated
  byte-for-byte in `landing.html`, `about.html`, `login.html`, `register.html`; the dashboard
  sidebar+topbar duplicated in `index.html`, `History_model.html`, `profile_settings.html`;
  the public footer duplicated in `landing.html`/`about.html`; the AOS-init +
  navbar-scroll-shrink script duplicated across 4 templates; the password show/hide toggle
  script duplicated in `login.html`/`register.html`; a one-line copyright footer duplicated
  5 times.
- **`flash()` imported but never called** in `auth.py` — errors are passed as an ad-hoc
  `error=` template variable instead (`login.html`, `register.html`).
- **Both Bootstrap Icons and Font Awesome are genuinely used** across every template (9-25
  occurrences each per file) — neither can be dropped without re-doing every icon.
- **Existing design-token system**: `auth.css` and `dashboard.css` each define their own copy
  of the same CSS custom properties (`--theme-color-primary: #4361ee`, spacing scale, border
  radius scale, shadow tokens, gradients) with slight value drift between the two files
  instead of one shared source of truth.
- **Dead CSS/JS**: `pages.css`'s `.testimonial*` rules and `.stats-section` rule have no
  matching markup in `landing.html` (the sections were deleted, leaving empty HTML comments);
  `landing.html`'s inline script queries `.stats-section`, which no longer exists, so the
  handler silently no-ops.
- **No build tooling today**: plain CDN Bootstrap 5.3.3 + Font Awesome 6 + Bootstrap Icons,
  hand-written CSS/JS, deployed as a Docker image to Hugging Face Spaces (`Dockerfile` already
  exists from the Firebase migration work).

## Decisions (via brainstorming with the user)

- **Bootstrap is fully replaced**, CSS and JS both — not layered alongside Tailwind (the two
  frameworks' resets conflict, and running both is more surface area, not less).
- **Tailwind is compiled via the standalone CLI binary** (no Node/npm, no `package.json`), not
  the Play CDN `<script>` — the Play CDN JIT-compiles in the visitor's browser on every page
  load, which Tailwind's own docs call out as unsuitable for production and would work against
  the Performance goal.
- **Alpine.js (CDN script, no build step)** replaces the interactivity Bootstrap's JS bundle
  used to provide: navbar collapse/toggle, the profile dropdown, sidebar behavior, and the
  password show/hide toggle.
- **Font Awesome + Bootstrap Icons both stay** — icon-only usage, unrelated to Bootstrap's CSS
  or JS, and both are load-bearing across every template.
- **AOS (scroll animations) stays as-is** — a separate library, unrelated to Bootstrap.
- **`flash()` gets adopted** in `auth.py` for login/register errors, replacing the ad-hoc
  `error=` variable, since introducing a shared `_flash.html` partial is part of this refactor
  anyway.

## Template architecture

Two base layouts, matching the app's two visual "modes":

- `templates/base_public.html` — used by `landing.html`, `about.html`, `login.html`,
  `register.html`. Blocks: `title`, `head_extra`, `content`, `scripts`. Includes
  `_navbar_public.html` and `_footer.html`.
- `templates/base_dashboard.html` — used by `index.html`, `History_model.html`,
  `profile_settings.html`. Same block set. Includes `_navbar_dashboard.html` (sidebar + topbar
  + profile dropdown).

Shared partials (`templates/` root, `_`-prefixed by convention):

- `_navbar_public.html`, `_navbar_dashboard.html`, `_footer.html`
- `_flash.html` — renders `get_flashed_messages(with_categories=true)`, replaces the ad-hoc
  `error` variable rendering in `login.html`/`register.html`.

Each of the 7 page templates becomes `{% extends %}` + a `content` block with only what's
actually unique to that page, plus a `scripts` block for any page-specific JS.

## Styling system

- `static/tailwind-input.css` — the Tailwind entry file (`@tailwind base/components/utilities`
  plus any small custom CSS that doesn't fit utility classes, e.g. keyframe animations for the
  loading spinner).
- `tailwind.config.js` — `theme.extend` populated from the existing CSS custom properties
  (colors: `primary`/`primary-dark`/`primary-darker`/gradient start-end/etc.; spacing scale;
  border radius scale; box shadows), so the visual language carries over rather than being
  reinvented, and the auth.css/dashboard.css value drift gets resolved to one canonical value
  per token.
- `static/tailwind.css` — the compiled, purged, minified output. Committed to the repo so
  `python app.py` works locally with no setup. Regenerated fresh as part of the Docker build
  (see below), so production never silently depends on a stale committed file.
- `auth.css`, `dashboard.css`, `pages.css` are removed once their rules are ported to Tailwind
  utilities/config; the dead `.testimonial*`/`.stats-section` rules are dropped rather than
  ported, along with the dead `querySelector('.stats-section')` call in `landing.html`.

## Build & local dev

- Tailwind's standalone CLI binary is downloaded (a documented, pinned version) and used to
  compile `static/tailwind.css` from `static/tailwind-input.css` + `tailwind.config.js`.
- `scripts/tailwind-watch.sh` — thin wrapper that runs the same binary in `--watch` mode, for
  anyone actively editing markup/classes locally. Not required for `python app.py` to work —
  only needed when iterating on styles.
- `Dockerfile` gets one added stage/`RUN` step: fetch the same pinned CLI binary and run it
  once (non-watch) to produce a fresh `static/tailwind.css` at image build time, so the
  deployed image's CSS always matches the deployed templates/config even if the committed
  compiled file drifts.

## Testing / verification

- No automated test suite exists for the UI today (Flask app, no frontend test tooling) — this
  is confirmed manually: run `python app.py` locally, visit every one of the 7 pages
  (landing, about, login, register, index/analyze results, History, profile settings) in a
  browser, and confirm layout/interactivity (navbar toggle, dropdown, sidebar, password
  show/hide, AOS scroll animations) all work with Bootstrap fully removed.
- Rebuild the Docker image locally (or verify the added `RUN` step manually) to confirm
  `static/tailwind.css` regenerates without error before this ships.

## Out of scope

- No change to `app.py`/`analyses.py`/the analysis pipeline, Firestore schema, or auth logic
  beyond the `flash()` swap described above.
- No new component library beyond the shared partials/base layouts described above — button/
  card styling is done with Tailwind utility classes directly in templates, not extracted into
  Jinja macros, since the survey didn't find enough repetition of those specific elements to
  justify it (YAGNI).
- No icon-library consolidation (Font Awesome + Bootstrap Icons both stay).

# Clay + 3D Visual Redesign — Design Spec

**Date:** 2026-08-21
**Status:** Draft, pending user review

## Goal

Overhaul the app's visual design, color scheme, and structure for a stronger, more
engaging UI/UX, while keeping the current Tailwind CLI build pipeline (established in
`docs/superpowers/specs/2026-08-20-ui-refactor-design.md` and its phase plans) and adding
no new build tooling.

Decided through visual brainstorming (mockups in
`.superpowers/brainstorm/251273-1787314780/content/`, not committed):

1. **Palette** — "Slate & Coral", softened for Claymorphism.
2. **Light-first with a real, persisted dark-mode toggle** (not just `prefers-color-scheme`).
3. **Claymorphism + 3D** as the dominant visual language — puffy, dual-shadow extruded
   surfaces — applied broadly, with sidebar navigation deliberately kept flat as a
   structural exception.

## 1. Color tokens

Replace the current purple/indigo/gradient tokens in `tailwind.config.js` with a
CSS-variable-backed palette, so both the light and dark values live in one place and
components don't need `dark:` variants sprinkled everywhere.

`static/tailwind-input.css` gets new `:root` / `.dark` custom properties:

| Token | Light | Dark | Use |
|---|---|---|---|
| `--clay-base` | `#e9edf5` | `#1a2036` | page/app background |
| `--clay-surface` | `#f3f6fb` | `#222b47` | card/tile/panel fill |
| `--clay-text` | `#2b3550` | `#e2e8f0` | primary text |
| `--clay-muted` | `#5b6478` | `#94a3b8` | secondary text |
| `--clay-shadow-dark` | `#c9d1e0` | `#11152355` | dual-shadow dark side |
| `--clay-shadow-light` | `#ffffff` | `#2c3760` | dual-shadow light side |
| `--clay-border` | `#e2e8f0` | `#26314f` | hairline borders (forms, tables) |
| `--clay-coral` | `#ff7a72` | `#ff7a72` | primary accent — CTAs, negative sentiment |
| `--clay-blue` | `#2f6fed` | `#5ac8fa` | secondary accent — positive sentiment, data |

`positive`/`negative`/`neutral` sentiment colors stay as distinct tokens (not folded into
coral/blue) since `Model.py`/`emoji_analyzer.py` results are semantically 3-way, not just
accent choices — reuse `--clay-blue`-family for positive, `--clay-coral` for negative,
keep a muted amber/gold for neutral.

`tailwind.config.js` exposes these as `theme.extend.colors` pointing at `var(--clay-*)`
(e.g. `base: 'var(--clay-base)'`) so utilities like `bg-base`, `text-clay-muted` work
normally, and `darkMode: 'class'` is added so the toggle (not just OS preference) controls
which set of variables is active via a `.dark` class on `<html>`.

## 2. Dark-mode toggle

- `darkMode: 'class'` in `tailwind.config.js`.
- A small inline script in `<head>` of both `base_dashboard.html` and `base_public.html`,
  before the stylesheet link, reads `localStorage.theme` (`'dark'`/`'light'`) and applies
  the `dark` class to `<html>` immediately — avoids a flash of the wrong theme.
- A toggle control (🌗) added to the topbar (dashboard) and public navbar, wired via a
  small function in `static/myjs.js`: flips the `dark` class and writes the choice to
  `localStorage.theme`. No server/profile persistence in this pass — purely client-side.
  If no stored preference, default to light (per the "light-first" decision), ignoring OS
  `prefers-color-scheme` for the initial pick.

## 3. Claymorphism + 3D component system

Reusable classes added under `@layer components` in `static/tailwind-input.css`, built on
the tokens above, so templates use one class instead of repeating shadow declarations:

- `.clay-card` — `rounded-[20px] bg-[var(--clay-surface)] shadow-[6px_6px_14px_var(--clay-shadow-dark),-6px_-6px_14px_var(--clay-shadow-light)]`
- `.clay-btn` — same shadow treatment, `rounded-2xl`, coral fill, used for primary CTAs
- `.clay-tile` — smaller-radius variant for stat tiles / icon tiles
- `.clay-blob` — decorative background shape (`rounded-full`, inset dual-shadow), used
  sparingly behind hero copy — landing/about hero sections only, capped at 2 per hero to
  avoid visual noise and extra paint cost.

**Where full clay + 3D applies:** landing hero/features/CTA sections, about page, login
and register cards, the dashboard topbar, every dashboard content surface — stat cards,
chart containers, comment/history cards, profile settings panels, form inputs.

**Where it deliberately does NOT apply (flat, structural chrome):**
- Dashboard sidebar (`_navbar_dashboard.html`) — flat panel background, plain icons,
  coral color (not a shadow) marking the active item. Confirmed via mockup
  `full-preview-v2.html`.
- Public navbar (`_navbar_public.html`) — same reasoning extended by me, not separately
  mocked: a puffy nav bar reads oddly as a fixed top strip and every other site convention
  keeps nav chrome flat. **Flagging this for explicit confirmation** since only the
  sidebar was visually approved.
- Footer (`_footer.html`) — flat, minimal, unchanged in spirit.

## 4. Per-template scope

| Template | Change |
|---|---|
| `tailwind.config.js`, `static/tailwind-input.css` | New tokens, `darkMode:'class'`, `.clay-*` component classes |
| `base_public.html`, `base_dashboard.html` | Anti-flash dark-mode script, dark-mode toggle control, swap `bg-app-bg`/`bg-surface` etc. to new tokens |
| `landing.html`, `about.html` | Full clay+3D: hero gets 2 clay-blobs + `.clay-btn`, feature/step cards become `.clay-card` |
| `login.html`, `register.html` | Auth card becomes `.clay-card` |
| `index.html` | Analyze form + result cards become `.clay-card`/`.clay-tile` |
| `History_model.html` | Each `video-card` becomes `.clay-card`; sentiment count tiles become `.clay-tile`; add `loading="lazy"` to thumbnail/chart `<img>` tags (perf) |
| `profile_settings.html` | Panels become `.clay-card` |
| `_navbar_dashboard.html` | Sidebar stays flat (icon color/active-state only); topbar becomes `.clay-card`-style bar |
| `_navbar_public.html` | Stays flat (pending confirmation above) |
| `_footer.html`, `_flash.html` | Token color swap only, no structural change |

No page's section structure changes (landing's hero → features → how-it-works → CTA →
FAQ order stays); this is a visual/token-level redesign, not an information-architecture
change.

## 5. Performance

Addressing "best performance" from the original request, scoped to what's low-risk here:

- Add `loading="lazy"` to all base64 thumbnail/chart `<img>` tags (`History_model.html`,
  `index.html`) — these are the largest inline payloads on the page.
- Add `rel="preconnect"` for `fonts.googleapis.com`/`fonts.gstatic.com` and
  `font-display: swap` already implied by the Google Fonts URL — verify it's present.
- Cap clay-blob decorative shapes to hero sections only (2 max) — dual box-shadows are
  cheap individually but compound if scattered across many small elements; avoid nesting
  a `.clay-card` inside another `.clay-card`.
- No change to the two icon-font CDNs (Font Awesome + Bootstrap Icons) in this pass —
  consolidating to one is a separate, unrelated cleanup and out of scope here.

## 6. Testing

- Rebuild `static/tailwind.css` via the existing `./.tailwindcss-cli` pipeline after every
  template/config/CSS change (per the established process — a stale compiled file was a
  prior Critical finding, per `docs/superpowers/plans/2026-08-21-dashboard-sidebar-alpine-fix.md`).
- Manually verify each page in both light and dark mode via the running dev server
  (`python app.py`), covering: landing, about, login, register, dashboard/index, history
  (with ≥1 saved analysis), profile settings.
- Confirm the dark-mode preference persists across a reload and across pages.
- Confirm sidebar/navbar remain flat and legible in both themes.

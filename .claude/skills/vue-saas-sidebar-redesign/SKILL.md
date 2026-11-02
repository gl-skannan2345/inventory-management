---
name: vue-saas-sidebar-redesign
description: Redesigns this Vue 3 app's UI into a modern SaaS-style layout with a vertical navigation sidebar on the left instead of the top nav bar, a consistent spacing scale, and a polished professional look. Use this skill whenever the user asks to move navigation to a sidebar, make the app look more like a SaaS product, modernize or polish the UI, add a left nav, fix inconsistent spacing or padding across views, or give the app a professional dashboard look, even if they don't say "redesign" or "sidebar" explicitly. Also use it when the user mentions collapsing navigation, nav tabs feeling cramped, or wanting the app to match tools like Linear, Stripe, or Notion in look and feel.
---

# Vue SaaS Sidebar Redesign

This skill converts the inventory client (Vue 3 + Vite, under `client/`) from a horizontal top nav into a SaaS-style shell: a left sidebar for navigation, a consistent spacing scale, and a restrained professional visual system. The goal is that every view looks like it belongs to one product, while the data and behavior stay exactly as they are.

## Before you start

Read these files so you work from the current code, not from memory:

- `client/src/App.vue`: the current shell. It has a `header.top-nav` with `.logo`, `nav.nav-tabs` (router links with `$route.path` active checks), `LanguageSwitcher`, `ProfileMenu`, then `FilterBar`, then `main.main-content` with `<router-view />`. Its `<style>` block (around line 168) holds the global styles.
- `client/CLAUDE.md`: the palette (`#0f172a`, `#64748b`, `#e2e8f0`), the "no emojis in UI" rule, and the Composition API conventions.
- `client/src/components/FilterBar.vue`, `ProfileMenu.vue`, `LanguageSwitcher.vue`: these sit in the header today and must be relocated into the new shell, not deleted.
- `client/src/locales/en.js` and `ja.js`: nav labels come from `t('nav.*')`. Keep using those keys, and add any new keys to both files.

## The non-negotiable rule: delegate `.vue` work

Root `CLAUDE.md` says any creation or significant modification of a `.vue` file must go to the vue-expert agent. This redesign is almost entirely `.vue` work (App.vue, the new sidebar component, and view styles), so spawn vue-expert for it and give it this skill's spec. Do the non-`.vue` parts yourself: a new `client/src/styles/tokens.css` (or equivalent) and any locale key additions.

## Target structure

```
.app-shell (CSS grid: sidebar | content)
├── AppSidebar.vue      vertical nav: logo, grouped links, footer with language + profile
├── .app-main
│   ├── AppTopBar       page title + FilterBar (slim, sits above content, not a nav)
│   └── main.main-content  <router-view />
└── modals (ProfileDetailsModal, TasksModal) unchanged
```

Design decisions and why:

- **Sidebar on the left, fixed width (about 240px expanded, 72px collapsed).** Vertical lists scale to more destinations than a horizontal bar, which is why the current bar with seven tabs is already crowded. Labels stay visible when expanded and collapse to icons or initials when narrow.
- **Group the links.** Overview, Inventory, Orders, Demand, Restocking, Finance, Reports are different kinds of work. Two or three small groups with headings (for example "Operations": Inventory, Orders, Restocking; "Planning": Demand, Reports; "Finance": Spending) make the sidebar scannable. Keep Overview at the top, unlabeled.
- **Active state is a left accent bar plus a tinted background**, not a bold underline. Use `router-link`'s `active` class or `$route.path`, matching the current code's approach.
- **Move the profile and language controls to the sidebar footer**, so the top of the page is free for the page title and filters.
- **Responsive:** below about 768px the sidebar becomes an off-canvas drawer opened by a hamburger button in a slim top bar. The page must have no horizontal scroll at 375px width, with a 16px side gutter.

## Spacing scale

Use one scale everywhere instead of ad hoc pixel values. Define these as CSS custom properties on `:root`:

| Token | Value | Use |
|---|---|---|
| `--space-1` | 4px | icon-to-label gaps |
| `--space-2` | 8px | tight groups, chip padding |
| `--space-3` | 12px | list item padding |
| `--space-4` | 16px | card inner padding on mobile, page gutter |
| `--space-5` | 20px | gaps between related cards |
| `--space-6` | 24px | card inner padding on desktop, section gaps |
| `--space-8` | 32px | gaps between page sections |

Why a scale: when every view picks its own 13px or 18px, the app looks unfinished even when each view is fine on its own. Replace hard-coded `padding`, `margin`, and `gap` values in the views with these tokens as you touch them. Do not do a mechanical find-and-replace across every file in one pass. Views that are not in scope stay as they are.

## Visual system

- **Palette:** keep the slate family from `client/CLAUDE.md`. Backgrounds `#f8fafc` (page) and `#ffffff` (cards), borders `#e2e8f0`, secondary text `#64748b`, primary text `#0f172a`. Status colors stay green, blue, yellow, red. Put these on `:root` as tokens.
- **Sidebar:** a slightly darker surface than the page (`#0f172a` background with light text is the classic SaaS look). Keep contrast at WCAG AA: at least 4.5:1 for text.
- **Typography:** one system font stack, a 14px base for dense tables and 15px for body, 20 to 24px for page titles, weight 600 for headings. Avoid more than three font sizes on one screen.
- **Cards:** 1px border, 8 to 12px radius, no heavy shadow. A faint `box-shadow` on hover for clickable cards only.
- **No emojis in UI.** Use simple inline SVG icons if the sidebar needs icons, with `aria-hidden="true"` and a visible text label or `aria-label`.
- **Dark mode:** if you add it, define tokens under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`, and also under `:root[data-theme="dark"]`, and give `body` an explicit background. This keeps the two modes from drifting apart.

## Things that must keep working

Check each of these after the redesign. They are the most likely to break when a shell is restructured.

1. **All seven routes** (`/`, `/inventory`, `/orders`, `/spending`, `/demand`, `/restocking`, `/reports`) still render in `client/src/main.js` and show the correct active link.
2. **FilterBar** still drives the same filters. Dashboard, Inventory, Orders, and Restocking depend on them. The filter state lives in `composables/useFilters.js`, so moving the component should not change behavior.
3. **Language switcher** still switches `en` and `ja`, and the sidebar labels update.
4. **Profile menu and modals** still open from the new location. `ProfileDetailsModal` and `TasksModal` are rendered from `App.vue`, so keep them there.
5. **Hard-coded labels:** the Reports link uses the literal text "Reports" instead of `t(...)`. Fix it while you're in there, and add a locale key for it.
6. **Keyboard and focus:** the sidebar links are real `<a>` elements (`router-link`), focus rings stay visible, and the mobile drawer traps focus while open and closes on Escape.

## Verification

Do not call the work done until you've checked it in a browser.

1. Start the app with the `start` skill or `npm run dev` in `client/`. Frontend is http://localhost:3000, API is http://localhost:8001.
2. Use the Playwright MCP tools (`mcp__playwright__*`) to visit every route at 1280px and 375px width. Take a screenshot of each. Check for horizontal scroll, overlapping elements, and truncated labels.
3. Click each sidebar link and confirm the URL and active state change. Switch language and confirm the sidebar text changes.
4. Run `npm run build` in `client/` and confirm it passes.
5. Run `cd tests && uv run --project ../server pytest backend/ -q`. The redesign should not touch the backend, so this is a sanity check.

## Scope

- In scope: layout shell, navigation, spacing and typography tokens, palette tokens, styling of the shell, and light spacing or typography cleanup in views that the user asked about.
- Out of scope unless the user asks: new features, data changes, API changes, rewriting view logic, or changing chart implementations.

## Reporting back

When you finish, tell the user:

- which files changed and which were delegated to vue-expert
- the spacing and palette tokens you defined
- which screenshots you checked, and anything that still looks off
- whether the build and tests passed

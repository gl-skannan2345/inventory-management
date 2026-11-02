---
name: vue-component-analysis
description: Analyze Vue 3 single-file components for structural problems and suggest performance and code-reuse improvements. Use when the user asks to review, audit, or optimize Vue components or views, find duplicated UI or logic, reduce component size, check reactivity or rendering cost, or asks what to refactor in client/src. Produces a prioritized report with file and line references. Does not edit files unless the user asks for fixes.
---

# Vue Component Analysis

Find where Vue components are slow to render, hard to reuse, or doing too much, and report it with evidence. The output is a ranked list of suggestions. It is not a rewrite.

## Scope

Default target: `client/src/**/*.vue` (views in `client/src/views/`, shared pieces in `client/src/components/`, `App.vue`). If the user names a file or folder, limit the analysis to that.

## Workflow

1. **Run the metrics helper first.** It counts measurable signals and flags components over thresholds:

   ```bash
   python3 .claude/skills/vue-component-analysis/scripts/vue_metrics.py client/src
   python3 .claude/skills/vue-component-analysis/scripts/vue_metrics.py --json client/src/views/Dashboard.vue
   ```

   It is regex-based and approximate. Treat every flag as a lead to check, not a finding.

2. **Verify each flag in the source.** Open the flagged lines with Read or grep. Drop flags that do not hold. Example: a `v-for` flagged as index-keyed may already use `item.id` on the same element.

3. **Read the largest components in full** (the top few by line count and flag count). The metrics cannot see intent, so judge reuse and structure by reading.

4. **Check the categories below.** Only report what you verified.

5. **Write the report** in the format at the end.

## What to Look For

### Performance

- **`v-for` keyed on index** (`:key="index"`, `:key="idx"`). Use a stable domain id (`id`, `sku`, `month`). Index keys break reuse when lists reorder or filter. Project rule: CLAUDE.md, "Common Issues" #1.
- **Template function calls that run on every render.** Calls like `formatX(...)`, `getForecastsByTrend('x').slice(0, 5)` inside `v-for` or interpolation recompute each render. Suggest a `computed`, or a `computed` returning a map keyed by argument.
- **Derived data stored or recomputed incorrectly.** Project rule: raw data in refs, derived data in computed. Flag a `ref` that is kept in sync by a `watch`, since the value can usually be a `computed`.
- **Watchers that should be computed.** A `watch` whose only job is to set another ref from a source ref.
- **Large arrays in deep `ref`.** `ref([...])` with thousands of rows makes Vue wrap every item in a proxy. Suggest `shallowRef` when the data is replaced wholesale and not mutated item by item.
- **Heavy work in `onMounted` or setup that is not needed on first paint.** Candidates for lazy loading or `defineAsyncComponent`, such as large modals that are rarely opened.
- **`v-if` vs `v-show`.** Frequently toggled, expensive subtrees should use `v-show`. Rarely shown ones should stay `v-if`.
- **Unbounded rendering.** Long tables or lists rendered without a limit, pagination, or a `slice` where the design only needs a preview.
- **Inline object or array literals in template bindings** (e.g. `:style="{ ... }"` built per item) when they could be a computed or a class.

### Code Reuse

- **Copy-pasted markup.** Repeated template blocks (the metrics helper flags repeated lines). Suggest a shared component with props, or a `v-for` over a config array.
- **Repeated script logic across views.** The same fetch-and-filter, formatting, or date-handling code in several views. Suggest a composable in `client/src/composables/` (create the folder only if the user agrees). Check that `client/src/api.js` is not already doing it.
- **Duplicate formatting helpers.** Currency, number, and date formatting defined in more than one file. Suggest one shared util.
- **Repeated modal or table scaffolding.** Several `*DetailModal.vue` files may share the same shell (overlay, header, close, body). Suggest a base modal component only where the shells really match.
- **Hard-coded hex colors** in `<style>` where `client/src/styles/tokens.css` already defines a token. Use the token.

### Structure and Size

- **Oversized components.** Files over ~400 lines or script blocks over ~250 lines usually mix concerns. Suggest splitting by responsibility: a data composable, a presentational child, a filter bar.
- **Too many props, emits, or watchers** for one component. A high count often means the parent should own more state, or the component should be split.
- **Prop drilling.** Props passed through two or more levels without being used in the middle component.
- **Dead code.** Unused imports, unused computed or functions, components registered but never used in the template. Verify with grep before reporting.
- **Missing component registration.** A component used in a template but not imported or registered. Vue logs `Failed to resolve component`. This is a bug, not a style issue; report it first.

### Correctness Checks That Affect Performance or Reuse

- **Dates.** Calls to `.getMonth()`, `.getFullYear()`, or `.getDate()` without validating the date first. Project rule: CLAUDE.md, "Common Issues" #2. The helper's check is coarse, so read the code before flagging.
- **Filters not applied.** Views that should respect the four global filters (Time Period, Warehouse, Category, Order Status) but do not. Project rule: CLAUDE.md, "Key Patterns".

## Project Conventions to Respect

- Stack: Vue 3, Composition API, Vite. Suggestions should use `<script setup>` and Composition API, matching the codebase.
- Design: slate and gray palette, status colors green/blue/yellow/red, custom SVG charts, no emojis in the UI.
- Comments: any non-obvious change suggested should include a comment explaining why (project rule).
- Subagent rule: CLAUDE.md requires delegating any creation or significant modification of a `.vue` file to the `vue-expert` subagent. This skill reports only. If the user asks you to apply fixes, hand the `.vue` edits to `vue-expert`.

## Report Format

Group by impact, highest first. Each item needs a location, the evidence, and a concrete suggestion.

```
## Vue component analysis: <scope>

Scanned N components. M flagged. Top 3 by impact below.

### High impact
1. **<short title>** — `client/src/views/Foo.vue:123`
   - Evidence: <what the code does, with the count or quote>
   - Suggestion: <specific change, e.g. "replace :key=\"index\" with :key=\"item.sku\"">
   - Effort: low | medium | high

### Medium impact
...

### Low impact / cleanup
...

### Checked and not flagged
<brief list, so the user knows what was verified>
```

Rules for the report:
- Cite `file:line` for every item.
- Give a count or quote as evidence. No unsupported claims like "this is slow".
- Say which items you verified by reading and which came only from the helper.
- Do not pad the list. Five verified findings beat twenty guesses.
- If nothing meaningful is found, say so and list what was checked.

---
name: claude-design-to-codebase
description: >
  Transfer Claude Design output (handoff bundles, HTML/CSS/JS prototypes, artifacts)
  into a real codebase in any target framework — React, Vue, Svelte, Angular, Solid,
  Qwik, Swift, React Native, Web Components and more — with design-token extraction
  (W3C DTCG + Style Dictionary), deterministic framework compilation (Mitosis), and
  pixel-level visual verification against the bundle screenshots. Use this skill
  whenever the user mentions a Claude Design handoff, a design bundle, converting a
  design/prototype/mockup HTML into framework components, extracting design tokens
  from CSS, porting a UI to another framework, or verifying that implemented UI
  matches a design — even if they don't say "claude-design-to-codebase" explicitly.
---

# Design Transfer

Pipeline that converts a Claude Design handoff bundle (or any HTML/CSS/JS prototype)
into production components for one or more target frameworks, with two invariants:

1. **Design data is normalized once** — colors, spacing, typography become DTCG
   tokens; markup becomes Mitosis JSX. Everything downstream is derived, never
   hand-translated per framework.
2. **The LLM is used exactly once** (HTML → Mitosis JSX normalization). Token
   extraction, framework fan-out, and verification are deterministic scripts and
   compilers. This keeps N target frameworks at cost O(1) LLM work, not O(N).

```
Bundle (HTML/CSS/JS + Screenshots + README)
  │
  ├─ Stage 1  Token extraction        CSS ──► tokens.tokens.json (DTCG)
  │                                          ──► Style Dictionary ──► per-platform vars
  ├─ Stage 2  Structure normalization HTML ──► components/*.lite.tsx (Mitosis JSX)
  ├─ Stage 3  Compilation             Mitosis ──► react/ vue/ svelte/ ... output
  ├─ Stage 4  Verification            headless render ──► screenshot diff vs bundle
  └─ Stage 5  Integration             move into repo per its conventions, commit
```

Work through the stages in order. Each stage has a reference file with the full
rules — read it before executing that stage for the first time in a session.

---

## Stage 0 — Intake and inventory

Unpack the bundle into a working directory (`work/bundle/`). Then build an
inventory before touching anything:

- Read the bundle `README.md` first. Claude Design writes target stack,
  conventions, and definition-of-done there; canvas **annotations** travel inside
  it and often carry behavioral requirements ("button needs loading state").
  Treat annotations as acceptance criteria, not decoration.
- List every screen/state: HTML files and their matching screenshots. Record the
  mapping in `work/inventory.md` (screen → html file → screenshot file →
  annotations that apply).
- Note external assets (fonts, images, icons) and any inline `<script>` behavior.
- Ask the user two things if not already known: **target framework(s)** and the
  **destination repo/path + its styling convention** (Tailwind, CSS Modules,
  vanilla CSS variables, styled-components). If the repo has a design system,
  token names must align with it — see Stage 1.

Bundle anatomy details and edge cases: `references/bundle-anatomy.md`.

## Stage 1 — Token extraction (CSS → DTCG)

Goal: one `design/tokens/tokens.tokens.json` in W3C DTCG format
(`$value` / `$type` / `$description`) that captures every design decision in the
bundle CSS, plus a Style Dictionary config that emits platform variables.

1. Run the extractor:
   ```bash
   python scripts/extract_tokens.py work/bundle/**/*.css -o design/tokens/tokens.tokens.json
   ```
   It harvests `:root` custom properties first, then recurring literal values
   (colors, dimensions, font sizes, radii, shadows, durations) and proposes
   token names. It is a *proposal generator* — you review the output.
2. Review and refine (this is judgment work, do not skip):
   - Merge duplicates into base tokens + aliases (`"$value": "{color.brand.primary}"`).
   - Rename to the `category.type.item` scheme, or to the destination repo's
     existing token names if it has a design system.
   - Delete one-off noise values (a margin used once is not a token).
3. Generate platform outputs with Style Dictionary v4 (DTCG-aware). Config
   template and full extraction/classification rules:
   `references/dtcg-extraction.md`.

Result check: the bundle CSS should be re-expressible using only token
references for color/spacing/typography. Anything that can't be is either a new
token or intentional one-off — decide explicitly.

## Stage 2 — Structure normalization (HTML → Mitosis JSX)

This is the single LLM step. Convert each screen's HTML into one or more
`.lite.tsx` Mitosis components under `design/library/src/components/`.

Non-negotiable contract (full version with examples in
`references/mitosis-conversion.md` — read it before writing any `.lite.tsx`):

- One component per file, default export, props typed.
- State via `useStore` from `@builder.io/mitosis`; loops via `<For>`,
  conditionals via `<Show>`. No raw `.map()` in JSX, no ternary chains for
  structure.
- No browser globals at module scope; lifecycle only via `onMount`/`onUnmount`.
- **Every hardcoded style value that has a token must become a token reference**
  (CSS variable emitted by Style Dictionary in Stage 1). This is what makes the
  output homogeneous across frameworks.
- Split by reuse: repeated markup blocks become child components; screens become
  composition of components, not monoliths.
- Interactive behavior from bundle `<script>` tags is ported into component
  state/handlers — never copied as a side-effect script.

Scaffold the Mitosis project (config + package.json + folder layout):
```bash
python scripts/scaffold_mitosis.py design/ --targets react,vue,svelte
```

## Stage 3 — Compilation (Mitosis fan-out)

```bash
cd design/library && npm install && npx @builder.io/mitosis build
```

Outputs land in `design/library/output/<target>/`. Compile errors here almost
always mean a contract violation in Stage 2 (unsupported JSX pattern) — fix the
`.lite.tsx`, not the generated code. Never hand-edit generated output; it is a
build artifact.

Supported targets include react, vue, svelte, angular, solid, qwik, alpine,
html, webcomponent, lit, stencil, preact, marko, reactNative, swift, rsc.
Target-specific notes: `references/mitosis-conversion.md` §Targets.

## Stage 4 — Verification (visual parity loop)

Render each compiled screen headless and diff against the bundle screenshot:

1. Serve/render the target build, screenshot at the **same viewport size as the
   bundle screenshot** (read dimensions from the PNG; the diff script does this).
2. ```bash
   python scripts/visual_diff.py work/bundle/screens/home.png work/shots/react-home.png \
     -o work/diffs/home-diff.png
   ```
   Prints % differing pixels and writes a heatmap.
3. Acceptance: **≤ 2.0 % differing pixels** per screen (anti-aliasing tolerance
   is built in). Between 2–5 %: inspect the heatmap, fix targeted (usually font
   loading, spacing token misassignment, or missing state). Above 5 %:
   structural problem — revisit Stage 2 for that component.
4. Iterate: fix in `.lite.tsx` or tokens → recompile → re-diff. Never "fix" by
   editing generated output or by relaxing the threshold.
5. Verify annotated behavior too (loading states, interactions) — screenshots
   only prove static parity. Check each annotation from `work/inventory.md` off
   explicitly.

Playwright snippet for the headless screenshot and the full loop protocol:
`references/verification.md`.

## Stage 5 — Integration

- Copy the chosen target's output components plus the Style Dictionary artifacts
  into the destination repo, following **its** structure and naming (check for a
  CLAUDE.md / contributing guide first).
- Keep `design/tokens/tokens.tokens.json` and the `.lite.tsx` sources in the
  repo (e.g. `design/` at root) — they are the source of truth for future
  design iterations; the framework components are derived.
- Commit in two parts: (1) tokens + build config, (2) components + verification
  diffs (include the final diff percentages in the commit message — it makes
  design-parity reviewable).
- If the repo uses wave/masterplan governance, register this as a wave task
  before starting Stage 5.

---

## Failure modes to watch for

- **Token drift**: Stage 2 written before Stage 1 is reviewed → components full
  of hardcoded values. Always finish token review first.
- **Screenshot mismatch from fonts**: webfonts not loaded in headless render
  produce huge false diffs. Ensure `document.fonts.ready` before screenshotting
  (the snippet in `references/verification.md` handles this).
- **Bundle README contradicts user instructions**: the user wins; note the
  deviation in `work/inventory.md`.
- **Very large bundles**: process screen-by-screen through all stages rather
  than all screens per stage — you get a verified vertical slice early.

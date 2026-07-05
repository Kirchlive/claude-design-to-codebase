# Structure Normalization — HTML → Mitosis JSX Contract

Mitosis (`@builder.io/mitosis`) compiles a constrained JSX dialect (`.lite.tsx`)
to many frameworks. The constraint is the point: only patterns that map cleanly
onto *every* target are allowed. Violating the contract produces code that
compiles for React but breaks for Svelte or Angular — so the contract is
enforced at conversion time, not discovered at build time.

## File and component rules

- One component per `.lite.tsx` file, **default export**, PascalCase name
  matching the filename.
- Props: single typed `props` object. Give every prop a default (via
  `defaultProps` or in-body fallback) — components must render standalone.
- Location: `design/library/src/components/<Name>.lite.tsx`.

## State, control flow, events

```tsx
import { useStore, Show, For, onMount } from '@builder.io/mitosis';

export default function NavBar(props: { items: { label: string; href: string }[] }) {
  const state = useStore({
    open: false,
    toggle() { state.open = !state.open; },
  });

  return (
    <nav class="navbar">
      <button class="navbar-toggle" onClick={() => state.toggle()}>Menu</button>
      <Show when={state.open}>
        <ul class="navbar-list">
          <For each={props.items}>
            {(item) => <li key={item.href}><a href={item.href}>{item.label}</a></li>}
          </For>
        </ul>
      </Show>
    </nav>
  );
}
```

- State: `useStore` (methods live on the store). Simple local state may use
  `useState`, but prefer one `useStore` per component for uniformity.
- Conditionals: `<Show when={...}>` — never `{cond && <X/>}` or structural
  ternaries.
- Lists: `<For each={...}>` with a `key` — never inline `.map()`.
- Events: `onClick={...}` etc. with handler functions; no inline multi-statement
  bodies beyond a single call/assignment.
- Attributes: use `class` (not `className`).
- Lifecycle: `onMount` / `onUnmount` only. **No browser globals
  (window/document) at module scope** — guard everything inside `onMount`.
- No framework-specific imports (no react, no vue) inside `.lite.tsx`.

## Styling rules

- Prefer plain `class` attributes + a component-adjacent CSS file (or the
  `css={{...}}` prop for small scoped styles — Mitosis compiles it per target).
- **Token discipline**: every color, spacing, radius, font value must be a
  token reference — `var(--color-brand-primary)` etc. from the Stage 1 build.
  Grep your output for raw hex codes and px literals that exist in the token
  set; each hit is a contract violation.
- Port bundle CSS by *meaning*, not by copy: collapse duplicated declarations,
  drop dead selectors, replace values with token vars.

## Decomposition rules (screen → components)

- A repeated markup block (card, list row, nav item group) → child component.
- A screen = thin composition component that arranges children and owns
  page-level state.
- Interactive behavior found in bundle `<script>` tags → state + handlers in
  the owning component. Never ship imperative DOM-query scripts.
- Annotated states from the README ("loading state", "error state") must be
  reachable via props or store state — verification will screenshot them.

## Scaffold and build

`scripts/scaffold_mitosis.py` writes this layout:

```
design/library/
├── package.json          (@builder.io/mitosis + CLI as devDependencies)
├── mitosis.config.js
└── src/components/*.lite.tsx
```

`mitosis.config.js` template:

```js
/** @type {import('@builder.io/mitosis').MitosisConfig} */
module.exports = {
  files: 'src/**',
  targets: ['react', 'vue', 'svelte'],
  dest: 'output',
  options: {
    react: { typescript: true },
    vue: { typescript: true },
    svelte: { typescript: true },
  },
};
```

Build: `npx @builder.io/mitosis build` → `output/<target>/src/components/`.

## Targets — notes

Available targets include: react, preact, rsc, vue, svelte, angular, solid,
qwik, alpine, lit, stencil, webcomponent, html, marko, reactNative, swift,
liquid, template. Practical notes:

- **react/vue/svelte/solid/qwik/angular**: mature, use freely.
- **swift / reactNative**: expect manual finishing for layout (CSS does not
  translate 1:1 to native layout) — plan a review pass, keep scope to
  component structure + tokens.
- **webcomponent/lit/stencil**: good neutral targets when the destination repo
  is framework-agnostic.
- Generated output is a **build artifact**: never hand-edit; fix the
  `.lite.tsx` source and rebuild. If a target needs an escape hatch, use
  Mitosis `useTarget()` sparingly and document why.

## Compile-error triage

| Error smell | Likely violation |
|---|---|
| "Cannot process node / unsupported expression" | ternary/&& structural logic → use Show/For |
| Target output references undefined var | browser global at module scope |
| Styles missing in one target | css prop misuse → move to class + CSS file |
| Hook-order or reactivity errors in output | logic in JSX body → move into useStore methods |

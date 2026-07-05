# Verification — Visual Parity Loop

Static parity is proven by pixel diff against the bundle screenshots; behavioral
parity is proven by checking off annotations. Both are required before Stage 5.

## 1. Render headless at the reference viewport

The reference viewport = the bundle screenshot's pixel dimensions
(`visual_diff.py --print-size ref.png` prints them). Rendering at a different
size invalidates the diff.

Playwright snippet (Node; `npm i -D playwright && npx playwright install chromium`):

```js
// shoot.mjs  — usage: node shoot.mjs <url> <width> <height> <out.png>
import { chromium } from 'playwright';
const [url, w, h, out] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
await page.goto(url, { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);          // webfonts loaded
await page.evaluate(() => new Promise(r => setTimeout(r, 300))); // settle animations
await page.screenshot({ path: out, fullPage: false });
await browser.close();
```

Serve the compiled target with its dev server (vite/webpack) or a static
server for the html target. For stateful screenshots (menu open, loading),
drive the state before shooting: `await page.click('.navbar-toggle')` or mount
the component with the state prop set.

Python alternative: `playwright` pip package with the sync API — same steps.

## 2. Diff

```bash
python scripts/visual_diff.py ref.png candidate.png -o diff.png [--threshold 2.0]
```

- Compares at identical dimensions (errors out otherwise — that's a viewport
  bug, fix the render, don't resize images).
- Per-pixel tolerance absorbs anti-aliasing; the reported number is the
  percentage of significantly differing pixels.
- Writes a heatmap (`diff.png`): unchanged = dimmed, differing = red.
- Exit code 0 if ≤ threshold, 1 otherwise → usable in CI.

## 3. Acceptance and triage

| Diff % | Verdict | Typical cause / action |
|---|---|---|
| ≤ 2.0 | pass | record the number, move on |
| 2–5 | inspect heatmap | font fallback (check fonts.ready + font files copied), one wrong spacing/color token, missing asset |
| 5–15 | component-level bug | wrong token mapping, missing CSS block, state not set |
| > 15 | structural | wrong screen, layout collapsed, CSS not loaded — back to Stage 2/3 |

Fix location rule: **always** in `.lite.tsx` sources or the token files, then
recompile and re-shoot. Never edit generated output, never relax the threshold
to pass.

## 4. Behavioral checklist

For each annotation captured in `work/inventory.md`:
- reproduce the state/interaction in the rendered target,
- screenshot it if a reference state-screenshot exists (diff it),
- otherwise verify functionally and note "verified manually" with what was done.

## 5. Record

Write `work/verification-report.md`: table of screen × target × diff % ×
annotations verified. Include it (or its summary) in the Stage 5 commit
message. A reviewer should be able to see design parity as numbers, not vibes.

## Multi-target note

Verify the *primary* target screen-by-screen first. Secondary targets: verify
one representative screen fully, then spot-check — Mitosis output differences
between targets are systematic, so one verified screen catches most
target-specific drift (usually styling-injection differences).

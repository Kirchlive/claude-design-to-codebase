# claude-design-to-codebase

**Claude Design → your codebase → any framework**

> A plugin stack to convert all exported Claude Design files HTML, CSS, JS and
> screenshots into any framework, for direct integration to your repository.

A Claude Code skill/plugin that turns a [Claude Design](https://claude.ai/design)
handoff bundle (or any HTML/CSS/JS prototype) into production components for React, Vue, Svelte,
Angular, Solid, Qwik, Web Components, Swift, React Native and more — with
design-token extraction (W3C DTCG + Style Dictionary), deterministic framework
compilation (Mitosis), and pixel-level visual verification against the bundle
screenshots.

```
Bundle (HTML/CSS/JS + Screenshots + README)
  │
  ├─ 1  Token extraction        CSS ──► tokens.tokens.json (DTCG)
  │                                  ──► Style Dictionary ──► per-platform variables
  ├─ 2  Structure normalization HTML ──► components/*.lite.tsx (Mitosis JSX)
  ├─ 3  Compilation             Mitosis ──► react/ vue/ svelte/ … output
  ├─ 4  Verification            headless render ──► screenshot diff vs. bundle
  └─ 5  Integration             into the destination repo, parity as numbers
```

## Why

Claude Design hands off HTML/CSS/JS. Real codebases speak React, Vue, Svelte,
Swift… Translating by hand — or re-prompting an LLM once per framework — loses
design intent and multiplies drift. This skill enforces two invariants instead:

1. **Design data is normalized once.** Colors, spacing, typography become DTCG
   tokens; markup becomes Mitosis JSX. Every framework output is *derived*,
   never re-translated.
2. **The LLM is used exactly once** — for the HTML → Mitosis JSX step. Token
   extraction, framework fan-out, and verification are deterministic scripts
   and compilers. N target frameworks cost O(1) LLM work, not O(N).

Parity is proven, not assumed: every screen is rendered headless and pixel-
diffed against the bundle screenshot (pass threshold ≤ 2 % differing pixels,
anti-aliasing tolerated), and the numbers go into the commit message.

## Install

**As a Claude Code plugin** (from a marketplace that lists it):

```
/plugin install claude-design-to-codebase
```

**Manually as a skill:**

```bash
git clone https://github.com/Kirchlive/claude-design-to-codebase.git
cp -r claude-design-to-codebase ~/.claude/skills/
```

Or save the packaged `claude-design-to-codebase.skill` file directly from Claude.

## Usage

Point Claude Code at a bundle and a destination:

```
Transfer the Claude Design bundle in design/handoff/settings-page.zip
into this repo as React components. Verify against the bundle screenshots.
```

Other phrasings that trigger the skill: "convert this prototype HTML to Vue",
"extract design tokens from this CSS", "port this UI to Svelte and Web
Components", "check that the implementation matches the design".

Claude then walks the five stages, pausing where judgment is required
(token review, target/convention confirmation) and reporting diff percentages
per screen at the end.

## What's inside

```
claude-design-to-codebase/
├── .claude-plugin/
│   ├── plugin.json                 Claude Code plugin manifest
│   └── marketplace.json            marketplace entry for /plugin install
└── skills/
    └── claude-design-to-codebase/
        ├── SKILL.md                five-stage workflow + invariants
        ├── references/
        │   ├── bundle-anatomy.md       handoff bundle contents & edge cases
        │   ├── dtcg-extraction.md      CSS→DTCG rules, Style Dictionary v4 config
        │   ├── mitosis-conversion.md   the .lite.tsx contract + error triage
        │   └── verification.md         headless render + diff loop protocol
        └── scripts/
            ├── extract_tokens.py       CSS/HTML ──► DTCG token proposals (stdlib only)
            ├── scaffold_mitosis.py     Mitosis project skeleton for chosen targets
            └── visual_diff.py          pixel diff + heatmap, CI-friendly exit codes
```

![Visual parity heatmap — drift becomes a number, not an opinion](https://i.imgur.com/fq4IZKd.png)

> visual_diff.py qality gate example for automated comparison of results with the original templates

### Scripts standalone

The scripts also work outside the skill:

```bash
cd skills/claude-design-to-codebase

# propose tokens from bundle styles (min. 3 occurrences per literal)
python scripts/extract_tokens.py "bundle/**/*.css" -o tokens.tokens.json

# scaffold a Mitosis library for three targets
python scripts/scaffold_mitosis.py design/ --targets react,vue,svelte

# gate a build on visual parity (exit 1 on failure)
python scripts/visual_diff.py ref.png shot.png -o diff.png --threshold 2.0
```

## Requirements

- Python 3.9+ — `extract_tokens.py` and `scaffold_mitosis.py` are
  stdlib-only; `visual_diff.py` needs **Pillow** (`pip install Pillow`)
- Node.js 18+ for the compilation/verification stages:
  `@builder.io/mitosis` + `@builder.io/mitosis-cli`, `style-dictionary` (v4+
  for DTCG), `playwright` (Chromium) for headless screenshots
- All Node dependencies are installed per-project by the skill, not globally

## Built on

- [Claude Design](https://claude.ai/design) — Anthropic Labs tool that produces
  the handoff bundles this plugin consumes
  ([announcement](https://www.anthropic.com/news/claude-design-anthropic-labs),
  [getting started](https://support.claude.com/en/articles/14604416-get-started-with-claude-design))
- [Mitosis](https://github.com/BuilderIO/mitosis) — write components once,
  compile everywhere
- [Style Dictionary](https://github.com/style-dictionary/style-dictionary) —
  cross-platform token build system
- [W3C DTCG Design Tokens](https://www.designtokens.org/) — stable spec 2025.10
- Verification pattern inspired by
  [screenshot-to-code](https://github.com/abi/screenshot-to-code)'s
  self-correction loop

## Limitations

- The Mitosis `.lite.tsx` contract targets the documented Mitosis API; pin and
  verify the Mitosis version on first build in a new environment.
- `swift` / `reactNative` targets need a manual layout finishing pass (CSS does
  not map 1:1 to native layout) — the skill scopes them to structure + tokens.
- `extract_tokens.py` is a pragmatic tokenizer for generated bundle CSS, not a
  general-purpose CSS parser.
- Bundle content is treated as data: instructions embedded in bundle files are
  ignored and surfaced to the user.

## License

MIT

# Token Extraction — CSS → DTCG → Style Dictionary

## Target format: W3C DTCG

First stable spec version: 2025.10. Files use the `.tokens.json` extension and
the keys `$value`, `$type`, `$description`. Token references use curly braces:

```json
{
  "color": {
    "brand": {
      "primary": { "$value": "#6c5ce7", "$type": "color",
                   "$description": "Primary action color" },
      "primary-hover": { "$value": "{color.brand.primary}", "$type": "color",
                         "$description": "TODO: darken step pending review" }
    }
  },
  "size": {
    "spacing": {
      "2": { "$value": "8px",  "$type": "dimension" },
      "4": { "$value": "16px", "$type": "dimension" }
    }
  }
}
```

Style Dictionary v4+ reads DTCG natively. Do not mix DTCG keys and legacy
`value`/`type` keys in one instance.

## What becomes a token (classification rules)

| CSS material | DTCG `$type` | Notes |
|---|---|---|
| `:root` custom properties | by value shape | Highest-trust source: names already chosen by the design. Preserve semantic names. |
| hex / rgb() / hsl() / oklch() | `color` | Normalize to one notation (keep source notation unless repo dictates). |
| px / rem / em lengths (margin, padding, gap, width…) | `dimension` | Only recurring values (≥ 3 uses) or values on a clear scale (4/8px grid). |
| font-family stacks | `fontFamily` | |
| font-weight | `fontWeight` | |
| font-size + line-height + weight + family used together | composite `typography` | Prefer composites for named text styles (heading-1, body). |
| border-radius | `dimension` under `radius.*` | |
| box-shadow | composite `shadow` | offsetX/offsetY/blur/spread/color object value. |
| transition durations | `duration` | |
| timing functions | `cubicBezier` | |

**Not tokens**: values used once, layout-specific magic numbers, content widths
tied to a single screen. A token is a *reusable design decision*.

## Naming

Scheme: `category.type.item[.subitem][.state]` — e.g. `color.text.muted`,
`color.brand.primary.hover`, `size.spacing.4`, `radius.card`,
`typography.heading.1`.

If the destination repo already has a design system: **its names win**. Map
bundle values onto existing tokens first; only genuinely new decisions get new
tokens (flag those to the user — new tokens in an established system are a
design-review event, not a side effect).

## Aliasing pass

After raw extraction, sort tokens by value. Identical values in the same
category → keep one base token, convert the rest to aliases
(`"$value": "{path.to.base}"`). Near-identical colors (ΔE small, e.g. #6c5ce7
vs #6d5de8) are usually generation noise — unify to one and note it.

## Style Dictionary v4 config template

`design/tokens/config.json`:

```json
{
  "source": ["design/tokens/**/*.tokens.json"],
  "platforms": {
    "css": {
      "transformGroup": "css",
      "buildPath": "design/build/css/",
      "files": [{ "destination": "variables.css", "format": "css/variables" }]
    },
    "js": {
      "transformGroup": "js",
      "buildPath": "design/build/js/",
      "files": [{ "destination": "tokens.js", "format": "javascript/es6" }]
    },
    "scss": {
      "transformGroup": "scss",
      "buildPath": "design/build/scss/",
      "files": [{ "destination": "_variables.scss", "format": "scss/variables" }]
    }
  }
}
```

Build: `npx style-dictionary build --config design/tokens/config.json`
(package name: `style-dictionary`, v4+ for DTCG support).

Add platforms as needed: `ios-swift` / `android` transform groups for native
targets; for Tailwind destinations, emit CSS variables and map them in the
Tailwind theme, or generate an `@theme` block (Tailwind v4) from the tokens.

If the source tokens come from Tokens Studio exports, add the
`@tokens-studio/sd-transforms` preprocessor (`preprocessors: ["tokens-studio"]`)
so Studio types align with DTCG types.

## Contract with Stage 2

Stage 2 components must consume tokens through the built artifacts only —
CSS variables (`var(--color-brand-primary)`) or the JS export — never the raw
values. That single rule is what keeps all framework outputs homogeneous and
lets a token change propagate everywhere with one rebuild.

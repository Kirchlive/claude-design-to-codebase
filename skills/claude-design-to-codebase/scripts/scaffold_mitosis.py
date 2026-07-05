#!/usr/bin/env python3
"""scaffold_mitosis.py — Create the Mitosis library skeleton for Stage 2/3.

Usage:
  python scaffold_mitosis.py design/ --targets react,vue,svelte

Writes (never overwrites existing files):
  <dest>/library/package.json
  <dest>/library/mitosis.config.js
  <dest>/library/src/components/        (empty, for .lite.tsx files)
"""
import argparse
import json
from pathlib import Path

KNOWN_TARGETS = {
    "react", "preact", "rsc", "vue", "svelte", "angular", "solid", "qwik",
    "alpine", "lit", "stencil", "webcomponent", "html", "marko",
    "reactNative", "swift", "liquid", "template",
}

CONFIG_TEMPLATE = """/** @type {{import('@builder.io/mitosis').MitosisConfig}} */
module.exports = {{
  files: 'src/**',
  targets: {targets},
  dest: 'output',
  options: {{
{options}
  }},
}};
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest", help="design workspace root (e.g. design/)")
    ap.add_argument("--targets", default="react,vue,svelte",
                    help="comma-separated Mitosis targets (default react,vue,svelte)")
    ap.add_argument("--name", default="design-library", help="npm package name")
    args = ap.parse_args()

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    unknown = [t for t in targets if t not in KNOWN_TARGETS]
    if unknown:
        print(f"warn: unrecognized target(s) {unknown} — passing through, "
              f"verify against current Mitosis docs.")

    lib = Path(args.dest) / "library"
    (lib / "src" / "components").mkdir(parents=True, exist_ok=True)

    pkg = lib / "package.json"
    if not pkg.exists():
        pkg.write_text(json.dumps({
            "name": args.name,
            "version": "0.1.0",
            "private": True,
            "scripts": {"build": "mitosis build"},
            "devDependencies": {
                "@builder.io/mitosis": "latest",
                "@builder.io/mitosis-cli": "latest",
            },
        }, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {pkg}")
    else:
        print(f"kept existing {pkg}")

    cfg = lib / "mitosis.config.js"
    if not cfg.exists():
        ts_capable = {"react", "vue", "svelte", "solid", "qwik", "angular", "preact", "lit", "stencil"}
        opts = "\n".join(
            f"    {t}: {{ typescript: true }}," for t in targets if t in ts_capable
        ) or "    // per-target options here"
        cfg.write_text(CONFIG_TEMPLATE.format(
            targets=json.dumps(targets), options=opts), encoding="utf-8")
        print(f"wrote {cfg}")
    else:
        print(f"kept existing {cfg}")

    print("next: write .lite.tsx components into "
          f"{lib / 'src' / 'components'}, then: cd {lib} && npm install && npm run build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

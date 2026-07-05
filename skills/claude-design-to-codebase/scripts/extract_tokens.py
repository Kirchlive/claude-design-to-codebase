#!/usr/bin/env python3
"""extract_tokens.py — Harvest design tokens from CSS/HTML into W3C DTCG format.

Proposal generator: output is a starting point for human/agent review
(aliasing, renaming, pruning), not a finished token set.

Usage:
  python extract_tokens.py styles.css page.html ... -o tokens.tokens.json
  python extract_tokens.py "bundle/**/*.css" --min-uses 3

Sources harvested, in trust order:
  1. :root { --custom-properties }  → semantic names preserved
  2. Recurring literals in declarations (and style="" attributes in HTML):
     colors, dimensions, font families/weights/sizes, radii, shadows, durations

Stdlib only. No CSS parser dependency — a pragmatic tokenizer good enough for
generated bundle CSS (not a general-purpose CSS parser).
"""
import argparse
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

COLOR_RE = re.compile(
    r"(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)|oklch\([^)]*\)|oklab\([^)]*\))"
)
DIM_RE = re.compile(r"(?<![\w.-])(-?\d*\.?\d+)(px|rem|em|vh|vw|%)\b")
DURATION_RE = re.compile(r"(?<![\w.-])(\d*\.?\d+)(ms|s)\b")
FONT_WEIGHT_RE = re.compile(r"font-weight\s*:\s*([1-9]00|bold|normal)\b", re.I)
FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}{]+)", re.I)
SHADOW_RE = re.compile(r"box-shadow\s*:\s*([^;}{]+)", re.I)
ROOT_BLOCK_RE = re.compile(r":root\s*{([^}]*)}", re.S)
CUSTOM_PROP_RE = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
STYLE_ATTR_RE = re.compile(r'style\s*=\s*"([^"]*)"', re.I)
DECL_RE = re.compile(r"([\w-]+)\s*:\s*([^;}{]+)")

DIMENSION_PROPS = {
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "gap", "row-gap", "column-gap", "width", "height", "min-width", "max-width",
    "min-height", "max-height", "top", "right", "bottom", "left", "inset",
}
RADIUS_PROPS = {"border-radius"}
FONT_SIZE_PROPS = {"font-size"}


def slug(value: str) -> str:
    s = re.sub(r"[^\w]+", "-", value.strip().lower()).strip("-")
    return s or "value"


def classify_value(value: str):
    """Return ($type, normalized_value) or None for a raw CSS value."""
    v = value.strip()
    if COLOR_RE.fullmatch(v):
        return "color", v.lower()
    m = DIM_RE.fullmatch(v)
    if m:
        return "dimension", v
    m = DURATION_RE.fullmatch(v)
    if m:
        return "duration", v
    return None


def read_sources(patterns):
    texts = []
    for pat in patterns:
        paths = sorted(glob.glob(pat, recursive=True)) or [pat]
        for p in paths:
            path = Path(p)
            if not path.is_file():
                print(f"warn: not a file, skipped: {p}", file=sys.stderr)
                continue
            raw = path.read_text(encoding="utf-8", errors="replace")
            if path.suffix.lower() in {".html", ".htm"}:
                # style="" attributes + <style> blocks
                inline = " ; ".join(STYLE_ATTR_RE.findall(raw))
                styles = " ".join(
                    re.findall(r"<style[^>]*>(.*?)</style>", raw, re.S | re.I)
                )
                texts.append((str(path), inline + "\n" + styles))
            else:
                texts.append((str(path), raw))
    return texts


def harvest(texts, min_uses):
    tokens = {}          # dotted.path -> {"$value":..,"$type":..,"$description":..}
    color_uses = Counter()
    dim_uses = defaultdict(Counter)   # group -> value counter
    font_sizes = Counter()
    weights = Counter()
    families = Counter()
    shadows = Counter()
    durations = Counter()

    for src, css in texts:
        # 1) :root custom properties — trusted, keep names
        for block in ROOT_BLOCK_RE.findall(css):
            for name, value in CUSTOM_PROP_RE.findall(block):
                cls = classify_value(value)
                ttype = cls[0] if cls else guess_type_from_name(name, value)
                path = f"custom.{name}"
                tokens[path] = {
                    "$value": value.strip(),
                    "$type": ttype,
                    "$description": f"from :root custom property --{name} ({Path(src).name})",
                }

        # 2) declaration scan
        for prop, value in DECL_RE.findall(css):
            prop = prop.lower()
            value = value.strip()
            for c in COLOR_RE.findall(value):
                color_uses[c.lower()] += 1
            if prop in FONT_SIZE_PROPS:
                m = DIM_RE.search(value)
                if m:
                    font_sizes[m.group(0)] += 1
            elif prop in RADIUS_PROPS:
                m = DIM_RE.search(value)
                if m:
                    dim_uses["radius"][m.group(0)] += 1
            elif prop in DIMENSION_PROPS:
                for m in DIM_RE.finditer(value):
                    dim_uses["spacing"][m.group(0)] += 1
            if prop == "transition" or prop == "transition-duration" or prop.startswith("animation"):
                for m in DURATION_RE.finditer(value):
                    durations[m.group(0)] += 1

        for m in FONT_WEIGHT_RE.finditer(css):
            weights[m.group(1)] += 1
        for m in FONT_FAMILY_RE.finditer(css):
            families[m.group(1).strip()] += 1
        for m in SHADOW_RE.finditer(css):
            val = m.group(1).strip()
            if val not in ("none", "inherit", "initial"):
                shadows[val] += 1

    def add(path, value, ttype, uses=None, note=""):
        if path in tokens:
            return
        desc = note or (f"seen {uses}×" if uses else "")
        tokens[path] = {"$value": value, "$type": ttype, "$description": desc}

    for color, n in color_uses.items():
        if n >= min_uses:
            add(f"color.extracted.{slug(color)}", color, "color", n)
    for group, counter in dim_uses.items():
        for value, n in counter.items():
            if n >= min_uses:
                add(f"size.{group}.{slug(value)}", value, "dimension", n)
    for value, n in font_sizes.items():
        if n >= min_uses:
            add(f"size.font.{slug(value)}", value, "dimension", n)
    for value, n in weights.items():
        add(f"font.weight.{slug(value)}", value, "fontWeight", n)
    for value, n in families.items():
        fams = [f.strip().strip("'\"") for f in value.split(",")]
        add(f"font.family.{slug(fams[0])}", fams, "fontFamily", n)
    for value, n in shadows.items():
        if n >= max(2, min_uses - 1):
            add(f"shadow.{slug(value)[:40]}", value, "shadow", n,
                note=f"raw box-shadow, seen {n}× — convert to composite object in review")
    for value, n in durations.items():
        if n >= 2:
            add(f"duration.{slug(value)}", value, "duration", n)

    return tokens


def guess_type_from_name(name, value):
    n = name.lower()
    if "color" in n or "bg" in n or COLOR_RE.search(value):
        return "color"
    if any(k in n for k in ("space", "size", "gap", "radius", "width", "height")):
        return "dimension"
    if "font" in n and "weight" in n:
        return "fontWeight"
    if "duration" in n or "time" in n:
        return "duration"
    return "other"


def nest(flat):
    root = {}
    for dotted, token in sorted(flat.items()):
        node = root
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = token
    return root


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", help="CSS/HTML files or glob patterns")
    ap.add_argument("-o", "--output", default="tokens.tokens.json")
    ap.add_argument("--min-uses", type=int, default=3,
                    help="minimum occurrences for a literal to become a token proposal (default 3)")
    args = ap.parse_args()

    texts = read_sources(args.sources)
    if not texts:
        print("error: no readable source files", file=sys.stderr)
        return 2
    flat = harvest(texts, args.min_uses)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(nest(flat), indent=2) + "\n", encoding="utf-8")
    print(f"{len(flat)} token proposals -> {out}")
    print("next: review — alias duplicates, rename to category.type.item, prune one-offs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

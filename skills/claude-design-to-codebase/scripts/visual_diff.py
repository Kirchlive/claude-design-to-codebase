#!/usr/bin/env python3
"""visual_diff.py — Pixel diff between a reference screenshot and a rendered candidate.

Usage:
  python visual_diff.py ref.png candidate.png -o diff.png [--threshold 2.0]
  python visual_diff.py --print-size ref.png        # print WxH (for viewport setup)

Reports the percentage of significantly differing pixels (per-channel tolerance
absorbs anti-aliasing) and writes a heatmap: unchanged pixels dimmed, differing
pixels red. Exit code 0 if diff%% <= threshold, 1 otherwise (CI-friendly),
2 on usage errors.

Requires Pillow:  pip install Pillow
"""
import argparse
import sys

try:
    from PIL import Image, ImageChops
except ImportError:
    print("error: Pillow required — pip install Pillow", file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("reference", help="reference screenshot (from the bundle)")
    ap.add_argument("candidate", nargs="?", help="rendered candidate screenshot")
    ap.add_argument("-o", "--output", default=None, help="write heatmap PNG here")
    ap.add_argument("--threshold", type=float, default=2.0,
                    help="max %% differing pixels to pass (default 2.0)")
    ap.add_argument("--pixel-tolerance", type=int, default=16,
                    help="per-channel delta treated as identical (anti-aliasing), default 16")
    ap.add_argument("--print-size", action="store_true",
                    help="print WIDTHxHEIGHT of the reference and exit")
    args = ap.parse_args()

    def load(path):
        try:
            return Image.open(path).convert("RGB")
        except Exception as e:
            print(f"error: cannot read image {path!r}: {e}", file=sys.stderr)
            raise SystemExit(2)

    ref = load(args.reference)
    if args.print_size:
        print(f"{ref.width}x{ref.height}")
        return 0

    if not args.candidate:
        print("error: candidate image required (or use --print-size)", file=sys.stderr)
        return 2

    cand = load(args.candidate)
    if ref.size != cand.size:
        print(f"error: size mismatch ref={ref.size} candidate={cand.size} — "
              f"re-render at the reference viewport instead of resizing.", file=sys.stderr)
        return 2

    diff = ImageChops.difference(ref, cand)
    # max channel delta per pixel
    delta = diff.split()
    maxdelta = delta[0].point(lambda p: p)
    for ch in delta[1:]:
        maxdelta = ImageChops.lighter(maxdelta, ch)

    tol = args.pixel_tolerance
    mask = maxdelta.point(lambda p: 255 if p > tol else 0)  # differing pixels
    hist = mask.histogram()
    differing = hist[255] if len(hist) > 255 else sum(hist[1:])
    total = ref.width * ref.height
    pct = 100.0 * differing / total

    if args.output:
        dimmed = ref.point(lambda p: int(p * 0.35))
        red = Image.new("RGB", ref.size, (230, 40, 40))
        heat = Image.composite(red, dimmed, mask)
        heat.save(args.output)

    verdict = "PASS" if pct <= args.threshold else "FAIL"
    print(f"{verdict}  differing pixels: {pct:.2f}%  "
          f"(threshold {args.threshold}%, tolerance ±{tol}/channel, {differing}/{total} px)"
          + (f"  heatmap: {args.output}" if args.output else ""))
    return 0 if pct <= args.threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())

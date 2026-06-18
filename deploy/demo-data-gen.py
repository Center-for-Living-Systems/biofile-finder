#!/usr/bin/env python3
"""Generate a synthetic BioFile Finder demo dataset + manifest.

Creates fake microscopy-style PNGs laid out by plate/well/channel and a
manifest.csv whose **File Path** column holds full HTTP(S) URLs (the column
the app treats as the openable file). No NAS required.

Usage:
  demo-data-gen.py --root ./demo-data --base-url http://localhost:8080/nas
"""
import argparse, csv, math, random
from pathlib import Path
from PIL import Image, ImageDraw

CHANNELS = {            # channel -> (base RGB tint, blob RGB)
    "DAPI":  ((6, 8, 30),   (90, 110, 255)),
    "GFP":   ((4, 24, 6),   (90, 255, 120)),
    "RFP":   ((30, 4, 8),   (255, 90, 90)),
}
PLATES = [1, 2]
WELLS = ["A01", "A02", "B01", "B02"]
SIZE = 256


def render(path: Path, channel: str, seed: int) -> None:
    rng = random.Random(seed)
    base, blob = CHANNELS[channel]
    img = Image.new("RGB", (SIZE, SIZE), base)
    d = ImageDraw.Draw(img)
    for _ in range(rng.randint(18, 40)):                 # scatter "cells"
        cx, cy = rng.randint(0, SIZE), rng.randint(0, SIZE)
        r = rng.randint(4, 14)
        f = rng.uniform(0.4, 1.0)
        col = tuple(min(255, int(c * f)) for c in blob)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="./demo-data")
    ap.add_argument("--base-url", default="http://localhost:8080/nas")
    ap.add_argument("--out", default=None, help="manifest path (default <root>/manifest.csv)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    base = args.base_url.rstrip("/")
    out = Path(args.out) if args.out else root / "manifest.csv"

    cols = ["File Name", "File Path", "File Size", "Folder",
            "Plate", "Well", "Condition", "Channel", "Timepoint (hr)", "Extension"]
    rows = []
    seed = 0
    for plate in PLATES:
        timepoint = 0 if plate == 1 else 24
        for well in WELLS:
            condition = "control" if well.startswith("A") else "treated"
            for channel in CHANNELS:
                seed += 1
                name = f"P{plate}_{well}_{channel}.png"
                rel = f"Plate{plate}/{well}/{name}"
                full = root / rel
                render(full, channel, seed)
                rows.append({
                    "File Name": name,
                    "File Path": f"{base}/{rel}",
                    "File Size": full.stat().st_size,
                    "Folder": f"Plate{plate}/{well}",
                    "Plate": f"Plate{plate}",
                    "Well": well,
                    "Condition": condition,
                    "Channel": channel,
                    "Timepoint (hr)": timepoint,
                    "Extension": "png",
                })

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} images under {root}")
    print(f"Manifest: {out}  (File Path base = {base})")


if __name__ == "__main__":
    main()

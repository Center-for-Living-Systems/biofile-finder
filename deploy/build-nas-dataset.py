#!/usr/bin/env python3
"""Onboard one NAS dataset folder into BioFile Finder.

Raw files stay on the read-only NAS (served via Caddy /gardel/*). Previews and
the per-dataset manifest are written to LOCAL disk under /srv/shared/_derived
(served via /data/*), since the NAS is read-only.

  build-nas-dataset.py --src "<dir under /srv/gardelnas>" --id <slug> --name "<label>"
"""
import argparse, csv, re, sys
from pathlib import Path
from urllib.parse import quote
import numpy as np
from PIL import Image

HOST = "https://128.135.108.226"
RAW_ROOT = Path("/srv/gardelnas")
RAW_BASE = f"{HOST}/gardel"
DERIVED_ROOT = Path("/srv/shared/_derived/gardel")
DERIVED_BASE = f"{HOST}/data/_derived/gardel"
THUMB = 512

KIND = {".czi": "Raw image (CZI)", ".tif": "Image (TIF)", ".tiff": "Image (TIF)",
        ".zip": "ROI archive (ZIP)", ".xlsx": "Spreadsheet", ".csv": "Table (CSV)"}
SKIP = {".db"}  # Thumbs.db etc.


def url(base: str, rel: str) -> str:
    return f"{base}/{quote(rel)}"


def stretch(a):
    lo, hi = np.percentile(a, (2, 98))
    return np.clip((a.astype(np.float32) - lo) / max(hi - lo, 1) * 255, 0, 255)


def czi_thumb(src: Path, dst: Path):
    from aicspylibczi import CziFile
    img, _ = CziFile(str(src)).read_image()
    arr = np.squeeze(img)
    if arr.ndim == 3 and arr.shape[0] <= 8:
        chans = arr
    elif arr.ndim == 2:
        chans = arr[None]
    else:
        chans = arr.reshape(-1, arr.shape[-2], arr.shape[-1])
    proj = np.max([stretch(c) for c in chans], axis=0).astype(np.uint8)
    im = Image.fromarray(proj).convert("L"); im.thumbnail((THUMB, THUMB))
    dst.parent.mkdir(parents=True, exist_ok=True); im.save(dst)


def tif_thumb(src: Path, dst: Path):
    a = np.asarray(Image.open(src))
    if a.dtype != np.uint8:
        a = stretch(a).astype(np.uint8)
    im = Image.fromarray(a).convert("L"); im.thumbnail((THUMB, THUMB))
    dst.parent.mkdir(parents=True, exist_ok=True); im.save(dst)


def condition(p: Path) -> str:
    s = str(p).lower()
    if "control" in s:
        return "Control"
    if "y-comp" in s or "ycomp" in s or "ycompound" in s or "y-compound" in s:
        return "Y-comp"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--name", required=True)
    a = ap.parse_args()

    src = Path(a.src).resolve()
    if not src.is_dir():
        sys.exit(f"not a dir: {src}")
    out_dir = DERIVED_ROOT / a.id
    manifest = DERIVED_ROOT / f"{a.id}-manifest.csv"
    cols = ["File Name", "File Path", "Thumbnail", "File Size", "Condition",
            "Kind", "Replicate", "Folder", "Experiment", "Extension"]

    files = sorted(p for p in src.rglob("*") if p.is_file() and p.suffix.lower() not in SKIP)
    rows, nthumb, nfail = [], 0, 0
    for i, f in enumerate(files, 1):
        ext = f.suffix.lower()
        rel_src = f.relative_to(src).as_posix()
        thumb_url = ""
        prev = out_dir / (rel_src + ".png")
        try:
            if ext == ".czi":
                czi_thumb(f, prev); thumb_url = url(DERIVED_BASE, f"{a.id}/{rel_src}.png"); nthumb += 1
            elif ext in (".tif", ".tiff"):
                tif_thumb(f, prev); thumb_url = url(DERIVED_BASE, f"{a.id}/{rel_src}.png"); nthumb += 1
        except Exception as e:
            nfail += 1; print(f"  [{i}/{len(files)}] FAIL {f.name}: {e}", file=sys.stderr)
        m = re.search(r"-(\d+)\.", f.name)
        rows.append({
            "File Name": f.name,
            "File Path": url(RAW_BASE, f.relative_to(RAW_ROOT).as_posix()),
            "Thumbnail": thumb_url,
            "File Size": f.stat().st_size,
            "Condition": condition(f),
            "Kind": KIND.get(ext, ext.lstrip(".").upper()),
            "Replicate": m.group(1) if m else "",
            "Folder": f.parent.relative_to(src).as_posix() if f.parent != src else ".",
            "Experiment": a.name,
            "Extension": ext.lstrip("."),
        })
        if i % 10 == 0:
            print(f"  ...{i}/{len(files)}")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"Done: {len(rows)} rows, {nthumb} thumbnails ({nfail} failed)")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()

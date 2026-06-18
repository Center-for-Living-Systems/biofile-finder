#!/usr/bin/env python3
"""Build thumbnails + a BioFile Finder manifest for /srv/shared/031125data.

- CZI  -> contrast-stretched max-projection 512px grayscale PNG preview
- TIF  -> 512px PNG preview (masks)
- CSV/IJM -> listed in the manifest (no preview)

Outputs:
  /srv/shared/_derived/previews/<mirrored path>.png
  /srv/shared/_derived/031125data-manifest.csv

File Path / Thumbnail columns are full URLs under Caddy's /data route.
Run inside the venv:  .venv/bin/python build-shared-dataset.py
"""
import csv, re, sys
from pathlib import Path
from urllib.parse import quote
import numpy as np
from PIL import Image

ROOT = Path("/srv/shared")              # Caddy /data/* -> /srv/shared
SRC = ROOT / "031125data"
DERIVED = ROOT / "_derived"
PREVIEWS = DERIVED / "previews"
BASE_URL = "https://128.135.108.226/data"
MANIFEST = DERIVED / "031125data-manifest.csv"
STAIN_PANEL = "eGFP-Zyxin (488), Phalloidin (405), Vinculin (647), Paxillin (568)"
THUMB = 512

KIND = {".czi": "Raw image (CZI)", ".tif": "Front mask (TIF)",
        ".tiff": "Front mask (TIF)", ".csv": "Channel profile (CSV)",
        ".ijm": "Macro (IJM)"}


def url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    return f"{BASE_URL}/{quote(rel)}"


def stretch(a: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(a, (2, 98))
    return np.clip((a.astype(np.float32) - lo) / max(hi - lo, 1) * 255, 0, 255)


def czi_thumb(src: Path, dst: Path) -> bool:
    from aicspylibczi import CziFile
    img, _ = CziFile(str(src)).read_image()
    arr = np.squeeze(img)
    if arr.ndim == 3 and arr.shape[0] <= 8:
        chans = arr
    elif arr.ndim == 2:
        chans = arr[None]
    else:
        chans = arr.reshape(-1, arr.shape[-2], arr.shape[-1])
    proj = np.max([stretch(ch) for ch in chans], axis=0).astype(np.uint8)
    im = Image.fromarray(proj).convert("L")
    im.thumbnail((THUMB, THUMB))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)
    return True


def tif_thumb(src: Path, dst: Path) -> bool:
    im = Image.open(src)
    a = np.asarray(im)
    if a.dtype != np.uint8:
        a = stretch(a).astype(np.uint8)
    im = Image.fromarray(a).convert("L")
    im.thumbnail((THUMB, THUMB))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)
    return True


def meta(path: Path) -> dict:
    name = path.name
    low = name.lower()
    cond = "YComp" if "ycomp" in low else "Control" if "control" in low else ""
    if not cond:  # fall back to folder
        cond = "YComp" if "ycomp" in path.parent.name.lower() else \
               "Control" if "control" in path.parent.name.lower() else ""
    m = re.search(r"-(\d+)\.", name)
    rep = m.group(1) if m else ""
    ext = path.suffix.lower()
    return {
        "Condition": cond,
        "Kind": KIND.get(ext, ext.lstrip(".").upper()),
        "Replicate": rep,
        "Folder": path.parent.relative_to(SRC).as_posix() if path.parent != SRC else ".",
        "Stain panel": STAIN_PANEL,
        "Dataset": "031125data",
        "Extension": ext.lstrip("."),
    }


def main() -> None:
    if not SRC.is_dir():
        sys.exit(f"missing {SRC}")
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    cols = ["File Name", "File Path", "Thumbnail", "File Size", "Condition",
            "Kind", "Replicate", "Folder", "Stain panel", "Dataset", "Extension"]
    rows, n_thumb, n_fail = [], 0, 0
    files = sorted(p for p in SRC.rglob("*") if p.is_file())
    for i, f in enumerate(files, 1):
        ext = f.suffix.lower()
        thumb_url = ""
        prev = PREVIEWS / (f.relative_to(SRC).as_posix() + ".png")
        try:
            if ext == ".czi" and czi_thumb(f, prev):
                thumb_url = url(prev); n_thumb += 1
            elif ext in (".tif", ".tiff") and tif_thumb(f, prev):
                thumb_url = url(prev); n_thumb += 1
        except Exception as e:
            n_fail += 1
            print(f"  [{i}/{len(files)}] thumb FAIL {f.name}: {e}", file=sys.stderr)
        d = meta(f)
        d.update({"File Name": f.name, "File Path": url(f),
                  "Thumbnail": thumb_url, "File Size": f.stat().st_size})
        rows.append(d)
        if i % 20 == 0:
            print(f"  ...{i}/{len(files)} processed")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Done: {len(rows)} rows, {n_thumb} thumbnails ({n_fail} failed)")
    print(f"Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()

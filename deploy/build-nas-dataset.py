#!/usr/bin/env python3
"""Onboard one NAS dataset folder into BioFile Finder.

Raw files stay on the read-only NAS (served via Caddy /gardel/*). Previews and
the per-dataset manifest are written to LOCAL disk under /srv/shared/_derived
(served via /data/*), since the NAS is read-only.

  build-nas-dataset.py --src "<dir under /srv/gardelnas>" --id <slug> --name "<label>"
"""
import argparse, csv, json, re, sys
from pathlib import Path
from urllib.parse import quote
import numpy as np
from PIL import Image

HOST = "http://128.135.108.226"
RAW_ROOT = Path("/srv/gardelnas")
RAW_BASE = f"{HOST}/gardel"
DERIVED_ROOT = Path("/srv/shared/_derived/gardel")
DERIVED_BASE = f"{HOST}/data/_derived/gardel"
THUMB = 512
PREVIEW = 512

KIND = {".czi": "Raw image (CZI)", ".tif": "Image (TIF)", ".tiff": "Image (TIF)",
        ".nd2": "Raw image (ND2)"}
PREVIEW_EXTS = {".czi", ".tif", ".tiff", ".nd2"}


def url(base: str, rel: str) -> str:
    return f"{base}/{quote(rel)}"


def stretch(a):
    lo, hi = np.percentile(a, (2, 98))
    return np.clip((a.astype(np.float32) - lo) / max(hi - lo, 1) * 255, 0, 255)


def _save_preview(arr: np.ndarray, dst: Path):
    arr = np.squeeze(arr)
    im = Image.fromarray(stretch(arr).astype(np.uint8)).convert("L")
    im.thumbnail((PREVIEW, PREVIEW), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "JPEG", quality=85)


# ---------------------------------------------------------------------------
# Thumbnail generators (one composite PNG per file)
# ---------------------------------------------------------------------------

def czi_thumb(src: Path, dst: Path):
    from aicspylibczi import CziFile
    czi = CziFile(str(src))
    shape = czi.get_dims_shape()[0]
    Z_count = shape.get('Z', (0, 1))[1]
    C_count = shape.get('C', (0, 1))[1]
    # Pin all non-spatial dims to 0; use middle Z for representative slice
    base = {}
    for dim in ('S', 'T', 'M', 'H'):
        if shape.get(dim, (0, 1))[1] > 1:
            base[dim] = 0
    if Z_count > 1:
        base['Z'] = Z_count // 2
    planes = []
    for c in range(C_count):
        plane, _ = czi.read_image(**base, C=c)
        planes.append(np.squeeze(plane))
    proj = np.max([stretch(p) for p in planes], axis=0).astype(np.uint8)
    im = Image.fromarray(proj).convert("L")
    im.thumbnail((THUMB, THUMB))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


def tif_thumb(src: Path, dst: Path):
    a = np.asarray(Image.open(src))
    if a.dtype != np.uint8:
        a = stretch(a).astype(np.uint8)
    im = Image.fromarray(a).convert("L")
    im.thumbnail((THUMB, THUMB))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


# ---------------------------------------------------------------------------
# Per-channel / per-Z preview generators (JPEG grid, S=0 T=0)
# ---------------------------------------------------------------------------

def czi_previews(src: Path, out_dir: Path, rel_src: str) -> dict:
    from aicspylibczi import CziFile
    czi = CziFile(str(src))
    shape = czi.get_dims_shape()[0]
    Z_count = shape.get('Z', (0, 1))[1]
    C_count = shape.get('C', (0, 1))[1]
    base = {}
    for dim in ('S', 'T', 'M', 'H'):
        if shape.get(dim, (0, 1))[1] > 1:
            base[dim] = 0

    # Try to extract channel names from CZI XML metadata
    channel_names = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(czi.meta)
        for ch in root.iter('Channel'):
            name = ch.get('Name') or ''
            if name:
                channel_names.append(name)
    except Exception:
        pass
    channel_names = (channel_names + [''] * C_count)[:C_count]

    for z in range(Z_count):
        z_kwargs = dict(base)
        if Z_count > 1:
            z_kwargs['Z'] = z
        for c in range(C_count):
            plane, _ = czi.read_image(**z_kwargs, C=c)
            _save_preview(np.squeeze(plane), out_dir / f"{rel_src}.c{c}.z{z:03d}.jpg")

    return {"z_count": Z_count, "c_count": C_count, "channel_names": channel_names}


def tif_previews(src: Path, out_dir: Path, rel_src: str) -> dict:
    import tifffile
    with tifffile.TiffFile(src) as tf:
        series = tf.series[0]
        axes = series.axes   # e.g. 'CYX', 'ZYX', 'CZYX', 'TCZYX'
        shape = series.shape
    dim = {ax: i for i, ax in enumerate(axes)}
    Z_count = shape[dim['Z']] if 'Z' in dim else 1
    C_count = shape[dim['C']] if 'C' in dim else 1
    data = tifffile.imread(str(src))
    for z in range(Z_count):
        for c in range(C_count):
            idx = [slice(None)] * len(axes)
            for ax, val in [('T', 0), ('S', 0)]:
                if ax in dim: idx[dim[ax]] = val
            if 'Z' in dim: idx[dim['Z']] = z
            if 'C' in dim: idx[dim['C']] = c
            _save_preview(np.squeeze(data[tuple(idx)]),
                          out_dir / f"{rel_src}.c{c}.z{z:03d}.jpg")
    return {"z_count": Z_count, "c_count": C_count, "channel_names": []}


def nd2_previews(src: Path, out_dir: Path, rel_src: str) -> dict:
    import nd2
    with nd2.ND2File(src) as f:
        sizes = dict(f.sizes)
        Z_count = sizes.get('Z', 1)
        C_count = sizes.get('C', 1)
        channel_names = []
        try:
            for ch in f.metadata.channels:
                channel_names.append(ch.channel.name)
        except Exception:
            pass
        channel_names = (channel_names + [''] * C_count)[:C_count]
        dask_arr = f.to_dask()
        axes = list(sizes.keys())
        for z in range(Z_count):
            for c in range(C_count):
                idx = []
                for ax in axes:
                    if ax in ('Y', 'X'):   idx.append(slice(None))
                    elif ax == 'Z':        idx.append(z)
                    elif ax == 'C':        idx.append(c)
                    else:                  idx.append(0)  # P, T, S → first
                plane = dask_arr[tuple(idx)].compute()
                _save_preview(plane, out_dir / f"{rel_src}.c{c}.z{z:03d}.jpg")
    return {"z_count": Z_count, "c_count": C_count, "channel_names": channel_names}


def write_previews(src: Path, out_dir: Path, rel_src: str, ext: str) -> dict | None:
    """Dispatch to the right preview generator. Returns meta dict or None on failure."""
    try:
        if ext == ".czi":
            return czi_previews(src, out_dir, rel_src)
        elif ext in (".tif", ".tiff"):
            return tif_previews(src, out_dir, rel_src)
        elif ext == ".nd2":
            return nd2_previews(src, out_dir, rel_src)
    except Exception as e:
        print(f"  PREVIEW FAIL {src.name}: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

def condition(p: Path) -> str:
    s = str(p).lower()
    if "control" in s:
        return "Control"
    if "y-comp" in s or "ycomp" in s or "ycompound" in s or "y-compound" in s:
        return "Y-comp"
    return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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
    cols = ["File Name", "File Path", "Thumbnail", "Preview", "File Size", "Condition",
            "Kind", "Replicate", "Folder", "Experiment", "Extension"]

    files = sorted(p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in KIND)
    rows, nthumb, npreview, nfail = [], 0, 0, 0
    for i, f in enumerate(files, 1):
        ext = f.suffix.lower()
        rel_src = f.relative_to(src).as_posix()
        thumb_url = preview_url = ""
        prev = out_dir / (rel_src + ".png")

        # Composite thumbnail
        try:
            if ext == ".czi":
                czi_thumb(f, prev)
                thumb_url = url(DERIVED_BASE, f"{a.id}/{rel_src}.png")
                nthumb += 1
            elif ext in (".tif", ".tiff"):
                tif_thumb(f, prev)
                thumb_url = url(DERIVED_BASE, f"{a.id}/{rel_src}.png")
                nthumb += 1
        except Exception as e:
            nfail += 1
            print(f"  [{i}/{len(files)}] THUMB FAIL {f.name}: {e}", file=sys.stderr)

        # Per-channel / per-Z previews + meta.json
        if ext in PREVIEW_EXTS:
            print(f"  [{i}/{len(files)}] previews {f.name} …")
            meta = write_previews(f, out_dir, rel_src, ext)
            if meta:
                meta["filename"] = f.name
                meta["preview_base"] = url(DERIVED_BASE, f"{a.id}/{rel_src}")
                meta_path = out_dir / (rel_src + ".meta.json")
                meta_path.parent.mkdir(parents=True, exist_ok=True)
                meta_path.write_text(json.dumps(meta))
                meta_url = url(DERIVED_BASE, f"{a.id}/{rel_src}.meta.json")
                preview_url = f"{HOST}/data/viewer.html?meta={quote(meta_url)}"
                npreview += 1

        m = re.search(r"-(\d+)\.", f.name)
        rows.append({
            "File Name": f.name,
            "File Path": url(RAW_BASE, f.relative_to(RAW_ROOT).as_posix()),
            "Thumbnail": thumb_url,
            "Preview": preview_url,
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
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Done: {len(rows)} rows, {nthumb} thumbnails, {npreview} previews ({nfail} failed)")
    print(f"Manifest: {manifest}")


if __name__ == "__main__":
    main()

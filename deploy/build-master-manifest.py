#!/usr/bin/env python3
"""Generate the master Dataset Manifest that powers the /datasets page.

Reads:  deploy/datasets-meta.csv   (human-editable; one row per dataset)
Writes: /srv/shared/Dataset+Manifest.csv  (served at /data/Dataset+Manifest.csv)

To add a new dataset: append a row to datasets-meta.csv, then re-run this script.
To add a new metadata field: add a column to datasets-meta.csv; the script passes
all columns through to the output automatically.

Columns auto-computed (do NOT put these in datasets-meta.csv):
  dataset_path   — derived from dataset_id
  specific_query — derived from dataset_path + dataset_id
  file_count     — counted from the built per-dataset manifest on disk
  dataset_size   — summed from the built per-dataset manifest on disk
"""
import csv, json, sys
from pathlib import Path
from urllib.parse import quote

HOST       = "http://128.135.108.226"
NAS_BASE   = f"{HOST}/data/_derived/gardel"
DERIVED    = Path("/srv/shared/_derived/gardel")
OUT        = Path("/srv/shared/Dataset+Manifest.csv")
META_CSV   = Path(__file__).parent / "datasets-meta.csv"

# The /datasets page maps columns by DISPLAY LABEL, so output headers must
# be the display labels, not the Python keys.
# (python_key, display_label) — order controls column order in the output.
FIXED_COLUMNS = [
    ("dataset_id",           "Dataset ID"),
    ("dataset_name",         "Dataset name"),
    ("dataset_path",         "File Path"),
    ("dataset_size",         "Size"),
    ("description",          "Short description"),
    ("file_count",           "File count"),
    ("featured",             "Featured"),
    ("created",              "Creation date"),
    ("organization",         "Organization"),
    ("related_publication",  "Related publication"),
    ("doi",                  "DOI"),
    ("version",              "Version"),
    ("index",                "Index"),
    ("source",               "Source"),
    ("specific_query",       "Specific query"),
]
FIXED_KEYS = {k for k, _ in FIXED_COLUMNS}


def fmt_size(total_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if total_bytes < 1024:
            return f"{total_bytes:.1f} {unit}" if unit != "B" else f"{total_bytes} B"
        total_bytes /= 1024
    return f"{total_bytes:.1f} PB"


def manifest_stats(dataset_id: str) -> tuple[str, str]:
    """Return (file_count, dataset_size) by reading the per-dataset manifest."""
    manifest = DERIVED / f"{dataset_id}-manifest.csv"
    if not manifest.exists():
        return "—", "—"
    try:
        with open(manifest, newline="") as f:
            rows = list(csv.DictReader(f))
        count = len(rows)
        total = sum(int(r.get("File Size", 0) or 0) for r in rows)
        return str(count), fmt_size(total)
    except Exception:
        return "—", "—"


def make_specific_query(dataset_path: str, dataset_id: str) -> str:
    src = {"name": dataset_id, "type": "csv", "uri": dataset_path}
    return "source=" + quote(json.dumps(src, separators=(",", ":")), safe="")


def main() -> None:
    if not META_CSV.exists():
        sys.exit(f"datasets-meta.csv not found at {META_CSV}")

    with open(META_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Human-readable labels for extra columns added to datasets-meta.csv
    EXTRA_COLUMN_LABELS = {
        "group":             "group",
        "cell_line":         "Cell line",
        "microscopy":        "Microscopy",
        "magnification":     "Magnification",
        "pixel_size":        "Pixel size",
        "image_width_pixel": "Image width (px)",
        "image_width_um":    "Image width (µm)",
        "image_height_pixel":"Image height (px)",
        "image_height_um":   "Image height (µm)",
        "channel_1":         "Channel 1",
        "channel_2":         "Channel 2",
        "channel_3":         "Channel 3",
        "channel_4":         "Channel 4",
        "channel_5":         "Channel 5",
        "channel_6":         "Channel 6",
        "channel_7":         "Channel 7",
    }

    # Discover any extra columns the user added beyond the fixed set
    sample_keys = list(rows[0].keys()) if rows else []
    extra_keys = [k for k in sample_keys if k not in FIXED_KEYS]

    # Build output column spec: fixed columns + extras with nice display labels
    out_columns = list(FIXED_COLUMNS) + [(k, EXTRA_COLUMN_LABELS.get(k, k)) for k in extra_keys]

    out_rows = []
    for row in rows:
        did = row["dataset_id"].strip()
        dataset_path = f"{NAS_BASE}/{did}-manifest.csv"
        file_count, dataset_size = manifest_stats(did)

        out_rows.append({
            **row,
            "dataset_path":   dataset_path,
            "specific_query": make_specific_query(dataset_path, did),
            "file_count":     file_count,
            "dataset_size":   dataset_size,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([label for _, label in out_columns])
        for r in out_rows:
            w.writerow([r.get(key, "") for key, _ in out_columns])

    print(f"Wrote {len(out_rows)} dataset(s) to {OUT}")
    for r in out_rows:
        print(f"  {r['dataset_id']:35s}  files={r['file_count']:>6}  size={r['dataset_size']}")


if __name__ == "__main__":
    main()

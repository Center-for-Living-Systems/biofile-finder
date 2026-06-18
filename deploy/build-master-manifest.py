#!/usr/bin/env python3
"""Generate the master Dataset Manifest that powers the /datasets page.

Each entry becomes one row (a PublicDataset). `specific_query` is the preset
query that auto-opens the dataset's own file-manifest when clicked.

Writes /srv/shared/Dataset+Manifest.csv  (served at /data/Dataset+Manifest.csv).
Adding a dataset later = append to DATASETS and re-run (no rebuild needed).
"""
import csv, json
from urllib.parse import quote
from pathlib import Path

HOST = "https://128.135.108.226"
OUT = Path("/srv/shared/Dataset+Manifest.csv")

# The /datasets page maps columns by DISPLAY LABEL (annotations.find(name == displayLabel)),
# so CSV headers MUST be the display labels, not the machine prop names.
# (machine_key, csv_header) in display order.
LABELS = [
    ("dataset_id", "Dataset ID"),
    ("dataset_name", "Dataset name"),
    ("dataset_path", "File Path"),
    ("dataset_size", "Size"),
    ("description", "Short description"),
    ("file_count", "File count"),
    ("featured", "Featured"),
    ("created", "Creation date"),
    ("organization", "Organization"),
    ("related_publication", "Related publication"),
    ("doi", "DOI"),
    ("version", "Version"),
    ("index", "Index"),
    ("source", "Source"),
    ("specific_query", "Specific query"),
]


def specific_query(manifest_url: str, name: str) -> str:
    src = {"name": name, "type": "csv", "uri": manifest_url}
    return "source=" + quote(json.dumps(src, separators=(",", ":")), safe="")


DATASETS = [
    {
        "dataset_id": "031125data",
        "dataset_name": "031125data — Adhesion markers (Control vs YComp)",
        "dataset_path": f"{HOST}/data/_derived/031125data-manifest.csv",
        "dataset_size": "1.0 GB",
        "description": ("Confocal microscopy: 91 CZI (4 channels — eGFP-Zyxin 488, "
                        "Phalloidin 405, Vinculin 647, Paxillin 568) + 91 frontmask TIFs. "
                        "Conditions: Control vs YComp. Includes PNG previews."),
        "file_count": "189",
        "featured": "TRUE",
        "created": "2025-03-11",
        "organization": "University of Chicago",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "1",
        "source": "external",
    },
    {
        "dataset_id": "20250721-pPaxy118",
        "dataset_name": "20250721 — pPaxillin-Y118 (Control vs Y-comp)",
        "dataset_path": f"{HOST}/data/_derived/gardel/20250721-pPaxy118-manifest.csv",
        "dataset_size": "174 MB",
        "description": ("Confocal: 21 CZI (eGFP-Zyxin 488, Phalloidin 405, "
                        "pPaxillin-Y118 (rb) 647, Paxillin (m) 568) + ROI archives. "
                        "Control vs Y-comp. Served live from Gardel Lab NAS (read-only)."),
        "file_count": "32",
        "featured": "TRUE",
        "created": "2025-07-21",
        "organization": "University of Chicago — Gardel Lab",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "2",
        "source": "external",
    },
]


def main() -> None:
    for d in DATASETS:
        d["specific_query"] = specific_query(d["dataset_path"], d["dataset_id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([label for _, label in LABELS])
        for d in DATASETS:
            w.writerow([d.get(key, "") for key, _ in LABELS])
    print(f"Wrote {len(DATASETS)} dataset(s) to {OUT}")


if __name__ == "__main__":
    main()

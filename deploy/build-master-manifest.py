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

HOST = "http://128.135.108.226"
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


NAS_BASE = f"{HOST}/data/_derived/gardel"

# All four Annabel / FA-ML datasets from the Gardel Lab NAS.
# Manifests are built by running deploy/build-annabel-datasets.sh on the server.
# File counts and sizes are filled in after the first manifest build.
DATASETS = [
    {
        "dataset_id": "20250311-vinc-pax",
        "dataset_name": "20250311 — eGFP-Zyxin 488 / Phalloidin 405 / Vinculin 647 / Paxillin 568",
        "dataset_path": f"{NAS_BASE}/20250311-vinc-pax-manifest.csv",
        "dataset_size": "—",
        "description": ("Confocal CZI: eGFP-Zyxin (488), Phalloidin (405), "
                        "Vinculin (rb, 647), Paxillin (m, 568). "
                        "Focal-adhesion marker panel. "
                        "Served live from Gardel Lab NAS (read-only)."),
        "file_count": "—",
        "featured": "TRUE",
        "created": "2025-03-11",
        "organization": "University of Chicago — Gardel Lab",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "1",
        "source": "external",
    },
    {
        "dataset_id": "20250720-pfak-pax",
        "dataset_name": "20250720 — eGFP-Zyxin 488 / Phalloidin 405 / pFAK 647 / Paxillin 568",
        "dataset_path": f"{NAS_BASE}/20250720-pfak-pax-manifest.csv",
        "dataset_size": "—",
        "description": ("Confocal CZI: eGFP-Zyxin (488), Phalloidin (405), "
                        "pFAK (rb, 647), Paxillin (m, 568). "
                        "FAK-phosphorylation panel. "
                        "Served live from Gardel Lab NAS (read-only)."),
        "file_count": "—",
        "featured": "TRUE",
        "created": "2025-07-20",
        "organization": "University of Chicago — Gardel Lab",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "2",
        "source": "external",
    },
    {
        "dataset_id": "20250721-ppax118",
        "dataset_name": "20250721 — eGFP-Zyxin 488 / Phalloidin 405 / pPaxillin-Y118 647 / Paxillin 568",
        "dataset_path": f"{NAS_BASE}/20250721-ppax118-manifest.csv",
        "dataset_size": "—",
        "description": ("Confocal CZI: eGFP-Zyxin (488), Phalloidin (405), "
                        "pPaxillin-Y118 (rb, 647), Paxillin (m, 568). "
                        "Paxillin Y118 phosphorylation panel. "
                        "Served live from Gardel Lab NAS (read-only)."),
        "file_count": "—",
        "featured": "TRUE",
        "created": "2025-07-21",
        "organization": "University of Chicago — Gardel Lab",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "3",
        "source": "external",
    },
    {
        "dataset_id": "20260227-nih3t3-vinc-pax",
        "dataset_name": "20260227 — NIH3T3 / Zyxin-GFP / Phalloidin 405 / Vinculin 647 / Paxillin 555",
        "dataset_path": f"{NAS_BASE}/20260227-nih3t3-vinc-pax-manifest.csv",
        "dataset_size": "—",
        "description": ("Confocal CZI (reduced size): NIH3T3 cells, "
                        "Zyxin-GFP, Phalloidin (405), "
                        "Vinculin (rb, 647), Paxillin (m, 555). "
                        "Served live from Gardel Lab NAS (read-only)."),
        "file_count": "—",
        "featured": "TRUE",
        "created": "2026-02-27",
        "organization": "University of Chicago — Gardel Lab",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "4",
        "source": "external",
    },
    # --- Test datasets (Liya / bff_test_files) ---
    {
        "dataset_id": "test-czi",
        "dataset_name": "Test — CZI files",
        "dataset_path": f"{NAS_BASE}/test-czi-manifest.csv",
        "dataset_size": "—",
        "description": "Test CZI dataset for BioFile Finder preview development.",
        "file_count": "—",
        "featured": "TESTING",
        "created": "2026-07-14",
        "organization": "University of Chicago — Gardel Lab",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "5",
        "source": "external",
    },
    {
        "dataset_id": "test-tiff",
        "dataset_name": "Test — TIFF files",
        "dataset_path": f"{NAS_BASE}/test-tiff-manifest.csv",
        "dataset_size": "—",
        "description": "Test TIFF dataset for BioFile Finder preview development.",
        "file_count": "—",
        "featured": "TESTING",
        "created": "2026-07-14",
        "organization": "University of Chicago — Gardel Lab",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "6",
        "source": "external",
    },
    {
        "dataset_id": "test-nd",
        "dataset_name": "Test — ND2 files",
        "dataset_path": f"{NAS_BASE}/test-nd-manifest.csv",
        "dataset_size": "—",
        "description": "Test ND2 dataset for BioFile Finder preview development.",
        "file_count": "—",
        "featured": "TESTING",
        "created": "2026-07-14",
        "organization": "University of Chicago — Gardel Lab",
        "related_publication": "",
        "doi": "",
        "version": "1",
        "index": "7",
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

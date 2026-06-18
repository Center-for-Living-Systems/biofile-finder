#!/usr/bin/env python3
"""Build the PUBLIC allowlist of NAS files = exactly what's in the dataset manifests.

Creates /srv/published/gardel as a symlink tree containing ONLY the files
referenced by `File Path` in the per-dataset manifests under
/srv/shared/_derived/gardel/*-manifest.csv. Caddy serves /gardel/* from this
tree, so nothing else on the NAS is web-reachable. Re-run after onboarding a
dataset. Idempotent (rebuilds the tree from scratch).
"""
import csv, glob, shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

NAS = Path("/srv/gardelnas")
PUB = Path("/srv/published/gardel")
PREFIX = "/gardel/"
MANIFESTS = "/srv/shared/_derived/gardel/*-manifest.csv"


def main() -> None:
    if PUB.exists():
        shutil.rmtree(PUB)
    PUB.mkdir(parents=True)
    linked, missing = 0, 0
    for mf in sorted(glob.glob(MANIFESTS)):
        for row in csv.DictReader(open(mf)):
            fp = (row.get("File Path") or "").strip()
            path = urlparse(fp).path
            if not path.startswith(PREFIX):
                continue
            rel = unquote(path[len(PREFIX):])
            target = NAS / rel
            link = PUB / rel
            if not target.exists():
                missing += 1
                continue
            link.parent.mkdir(parents=True, exist_ok=True)
            if not link.exists():
                link.symlink_to(target)
                linked += 1
    print(f"published {linked} files to {PUB}" + (f" ({missing} missing on NAS)" if missing else ""))


if __name__ == "__main__":
    main()

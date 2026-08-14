#!/usr/bin/env bash
# Build per-dataset manifests for the four Annabel / FA-ML paxillin datasets.
# Run on the deployment server (128.135.108.226) as root or the service account.
#
# Prerequisites:
#   - NAS mounted at /srv/gardelnas  (run mount-nas.sh if not already mounted)
#   - pip install aicspylibczi Pillow numpy  (for CZI thumbnail generation)
#
# After this script completes, run build-master-manifest.py to regenerate
# the datasets-page index, then update file_count / dataset_size by hand if desired.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
BUILDER="$SCRIPT_DIR/build-nas-dataset.py"
NAS_ROOT="/srv/gardelnas"
FA_ML_BASE="$NAS_ROOT/Annabel/FA-ML/For-Liya_Data-Sets-that-look-good-and-contain-paxillin"

echo "=== 1/4  20250311 — Vinculin / Paxillin ==="
"$PYTHON" "$BUILDER" \
  --src "$FA_ML_BASE/20250311_eGFPZyxin488_Phalloidin405_Vinculin(rb)647_paxillin(m)568" \
  --id  "20250311-vinc-pax" \
  --name "20250311 eGFP-Zyxin Phalloidin Vinculin Paxillin"

echo ""
echo "=== 2/4  20250720 — pFAK / Paxillin ==="
"$PYTHON" "$BUILDER" \
  --src "$FA_ML_BASE/20250720_eGFP-Zyxin 488, Phalloidin 405, pFAK (rb) 647, paxillin(m)568" \
  --id  "20250720-pfak-pax" \
  --name "20250720 eGFP-Zyxin Phalloidin pFAK Paxillin"

echo ""
echo "=== 3/4  20250721 — pPaxillin-Y118 ==="
"$PYTHON" "$BUILDER" \
  --src "$FA_ML_BASE/20250721_eGFP-Zyxin 488_Phalloidin405_pPaxy118(rb) 647_Pax(m)568" \
  --id  "20250721-ppax118" \
  --name "20250721 eGFP-Zyxin Phalloidin pPaxillin-Y118 Paxillin"

echo ""
echo "=== 4/4  20260227 — NIH3T3 Vinculin / Paxillin ==="
"$PYTHON" "$BUILDER" \
  --src "$FA_ML_BASE/20260227_NIH3T3_ZyxinGFP,Phalloidin405,Vinc_rb647,Pax_m555_reduced_size_AH" \
  --id  "20260227-nih3t3-vinc-pax" \
  --name "20260227 NIH3T3 Zyxin-GFP Phalloidin Vinculin Paxillin"

echo ""
echo "=== All manifests built. Now regenerate the master index: ==="
echo "    python3 $SCRIPT_DIR/build-master-manifest.py"

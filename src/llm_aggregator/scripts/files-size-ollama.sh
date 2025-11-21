#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <base_path> <model_id>" >&2
  exit 1
fi

BASE_PATH=$1
MODEL_ID=$2

NAME=${MODEL_ID%%:*}
TAG=${MODEL_ID#*:}
if [[ "$TAG" == "$MODEL_ID" ]]; then
  TAG="latest"
fi

MANIFEST="${BASE_PATH%/}/manifests/registry.ollama.ai/library/${NAME}/${TAG}"

if [[ ! -f "$MANIFEST" ]]; then
  # If the manifest is missing, report zero to avoid hard failures.
  echo 0
  exit 0
fi

python3 - <<'PY' "$MANIFEST" || exit 1
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
try:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
except Exception:
    sys.exit(1)

layers = data.get("layers")
if not isinstance(layers, list):
    sys.exit(1)

total = 0
matched = False
for layer in layers:
    if isinstance(layer, dict):
        size = layer.get("size")
        if isinstance(size, int) and size >= 0:
            total += size
            matched = True

if not matched:
    sys.exit(1)

print(total)
PY

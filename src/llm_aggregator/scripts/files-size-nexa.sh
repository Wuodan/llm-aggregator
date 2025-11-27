#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <base_path> <model_id>" >&2
  exit 1
fi

BASE_PATH=$1
MODEL_ID=$2

# Drop quant suffix after colon if present
BASE_ID=${MODEL_ID%%:*}

PATTERN=${PATTERN//:/\?}
PATTERN="${PATTERN}*"

if [[ ! -d "$BASE_PATH" ]]; then
  exit 1
fi

tmpfile=$(mktemp)
trap 'rm -f "$tmpfile"' EXIT

find "$BASE_PATH" -type f -name "$PATTERN" -print0 > "$tmpfile"

if [[ ! -s "$tmpfile" ]]; then
  exit 1
fi

total=0
while IFS= read -r -d '' file; do
  if [[ -e "$file" ]]; then
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file")
    total=$((total + size))
  fi
done <"$tmpfile"

echo "$total"

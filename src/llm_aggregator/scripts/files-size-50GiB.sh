#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <base_path> <model_id>" >&2
  exit 1
fi

BASE_PATH=$1
MODEL_ID=$2

PATTERN=${MODEL_ID//\//\?}
PATTERN=${PATTERN//:/\?}
PATTERN="${PATTERN}*"

echo "$0: BASE_PATH=$BASE_PATH" >&2
echo "$0: PATTERN=$PATTERN" >&2

# 50 GiB
printf $((50 * 1024**3))

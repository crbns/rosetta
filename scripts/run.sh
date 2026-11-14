#!/usr/bin/env bash
# run.sh [board]: offline env + `python3 app.py` (app.py starts the engines). Plan §9.11 / §11.4.
#
#   scripts/run.sh                      # VLM_MODE=engine (resident C++), falls back to cli if not built
#   VLM_MODE=cli scripts/run.sh         # P0: one-shot tools/zetic_run.py per scan, no compile
#   DECIDER=none scripts/run.sh         # translation only
# Any plan §10.6 env var (VL_MODEL, D1_MODEL, VLM_CMD, D1_CMD, CAMERA, PORT, ...) passes through.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${IXIAN_SDK:-}" ]]; then
  if [[ -d "$HOME/rosetta/sdk" ]]; then
    IXIAN_SDK="$HOME/rosetta/sdk"
  elif [[ -d "$ROOT/sdk" ]]; then
    IXIAN_SDK="$ROOT/sdk"
  else
    IXIAN_SDK="$HOME/rosetta/sdk"
    echo "WARNING: no SDK at \$HOME/rosetta/sdk or ./sdk; set IXIAN_SDK" >&2
  fi
fi
export IXIAN_SDK
export LD_LIBRARY_PATH="$IXIAN_SDK/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

# Offline at runtime (plan §12 rule 1)
export HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 TRANSFORMERS_OFFLINE=1

export VLM_MODE="${VLM_MODE:-engine}"
if [[ "$VLM_MODE" == "engine" && -z "${VLM_CMD:-}" && ! -x engine/build/rosetta_vlm ]]; then
  echo "WARNING: engine/build/rosetta_vlm not built; falling back to VLM_MODE=cli (one-shot, ~3.3 s slower per scan)" >&2
  echo "         build it with: scripts/setup_board.sh" >&2
  export VLM_MODE=cli
fi

echo "rosetta: IXIAN_SDK=$IXIAN_SDK VLM_MODE=$VLM_MODE DECIDER=${DECIDER:-zetic} HOST=${HOST:-127.0.0.1} PORT=${PORT:-8000}" >&2
exec python3 app.py "$@"

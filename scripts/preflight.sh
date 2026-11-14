#!/usr/bin/env bash
# Vendored from heath0xFF/cleared-for-takeoff-hackathon (MIT)
# MIT License. Copyright (c) 2026 On-Device AI Hackathon contributors
# Source: skills/iq9-preflight/scripts/preflight.sh
# shellcheck disable=SC2015  # `test && add ok || add FAIL` is intended: add() always returns 0
# preflight.sh: is this IQ-9075 ready for the hackathon stack? Read-only; changes nothing, downloads nothing.
#
#   preflight.sh [--json] [--profile reference|generator|board] [--model cached-name:precision]
# reference checks the full example stack; generator omits d1; board checks hardware only.
#
# Exit 0: no FAIL. Exit 1: at least one FAIL. WARN never fails the run.
# Env: D1_PYTHON (default ~/.venvs/d1/bin/python), D1_MODEL_DIR (default ~/models/d1-2B),
#      EXPECT_GENIEX (default v0.10.0), MIN_FREE_GB (default 10), GENIEX_PORT (default 18181)

set -euo pipefail

JSON=0
PROFILE=reference
MODEL="LiquidAI/LFM3-1.7B-GGUF:Q4_0"
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1; shift ;;
    --profile|--model)
      [ $# -ge 2 ] || { echo "missing value for $1" >&2; exit 64; }
      if [ "$1" = --profile ]; then PROFILE="$2"; else MODEL="$2"; fi
      shift 2 ;;
    --help|-h)
      echo "usage: preflight.sh [--json] [--profile reference|generator|board] [--model cached-name:precision]"
      exit 0 ;;
    *) echo "unknown flag: $1" >&2; exit 64 ;;
  esac
done
case "$PROFILE" in reference|generator|board) ;; *) echo "invalid profile: $PROFILE" >&2; exit 64 ;; esac
[[ "$MODEL" == *:* && -n "${MODEL%:*}" && -n "${MODEL##*:}" ]] || { echo "--model needs a cached name:precision" >&2; exit 64; }
D1_PYTHON="${D1_PYTHON:-$HOME/.venvs/d1/bin/python}"
D1_MODEL_DIR="${D1_MODEL_DIR:-$HOME/models/d1-2B}"
EXPECT_GENIEX="${EXPECT_GENIEX:-v0.10.0}"
MIN_FREE_GB="${MIN_FREE_GB:-10}"
PORT="${GENIEX_PORT:-18181}"
D1_REVISION="10e7671d44e4b37700020b1eed3f594c5f2af0b4"

RESULTS=()
FAILS=0
add() {  # status name detail fix
  local s="$1" n="$2" d="$3" f="${4:-}"
  if [ "$s" = FAIL ]; then FAILS=$((FAILS + 1)); fi
  RESULTS+=("$s"$'\t'"$n"$'\t'"$d"$'\t'"$f")
  return 0
}

# ---- board ------------------------------------------------------------------------------------------
arch="$(uname -m)"
[ "$arch" = aarch64 ] && add ok arch "$arch" || add FAIL arch "$arch" "run this on the IQ-9075"

# Informational for every profile: this is not a display test or affected-version detection.
add WARN display "external monitor compatibility not checked; organizer-reported Adreno APT update issue; SSH unaffected" \
  "for monitor setups, confirm the affected update and approved removal/rollback with organizers; upstream installer is not event-adapted (docs/developer-guide.md section 3.2)"

nodes="$(find /dev -maxdepth 1 -name 'fastrpc-cdsp*' ! -name '*-secure' 2>/dev/null | wc -l | tr -d ' ')"
[ "$nodes" -ge 2 ] && add ok npu-nodes "$nodes CDSP nodes (/dev/fastrpc-cdsp, -cdsp1)" \
  || add FAIL npu-nodes "$nodes CDSP nodes (expect 2)" "inspect drivers and permissions; see docs/developer-guide.md section 3.2 (ask before changes; do not install/update Adreno as a generic NPU fix)"

# GenieX needs read AND write access; readable-only nodes still fail at runtime.
npu_bad=""
while IFS= read -r node; do
  [ -n "$node" ] || continue
  if [ ! -r "$node" ] || [ ! -w "$node" ]; then
    npu_bad="$npu_bad ${node#/dev/}($(stat -c '%U:%G %a' "$node" 2>/dev/null || echo '?'))"
  fi
done < <(find /dev -maxdepth 1 -name 'fastrpc-cdsp*' ! -name '*-secure' 2>/dev/null | sort)
if [ "$nodes" -ge 1 ]; then
  if [ -z "$npu_bad" ]; then add ok npu-access "read/write by $(id -un)"
  elif getent group fastrpc >/dev/null 2>&1; then
    if case " $(id -nG) " in *" fastrpc "*) true ;; *) false ;; esac; then
      add FAIL npu-access "not read/write by $(id -un):$npu_bad" "in fastrpc but no access: inspect udev rules/node group; see docs/developer-guide.md section 3.2"
    else
      add FAIL npu-access "not read/write by $(id -un):$npu_bad" "with approval: sudo usermod -aG fastrpc $(id -un), then start a new login/SSH session"
    fi
  else
    add FAIL npu-access "not read/write by $(id -un):$npu_bad; no fastrpc group" "FastRPC package (qcom-fastrpc1) not installed or rules missing; see docs/developer-guide.md section 3.2 (ask first)"
  fi
fi

free_gb="$(df -BG --output=avail / 2>/dev/null | tail -1 | tr -dc '0-9' || true)"
if [ -n "$free_gb" ]; then
  [ "$free_gb" -ge "$MIN_FREE_GB" ] && add ok disk "${free_gb}G free on /" \
    || add WARN disk "${free_gb}G free on / (< ${MIN_FREE_GB}G)" "geniex list; remove only models the user confirms are unused"
fi

mem_gb="$(awk '/MemAvailable/ {printf "%d", $2/1024/1024}' /proc/meminfo 2>/dev/null || true)"
if [ -n "$mem_gb" ]; then
  min_mem=2; [ "$PROFILE" != reference ] || min_mem=20
  [ "$mem_gb" -ge "$min_mem" ] && add ok memory "${mem_gb} GiB available" \
    || add WARN memory "${mem_gb} GiB available (planning floor ${min_mem} GiB, not a measured model requirement)" "measure app peak RSS; ask before stopping other processes"
fi

# ---- geniex (reference/generator profiles) -----------------------------------------------------------
if [ "$PROFILE" != board ]; then
if command -v geniex >/dev/null; then
  ver="$(geniex version 2>/dev/null | awk -F': *' '/CLI Version/ {print $2}' | tr -d ' ' || true)"
  [ "$ver" = "$EXPECT_GENIEX" ] && add ok geniex "$ver" \
    || add WARN geniex "${ver:-unknown} (reference target $EXPECT_GENIEX)" "the active stack may not apply; do not reinstall without asking"
  chip="$(geniex config get chipset 2>/dev/null | tail -1 || true)"
  case "$chip" in *IQ-9075*) add ok chipset "$chip" ;; *) add WARN chipset "${chip:-unknown}" "" ;; esac
  list="$(geniex list 2>/dev/null || true)"
  repo="${MODEL%:*}"; precision="${MODEL##*:}"
  if echo "$list" | awk -F'│' -v r="$repo" -v p="$precision" '{gsub(/ /,"",$2); gsub(/ /,"",$4)} $2==r && ($4==p || (p=="Q4_0" && $4=="QAD-Q4_0")) {f=1} END {exit !f}'; then
    add ok "model:$repo" "$precision cached"
  else
    add FAIL "model:$repo" "$precision not registered in cache" "inspect existing local weights and disk; ask before any import or download (geniex pull)"
  fi
else
  add FAIL geniex "not on PATH" "export PATH=\"\$HOME/.local/bin:\$PATH\", or install per docs/developer-guide.md §3.3"
fi

if curl -fsS -o /dev/null -m 3 "http://127.0.0.1:$PORT/v1/models" 2>/dev/null; then
  add ok server "geniex serve answering on 127.0.0.1:$PORT"
else
  add WARN server "no successful /v1/models response on 127.0.0.1:$PORT" "start a foreground server in a separate pane: skills/iq9-geniex-lfm/scripts/serve.sh run"
fi
fi

# ---- optional d1 (reference profile only) ------------------------------------------------------------
if [ "$PROFILE" = reference ]; then
if [ -x "$D1_PYTHON" ]; then
  # shellcheck disable=SC2016
  vers="$("$D1_PYTHON" -c 'import torch, transformers; print(torch.__version__, transformers.__version__)' 2>/dev/null || true)"
  if [ -n "$vers" ]; then add ok d1-venv "$D1_PYTHON (torch/transformers $vers)"
  else add FAIL d1-venv "$D1_PYTHON cannot import torch/transformers" "see examples/system-one-decision/README.md (Install)"; fi
else
  add FAIL d1-venv "no python at $D1_PYTHON" "see examples/system-one-decision/README.md (Install)"
fi
if [ -f "$D1_MODEL_DIR/model.safetensors" ]; then
  rev="$(cat "$D1_MODEL_DIR/REVISION" 2>/dev/null | tr -d '[:space:]' || true)"
  [ "$rev" = "$D1_REVISION" ] && add ok d1-snapshot "$D1_MODEL_DIR @ ${rev:0:12}" \
    || add FAIL d1-snapshot "REVISION ${rev:-missing} (expected ${D1_REVISION:0:12})" "inspect local snapshots first; ask before fetch_d1.py or moving the pin; review remote code"
else
  add FAIL d1-snapshot "no model.safetensors in $D1_MODEL_DIR" "inspect local snapshots first; ask before fetch_d1.py (needs network, about 3.8 GB)"
fi
fi

# ---- thermal (the default sensor) -------------------------------------------------------------------
zones=0
for z in /sys/class/thermal/thermal_zone*/temp; do
  if [ -r "$z" ] && cat "$z" >/dev/null 2>&1; then zones=$((zones + 1)); fi
done
[ "$zones" -gt 0 ] && add ok thermal "$zones readable thermal zones" || add WARN thermal "no readable thermal zones" ""

# ---- network (informational) ------------------------------------------------------------------------
if curl -fsS -o /dev/null -m 4 https://huggingface.co 2>/dev/null; then add ok network "external HTTPS probe succeeded (demo must run offline)"
else add ok network "external probe failed (offline or endpoint unreachable; not a rehearsal)"; fi

# ---- report -----------------------------------------------------------------------------------------
if [ "$JSON" -eq 1 ]; then
  printf '%s\n' "${RESULTS[@]}" | python3 -c '
import json, sys
rows = [l.rstrip("\n").split("\t") for l in sys.stdin if l.strip()]
checks = [{"status": r[0], "check": r[1], "detail": r[2], "fix": r[3] if len(r) > 3 and r[3] else None} for r in rows]
print(json.dumps({"ready": not any(c["status"] == "FAIL" for c in checks), "profile": sys.argv[1], "model": sys.argv[2] if sys.argv[1] != "board" else None, "checks": checks}, indent=1))' "$PROFILE" "$MODEL"
else
  for r in "${RESULTS[@]}"; do
    IFS=$'\t' read -r s n d f <<<"$r"
    printf '[%-4s] %-32s %s\n' "$s" "$n" "$d"
    if [ -n "$f" ] && [ "$s" != ok ]; then printf '       fix: %s\n' "$f"; fi
  done
  [ "$FAILS" -eq 0 ] && echo "ready" || echo "$FAILS check(s) failed"
fi
[ "$FAILS" -eq 0 ]

#!/usr/bin/env bash
# setup_board.sh [board]: print the sudo commands of plan §11.3 for a HUMAN to paste (never runs them),
# then run read-only readiness checks, then build engine/ if every check passes (or with --build).
#
#   scripts/setup_board.sh [--build] [--no-build] [--print-only] [--no-verify]
#     --build       build engine/ even if some checks failed
#     --no-build    checks only
#     --print-only  print the sudo commands and exit
#     --no-verify   skip the SDK verify-load of each model (~1 min each); checksums still run
#
# Env: IXIAN_SDK (default $HOME/rosetta/sdk, else ./sdk), VL_MODEL, D1_MODEL (plan §10.6).
# Rules (plan §12): never chmod device nodes, never apt upgrade, never install qcom-adreno1,
# never type passwords into commands. This script installs nothing and changes nothing outside engine/build.
set -uo pipefail

FORCE_BUILD=0; NO_BUILD=0; PRINT_ONLY=0; NO_VERIFY=0
for arg in "$@"; do
  case "$arg" in
    --build) FORCE_BUILD=1 ;;
    --no-build) NO_BUILD=1 ;;
    --print-only) PRINT_ONLY=1 ;;
    --no-verify) NO_VERIFY=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${IXIAN_SDK:-}" ]]; then
  if [[ -d "$HOME/rosetta/sdk" ]]; then IXIAN_SDK="$HOME/rosetta/sdk"; else IXIAN_SDK="$ROOT/sdk"; fi
fi
VL_MODEL="${VL_MODEL:-models/lfm3-vl-2b}"
D1_MODEL="${D1_MODEL:-models/d1-2b}"

cat <<'EOF'
================================================================================
 PASTE THESE YOURSELF (human types sudo password). This script does NOT run them.
 NO qcom-adreno1. NO install_ppa_pkgs.sh. NO apt upgrade.
================================================================================
sudo apt-get update
apt-get -s install --no-install-recommends libatomic1 qcom-fastrpc1 libqnn1     # simulate; read the plan
sudo apt-get \
  install --no-install-recommends libatomic1 qcom-fastrpc1 libqnn1
sudo usermod -aG fastrpc "$USER"        # then RECONNECT ssh; check: id -nG | grep fastrpc
sudo apt-get \
  install --no-install-recommends cmake g++ make python3-opencv nlohmann-json3-dev tmux
================================================================================
EOF
(( PRINT_ONLY )) && exit 0

FAILS=0
ok()   { printf '  ok    %s\n' "$*"; }
warn() { printf '  WARN  %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*"; FAILS=$((FAILS + 1)); }

echo
echo "== read-only checks (IXIAN_SDK=$IXIAN_SDK)"

[[ "$(uname -m)" == "aarch64" ]] && ok "arch aarch64" || warn "arch $(uname -m) (SDK only runs on the IQ9)"

found_dev=0
for n in /dev/fastrpc-cdsp*; do
  [[ -e "$n" ]] || continue
  found_dev=1
  if [[ -r "$n" && -w "$n" ]]; then ok "rw $n"; else fail "no rw on $n (add user to fastrpc group + reconnect; never chmod)"; fi
done
(( found_dev )) || fail "no /dev/fastrpc-cdsp* nodes (qcom-fastrpc1 installed?)"

if id -nG | tr ' ' '\n' | grep -qx fastrpc; then ok "user in fastrpc group"; else fail "user not in fastrpc group (usermod above, then reconnect ssh)"; fi

if command -v cmake >/dev/null 2>&1; then ok "$(cmake --version | head -1)"; else fail "cmake missing"; fi
if command -v g++ >/dev/null 2>&1; then ok "$(g++ --version | head -1)"; else fail "g++ missing"; fi
if python3 -c 'import cv2' >/dev/null 2>&1; then
  ok "python3 cv2 $(python3 -c 'import cv2; print(cv2.__version__)')"
else
  warn "python3 cv2 missing (camera falls back to upload; apt python3-opencv)"
fi

if [[ -d "$IXIAN_SDK/bin" ]]; then
  ok "SDK bin: $(ls "$IXIAN_SDK/bin" | tr '\n' ' ')"
  [[ -x "$IXIAN_SDK/bin/zetic_lfm3_cli" ]] || fail "missing $IXIAN_SDK/bin/zetic_lfm3_cli"
  [[ -x "$IXIAN_SDK/bin/zetic_d1_cli" ]] || fail "missing $IXIAN_SDK/bin/zetic_d1_cli"
  [[ -f "$IXIAN_SDK/lib/libzetic_ixian_hexagon.so" ]] || fail "missing $IXIAN_SDK/lib/libzetic_ixian_hexagon.so"
  [[ -f "$IXIAN_SDK/lib/libhexrt_v73_skel.so" ]] || fail "missing $IXIAN_SDK/lib/libhexrt_v73_skel.so"
  [[ -d "$IXIAN_SDK/lib/cmake" ]] || fail "missing $IXIAN_SDK/lib/cmake (find_package IxianHexagon)"
else
  fail "no SDK at $IXIAN_SDK/bin (scp stage/sdk; set IXIAN_SDK)"
fi

for m in "$VL_MODEL" "$D1_MODEL"; do
  if [[ -f "$m/v73/manifest.json" ]]; then
    ok "manifest $m/v73/manifest.json ($(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("package",{}).get("name"), d.get("target",{}).get("name"), "nsp", d.get("target",{}).get("nsp"))' "$m/v73/manifest.json" 2>/dev/null || echo unparsed))"
  else
    fail "no $m/v73/manifest.json (scp stage/models; ln -s ../models models)"
  fi
done
[[ -f "$VL_MODEL/v73-1nsp/manifest.json" ]] && ok "optional $VL_MODEL/v73-1nsp present" || warn "no $VL_MODEL/v73-1nsp (only needed if NSPs contend)"

# Re-check package checksums on the board: the laptop verified them, but laptop -> USB -> scp can truncate.
if command -v sha256sum >/dev/null 2>&1; then SHA=(sha256sum); else SHA=(shasum -a 256); fi
for m in "$VL_MODEL" "$D1_MODEL"; do
  if [[ ! -f "$m/v73/SHA256SUMS" ]]; then
    fail "no $m/v73/SHA256SUMS (incomplete copy? re-scp from stage/models)"
  elif out="$(cd "$m/v73" && "${SHA[@]}" -c SHA256SUMS 2>&1)"; then
    ok "sha256 $m/v73 ($(grep -c ': OK$' <<<"$out") files)"
  else
    fail "sha256 mismatch in $m/v73 (re-copy from stage/models; never edit packages):"
    grep -v ': OK$' <<<"$out" | head -5 | sed 's/^/          /'
  fi
done

# SDK verify-load (starter repo examples/zetic-lfm/README.md): proves libs + FastRPC + package + NPU together.
# verify_load <label> <log name> <cmd...>: FAIL on nonzero exit; WARN if no hexrt load line (plan §8.5 evidence).
verify_load() {
  local label="$1" log="${TMPDIR:-/tmp}/rosetta_verify_$2.log"; shift 2
  if LD_LIBRARY_PATH="$IXIAN_SDK/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" timeout 180s "$@" >"$log" 2>&1; then
    ok "verify-load $label"
    grep -m1 'hexrt open' "$log" | sed 's/^/          /' || warn "verify-load $label: no 'hexrt open' line (see $log)"
  else
    fail "verify-load $label exited $? (log: $log):"
    tail -5 "$log" | sed 's/^/          /'
  fi
}
if (( NO_VERIFY )); then
  warn "SDK verify-load skipped (--no-verify)"
elif ! command -v timeout >/dev/null 2>&1; then
  warn "SDK verify-load skipped (no 'timeout' command; not on the board?)"
else
  [[ -x "$IXIAN_SDK/bin/zetic_lfm3_cli" && -f "$VL_MODEL/v73/manifest.json" ]] \
    && verify_load "$VL_MODEL (lfm3, v73)" lfm3 "$IXIAN_SDK/bin/zetic_lfm3_cli" info --model "$VL_MODEL" --target v73 --verify --verbose
  [[ -x "$IXIAN_SDK/bin/zetic_d1_cli" && -f "$D1_MODEL/v73/manifest.json" ]] \
    && verify_load "$D1_MODEL (d1)" d1 "$IXIAN_SDK/bin/zetic_d1_cli" info --model "$D1_MODEL" --verify --verbose
fi

if [[ -f engine/third_party/nlohmann/json.hpp ]] || [[ -f /usr/include/nlohmann/json.hpp ]]; then
  ok "nlohmann/json.hpp available"
else
  fail "nlohmann/json.hpp missing (engine/third_party or apt nlohmann-json3-dev)"
fi

echo
echo "== $FAILS check(s) failed"

if (( NO_BUILD )); then exit $(( FAILS > 0 )); fi
if (( FAILS > 0 && ! FORCE_BUILD )); then
  echo "not building engine/ (fix the FAILs above, or rerun with --build). P0 path needs no build: VLM_MODE=cli scripts/run.sh"
  exit 1
fi
if [[ ! -f engine/CMakeLists.txt ]]; then
  echo "engine/CMakeLists.txt missing; nothing to build. Use VLM_MODE=cli scripts/run.sh"
  exit 1
fi

echo "== building engine/"
set -e
cmake -S engine -B engine/build -DCMAKE_PREFIX_PATH="$IXIAN_SDK/lib/cmake"
cmake --build engine/build -j8
ls -la engine/build/rosetta_vlm engine/build/rosetta_d1 2>/dev/null || true
echo "built. Run: scripts/run.sh   (VLM_MODE=engine default; VLM_MODE=cli fallback)"

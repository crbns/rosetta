#!/usr/bin/env bash
# stage_zetic.sh [laptop, Wi-Fi ON]: download + verify the ZETIC Ixian Hexagon SDK and the pinned
# LFM3-VL-2B / d1-2B IQ9 packages into ./stage/, and nlohmann/json.hpp into engine/third_party/.
# Plan §9.11 / §11.0. Idempotent: already-downloaded files that verify are skipped.
#
#   scripts/stage_zetic.sh [--1nsp] [--no-models] [--no-sdk]
#     --1nsp       also fetch the one-NSP packages ('v73-1nsp/*', ~2.4 GB more)
#     --no-models  SDK + json.hpp only
#     --no-sdk     models + json.hpp only
#
# Needs: curl, tar, shasum (or sha256sum), and `hf` (pipx install huggingface_hub) for models.
# Afterwards copy stage/ to the USB stick (exFAT) and scp stage/{sdk,models} to the board (§11.3).
set -euo pipefail

ONE_NSP=0; DO_MODELS=1; DO_SDK=1
for arg in "$@"; do
  case "$arg" in
    --1nsp) ONE_NSP=1 ;;
    --no-models) DO_MODELS=0 ;;
    --no-sdk) DO_SDK=0 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
STAGE="$ROOT/stage"
mkdir -p "$STAGE"

if command -v shasum >/dev/null 2>&1; then SHA=(shasum -a 256); else SHA=(sha256sum); fi
say() { printf '\n== %s\n' "$*"; }

# ---------------------------------------------------------------- SDK
REL=https://github.com/zetic-ai/IxianHexagon/releases/download
# (no associative arrays: macOS /bin/bash is 3.2)
pinned() {
  case "$1" in
    0.2.2) echo 0eec13f5ff8464f7ea7f9a8982042df249119aa01605327a4e3fe98e8fbecb05 ;;
    0.2.1) echo afb426755bb793efd929fc1a8e37fb7a5bd2ff3133576d5f3e22de8bb7fe8b0b ;;
  esac
}

# verify_tarball <file> <expected-hash>: shasum -c against a normalized "<hash>  <file>" line
verify_tarball() {
  (cd "$STAGE" && echo "$2  $1" | "${SHA[@]}" -c -)
}

fetch_sdk() {
  local v="$1" a="ixian-hexagon-$1-linux-arm64-qcom-iq9.tar.gz" expected
  if [[ -f "$STAGE/$a" ]] && verify_tarball "$a" "$(pinned "$v")" >/dev/null 2>&1; then
    echo "skip: $a already downloaded and verified"
    return 0
  fi
  echo "downloading $a"
  curl -fSL -o "$STAGE/$a.part" "$REL/$v/$a"
  mv "$STAGE/$a.part" "$STAGE/$a"
  curl -fSL -o "$STAGE/$a.sha256" "$REL/$v/$a.sha256"
  expected="$(awk 'NF{print $1; exit}' "$STAGE/$a.sha256")"
  if [[ "$expected" != "$(pinned "$v")" ]]; then
    echo "WARNING: $a.sha256 ($expected) differs from the plan's pinned hash ($(pinned "$v")); record in plan §16" >&2
  fi
  verify_tarball "$a" "$expected"
}

if (( DO_SDK )); then
  say "SDK 0.2.2 (default) + 0.2.1 (fallback)"
  fetch_sdk 0.2.2
  fetch_sdk 0.2.1 || echo "WARNING: SDK 0.2.1 fallback download/verify failed (non-fatal)" >&2

  A22="ixian-hexagon-0.2.2-linux-arm64-qcom-iq9.tar.gz"
  say "tar review: $A22"
  LISTING="$(tar -tzf "$STAGE/$A22")"
  echo "$LISTING" | head -25
  echo "... $(echo "$LISTING" | wc -l | tr -d ' ') entries"
  if echo "$LISTING" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
    echo "ERROR: tarball has absolute or '..' paths; refusing to extract" >&2; exit 1
  fi
  if [[ -x "$STAGE/sdk/bin/zetic_lfm3_cli" ]]; then
    echo "skip: stage/sdk already extracted"
  else
    mkdir -p "$STAGE/sdk"
    tar -xzf "$STAGE/$A22" --strip-components=1 -C "$STAGE/sdk"
    echo "extracted to stage/sdk"
  fi
  ls "$STAGE/sdk/bin" "$STAGE/sdk/lib" || true
fi

# ---------------------------------------------------------------- models
# pinned revisions (plan §11.0). If one 404s: drop --revision and record the actual commit in §16.
VL_REPO=ZETIC-ai/LFM3-VL-2B-IQ9; VL_REV=4b97823becd3c17a050aef419924af48075eb199
D1_REPO=ZETIC-ai/d1-2B-IQ9;      D1_REV=c82c9736e92a3cafcfbac7625ead99ad99138a89

verify_pkg() {  # verify_pkg <dir>: shasum -c SHA256SUMS inside the package dir
  [[ -f "$1/SHA256SUMS" ]] && (cd "$1" && "${SHA[@]}" -c SHA256SUMS >/dev/null 2>&1)
}

fetch_model() {  # fetch_model <repo> <rev> <local-dir> <subdir>
  local repo="$1" rev="$2" dir="$3" sub="$4"
  if verify_pkg "$dir/$sub"; then
    echo "skip: $dir/$sub already downloaded and verified"
  else
    echo "downloading $repo@$rev $sub/* -> $dir"
    # one --include per call: old argparse hf and new typer hf parse repeated/multi --include differently
    hf download "$repo" --revision "$rev" --include "$sub/*" --local-dir "$dir"
    (cd "$dir/$sub" && "${SHA[@]}" -c SHA256SUMS)
  fi
  if [[ ! -f "$dir/LICENSE" || ! -f "$dir/README.md" ]]; then
    hf download "$repo" LICENSE README.md --revision "$rev" --local-dir "$dir"
  fi
}

if (( DO_MODELS )); then
  if ! command -v hf >/dev/null 2>&1; then
    echo "ERROR: 'hf' not found. pipx install huggingface_hub (or pip install -U huggingface_hub)" >&2
    exit 1
  fi
  say "models (pinned revisions)"
  fetch_model "$VL_REPO" "$VL_REV" "$STAGE/models/lfm3-vl-2b" v73
  fetch_model "$D1_REPO" "$D1_REV" "$STAGE/models/d1-2b" v73
  if (( ONE_NSP )); then
    fetch_model "$VL_REPO" "$VL_REV" "$STAGE/models/lfm3-vl-2b" v73-1nsp
  fi
  du -sh "$STAGE"/models/* || true
fi

# ---------------------------------------------------------------- nlohmann/json.hpp
JSON_HPP="$ROOT/engine/third_party/nlohmann/json.hpp"
say "nlohmann/json.hpp v3.12.0"
if [[ -s "$JSON_HPP" ]] && grep -q 'NLOHMANN_JSON_VERSION_MINOR 12' "$JSON_HPP"; then
  echo "skip: $JSON_HPP present (v3.12.x)"
else
  mkdir -p "$(dirname "$JSON_HPP")"
  curl -fSL -o "$JSON_HPP.part" https://github.com/nlohmann/json/releases/download/v3.12.0/json.hpp
  mv "$JSON_HPP.part" "$JSON_HPP"
  echo "wrote $JSON_HPP"
fi

say "done. stage/ contents:"
ls -la "$STAGE"
echo "Next: copy stage/ to the USB stick; scp -r stage/sdk stage/models \"\$IQ9_HOST\":rosetta/  (plan §11.3)"

#!/usr/bin/env python3
# Vendored from heath0xFF/cleared-for-takeoff-hackathon (MIT)
# MIT License. Copyright (c) 2026 On-Device AI Hackathon contributors
# Source: skills/iq9-offline-rehearsal/scripts/offline_audit.py
"""Static offline audit: find code that will break or phone home when the network is cut.

    python3 offline_audit.py <app-dir> [<more paths>...]
    python3 offline_audit.py apps/my-agent --json

Scans .py .js .ts .mjs .html .sh .json .toml .yaml .yml files for:
  hub-id      from_pretrained("org/name") / snapshot_download / hf_hub_download / pipeline("...", model="org/name")
              with a repo id instead of a local path
  local-only  from_pretrained(...) without local_files_only=True on the call
  pull        `geniex pull` or `pip install` inside app code (should happen before the cut)
  url         http(s) URLs to anything other than localhost / 127.0.0.1
  cdn         <script src=http...> / <link href=http...> / @import url(http...) in UI files
  telemetry   imports or calls known to send telemetry (wandb, sentry_sdk, posthog, mixpanel, segment, gradio share)
  env         reminders when HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE are not set anywhere

Exit 0 if no findings at level "error". This is a static check. It does not replace unplugging the cable.
"""

import argparse
import json
import os
import re
import sys

EXTS = {".py", ".js", ".ts", ".mjs", ".cjs", ".html", ".htm", ".sh", ".json", ".toml", ".yaml", ".yml", ".vue", ".jsx", ".tsx"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".mypy_cache"}
LOCAL = re.compile(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(:\d+)?", re.I)
URL = re.compile(r"https?://[^\s'\"<>)\]]+", re.I)
HUB_ID = re.compile(
    r"(from_pretrained|snapshot_download|hf_hub_download|AutoTokenizer\.from_pretrained|pipeline)\s*\(\s*"
    r"(?:[^)]*?model\s*=\s*)?[rbuf]?['\"]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)['\"]")
FETCH = r"(geniex\s+pull|pip3?\s+install|python3?\s+-m\s+pip\s+install|npm\s+(install|i)\b|apt(-get)?\s+install|curl\s.*\|\s*sh)"
# Executed fetches only: a shell line that starts with the command, or a Python subprocess/os.system call.
# Fix hints inside messages ("Run: geniex pull ...") are not findings.
PULL_SH = re.compile(r"^\s*(sudo\s+)?(\S+=\S+\s+)*" + FETCH)
PULL_PY = re.compile(r"(subprocess\.\w+|os\.system|os\.popen|Popen)\s*\(.*" + FETCH.replace("\\s+", "[\\s'\",]+"))
RULES = [
    ("error", "cdn", re.compile(r"<script[^>]+src=['\"]https?://|<link[^>]+href=['\"]https?://|@import\s+url\(['\"]?https?://", re.I)),
    ("warn", "telemetry", re.compile(r"\bimport\s+(wandb|sentry_sdk|posthog|mixpanel|analytics)\b|\bshare\s*=\s*True\b|"
                                     r"googletagmanager|google-analytics|segment\.com", re.I)),
]
ALLOW_URL_HOSTS = ("schemas.", "json-schema.org", "www.w3.org", "example.com")  # identifiers, not fetches


def files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for root, dirs, names in os.walk(p):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for n in names:
                full = os.path.join(root, n)
                if os.path.abspath(full) == os.path.abspath(__file__):
                    continue  # its own patterns would match
                if os.path.splitext(n)[1].lower() in EXTS:
                    yield os.path.join(root, n)


def scan(paths):
    findings, offline_env = [], False
    for f in files(paths):
        try:
            lines = open(f, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        is_script = f.endswith((".sh",))
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if "HF_HUB_OFFLINE" in s or "TRANSFORMERS_OFFLINE" in s:
                offline_env = True
            if s.startswith(("#", "//")) and not is_script:
                continue
            if s.startswith("#"):
                continue
            for m in HUB_ID.finditer(line):
                rid = m.group(2)
                if not rid.startswith((".", "/", "~")):
                    findings.append(("error", "hub-id", f, i, f"loads '{rid}' by repo id; use a local path"))
            # The call may wrap, so look a few lines ahead for the argument.
            if f.endswith(".py") and "from_pretrained(" in line and \
                    "local_files_only=True" not in " ".join(lines[i - 1:i + 3]):
                findings.append(("warn", "local-only", f, i,
                                 "from_pretrained() without local_files_only=True; a local path can still reach the Hub"))
            if (PULL_SH if is_script else PULL_PY).search(line):
                findings.append(("error", "pull", f, i, s[:160]))
            for level, kind, rx in RULES:
                if rx.search(line):
                    findings.append((level, kind, f, i, s[:160]))
            for m in URL.finditer(line):
                u = m.group(0)
                if LOCAL.match(u) or "{" in u or "$" in u or any(h in u for h in ALLOW_URL_HOSTS):
                    continue
                findings.append(("warn", "url", f, i, u[:160]))
    if not offline_env:
        findings.append(("info", "env", "-", 0,
                         "HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 are not set anywhere; set them in the launch "
                         "script so a missing file fails fast instead of trying the network"))
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    fs = scan(args.paths)
    if args.json:
        print(json.dumps([{"level": l, "kind": k, "file": f, "line": n, "detail": d} for l, k, f, n, d in fs], indent=1))
    else:
        for l, k, f, n, d in fs:
            print(f"[{l:5}] {k:10} {f}:{n}  {d}")
        errors = sum(1 for x in fs if x[0] == "error")
        print(f"{errors} error(s), {sum(1 for x in fs if x[0] == 'warn')} warning(s)")
    sys.exit(1 if any(x[0] == "error" for x in fs) else 0)


if __name__ == "__main__":
    main()

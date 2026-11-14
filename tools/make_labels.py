#!/usr/bin/env python3
"""Draft tools/labels.json from logged prop scans + check them against plan §14.4 "Must" (B11/B14). Stdlib only.

    python3 tools/make_labels.py [--log logs/rosetta.jsonl] [--key tools/prop_key.json]
                                 [--map 12=tibet,13=kyrgyz] [--out tools/labels.json] [--force] [--dry-run]

For each logged scan:
  1. Identify the prop: the prop in prop_key.json whose `fingerprint` regexes hit the most translated lines
     (needs >= 2 distinct hits), or an explicit --map scan_id=prop. Scans that match nothing (no-text image,
     random frames) are skipped.
  2. Label: every VLM line matching any `must` regex -> 1-based index (what calibrate.py expects).
  3. Acceptance: each `must` item found in >= 1 line? d1 flagged it (importance >= threshold)? severity >=
     min_severity? Tibetan prop: `unreadable` non-empty? Prints PASS/MISS per scan.

ALWAYS eyeball the printed lines before trusting labels.json: regexes are a draft, not ground truth.
Then: python3 tools/calibrate.py --holdout <3 scan ids>  and log the threshold in plan §16.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_records(path):
    recs = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("scan_id") is not None:
                recs[str(rec["scan_id"])] = rec          # last record wins for a duplicate id
    return recs


def proposal(rec):
    p = ((rec.get("vlm") or {}).get("proposal")) or {}
    return [str(x) for x in p.get("lines") or []], p.get("unreadable") or []


def identify(lines, key):
    text = "\n".join(lines)
    best, best_hits = None, 0
    for name, prop in key.items():
        if name.startswith("_"):
            continue
        hits = sum(1 for rx in prop.get("fingerprint", []) if re.search(rx, text, re.I))
        if hits > best_hits:
            best, best_hits = name, hits
    return (best, best_hits) if best_hits >= 2 else (None, best_hits)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--log", default=os.path.join(ROOT, "logs", "rosetta.jsonl"))
    ap.add_argument("--key", default=os.path.join(HERE, "prop_key.json"))
    ap.add_argument("--map", default="", help="scan_id=prop[,scan_id=prop...] overrides auto-detection")
    ap.add_argument("--out", default=os.path.join(HERE, "labels.json"))
    ap.add_argument("--threshold", type=float, default=float(os.environ.get("IMPORTANCE_THRESHOLD", "0.5")))
    ap.add_argument("--force", action="store_true", help="overwrite an existing --out")
    ap.add_argument("--dry-run", action="store_true", help="print only, write nothing")
    a = ap.parse_args()

    with open(a.key, encoding="utf-8") as fh:
        key = json.load(fh)
    overrides = dict(kv.split("=", 1) for kv in a.map.split(",") if "=" in kv)
    for sid, prop in overrides.items():
        if prop not in key:
            sys.exit(f"--map {sid}={prop}: unknown prop (have: {', '.join(k for k in key if not k.startswith('_'))})")
    try:
        recs = load_records(a.log)
    except OSError as exc:
        sys.exit(f"cannot read {a.log}: {exc}")

    labels, summary = {}, []
    for sid in sorted(recs, key=lambda s: int(s) if s.isdigit() else 0):
        rec = recs[sid]
        lines, unreadable = proposal(rec)
        if sid in overrides:
            prop, why = overrides[sid], "--map"
        else:
            prop, hits = identify(lines, key)
            why = f"{hits} fingerprint hits"
        if not prop:
            continue
        spec = key[prop]
        imp = (rec.get("d1") or {}).get("importance") or []
        sev = (rec.get("d1") or {}).get("severity")
        flagged, missing, unflagged = set(), [], []
        for item, rx in spec.get("must", {}).items():
            idx = [i for i, ln in enumerate(lines, 1) if re.search(rx, ln, re.I)]
            if not idx:
                missing.append(item)
                continue
            flagged.update(idx)
            ps = [imp[i - 1] for i in idx if i - 1 < len(imp) and isinstance(imp[i - 1], (int, float))]
            if not ps or max(ps) < a.threshold:
                unflagged.append(item)
        checks = []
        if spec.get("unreadable_required") and not unreadable:
            checks.append("unreadable empty (should hold the Tibetan line)")
        if spec.get("min_severity") is not None and (sev is None or sev < spec["min_severity"]):
            checks.append(f"severity {sev} < {spec['min_severity']}")
        ok = not missing and not checks
        labels[sid] = sorted(flagged)
        summary.append((sid, prop, ok))

        print(f"\n== scan {sid}: {prop} ({why})  about={((rec.get('input') or {}).get('about') or '')!r}  "
              f"severity={sev}  {'PASS' if ok else 'MISS'}")
        for i, ln in enumerate(lines, 1):
            p = imp[i - 1] if i - 1 < len(imp) else None
            mark = "*" if i in flagged else " "
            print(f"  {mark}{i:>2} {p if p is None else f'{p:.2f}':>5}  {ln}")
        for u in unreadable:
            print(f"   unreadable: {u}")
        for m in missing:
            print(f"  MISS must not translated/found: {m}")
        for m in unflagged:
            print(f"  low  d1 importance < {a.threshold} for: {m}")
        for c in checks:
            print(f"  MISS {c}")

    if not labels:
        sys.exit("no prop scans recognized in the log (use --map scan_id=prop)")
    print("\n== summary: " + "  ".join(f"{sid}:{prop}:{'PASS' if ok else 'MISS'}" for sid, prop, ok in summary))
    if a.dry_run:
        return
    if os.path.exists(a.out) and not a.force:
        sys.exit(f"{a.out} exists; review it or pass --force to overwrite")
    out = {"_comment": "Generated by tools/make_labels.py from prop_key.json regexes; reviewed by a human before calibrating."}
    out.update(labels)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"wrote {a.out} ({len(labels)} scans)")


if __name__ == "__main__":
    main()

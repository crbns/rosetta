#!/usr/bin/env python3
"""Pick IMPORTANCE_THRESHOLD from logged prop scans + hand labels (plan §9.11, B14). Stdlib only.

    python3 tools/calibrate.py [--log logs/rosetta.jsonl] [--labels tools/labels.json]
                               [--holdout 12,15,19] [--json]

labels.json: {"<scan_id>": [1-based indices of lines that MUST be flagged], ...}  (see tools/labels.example.json)
  A key may also be the logged image stem (e.g. "12" for logs/img/12.png). Labels come from §14.4.

Per-line importance per scan, from the JSONL record (§9.2):
  1. d1.importance  full list, one p per VLM line in order (index 0 = line 1)   <- preferred
     (also accepted: [[line, p], ...] or {"<line>": p})
  2. d1.top         [[line, p], ...] fallback; lines missing from top are scored p=0.0 (pessimistic recall)
Line count comes from vlm.lines (int) or len(importance); labels beyond it count as missed.

Sweeps thresholds 0.05..0.95 step 0.05, flags a line when p >= threshold, prints micro precision/recall/F1,
recommends the max-F1 threshold (ties -> higher threshold). With --holdout, fits on the other scans and
reports the held-out scans at the chosen threshold (plan: calibrate on 4 props, check on the other 3).
Log the result in plan §16.
"""

import argparse
import json
import os
import sys

THRESHOLDS = [round(0.05 * i, 2) for i in range(1, 20)]


def load_log(path):
    """Return {scan_id_str: record}; last record wins for duplicate ids. Skips unparseable lines."""
    records, bad = {}, 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if not isinstance(rec, dict) or rec.get("scan_id") is None:
                continue
            records[str(rec["scan_id"])] = rec
            img = (rec.get("input") or {}).get("image")
            if isinstance(img, str) and img:
                stem = os.path.splitext(os.path.basename(img))[0]
                records.setdefault("img:" + stem, rec)
    if bad:
        print(f"warning: skipped {bad} unparseable log line(s)", file=sys.stderr)
    return records


def line_scores(rec):
    """Return (scores {line_1based: p}, n_lines, source) or (None, 0, reason)."""
    d1 = rec.get("d1") or {}
    vlm = rec.get("vlm") or {}
    n_lines = vlm.get("lines") if isinstance(vlm.get("lines"), int) else None
    if isinstance(vlm.get("lines"), list):
        n_lines = len(vlm["lines"])
    imp = d1.get("importance")
    scores, source = {}, None
    if isinstance(imp, list) and imp:
        if all(isinstance(x, (int, float)) or x is None for x in imp):
            scores = {i + 1: float(p) for i, p in enumerate(imp) if p is not None}
            n_lines = max(n_lines or 0, len(imp))
        else:
            scores = {int(x[0]): float(x[1]) for x in imp
                      if isinstance(x, (list, tuple)) and len(x) >= 2 and x[1] is not None}
        source = "importance"
    elif isinstance(imp, dict) and imp:
        scores = {int(k): float(v) for k, v in imp.items() if v is not None}
        source = "importance"
    elif isinstance(d1.get("top"), list) and d1["top"]:
        scores = {int(x[0]): float(x[1]) for x in d1["top"]
                  if isinstance(x, (list, tuple)) and len(x) >= 2 and x[1] is not None}
        source = "top"
    else:
        return None, 0, "no d1.importance or d1.top"
    n_lines = max(n_lines or 0, max(scores) if scores else 0)
    return scores, n_lines, source


def build_dataset(records, labels):
    data, notes = [], []
    for key, must in labels.items():
        if key.startswith("_"):
            continue  # comments
        rec = records.get(str(key)) or records.get("img:" + str(key))
        if rec is None:
            notes.append(f"label {key!r}: no matching scan in log")
            continue
        scores, n_lines, source = line_scores(rec)
        if scores is None:
            notes.append(f"label {key!r}: {source}")
            continue
        if source == "top":
            notes.append(f"label {key!r}: using d1.top fallback (unlisted lines scored 0.0)")
        must = {int(i) for i in must}
        n = max(n_lines, max(must) if must else 0)
        data.append({"key": str(key), "scan_id": str(rec.get("scan_id")), "n": n,
                     "scores": scores, "must": must})
    return data, notes


def metrics(data, t):
    tp = fp = fn = tn = 0
    for d in data:
        for i in range(1, d["n"] + 1):
            flagged = d["scores"].get(i, 0.0) >= t
            want = i in d["must"]
            if flagged and want:
                tp += 1
            elif flagged:
                fp += 1
            elif want:
                fn += 1
            else:
                tn += 1
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"threshold": t, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4)}


def sweep(data):
    return [metrics(data, t) for t in THRESHOLDS]


def recommend(rows):
    # max F1; ties -> higher threshold (fewer false alarms at equal F1)
    return max(rows, key=lambda m: (m["f1"], m["threshold"]))


def print_table(title, rows, best=None):
    print(f"\n{title}")
    print(f"  {'thr':>5} {'prec':>6} {'rec':>6} {'F1':>6} {'tp':>4} {'fp':>4} {'fn':>4}")
    for m in rows:
        mark = "  <-" if best is not None and m["threshold"] == best["threshold"] else ""
        print(f"  {m['threshold']:>5.2f} {m['precision']:>6.3f} {m['recall']:>6.3f} {m['f1']:>6.3f}"
              f" {m['tp']:>4} {m['fp']:>4} {m['fn']:>4}{mark}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default="logs/rosetta.jsonl")
    ap.add_argument("--labels", default="tools/labels.json")
    ap.add_argument("--holdout", default="", help="comma-separated scan ids (label keys) to hold out")
    ap.add_argument("--json", action="store_true", help="print a JSON summary instead of tables")
    args = ap.parse_args()

    try:
        records = load_log(args.log)
        with open(args.labels, encoding="utf-8") as fh:
            labels = json.load(fh)
        if not isinstance(labels, dict):
            raise ValueError("labels must be a JSON object {scan_id: [line indices]}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    data, notes = build_dataset(records, labels)
    for n in notes:
        print("note:", n, file=sys.stderr)
    if not data:
        print("error: no labeled scans with d1 scores found", file=sys.stderr)
        return 1

    hold = {h.strip() for h in args.holdout.split(",") if h.strip()}
    fit = [d for d in data if d["key"] not in hold and d["scan_id"] not in hold]
    held = [d for d in data if d["key"] in hold or d["scan_id"] in hold]
    if hold and not fit:
        print("error: --holdout leaves no scans to fit on", file=sys.stderr)
        return 1

    rows = sweep(fit)
    best = recommend(rows)
    held_m = metrics(held, best["threshold"]) if held else None
    summary = {"fit_scans": [d["key"] for d in fit], "holdout_scans": [d["key"] for d in held],
               "sweep": rows, "recommended": best, "holdout_at_recommended": held_m,
               "IMPORTANCE_THRESHOLD": best["threshold"]}

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"fit on {len(fit)} scan(s): {', '.join(summary['fit_scans'])}"
          f"  ({sum(d['n'] for d in fit)} lines, {sum(len(d['must']) for d in fit)} must-flag)")
    print_table("threshold sweep (fit set)", rows, best)
    print(f"\nrecommended: IMPORTANCE_THRESHOLD={best['threshold']:.2f}"
          f"  (P={best['precision']:.3f} R={best['recall']:.3f} F1={best['f1']:.3f})")
    if held_m is not None:
        print(f"held-out {len(held)} scan(s) [{', '.join(summary['holdout_scans'])}] at {best['threshold']:.2f}:"
              f" P={held_m['precision']:.3f} R={held_m['recall']:.3f} F1={held_m['f1']:.3f}"
              f" (tp {held_m['tp']} fp {held_m['fp']} fn {held_m['fn']})")
    print("log this in plan §16.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

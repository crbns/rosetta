#!/usr/bin/env python3
"""Medians of our own workload from logs/rosetta.jsonl for the README (plan §9.8, §11.5). Stdlib only.

    python3 tools/metrics.py [--log logs/rosetta.jsonl] [--since <scan_id>] [--mode engine|cli]
                             [--skip-first] [--url http://127.0.0.1:8000]

Uses only successful scans (VLM ok, d1 ok, no errors). --since drops earlier scans (e.g. mock runs).
--skip-first drops the lowest scan_id in the window (the warm-up scan, if --since points at it). --url also reads
peak_rss_mb from GET /status. Prints a markdown table with sample counts; never quote vendor numbers.
"""

import argparse
import json
import statistics
import sys
import urllib.request


def med(values):
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    return (statistics.median(vals), len(vals)) if vals else (None, 0)


def fmt(m, n, digits):
    return "—" if m is None else f"{m:.{digits}f} (n={n})"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--log", default="logs/rosetta.jsonl")
    ap.add_argument("--since", type=int, default=0, help="only scan_id >= this")
    ap.add_argument("--mode", default=None, help="only this VLM mode (engine|cli)")
    ap.add_argument("--skip-first", action="store_true")
    ap.add_argument("--url", default=None, help="app URL to read peak RSS from /status")
    a = ap.parse_args()

    recs = []
    with open(a.log, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            v, d = r.get("vlm") or {}, r.get("d1") or {}
            if (int(r.get("scan_id") or 0) >= a.since and v.get("ok") and d.get("ok") and not r.get("errors")
                    and (a.mode is None or v.get("mode") == a.mode)):
                recs.append(r)
    recs.sort(key=lambda r: int(r.get("scan_id") or 0))
    if a.skip_first and recs:
        recs = recs[1:]
    if not recs:
        sys.exit("no successful scans in range")

    def col(section, key):
        return [(r.get(section) or {}).get(key) for r in recs]

    modes = sorted({str((r.get("vlm") or {}).get("mode")) for r in recs})
    rows = [
        ("VLM read (s/scan)", med(col("vlm", "seconds")), 2),
        ("TTFT (ms)", med(col("vlm", "ttft_ms")), 0),
        ("Decode (tok/s)", med(col("vlm", "tok_s")), 1),
        ("Completion tokens", med(col("vlm", "completion_tokens")), 0),
        ("d1 (s/scan)", med(col("d1", "seconds")), 2),
        ("d1 passes", med(col("d1", "passes")), 0),
        ("End-to-end (s)", med(col("metrics", "total_s")), 2),
    ]
    rss = "—"
    if a.url:
        try:
            st = json.load(urllib.request.urlopen(a.url.rstrip("/") + "/status", timeout=5))
            eng = st.get("engines") or {}
            rss = f"{(eng.get('vlm') or {}).get('peak_rss_mb', '—')} / {(eng.get('d1') or {}).get('peak_rss_mb', '—')}"
        except Exception as exc:
            print(f"warning: /status: {exc}", file=sys.stderr)

    ids = [r.get("scan_id") for r in recs]
    print(f"_Measured on the board: medians of {len(recs)} successful scans (scan_id {ids[0]}–{ids[-1]}), "
          f"VLM mode {', '.join(modes)}._\n")
    print("| Metric | Value |\n|---|---|")
    for name, (m, n), digits in rows:
        print(f"| {name} | {fmt(m, n, digits)} |")
    print(f"| Peak RSS VLM / d1 (MB) | {rss} |")
    if len(recs) < 5:
        print(f"\nwarning: only {len(recs)} scans; plan §9.8 wants >= 5", file=sys.stderr)


if __name__ == "__main__":
    main()

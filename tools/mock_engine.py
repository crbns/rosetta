"""Offline JSONL stand-ins for the two Ixian engines."""
import argparse
import json
import sys
import time

VLM = {
    "languages": ["Chinese", "Tibetan"],
    "summary": "Trailhead visitor notice at 4,650 m altitude.",
    "lines": [
        "Visitor notice", "Trail entrance · Altitude 4,650 m",
        "1. There is no mobile phone signal on this entire route.",
        "2. You must descend before 14:00. Thunderstorms and hail are common in the afternoon.",
        "3. If you have headache, vomiting or difficulty breathing (altitude sickness), descend immediately; do not keep climbing.",
        "4. Do not enter herders' pastures; beware of Tibetan mastiffs.",
        "5. Nearest supplies: checkpoint 5 km away (drinking water, oxygen).",
        "6. Fires and camping by the lake are strictly prohibited.",
        "Rescue phone (call where there is signal): 120",
    ],
    "unreadable": ["Top line: Tibetan script, cannot read confidently"],
    "answer": "Yes, but be back down before 14:00; there's no signal on the route.",
}
IMPORTANCE = [.08, .41, .83, .91, .97, .66, .58, .62, .71]
SEVERITY = ["Just information", "Good to know", "Caution: affects your plans, time or money",
            "Warning: legal trouble or health risk if ignored", "Danger: risk of serious injury or death"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=("vlm", "d1"))
    p.add_argument("--shape", choices=("dict", "list"), default="dict")
    p.add_argument("--delay", type=float, default=.3)
    p.add_argument("--fail-every", type=int, default=0)
    args = p.parse_args()
    ready = {"event": "ready", "model": "mock-" + args.kind, "target": "mock",
             "nsp_count": 0, "soc": "MOCK", "sdk": "0.2.2-mock", "max_context": 4096}
    print(json.dumps(ready), flush=True)
    for count, line in enumerate(sys.stdin, 1):
        try:
            req = json.loads(line)
            if args.fail_every and count % args.fail_every == 0:
                sys.exit(1)
            time.sleep(max(0, args.delay))
            if args.kind == "vlm" and "Respond with ONLY this JSON" not in req.get("system", ""):
                asked = req.get("prompt", "").rsplit("User:", 1)[-1].replace("Assistant:", "").strip()
                out = {"id": req.get("id"), "status": "Ok", "finish": "Stop",
                       "text": f"(mock) You asked: {asked} The sign says to descend before 14:00 "
                               "and that there is no phone signal on the route.",
                       "usage": {"prompt_rows": 900, "completion_tokens": 40},
                       "timings": {"ttft_ms": 190, "tokens_per_second": 57.0}}
            elif args.kind == "vlm":
                out = {"id": req.get("id"), "status": "Ok", "text": "```json\n" + json.dumps(VLM) + "\n```",
                       "finish": "Stop", "usage": {"prompt_rows": 700, "cached_rows": 420,
                                                   "completion_tokens": 260},
                       "timings": {"ttft_ms": 205, "tokens_per_second": 57.2,
                                   "encode_ms": 18, "prefill_ms": 30, "decode_ms": 4545}}
            else:
                answers = {
                    "category": {"choice": "safety warning", "confidence": .88,
                                 "labels": ["safety warning", "general information"],
                                 "probabilities": [.88, .12]},
                    "severity": {"score": 4, "legend": SEVERITY[4], "confidence": .61,
                                 "probabilities": [.01, .04, .12, .22, .61]},
                    "action": {"noul": .96}, "personal": {"noul": .74},
                }
                for i in range(1, 25):
                    answers[f"line_{i}"] = {"noul": IMPORTANCE[(i - 1) % len(IMPORTANCE)]}
                names = list(req.get("questions", {}))
                answers = {k: answers.get(k, {"noul": .2}) for k in names}
                if args.shape == "list":
                    converted = []
                    for k, v in answers.items():
                        if k == "category":
                            v = {"value": v["choice"], "confidence": v["confidence"]}
                        elif k == "severity":
                            v = {"index": v["score"], "confidence": v["confidence"],
                                 "probabilities": v["probabilities"]}
                        else:
                            v = {"probability": v["noul"]}
                        converted.append([k, v])
                    answers = converted
                out = {"id": req.get("id"), "status": "Ok", "answers": answers, "passes": 2,
                       "timings": {"total_ms": 210}}
            print(json.dumps(out, ensure_ascii=False), flush=True)
        except (ValueError, KeyError) as exc:
            print(json.dumps({"id": None, "status": "InvalidArgument", "error": str(exc)}), flush=True)


if __name__ == "__main__":
    main()

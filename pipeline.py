"""Model boundary for rosetta. Isaac's runtime work can replace this module."""
import json
import os
import queue
import re
import shlex
import subprocess
import threading
import time

IXIAN_SDK = os.environ.get("IXIAN_SDK", "./sdk")
VL_MODEL = os.environ.get("VL_MODEL", "models/lfm3-vl-2b")
D1_MODEL = os.environ.get("D1_MODEL", "models/d1-2b")
VLM_MODE = os.environ.get("VLM_MODE", "engine")
DECIDER = os.environ.get("DECIDER", "zetic")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "768"))
MAX_LINES = int(os.environ.get("MAX_LINES", "24"))
THINK = os.environ.get("THINK", "0") == "1"
ALERT_SEVERITY = int(os.environ.get("ALERT_SEVERITY", "3"))
IMPORTANCE_THRESHOLD = float(os.environ.get("IMPORTANCE_THRESHOLD", "0.5"))
ENGINE_LOAD_TIMEOUT = float(os.environ.get("ENGINE_LOAD_TIMEOUT", "120"))

SYSTEM_PROMPT = """You are an offline translator running entirely on a small device with no internet connection.
A traveler who cannot read the local language shows you a photo of a sign, notice, menu, label, ticket, form or screen.
Rules:
1. Read ALL text in the image, top to bottom, and translate it into clear, natural English, one entry per line or item.
2. Keep every number, price, time, date, distance and unit exactly as written. Convert unfamiliar digits (Thai, Arabic-Indic, etc.) to 0-9.
3. If any text is in a script or language you cannot read confidently, DO NOT guess or invent a translation. Describe it in "unreadable" (e.g. "Top line: Tibetan script, cannot read").
4. If the traveler asked a question, answer it in "answer" using only what the text says; otherwise "".
5. Respond with ONLY this JSON object, no markdown:
{"languages": ["..."], "summary": "one short sentence saying what this is", "lines": ["English line 1", "English line 2", "..."], "unreadable": ["..."], "answer": ""}"""
CATEGORIES = [
    ("safety warning", "danger, hazard, health or safety risk"),
    ("rule or prohibition", "something forbidden or required, permits, fines, towing, legal"),
    ("transport or directions", "routes, closures, schedules, platforms, roads, detours"),
    ("medicine or health", "dosage, drug use, symptoms, medical instructions"),
    ("prices or fees", "costs, charges, tickets, payment"),
    ("food or menu", "dishes, ingredients, allergens, food labels"),
    ("opening hours or schedule", "times, dates, opening or closing"),
    ("general information", "welcome, descriptions, advertising, anything else"),
]
SEVERITY = ["Just information", "Good to know", "Caution: affects your plans, time or money",
            "Warning: legal trouble or health risk if ignored", "Danger: risk of serious injury or death"]


class Engine:
    """One model per process; JSON Lines over pipes; restart after exit or timeout."""
    def __init__(self, name, cmd, timeout):
        self.name, self.cmd, self.timeout = name, cmd, timeout
        self.proc, self.q, self.ready, self.n, self.lock = None, None, None, 0, threading.Lock()

    def _start(self):
        env = dict(os.environ, LD_LIBRARY_PATH=f"{IXIAN_SDK}/lib:" + os.environ.get("LD_LIBRARY_PATH", ""))
        self.proc = subprocess.Popen(shlex.split(self.cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=None, text=True, bufsize=1, env=env)
        self.q = queue.Queue()
        threading.Thread(target=self._pump, args=(self.proc, self.q), daemon=True).start()
        try:
            self.ready = self._next(ENGINE_LOAD_TIMEOUT)
            if self.ready.get("event") != "ready": raise RuntimeError(f"{self.name} did not report ready")
        except Exception:
            if self.proc.poll() is None: self.proc.kill()
            self.proc = None
            raise
        print(f"[{self.name}] ready: {self.ready}", flush=True)

    @staticmethod
    def _pump(proc, q):
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("{"):
                try: q.put(json.loads(line))
                except json.JSONDecodeError: pass
        q.put(None)

    def _next(self, timeout):
        msg = self.q.get(timeout=timeout)
        if msg is None: raise RuntimeError(f"{self.name} engine exited")
        return msg

    def ensure(self):
        with self.lock:
            if self.proc is None or self.proc.poll() is not None: self._start()

    def call(self, req):
        with self.lock:
            try:
                if self.proc is None or self.proc.poll() is not None: self._start()
                self.n += 1
                req = dict(req, id=self.n)
                self.proc.stdin.write(json.dumps(req) + "\n"); self.proc.stdin.flush()
                while True:
                    msg = self._next(self.timeout)
                    if msg.get("id") == req["id"]: return msg
            except Exception:
                if self.proc and self.proc.poll() is None: self.proc.kill()
                self.proc = None
                raise

    def peak_rss_mb(self):
        try:
            with open(f"/proc/{self.proc.pid}/status") as f:
                for line in f:
                    if line.startswith("VmHWM:"): return round(int(line.split()[1]) / 1024)
        except Exception: return None


VLM = Engine("vlm", os.environ.get("VLM_CMD", f'engine/build/rosetta_vlm {VL_MODEL} "" 4096'),
             float(os.environ.get("VLM_TIMEOUT", "60"))) if VLM_MODE != "cli" else None
D1 = Engine("d1", os.environ.get("D1_CMD", f"{IXIAN_SDK}/bin/zetic_d1_cli serve --model {D1_MODEL}"),
            float(os.environ.get("D1_TIMEOUT", "20"))) if DECIDER != "none" else None


def warm_engines():
    for engine in (VLM, D1):
        if engine:
            try: engine.ensure()
            except Exception as exc: print(f"[{engine.name}] warm failed: {exc}", flush=True)


def status():
    engines = {}
    for name, engine in (("vlm", VLM), ("d1", D1)):
        engines[name] = dict(engine.ready or {}, alive=bool(engine.proc and engine.proc.poll() is None),
                             peak_rss_mb=engine.peak_rss_mb()) if engine else {"alive": False}
    return {"vlm_mode": VLM_MODE, "decider": DECIDER, "severity_levels": SEVERITY,
            "importance_threshold": IMPORTANCE_THRESHOLD, "engines": engines}


def parse_model_json(text):
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    cleaned = re.sub(r"^.*?</think>", "", cleaned, flags=re.S | re.I)
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
    if fence: cleaned = fence.group(1)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            out = json.loads(cleaned[start:end+1])
            if isinstance(out, dict): return out
        except json.JSONDecodeError: pass
    return {"lines": [line for line in cleaned.strip().splitlines() if line.strip()], "parse_error": True}


def read_and_translate(png_path, about, question):
    parts = []
    if about: parts.append("About the traveler: " + about)
    if question: parts.append("Traveler's question: " + question)
    parts.append("Read and translate all text in this image. Respond with the JSON object only.")
    prompt = "\n".join(parts)
    started = time.monotonic()
    for attempt in range(2):
        if VLM_MODE == "cli":
            from tools import zetic_run
            resp = zetic_run.run(IXIAN_SDK, VL_MODEL, SYSTEM_PROMPT + "\n\n" + prompt,
                                 image=png_path, max_tokens=MAX_TOKENS, timeout=VLM.timeout if VLM else 60)
            ok = resp.get("ok")
            text = resp.get("text", "")
            tokens = resp.get("completion_tokens", 0)
            finish = resp.get("finish_reason")
            timings = resp.get("timings", {})
            ttft, tok_s = timings.get("runtime_ttft_ms"), timings.get("runtime_decode_tok_s")
        else:
            resp = VLM.call({"system": SYSTEM_PROMPT, "prompt": prompt, "images": [png_path],
                             "max_tokens": MAX_TOKENS, "temperature": 0, "think": THINK})
            ok = resp.get("status") == "Ok"
            text = resp.get("text", "")
            tokens = (resp.get("usage") or {}).get("completion_tokens", 0)
            finish = resp.get("finish")
            timings = resp.get("timings") or {}
            ttft, tok_s = timings.get("ttft_ms"), timings.get("tokens_per_second")
        if ok and tokens and text.strip() and not re.fullmatch(r"\s*<think>.*?</think>\s*", text, re.S): break
        if attempt: raise RuntimeError(f"vlm invalid response: {resp.get('error') or resp.get('status') or 'empty text'}")
    out = parse_model_json(text)
    lines = out.get("lines", [])
    if isinstance(lines, str): lines = lines.splitlines()
    out["lines"] = [str(line).strip() for line in lines if str(line).strip()][:MAX_LINES]
    for key in ("languages", "unreadable"):
        if not isinstance(out.get(key), list): out[key] = []
    out.setdefault("summary", "")
    out.setdefault("answer", "")
    out["truncated"] = finish != "Stop"
    out["_vlm"] = {"mode": VLM_MODE, "seconds": round(time.monotonic()-started, 3), "raw": text,
                   "completion_tokens": tokens, "ttft_ms": ttft, "tok_s": tok_s, "finish": finish}
    return out


def build_questions(lines, about):
    who = f" The traveler says: {about.strip()}." if about.strip() else ""
    qs = {
        "category": {"type": "choice", "instructions": "What is this text mainly about, from a traveler's point of view?",
                     "criteria": {v: d for v, d in CATEGORIES}},
        "severity": {"type": "score", "instructions": "How serious are the consequences for a traveler who ignores or misunderstands this text?" + who, "criteria": SEVERITY},
        "action": {"type": "noul", "instructions": "Does this text require the reader to do something, or forbid them from doing something?"},
    }
    if about.strip(): qs["personal"] = {"type": "noul", "instructions": f"Does anything in this text specifically affect this traveler?{who}"}
    for i, line in enumerate(lines[:MAX_LINES], 1):
        qs[f"line_{i}"] = {"type": "noul", "instructions": (f'Line {i}: "{line[:160]}". Must the traveler notice or act on this line: '
                           f"a danger, prohibition, requirement, deadline, closure, fee, dosage limit, health risk, or something that affects them personally?{who}")}
    return qs


def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def _normalize_answer(qtype, a):
    if a is None: return None
    if not isinstance(a, dict): a = {"value": a}
    probs, labels = a.get("probabilities", a.get("probs")), a.get("labels")
    if isinstance(probs, list) and isinstance(labels, list) and len(probs) == len(labels): probs = dict(zip(labels, probs))
    if qtype == "noul":
        for k in ("noul", "p", "probability", "yes"):
            v = _num(a.get(k))
            if v is not None: return {"p": v}
        if isinstance(probs, dict):
            for k in ("yes", "true", "Yes", "True"):
                if k in probs: return {"p": _num(probs[k])}
        return None
    if qtype == "choice":
        v = a.get("choice", a.get("value", a.get("label")))
        if v is None and isinstance(probs, dict) and probs: v = max(probs, key=lambda k: _num(probs[k]) or 0)
        return {"value": v, "confidence": _num(a.get("confidence")), "probabilities": probs}
    if qtype == "score":
        idx = next((_num(a.get(k)) for k in ("score", "index", "value") if _num(a.get(k)) is not None), None)
        if idx is None and a.get("legend") in SEVERITY: idx = SEVERITY.index(a["legend"])
        if idx is None: return None
        i = max(0, min(len(SEVERITY)-1, int(round(idx))))
        return {"index": i, "label": SEVERITY[i], "confidence": _num(a.get("confidence")), "probabilities": a.get("probabilities", a.get("probs"))}
    return a


def decide(lines, about):
    if DECIDER == "none" or not lines: return None
    qs = build_questions(lines, about)
    started = time.monotonic()
    resp = D1.call({"state": "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1)), "questions": qs})
    if resp.get("error") or resp.get("status") not in (None, "Ok", "ok"):
        raise RuntimeError(resp.get("error") or resp.get("status"))
    answers = resp.get("answers", {})
    if isinstance(answers, list):
        if all(isinstance(item, list) and len(item) == 2 for item in answers): answers = dict(answers)
        elif all(isinstance(item, dict) and "name" in item for item in answers): answers = {item["name"]: item for item in answers}
        else: answers = dict(zip(qs, answers))
    norm = {name: _normalize_answer(q["type"], answers.get(name)) for name, q in qs.items()}
    return {"category": norm.get("category"), "severity": norm.get("severity"),
            "action_p": (norm.get("action") or {}).get("p"), "personal_p": (norm.get("personal") or {}).get("p"),
            "importance": [(norm.get(f"line_{i}") or {}).get("p") for i in range(1, len(lines)+1)],
            "passes": resp.get("passes"), "seconds": round(time.monotonic()-started, 3),
            "backend": "zetic-d1", "raw": resp}


def gate(d):
    if not d or d.get("error"): return {"alert": False, "reason": "no decision"}
    sev = (d.get("severity") or {}).get("index", -1)
    top = max([p for p in d.get("importance", []) if p is not None], default=0)
    if sev >= ALERT_SEVERITY: return {"alert": True, "reason": f"severity {sev} >= {ALERT_SEVERITY}"}
    if top >= IMPORTANCE_THRESHOLD and (d.get("action_p") or 0) >= 0.5:
        return {"alert": True, "reason": f"line importance {top:.2f} >= {IMPORTANCE_THRESHOLD}"}
    return {"alert": False, "reason": f"severity {sev}, top line {top:.2f}"}

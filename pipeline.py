"""rosetta model pipeline (Isaac-owned; plan §0, §9.2–9.4, §16 D16/D23).

Interface used by app.py (Rehan's HTTP/camera/log shell):
  warm_engines() · status() · read_and_translate(png, about, question) · decide(lines, about) · gate(decision)
Extras: analyze() one-call wrapper, vlm_log()/d1_log()/scan_errors() log helpers, EngineError (.engine).
"""
import json
import os
import queue
import re
import shlex
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))

# =====================================================================================
# [Isaac] Config (plan §10.6)
# =====================================================================================
def _env(name, default):
    v = os.environ.get(name)
    return default if v is None or v == "" else v

IXIAN_SDK = _env("IXIAN_SDK", os.path.join(ROOT, "sdk"))
VL_MODEL = _env("VL_MODEL", "models/lfm3-vl-2b")
D1_MODEL = _env("D1_MODEL", "models/d1-2b")
VLM_MODE = _env("VLM_MODE", "engine")                       # engine | cli | mock
VLM_CMD = _env("VLM_CMD", "python3 tools/mock_engine.py vlm" if VLM_MODE == "mock"
               else f'engine/build/rosetta_vlm {shlex.quote(VL_MODEL)} "" 4096')
D1_CMD = _env("D1_CMD", f"{shlex.quote(IXIAN_SDK + '/bin/zetic_d1_cli')} serve --model {shlex.quote(D1_MODEL)}")
DECIDER = _env("DECIDER", "zetic")                          # zetic | none
MAX_TOKENS = int(_env("MAX_TOKENS", "768"))
MAX_LINES = int(_env("MAX_LINES", "24"))
THINK = _env("THINK", "0") not in ("0", "false", "False", "no")
ALERT_SEVERITY = int(_env("ALERT_SEVERITY", "3"))
IMPORTANCE_THRESHOLD = float(_env("IMPORTANCE_THRESHOLD", "0.5"))   # placeholder until calibrated (§9.11)
VLM_TIMEOUT = float(_env("VLM_TIMEOUT", "60"))
D1_TIMEOUT = float(_env("D1_TIMEOUT", "20"))
ENGINE_LOAD_TIMEOUT = float(_env("ENGINE_LOAD_TIMEOUT", "120"))

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


# =====================================================================================
# [Isaac] Engine supervisor (plan §9.2, reference)
# =====================================================================================
class EngineError(RuntimeError):
    """A model engine is down, timed out, or returned an invalid answer. HTTP layer: 502 + engine name."""
    def __init__(self, engine, msg):
        super().__init__(f"{engine}: {msg}")
        self.engine = engine


class Engine:
    """One ZETIC model per process (SDK limit). JSON Lines over stdin/stdout. Restarts on exit or timeout."""
    def __init__(self, name, cmd, timeout):
        self.name, self.cmd, self.timeout = name, cmd, timeout
        self.proc, self.q, self.ready, self.n, self.lock = None, None, None, 0, threading.Lock()
        self.last_error = None

    def _start(self):
        # DSP may still be releasing after another NPU process exited (DeviceError ... map: 0x1):
        # wait 3 s and retry the load once (plan §9.2).
        for attempt in (1, 2):
            try:
                return self._start_once()
            except Exception as e:
                self.last_error = f"load failed: {e!r}"
                print(f"[{self.name}] {self.last_error}" + ("; retrying in 3 s" if attempt == 1 else ""), flush=True)
                if self.proc and self.proc.poll() is None:
                    self.proc.kill()
                self.proc = None
                if attempt == 2:
                    raise
                time.sleep(3)

    def _start_once(self):
        env = dict(os.environ, LD_LIBRARY_PATH=f"{IXIAN_SDK}/lib:" + os.environ.get("LD_LIBRARY_PATH", ""))
        self.proc = subprocess.Popen(shlex.split(self.cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=None, text=True, bufsize=1, env=env, cwd=ROOT)   # stderr → app console
        self.q = queue.Queue()
        threading.Thread(target=self._pump, args=(self.proc, self.q), daemon=True).start()
        try:
            self.ready = self._next(ENGINE_LOAD_TIMEOUT)          # first line: {"event": "ready", ...}
        except queue.Empty:
            raise RuntimeError(f"{self.name} engine: no ready line within {ENGINE_LOAD_TIMEOUT:.0f} s")
        self.last_error = None
        print(f"[{self.name}] ready: {self.ready}", flush=True)

    @staticmethod
    def _pump(proc, q):
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("{"):                          # skip any non-JSON chatter on stdout
                try: q.put(json.loads(line))
                except json.JSONDecodeError: pass
        q.put(None)                                           # EOF: process exited

    def _next(self, timeout):
        msg = self.q.get(timeout=timeout)                     # raises queue.Empty on timeout
        if msg is None:
            raise RuntimeError(f"{self.name} engine exited")
        return msg

    def ensure(self):
        with self.lock:
            if self.proc is None or self.proc.poll() is not None:
                self._start()

    def call(self, req):
        with self.lock:
            try:
                if self.proc is None or self.proc.poll() is not None:
                    self._start()
                self.n += 1
                req = dict(req, id=self.n)
                self.proc.stdin.write(json.dumps(req) + "\n"); self.proc.stdin.flush()
                while True:
                    msg = self._next(self.timeout)
                    if msg.get("id") == req["id"]:
                        return msg
            except Exception as e:
                self.last_error = "timeout" if isinstance(e, queue.Empty) else repr(e)
                if self.proc and self.proc.poll() is None:
                    self.proc.kill()                          # next call restarts cleanly
                self.proc = None
                raise

    def peak_rss_mb(self):
        try:
            with open(f"/proc/{self.proc.pid}/status") as f:
                for l in f:
                    if l.startswith("VmHWM:"): return round(int(l.split()[1]) / 1024)
        except Exception: return None

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def status(self):
        """For GET /status engines.<name> (§10.2): ready event + peak_rss_mb + alive."""
        return dict(self.ready or {}, peak_rss_mb=self.peak_rss_mb() if self.alive() else None,
                    alive=self.alive(), cmd=self.cmd, last_error=self.last_error)


VLM = Engine("vlm", VLM_CMD, VLM_TIMEOUT) if VLM_MODE in ("engine", "mock") else None
D1 = Engine("d1", D1_CMD, D1_TIMEOUT) if DECIDER != "none" else None
PIPELINE_LOCK = threading.Lock()          # models run sequentially; never two scans on the NPU at once


def warm_engines():
    """Start both engines sequentially (VLM first, then d1) so the first scan is warm.
    Blocking; app.py runs it in a background thread at startup."""
    for eng in (VLM, D1):
        if eng is None:
            continue
        try:
            eng.ensure()
        except Exception as e:
            print(f"[{eng.name}] failed to start: {e!r} (will retry on next scan)", flush=True)


def start_engines():
    """Non-blocking variant of warm_engines()."""
    t = threading.Thread(target=warm_engines, name="engine-warmup", daemon=True)
    t.start()
    return t


def engines_status():
    out = {}
    if VLM is not None:
        out["vlm"] = VLM.status()
    elif VLM_MODE == "cli":
        out["vlm"] = {"mode": "cli", "model": VL_MODEL, "alive": True,
                      "note": "zetic_lfm3_cli one-shot per scan (model reload each call)"}
    out["d1"] = D1.status() if D1 is not None else {"alive": False, "disabled": True}
    return out


def status():
    """GET /status body minus server_camera/watch (app.py adds those). §10.2."""
    return {"vlm_mode": VLM_MODE, "decider": DECIDER, "severity_levels": SEVERITY,
            "importance_threshold": IMPORTANCE_THRESHOLD, "engines": engines_status()}


# =====================================================================================
# [Isaac] Step 1: read & translate (plan §9.3, reference)
# =====================================================================================
SYSTEM_PROMPT = """You are an offline translator running entirely on a small device with no internet connection.
A traveler who cannot read the local language shows you a photo of a sign, notice, menu, label, ticket, form or screen.

Rules:
1. Read ALL text in the image, top to bottom, and translate it into clear, natural English, one entry per line or item.
2. Keep every number, price, time, date, distance and unit exactly as written. Convert unfamiliar digits (Thai, Arabic-Indic, etc.) to 0-9.
3. If any text is in a script or language you cannot read confidently, DO NOT guess or invent a translation. Describe it in "unreadable" (e.g. "Top line: Tibetan script, cannot read").
4. If the traveler asked a question, answer it in "answer" using only what the text says; otherwise "".
5. Respond with ONLY this JSON object, no markdown:
{"languages": ["..."], "summary": "one short sentence saying what this is", "lines": ["English line 1", "English line 2", "..."], "unreadable": ["..."], "answer": ""}"""


def parse_model_json(text: str) -> dict:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    cleaned = re.sub(r"^.*?</think>", "", cleaned, flags=re.S | re.I)   # think block with no opening tag
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
    if fence:
        cleaned = fence.group(1)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            out = json.loads(cleaned[start:end + 1])
            if isinstance(out, dict):
                return out
        except json.JSONDecodeError:
            pass
    return {"lines": [l for l in cleaned.strip().splitlines() if l.strip()], "parse_error": True}


def build_prompt(about, question):
    user_text = []
    if about:    user_text.append("About the traveler: " + about)
    if question: user_text.append("Traveler's question: " + question)
    user_text.append("Read and translate all text in this image. Respond with the JSON object only.")
    return "\n".join(user_text)


def _str_list(x):
    if x is None:
        return []
    if isinstance(x, str):
        x = x.splitlines()
    if not isinstance(x, (list, tuple)):
        x = [x]
    out = []
    for item in x:
        if isinstance(item, (dict, list)):
            item = json.dumps(item, ensure_ascii=False)
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def _vlm_engine(prompt, png_path):
    """VLM_MODE=engine|mock → resident engine (§10.4). Returns the internal response shape."""
    r = VLM.call({"system": SYSTEM_PROMPT, "prompt": prompt, "images": [os.path.abspath(png_path)],
                  "max_tokens": MAX_TOKENS, "temperature": 0, "think": THINK})
    usage, tm = r.get("usage") or {}, r.get("timings") or {}
    return {"status": r.get("status", "Ok"), "error": r.get("error"), "text": r.get("text") or "",
            "reasoning": r.get("reasoning") or "", "finish": r.get("finish"),
            "completion_tokens": usage.get("completion_tokens"),
            "ttft_ms": tm.get("ttft_ms"), "tok_s": tm.get("tokens_per_second"),
            "prompt_rows": usage.get("prompt_rows"), "device_evidence": None, "model_load_ms": None}


def _vlm_cli(prompt, png_path):
    """VLM_MODE=cli → vendored tools/zetic_run.py one-shot (P0, no compile; reloads the model per call)."""
    if os.path.join(ROOT, "tools") not in sys.path:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
    import zetic_run                                          # vendored from the starter repo (MIT)
    r = zetic_run.run(IXIAN_SDK, VL_MODEL, SYSTEM_PROMPT + "\n\n" + prompt, image=os.path.abspath(png_path),
                      max_tokens=MAX_TOKENS, timeout=VLM_TIMEOUT)
    tm = r.get("timings") or {}
    errs = [str(e) for e in (r.get("errors") or [])]
    # zetic_run sets ok=False on a length finish or a missing NSP evidence line: those are warnings for us
    # (parse + mark truncated / log it), not reasons to fail the scan.
    soft = ("generation did not finish naturally", "missing current-request Hexagon")
    fatal = [e for e in errs if not e.startswith(soft)]
    finish = (r.get("finish_reason") or "").capitalize() or None          # cli reports "stop"/"length"
    return {"status": "Ok" if not fatal and (r.get("text") or "").strip() else "Error",
            "error": "; ".join(fatal or errs) or None, "warnings": [e for e in errs if e.startswith(soft)],
            "text": r.get("text") or "", "reasoning": "", "finish": finish,
            "completion_tokens": r.get("completion_tokens"),
            "ttft_ms": tm.get("runtime_ttft_ms"), "tok_s": tm.get("runtime_decode_tok_s"),
            "prompt_rows": None, "device_evidence": r.get("device_evidence"),
            "model_load_ms": tm.get("model_load_ms")}


def _vlm_once(prompt, png_path):
    if VLM_MODE == "cli":
        return _vlm_cli(prompt, png_path)
    if VLM is None:
        raise EngineError("vlm", f"unknown VLM_MODE={VLM_MODE!r}")
    return _vlm_engine(prompt, png_path)


def _validate(r):
    """§12 rule 2: reject status != Ok, zero tokens, empty or reasoning-only text. Returns error str or None."""
    if str(r.get("status", "")).lower() != "ok":
        return f"status {r.get('status')}: {r.get('error') or 'no detail'}"
    if not (r.get("text") or "").strip():
        return "reasoning-only output (no answer text)" if (r.get("reasoning") or "").strip() else "empty text"
    ct = r.get("completion_tokens")
    if ct is not None and ct <= 0:
        return "zero completion tokens"
    return None


def read_and_translate(png_path, about="", question=""):
    """512x512 PNG → {languages, summary, lines, unreadable, answer, parse_error, truncated, _vlm}.
    Raises EngineError (→ HTTP 502) if the VLM is down or returns nothing usable after one retry."""
    about, question = (about or "").strip(), (question or "").strip()
    prompt = build_prompt(about, question)
    t0, errors, r = time.time(), [], None
    for attempt in (1, 2):                                    # retry at most once
        try:
            r = _vlm_once(prompt, png_path)
        except EngineError:
            raise
        except Exception as e:
            errors.append(f"vlm attempt {attempt}: {'timeout' if isinstance(e, queue.Empty) else repr(e)}")
            r = None
            continue
        err = _validate(r)
        if err is None:
            break
        errors.append(f"vlm attempt {attempt}: {err}")
        r = None
    if r is None:
        raise EngineError("vlm", errors[-1] if errors else "no response")

    errors.extend(f"vlm: {w}" for w in r.get("warnings") or [])
    parsed = parse_model_json(r["text"])
    truncated = (r.get("finish") or "Stop") != "Stop"
    if truncated:
        errors.append(f"vlm finish={r.get('finish')} (hit max_tokens={MAX_TOKENS}?)")
    lines = _str_list(parsed.get("lines"))[:MAX_LINES]
    out = {
        "languages": _str_list(parsed.get("languages")),
        "summary": str(parsed.get("summary") or "").strip(),
        "lines": lines,
        "unreadable": _str_list(parsed.get("unreadable")),
        "answer": str(parsed.get("answer") or "").strip(),
        "parse_error": bool(parsed.get("parse_error")),
        "truncated": truncated,
    }
    if out["parse_error"]:
        errors.append("vlm output was not clean JSON; showing raw lines")
    out["_vlm"] = {
        "mode": VLM_MODE, "seconds": round(time.time() - t0, 3),
        "ttft_ms": r.get("ttft_ms"), "tok_s": r.get("tok_s"), "completion_tokens": r.get("completion_tokens"),
        "finish": r.get("finish"), "model_load_ms": r.get("model_load_ms"),
        "device_evidence": r.get("device_evidence"), "raw": r["text"], "errors": errors,
    }
    return out


# =====================================================================================
# [Isaac] Step 2: decide what matters (plan §9.4, reference)
# =====================================================================================
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
SEVERITY = [
    "Just information",
    "Good to know",
    "Caution: affects your plans, time or money",
    "Warning: legal trouble or health risk if ignored",
    "Danger: risk of serious injury or death",
]


def build_questions(lines, about):
    """d1 native schema: {name: {type: noul|choice|score, instructions, criteria}}. Order = pass order."""
    who = f" The traveler says: {about.strip()}." if about.strip() else ""
    qs = {
        "category": {"type": "choice",
                     "instructions": "What is this text mainly about, from a traveler's point of view?",
                     "criteria": {v: d for v, d in CATEGORIES}},
        "severity": {"type": "score",
                     "instructions": "How serious are the consequences for a traveler who ignores or misunderstands this text?" + who,
                     "criteria": SEVERITY},
        "action":   {"type": "noul",
                     "instructions": "Does this text require the reader to do something, or forbid them from doing something?"},
    }
    if about.strip():
        qs["personal"] = {"type": "noul",
                          "instructions": f"Does anything in this text specifically affect this traveler?{who}"}
    for i, line in enumerate(lines[:MAX_LINES], 1):
        qs[f"line_{i}"] = {"type": "noul",
                           "instructions": (f'Line {i}: "{line[:160]}". Must the traveler notice or act on this line: '
                                            f"a danger, prohibition, requirement, deadline, closure, fee, dosage limit, "
                                            f"health risk, or something that affects them personally?{who}")}
    return qs


def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


def _normalize_answer(qtype, a):
    """Tolerant of zetic_d1_cli serve, rosetta_d1 and HF shapes: noul/choice/score/legend/labels/probabilities/probs."""
    if a is None: return None
    if not isinstance(a, dict): a = {"value": a}
    probs, labels = a.get("probabilities", a.get("probs")), a.get("labels")
    if isinstance(probs, list) and isinstance(labels, list) and len(probs) == len(labels):
        probs = dict(zip(labels, probs))
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
        if v is None and isinstance(probs, dict) and probs:
            v = max(probs, key=lambda k: _num(probs[k]) or 0)
        return {"value": v, "confidence": _num(a.get("confidence")), "probabilities": probs}
    if qtype == "score":
        idx = next((_num(a.get(k)) for k in ("score", "index", "value") if _num(a.get(k)) is not None), None)
        if idx is None and a.get("legend") in SEVERITY:
            idx = SEVERITY.index(a["legend"])
        if idx is None: return None
        i = max(0, min(len(SEVERITY) - 1, int(round(idx))))
        p = a.get("probabilities", a.get("probs"))
        if isinstance(probs, dict) and all(s in probs for s in SEVERITY):   # serve may emit {label: p}; UI wants a list
            p = [_num(probs[s]) for s in SEVERITY]
        return {"index": i, "label": SEVERITY[i], "confidence": _num(a.get("confidence")), "probabilities": p}
    return a


def _answers_to_dict(answers, qs):
    """d1 answers may be a dict, a list of [name, ans] pairs, dicts with "name", or bare answers in request order."""
    if isinstance(answers, dict):
        return answers
    if not isinstance(answers, list):
        return {}
    out, names = {}, list(qs)
    for i, item in enumerate(answers):
        if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[0], str):
            out[item[0]] = item[1]
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            out[item["name"]] = item.get("answer", item)
        elif i < len(names):
            out[names[i]] = item
    return out


def decide(lines, about=""):
    """One d1 call over the English lines → calibrated category/severity/action/personal/per-line importance.
    Returns None if DECIDER=none or no lines. Raises on engine failure (caller turns it into {"error": ...})."""
    about = (about or "").strip()
    if DECIDER == "none" or D1 is None or not lines:
        return None
    lines = lines[:MAX_LINES]
    state = "\n".join(f"{i}. {l}" for i, l in enumerate(lines, 1))
    qs = build_questions(lines, about)
    t0 = time.time()
    for attempt in (1, 2):                                    # engine crash/timeout → restart + retry once
        try:
            resp = D1.call({"state": state, "questions": qs})
            break
        except queue.Empty:
            err = f"timeout after {D1_TIMEOUT:.0f} s"
        except Exception as e:
            err = repr(e)
        print(f"[d1] attempt {attempt} failed: {err}", flush=True)
        if attempt == 2:
            raise EngineError("d1", err)
    seconds = round(time.time() - t0, 3)
    if resp.get("error") or str(resp.get("status", "Ok")).lower() not in ("ok",):
        raise EngineError("d1", f"status {resp.get('status')}: {resp.get('error')}")
    answers = _answers_to_dict(resp.get("answers", {}), qs)
    norm = {n: _normalize_answer(q["type"], answers.get(n)) for n, q in qs.items()}
    tm = resp.get("timings") or {}
    return {
        "category": norm.get("category"),
        "severity": norm.get("severity"),
        "action_p": (norm.get("action") or {}).get("p"),
        "personal_p": (norm.get("personal") or {}).get("p"),
        "importance": [(norm.get(f"line_{i}") or {}).get("p") for i in range(1, len(lines) + 1)],
        "passes": resp.get("passes"),
        "seconds": seconds,
        "d1_ms": tm.get("d1_ms", tm.get("prefill_ms")),
        "backend": "zetic-d1",
        "raw": resp,
    }


def gate(d):
    """Code (not the model) authorizes the alert action (§12 rule 4)."""
    if not d or d.get("error"): return {"alert": False, "reason": "no decision"}
    sev = (d.get("severity") or {}).get("index", -1)
    top = max([p for p in d.get("importance", []) if p is not None], default=0)
    if sev >= ALERT_SEVERITY: return {"alert": True, "reason": f"severity {sev} >= {ALERT_SEVERITY}"}
    if top >= IMPORTANCE_THRESHOLD and (d.get("action_p") or 0) >= 0.5:
        return {"alert": True, "reason": f"line importance {top:.2f} >= {IMPORTANCE_THRESHOLD}"}
    return {"alert": False, "reason": f"severity {sev}, top line {top:.2f}"}


def analyze(png_path, about="", question=""):
    """Full model pipeline for one 512x512 PNG: step 1 → step 2 (fail soft) → gate. Sequential on the NPU.
    Returns the /scan body (§10.1) minus scan_id/_image/log, which the HTTP layer adds.
    Raises EngineError only if the VLM fails (→ 502); d1 failures become decision={"error": ...}."""
    with PIPELINE_LOCK:
        t0 = time.time()
        res = read_and_translate(png_path, about, question)
        try:
            res["decision"] = decide(res["lines"], about)
        except Exception as e:
            res["decision"] = {"error": str(e)}
        res["gate"] = gate(res["decision"])
        res["_metrics"] = {"total_s": round(time.time() - t0, 3),
                           "vlm_s": res["_vlm"]["seconds"],
                           "d1_s": (res["decision"] or {}).get("seconds")}
        return res


def vlm_log(res):
    """`vlm` field of the JSONL record (§9.2)."""
    v = res.get("_vlm") or {}
    return {"ok": True, "mode": v.get("mode"), "seconds": v.get("seconds"), "ttft_ms": v.get("ttft_ms"),
            "tok_s": v.get("tok_s"), "completion_tokens": v.get("completion_tokens"), "finish": v.get("finish"),
            "lines": len(res.get("lines") or []), "unreadable": len(res.get("unreadable") or []),
            "parse_error": bool(res.get("parse_error"))}


def d1_log(d):
    """`d1` field of the JSONL record (§9.2). Includes the full per-line `importance` list for tools/calibrate.py."""
    if d is None:
        return {"ok": False, "skipped": True}
    if d.get("error"):
        return {"ok": False, "error": d["error"]}
    imp = d.get("importance") or []
    top = sorted(((i, p) for i, p in enumerate(imp, 1) if p is not None), key=lambda t: -t[1])[:3]
    return {"ok": True, "seconds": d.get("seconds"), "passes": d.get("passes"),
            "category": (d.get("category") or {}).get("value"), "severity": (d.get("severity") or {}).get("index"),
            "action_p": d.get("action_p"), "personal_p": d.get("personal_p"),
            "top": [[i, round(p, 3)] for i, p in top], "importance": imp,
            "importance_threshold": IMPORTANCE_THRESHOLD}


def scan_errors(res):
    """Errors list for the JSONL record: VLM warnings + d1 error."""
    errs = list((res.get("_vlm") or {}).get("errors") or [])
    d = res.get("decision")
    if isinstance(d, dict) and d.get("error"):
        errs.append(f"d1: {d['error']}")
    return errs

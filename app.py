"""rosetta local HTTP, camera and scan shell. Model functions live in pipeline.py."""
import base64
import datetime as dt
import json
import os
from pathlib import Path
import threading
import time
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None

import pipeline

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "logs" / "rosetta.jsonl"
IMAGE_DIR = ROOT / "logs" / "img"
SHM_DIR = Path(os.environ.get("SHM_DIR", "/dev/shm/rosetta" if os.name == "posix" else str(Path(tempfile.gettempdir()) / "rosetta")))
CROP = os.environ.get("CROP", "center")
CAMERA = os.environ.get("CAMERA", "0")
WATCH_CHANGE = float(os.environ.get("WATCH_CHANGE", "12"))
WATCH_STABLE_S = float(os.environ.get("WATCH_STABLE_S", "1.2"))
WATCH_SHARP = float(os.environ.get("WATCH_SHARP", "60"))
MAX_UPLOAD = 12 * 1024 * 1024

state_lock = threading.RLock()
scan_lock = threading.Lock()
log_lock = threading.Lock()
frame = None
camera_ok = False
watch_on = False
latest = {}
scan_id = 0


def to_model_image(img):
    """BGR ndarray -> exactly 512x512 BGR."""
    h, w = img.shape[:2]
    if CROP == "center":
        s = min(h, w); y, x = (h-s)//2, (w-s)//2
        return cv2.resize(img[y:y+s, x:x+s], (512, 512), interpolation=cv2.INTER_AREA)
    scale = 512 / max(h, w)
    img = cv2.resize(img, (max(1, round(w*scale)), max(1, round(h*scale))), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((512, 512, 3), np.uint8)
    y, x = (512-img.shape[0])//2, (512-img.shape[1])//2
    canvas[y:y+img.shape[0], x:x+img.shape[1]] = img
    return canvas


def camera_loop():
    global frame, camera_ok
    source = int(CAMERA) if CAMERA.isdigit() else CAMERA
    while True:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            with state_lock: camera_ok = False
            cap.release(); time.sleep(3); continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        try:
            while True:
                ok, next_frame = cap.read()
                if not ok: break
                with state_lock:
                    frame = next_frame
                    camera_ok = True
        finally:
            cap.release()
            with state_lock: camera_ok = False
        time.sleep(1)


def model_png(image_data):
    if image_data:
        if not isinstance(image_data, str) or not image_data.startswith("data:image/png;base64,"):
            raise ValueError("image must be a PNG data URL")
        raw = base64.b64decode(image_data.partition(",")[2], validate=True)
        if len(raw) > MAX_UPLOAD: raise ValueError("image is too large")
        if len(raw) < 26 or not raw.startswith(b"\x89PNG\r\n\x1a\n"): raise ValueError("invalid PNG")
        if cv2 is not None:
            img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if img is None: raise ValueError("invalid PNG image")
            ok, encoded = cv2.imencode(".png", to_model_image(img))
            if not ok: raise ValueError("could not encode image")
            return bytes(encoded), "upload"
        width, height = int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
        if (width, height) != (512, 512): raise ValueError("without OpenCV, upload a 512×512 PNG")
        if raw[25] not in (2, 6): raise ValueError("upload an RGB or RGBA PNG")
        return raw, "upload"
    with state_lock:
        current = frame.copy() if camera_ok and frame is not None else None
    if current is None: raise LookupError("camera has no frame; upload a photo")
    ok, encoded = cv2.imencode(".png", to_model_image(current))
    if not ok: raise ValueError("could not encode camera frame")
    return bytes(encoded), "webcam"


def _record(result, source, about, question, errors):
    d = result.get("decision") or {}
    v = result.get("_vlm") or {}
    sev = d.get("severity") or {}
    cat = d.get("category") or {}
    ranking = sorted(enumerate(d.get("importance") or [], 1), key=lambda pair: pair[1] if pair[1] is not None else -1, reverse=True)
    return {
        "ts": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="milliseconds"),
        "scan_id": result["scan_id"], "trigger": result["trigger"],
        "input": {"source": source, "image": f"logs/img/{result['scan_id']}.png", "about": about, "question": question},
        "vlm": {"ok": bool(result.get("lines")), "mode": v.get("mode"), "seconds": v.get("seconds"),
                "ttft_ms": v.get("ttft_ms"), "tok_s": v.get("tok_s"), "completion_tokens": v.get("completion_tokens"),
                "finish": v.get("finish"), "lines": len(result.get("lines", [])),
                "unreadable": len(result.get("unreadable", [])), "parse_error": result.get("parse_error", False),
                "proposal": {"languages": result.get("languages", []), "summary": result.get("summary", ""),
                             "lines": result.get("lines", []), "unreadable": result.get("unreadable", []),
                             "answer": result.get("answer", "")}},
        "d1": {"ok": bool(d and not d.get("error")), "seconds": d.get("seconds"), "passes": d.get("passes"),
               "category": cat.get("value"), "severity": sev.get("index"), "action_p": d.get("action_p"),
               "personal_p": d.get("personal_p"), "importance": d.get("importance"),
               "top": [[i, p] for i, p in ranking[:3]]},
        "decision": result.get("gate"),
        "action": {"type": "ui_alert" if result.get("gate", {}).get("alert") else "none",
                   "executed": bool(result.get("gate", {}).get("alert"))}, "errors": errors,
    }


def log_scan(record):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with log_lock, LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def run_scan(payload, trigger="button"):
    global scan_id, latest
    if not scan_lock.acquire(blocking=False): raise RuntimeError("scan already in progress")
    try:
        started = time.monotonic()
        png, source = model_png(payload.get("image"))
        with state_lock:
            scan_id += 1
            current_id = scan_id
        SHM_DIR.mkdir(parents=True, exist_ok=True); IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        path = SHM_DIR / f"scan-{current_id}.png"
        path.write_bytes(png)
        (IMAGE_DIR / f"{current_id}.png").write_bytes(png)
        about = str(payload.get("about") or "")[:500]
        question = str(payload.get("question") or "")[:500]
        errors = []
        result = {"scan_id": current_id, "trigger": trigger, "languages": [], "summary": "", "lines": [],
                  "unreadable": [], "answer": "", "parse_error": False, "truncated": False}
        try:
            result.update(pipeline.read_and_translate(str(path), about, question))
        except Exception as exc:
            errors.append(f"vlm: {exc}")
            result["error"] = f"vlm: {exc}"
        if not result.get("error"):
            try:
                result["decision"] = pipeline.decide(result.get("lines", []), about)
            except Exception as exc:
                errors.append(f"d1: {exc}")
                result["decision"] = {"error": str(exc)}
        else:
            result["decision"] = None
        result["gate"] = pipeline.gate(result.get("decision"))
        result["_metrics"] = {"total_s": round(time.monotonic()-started, 3)}
        result["_image"] = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        log_scan(_record(result, source, about, question, errors))
        with state_lock: latest = result
        return result
    finally:
        scan_lock.release()


def watch_loop():
    previous = scanned = None
    stable_since = None
    last_scan = 0
    while True:
        time.sleep(.25)
        with state_lock:
            active = watch_on and camera_ok and frame is not None
            current = frame.copy() if active else None
        if current is None or cv2 is None:
            previous = None; stable_since = None; continue
        thumb = cv2.resize(cv2.cvtColor(current, cv2.COLOR_BGR2GRAY), (160, 90))
        if previous is not None:
            movement = float(np.mean(cv2.absdiff(thumb, previous)))
            stable_since = time.monotonic() if movement >= 3 else (stable_since or time.monotonic())
        previous = thumb
        change = float(np.mean(cv2.absdiff(thumb, scanned))) if scanned is not None else 255
        sharpness = cv2.Laplacian(thumb, cv2.CV_64F).var()
        if (stable_since and time.monotonic()-stable_since >= WATCH_STABLE_S
                and change > WATCH_CHANGE and sharpness > WATCH_SHARP
                and time.monotonic()-last_scan >= 3 and not scan_lock.locked()):
            try:
                run_scan({}, "watch")
                scanned = thumb
                last_scan = time.monotonic()
            except Exception as exc:
                print(f"[watch] {exc}", flush=True)


class Handler(BaseHTTPRequestHandler):
    def json_response(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        global watch_on
        url = urlsplit(self.path)
        try:
            if url.path == "/":
                data = (ROOT / "index.html").read_bytes()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            elif url.path == "/status":
                with state_lock: camera, watch = camera_ok, watch_on
                self.json_response(200, dict(pipeline.status(), server_camera=camera, watch=watch))
            elif url.path == "/latest":
                after = int(parse_qs(url.query).get("after", [0])[0])
                with state_lock: result = latest if latest.get("scan_id", 0) > after else {}
                self.json_response(200, result)
            elif url.path == "/log":
                n = min(100, max(1, int(parse_qs(url.query).get("n", [20])[0])))
                records = []
                if LOG_FILE.exists():
                    for line in LOG_FILE.read_text(encoding="utf-8").splitlines()[-n:]:
                        try: records.append(json.loads(line))
                        except json.JSONDecodeError: pass
                self.json_response(200, {"records": records})
            elif url.path == "/stream":
                with state_lock: available = camera_ok
                if not available: return self.json_response(404, {"error": "server camera unavailable"})
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store"); self.end_headers()
                while True:
                    with state_lock: current = frame.copy() if camera_ok and frame is not None else None
                    if current is None: break
                    h, w = current.shape[:2]
                    if w > 960: current = cv2.resize(current, (960, round(h*960/w)))
                    h, w = current.shape[:2]; s = min(h, w); x = (w-s)//2; y = (h-s)//2
                    cv2.rectangle(current, (x, y), (x+s, y+s), (76, 217, 153), 2)
                    ok, jpg = cv2.imencode(".jpg", current, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ok:
                        data = bytes(jpg)
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n")
                    time.sleep(1/14)
            else: self.json_response(404, {"error": "not found"})
        except (BrokenPipeError, ConnectionResetError): pass
        except Exception as exc:
            try: self.json_response(500, {"error": str(exc)})
            except (BrokenPipeError, ConnectionResetError): pass

    def do_POST(self):
        global watch_on
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_UPLOAD * 2: return self.json_response(400, {"error": "invalid request size"})
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict): raise ValueError("expected JSON object")
            if self.path == "/scan":
                result = run_scan(payload, "upload" if payload.get("image") else "button")
                self.json_response(502 if result.get("error") else 200, result)
            elif self.path == "/watch":
                with state_lock: watch_on = bool(payload.get("on"))
                self.json_response(200, {"watch": watch_on})
            else: self.json_response(404, {"error": "not found"})
        except (ValueError, TypeError) as exc: self.json_response(400, {"error": str(exc)})
        except LookupError as exc: self.json_response(503, {"error": str(exc)})
        except RuntimeError as exc: self.json_response(503, {"error": str(exc)})
        except Exception as exc: self.json_response(500, {"error": str(exc)})


def main():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    if cv2 is not None and CAMERA.lower() != "none":
        threading.Thread(target=camera_loop, daemon=True).start()
    threading.Thread(target=watch_loop, daemon=True).start()
    threading.Thread(target=pipeline.warm_engines, daemon=True).start()
    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000"))
    print(f"rosetta http://{host}:{port} camera={CAMERA} vlm={os.environ.get('VLM_MODE','engine')} d1={os.environ.get('D1_CMD','default')}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__": main()

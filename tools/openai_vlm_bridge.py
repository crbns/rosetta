#!/usr/bin/env python3
"""VLM JSONL engine (plan §10.4) backed by an OpenAI-compatible chat server on loopback.

    python3 tools/openai_vlm_bridge.py [--url http://127.0.0.1:8080/v1/chat/completions] [--model NAME]
                                       [--timeout 120] [--allow-remote]

Uses: Mac prompt tuning against llama-server (plan §11.7); emergency GenieX on the board (§8.6).
NOT the NPU path: the ready event says target "cpu/gpu (not NPU)" and nsp_count 0 so the UI can say so.

stdin:  one request per line  {"id", "system", "prompt", "images": [png], "max_tokens", "temperature", "think"}
stdout: ready line first, then one response per request
        {"id", "status", "error"?, "text", "reasoning", "finish", "usage": {...}, "timings": {...}}
Errors are data: never crash the loop. Stdlib only. Refuses non-loopback URLs unless --allow-remote.
"""

import argparse
import base64
import ipaddress
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

LOOPBACK_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost"}


def is_loopback(host):
    if not host:
        return False
    if host.lower() in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def empty_response(req_id, status, error):
    return {"id": req_id, "status": status, "error": error, "text": "", "reasoning": "", "finish": "Error",
            "usage": {"prompt_rows": 0, "cached_rows": 0, "completion_tokens": 0},
            "timings": {"ttft_ms": None, "encode_ms": None, "prefill_ms": None, "decode_ms": None,
                        "tokens_per_second": None}}


def image_part(path):
    if not isinstance(path, str) or not path:
        raise ValueError("image path must be a non-empty string")
    with open(path, "rb") as fh:
        data = fh.read()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"not a PNG: {path}")
    return {"type": "image_url",
            "image_url": {"url": "data:image/png;base64," + base64.b64encode(data).decode("ascii")}}


def map_finish(reason):
    if not reason:
        return "Stop"
    reason = str(reason).lower()
    return {"stop": "Stop", "length": "Length", "eos": "Stop"}.get(reason, reason.capitalize())


def handle(req, args, opener):
    req_id = req.get("id")
    try:
        prompt = req.get("prompt", "")
        system = req.get("system", "")
        images = req.get("images") or []
        max_tokens = int(req.get("max_tokens", 768))
        temperature = float(req.get("temperature", 0))
        if not isinstance(prompt, str) or not isinstance(system, str) or not isinstance(images, list):
            raise ValueError("prompt/system must be strings and images a list")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        content = [image_part(p) for p in images] + [{"type": "text", "text": prompt}]
    except (ValueError, TypeError, OSError) as exc:
        return empty_response(req_id, "InvalidArgument", f"{type(exc).__name__}: {exc}")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})
    body = {"model": args.model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature, "stream": False}
    if req.get("think"):
        body["chat_template_kwargs"] = {"enable_thinking": True}

    http_req = urllib.request.Request(args.url, data=json.dumps(body).encode("utf-8"),
                                      headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with opener.open(http_req, timeout=args.timeout) as resp:
            raw = resp.read()
        wall_ms = (time.perf_counter() - started) * 1000.0
        out = json.loads(raw.decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:  # noqa: BLE001
            pass
        status = "InvalidArgument" if 400 <= exc.code < 500 else "DeviceError"
        if "context" in detail.lower() and ("exceed" in detail.lower() or "too long" in detail.lower()):
            status = "ContextExceeded"
        return empty_response(req_id, status, f"HTTP {exc.code}: {detail}")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return empty_response(req_id, "DeviceError", f"{type(exc).__name__}: {exc}")
    except ValueError as exc:
        return empty_response(req_id, "DeviceError", f"bad JSON from server: {exc}")

    try:
        choice = (out.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = msg.get("content") or ""
        if isinstance(text, list):  # some servers return content parts
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
        reasoning = msg.get("reasoning_content") or ""
        usage = out.get("usage") or {}
        t = out.get("timings") or {}  # llama-server extension
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", t.get("cache_n", 0)) or 0
        completion_tokens = int(usage.get("completion_tokens") or t.get("predicted_n") or 0)
        prefill_ms = t.get("prompt_ms")
        decode_ms = t.get("predicted_ms")
        tok_s = t.get("predicted_per_second")
        if tok_s is None and completion_tokens and wall_ms > 0:
            tok_s = completion_tokens / (wall_ms / 1000.0)  # wall-clock estimate (includes prefill)
        result = {
            "id": req_id, "status": "Ok", "text": text, "reasoning": reasoning,
            "finish": map_finish(choice.get("finish_reason")),
            "usage": {"prompt_rows": int(usage.get("prompt_tokens") or t.get("prompt_n") or 0),
                      "cached_rows": int(cached), "completion_tokens": completion_tokens},
            "timings": {"ttft_ms": prefill_ms if prefill_ms is not None else None,
                        "encode_ms": None, "prefill_ms": prefill_ms, "decode_ms": decode_ms,
                        "tokens_per_second": round(tok_s, 2) if tok_s is not None else None,
                        "wall_ms": round(wall_ms, 1)},
        }
        if not text.strip():
            result["status"] = "DeviceError"
            result["error"] = "empty text from server"
        return result
    except (AttributeError, TypeError, ValueError, IndexError) as exc:
        return empty_response(req_id, "DeviceError", f"unexpected server response: {type(exc).__name__}: {exc}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    ap.add_argument("--model", default="lfm3-vl-2b", help="model name sent to the server (llama-server ignores it)")
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds per request")
    ap.add_argument("--allow-remote", action="store_true", help="permit a non-loopback --url (breaks offline rule)")
    args = ap.parse_args()

    parsed = urllib.parse.urlparse(args.url)
    if parsed.scheme not in ("http", "https"):
        print(f"openai_vlm_bridge: unsupported URL scheme: {args.url}", file=sys.stderr)
        return 2
    if not is_loopback(parsed.hostname) and not args.allow_remote:
        print(f"openai_vlm_bridge: refusing non-loopback host {parsed.hostname!r} (pass --allow-remote)",
              file=sys.stderr)
        return 2

    # No proxies: an http_proxy env var must never route loopback traffic off the box.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    emit({"event": "ready", "model": "openai-bridge", "target": "cpu/gpu (not NPU)", "nsp_count": 0,
          "soc": "n/a", "sdk": "openai-compatible", "package": args.url, "max_context": None})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            if not isinstance(req, dict):
                raise ValueError("request must be a JSON object")
        except ValueError as exc:
            emit(empty_response(None, "InvalidArgument", f"bad request line: {exc}"))
            continue
        try:
            emit(handle(req, args, opener))
        except Exception as exc:  # noqa: BLE001  errors are data; never kill the loop
            emit(empty_response(req.get("id"), "DeviceError", f"bridge error: {type(exc).__name__}: {exc}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# rosetta: master plan

> **This file is the single source of truth.** Nothing else exists yet: every file in the repo is built from this spec, by Isaac and Rehan and their coding agents. Read it fully before writing code.
> When reality disagrees with this file (a command fails, an API answers differently, a number turns out wrong), fix the code **and update this file** (§15 known unknowns, §16 decision log) so the other agent sees it.
> Name: **rosetta** (always lowercase). Team: **Isaac** and **Rehan**. Written 2026-11-13, ~17:00 PT.

---

## Contents
0. [How to use this file](#0-how-to-use-this-file)
1. [TL;DR](#1-tldr)
2. [The event](#2-the-event)
3. [Product](#3-product)
4. [Demo script](#4-demo-script)
5. [Architecture](#5-architecture)
6. [Models: verified facts](#6-models)
7. [Hardware: IQ-9075 EVK](#7-hardware)
8. [Runtimes: GenieX, llama.cpp, Transformers](#8-runtimes)
9. [Build spec](#9-build-spec) (what to create, with reference code)
10. [API contracts](#10-api-contracts)
11. [Runbooks](#11-runbooks)
12. [Rules for coding agents](#12-rules-for-coding-agents)
13. [Timeline and task board](#13-timeline-and-task-board)
14. [Testing and acceptance](#14-testing-and-acceptance)
15. [Risks, fallbacks, known unknowns](#15-risks-fallbacks-known-unknowns)
16. [Decision log](#16-decision-log)
17. [Troubleshooting](#17-troubleshooting)
18. [Pitch and judge Q&A](#18-pitch-and-judge-qa)
19. [Stretch goals](#19-stretch-goals)
20. [Glossary](#20-glossary)
21. [Sources](#21-sources)

---

## 0. How to use this file

- **Humans:** §1–4 for the what and why, §11 for commands, §13 for who does what and when.
- **Coding agents:** §5, §9, §10, §12 are your spec. Build in the **priority order of §9.10**. Use the **reference code** in §9; it was written and tested against mock servers. Don't re-derive it.
- **Priorities:** **P0** = demo can't happen without it · **P1** = what makes it win · **P2** = polish. Never start P1 while a P0 is broken.
- **Ownership:** Isaac's agent owns the **model/runtime side** (model servers, `decider.py`, IQ9 setup, `app.py` pipeline functions). Rehan's agent owns the **app shell and UX** (`app.py` HTTP/camera layer, `index.html`, mocks, demo). Shared file = `app.py`; coordinate edits (§12).
- **Pre-building:** the event's rules aren't published. **Ask an organizer at 5–6 PM whether code written before 6:15 is allowed.** If not, everything in §9 gets built 6:15–8:15 from this spec. That's feasible with agents, which is why the spec is this detailed.

---

## 1. TL;DR

- **rosetta:** point a webcam at any foreign-language sign, notice, menu, label or medicine box. It **translates** the text, then **decides what matters**: how serious it is, what you must do, which lines are critical. **Zero internet.**
- **Two Liquid models, both running on the Qualcomm IQ9:**
  1. **LFM3-VL-2B** (vision-language): photo → English lines, plus a list of scripts it couldn't read, plus an answer to the user's optional question.
  2. **d1-2B** (Liquid's decision model): over the translation, **one call** returns calibrated probabilities for **category**, **severity (5 levels)**, **action required**, **affects you**, and **importance of every line**.
- **Story:** "Trekking on the Tibetan Plateau, no signal, there's a sign. rosetta reads it, flags it as a *Danger*-level notice, puts 'descend immediately if you get a headache' at the top, and honestly tells you which line it *couldn't* read."
- **Build window ≈ 2 hours (6:15–8:15 PM). Judging happens with Wi-Fi OFF.** Everything must run offline on the IQ9.

---

## 2. The event

**On-Device AI Hackathon: Cleared for Takeoff ✈️** (Qualcomm × Liquid AI)

| Item | Detail |
|---|---|
| When / where | Fri **Nov 13, 2026** · **555 Mission St, San Francisco** |
| Schedule | 5:00–6:00 doors, food · **6:00–6:15 on-device AI workshop** · **6:15–8:15 build** · **8:15–9:00 showcase, judging, awards** |
| Hardware | **One Qualcomm IQ9 dev kit per team** (organizer email). Cameras/mics/peripherals are **BYO**: "Bring a fully charged laptop, your charger, and your favorite coding agent." **We have a USB webcam.** |
| Models | Liquid **LFM3** family |
| The test | "At the end of the night, we'll turn off the Wi-Fi and put every project to the test." |
| Team | Isaac + Rehan (max 4) |
| Prizes | 1st: IQ9s · 2nd: Uno Qs |
| Field | ~246 registered → possibly ~60 teams → **short demos**. Optimize for a <60 s, instantly legible demo. |
| Judges | **Piotr Mazurek, Tianshu Yu, Alex Yuan** (Members of Technical Staff, Liquid AI) · **Charles Coudsi** (Senior Staff Engineer, Qualcomm) · **Heath Blandford** (Developer Relations, Qualcomm) |
| Criteria | **Not published.** The event page lists on-device benefits: **low latency, privacy, no server inference cost, offline.** |

**Implications**
- Liquid engineers (3 of 5) know LFM3's language list and limits, so **never overclaim.** Using **d1**, their newest model type, for a real reason is a differentiator.
- Qualcomm engineers (2 of 5) will care that it **visibly runs on the IQ9**. **GenieX / NPU** use is a bonus.
- Past Liquid hackathon winners were **simple, single-purpose, obviously useful** apps (on-device grammar assistant; screen-time tool; offline video change detector; semantic video search; private smart-home camera agent; lost-item finder). **Keep the story tight.**

---

## 3. Product

### Problem
Travelers with **no data** (mountains, deserts, rural roads, border zones, flights, roaming) hit text they can't read that **actually matters**: closures, curfews, permit rules, altitude warnings, last water or fuel, dosage limits, cover charges, allergens. Cloud translators fail exactly when you're most isolated. Even when they work, they return a wall of text without telling you *which line could hurt you*.

### Solution
**rosetta = offline translate + triage.**
1. **Read & translate** everything (LFM3-VL-2B).
2. **Decide what matters** (d1-2B): severity banner, ranked "What matters" list with calibrated %, per-line color coding, "action required" / "affects you" probabilities.
3. **Never guess** unreadable scripts. Say so explicitly (amber box).
4. Optional **"About you"** (e.g. "on a motorbike", "allergic to shellfish", "no permit") personalizes the ranking.
5. Optional **question** ("Can I hike this afternoon?"), answered from the text only.

### Why on-device is the point
- **Offline:** the scenario has no connectivity. That's the event's theme.
- **Latency:** seconds on a 2B model, no round trip.
- **Privacy:** photos of medicine, permits, tickets and IDs never leave the device.
- **Cost:** no per-call inference bill.

### Non-goals (do not build)
Speech in/out, AR overlays, multi-turn chat, accounts, cloud sync, history DB, maps, mobile packaging, fine-tuning, support for languages LFM3-VL-2B doesn't support (we **detect and admit** those instead), and medical/legal advice beyond the text.

---

## 4. Demo script

**Table setup:** IQ9 + USB webcam on a stand pointing down at the table · laptop showing `http://<iq9-ip>:8000` · printed props · **laptop Wi-Fi visibly OFF** · backup video on a phone.

### Props
Two printable PDFs were made earlier (separate from this repo): **`remote_translator_props.pdf`** (primary) and **`translator_demo_props.pdf`** (backup). Print in color, flat, no glare. Contents and expected outputs are in §14.4. Primary set:
1. French bistro menu (safe opener)
2. **Tibetan Plateau trailhead:** Tibetan greeting on top + Chinese body (**hero**)
3. Northern Thailand trail sign (Thai)
4. Ha Giang Loop road notice (Vietnamese)
5. Ladakh high pass (Hindi)
6. Kyrgyzstan border zone (Russian)
7. Desert reserve (Arabic)

### ~60–75 s script
1. **Hook (10 s):** "No signal on a trek, and a sign could be the difference between a nice hike and a rescue. rosetta runs entirely on this Qualcomm IQ9, Wi-Fi off."
2. **Hero scan (25 s):** Tibetan trailhead. Question: "Can I hike this afternoon?" → **Scan**.
   - Point at: **red Danger/Warning banner** with d1 confidence → **What matters** led by altitude sickness / be down by 14:00 / no signal → amber **"Couldn't read (not guessing): Tibetan line"** → the answer → "read X s · decide Y s" timer.
   - Line: "Two Liquid models: LFM3-VL reads and translates, **d1 decides what matters** with calibrated probabilities. And when it can't read Tibetan, it *says so* instead of hallucinating."
3. **Second scan (15 s):** Kyrgyz border (Russian) → "rule or prohibition", permit line on top. *Or* Ladakh (Hindi) → permit + landslide window.
4. **Personalization (10 s, optional):** French menu + "allergic to shellfish" → bouillabaisse line jumps up.
5. **Close (5 s):** "No cloud, no data plan, no inference bill. LFM3-VL-2B + d1-2B on the IQ9 via [GenieX / llama.cpp] on [NPU / CPU]." **State only what's verified.**

If a scan misreads, move to the next prop. Never debug live.

---

## 5. Architecture

```
┌──── Laptop (display only) ────┐   Ethernet   ┌────────────────────── Qualcomm IQ9 (all compute) ───────────────────────┐
│ Browser → http://<iq9>:8000   │────cable────►│ app.py :8000 (Python stdlib HTTP server)                                  │
│ live preview (MJPEG)          │              │  ├─ USB webcam (OpenCV thread) → /stream ; frame grabbed on /scan          │
│ Scan · About you · Question   │              │  ├─ Step 1 → VLM server   POST /v1/chat/completions                        │
│ results panel                 │              │  │     llama.cpp :8080  OR  geniex serve :18181   model: LFM3-VL-2B        │
└───────────────────────────────┘              │  └─ Step 2 → d1-2B        GenieX POST :18181/v1/decisions  (preferred)     │
                                               │                           decider.py POST :8090/decide      (fallback)     │
                                               └───────────────────────────────────────────────────────────────────────────┘
```

### Per-scan pipeline
1. **Capture:** latest IQ9 webcam frame (or an uploaded image) → downscale longest side to `MAX_SIDE` (1024) → JPEG q≈88 → base64 data URL.
2. **Read & translate (LFM3-VL-2B):** system prompt §9.3 → JSON `{"languages","summary","lines","unreadable","answer"}`. Strip `<think>` blocks and code fences; on parse failure, fall back to raw lines plus a `parse_error` flag. Cap at 40 lines.
3. **Decide (d1-2B):** input = numbered English lines. Questions §9.4: `category` (choice), `severity` (score, 5 levels), `action` (predicate), `personal` (predicate, only if About-you is set), `line_i` (predicate per line). One request, ≤ 64 questions.
4. **Normalize** answers from either backend → `{p}` / `{value,confidence}` / `{index,label,confidence,probabilities}` (§9.4 reference code).
5. **Render** (§9.7).
6. **Fail soft:** d1 down → translation still shows with a gray notice. VLM down → clear error. Camera missing → upload still works.

---

## 6. Models

Checked against Liquid, Qualcomm and Hugging Face pages on 2026-11-13 (links in §21).

### LFM3 family (released Oct 27, 2026)
Six open-weight ~2B models on one backbone (LFM3-1.7B-Base): LFM3-1.7B (text), **LFM3-VL-2B** (text+image+video → text), LFM3-Audio-2B, LFM3-Omni-2B, and decision models **d1-2B** and d1-omni-2B.

### LFM3-VL-2B: reader/translator
- 1.92B params, 128K context, in-house vision encoder, **reasoning mode** (may emit `<think>…</think>` before the answer).
- **Supported languages (model card):** English, Arabic, Chinese, French, German, Italian, Japanese, Korean, Portuguese, Spanish, Vietnamese, Thai, Indonesian, Hindi, Russian, Polish. That's **16**.
  - **Not supported:** Tibetan, Swati, Nepali, Kyrgyz, etc. The Tibetan prop is built around this: correct behavior = translate the Chinese, flag the Tibetan as unreadable.
- Model card: "not recommended for coding, multi-turn conversations, or complex reasoning." We do single-turn reading, so that's fine.
- Benchmarks: DocVQA 96.7, TextVQA 87.9, OCRBench v2 (English) 63.5. **Non-Latin OCR from a webcam is unverified. Test early.**
- **GGUF repo `LiquidAI/LFM3-VL-2B-GGUF`:** `LFM3-VL-2B-QAD-Q4_0.gguf` (1.05 GB, **default**), `LFM3-VL-2B-Q4_K_M.gguf` (1.1 GB, fallback), Q5_K_M/Q6_K/Q8_0/F16/BF16; projectors `mmproj-LFM3-VL-2B-Q8_0.gguf` (203 MB, **default**), F16/BF16 (379 MB).
- **Qualcomm listing `qualcomm/LFM3-VL-2B`:** runtime `GENIEX_LLAMACPP`, q4_0, lists **Dragonwing IQ-9075**. On IQ-9075: **~35–42 tok/s** in most configurations (some ~17–18); TTFT ~0.1–2.9 s at 512 ctx, longer at 4096 ctx. OS not stated; configuration rows unexplained.

### d1-2B: "what matters" decider
- Built on LFM3-VL-2B, 1.92B params. **Not a chat model.** Calibrated answers in **one forward pass, no token generation.** Inputs: text, pictures, video (no audio).
- **Transformers API:** `pip install "transformers>=5.19" torch torchvision pillow` · `AutoModel.from_pretrained("LiquidAI/d1-2B", trust_remote_code=True, dtype=dtype).to(device)` · `model.system_one(state, questions, media=None)` → `{"answers": {...}, "usage": {...}}` · float32 on CPU, bf16 on GPU/MPS.
  - Question types: `noul` (yes/no → `noul` = P(yes)) · `choice` (options in **`criteria`** dict `{name: description}`; `multiple: True` for multi-select → `choice`/`choices`, `confidence`, `probabilities`) · `score` (`criteria` = ordered list of 2–10 levels, lowest first → `score` (median level index), `confidence`, `probabilities`, `legend`) · `text`/`number`/`date` extraction · `box`/`boxes`.
  - Card gives ms-scale GPU/MPS timings, **no CPU timings.**
- **GGUF:** `LiquidAI/d1-2B-GGUF` → `d1-2B-Q4_K_M.gguf` (the file GenieX docs tested). Plain llama.cpp chat **won't** give typed decisions. Use GenieX `/v1/decisions` or Transformers.

### Not using
LFM3-Audio/Omni (hardware plus runtime risk), fine-tuning. LFM2.5-VL-1.6B/450M are emergency fallbacks if LFM3-VL-2B won't load or is too slow (untested by us).

---

## 7. Hardware

**Qualcomm Dragonwing IQ-9075 EVK**
- **8-core Kryo** CPU (≤2.36 GHz) · **Hexagon NPU up to 100 dense INT8 TOPS** · **Adreno 663** GPU · **up to 36 GB LPDDR5**.
- OS: Ubuntu or Qualcomm Linux; we don't know which image organizers flashed (`cat /etc/os-release`).
- Qualcomm's Ubuntu docs: the **old *Genie* SDK has no IQ-9075 models; use llama.cpp.** *GenieX* is different and newer, and explicitly lists IQ-9075/QCS9075.
- Webcam → `/dev/video*`. Display: the laptop over Ethernet. Access: SSH (default user likely `ubuntu`; confirm).

---

## 8. Runtimes

### 8.1 GenieX (Qualcomm; preferred, especially for d1)
- One SDK over **llama.cpp** (any GGUF; CPU / Adreno GPU / Hexagon NPU) and **`qairt`** (NPU-only AI Hub bundles). Supports **Linux ARM64**.
- **Install (Linux ARM64):**
  ```bash
  sudo apt update
  sudo apt install -y libatomic1 libglib2.0-0 ocl-icd-libopencl1
  sudo apt-get install -y qcom-adreno1 qcom-fastrpc1 libqnn1
  curl -fsSL https://qaihub-public-assets.s3.us-west-2.amazonaws.com/qai-hub-geniex/install.sh | sh
  geniex --help        # export HOME=/root first if HOME is unset
  ```
  Docker alternative: `docker.io/qualcomm/geniex` (`-cpu` tags are CPU-only; NPU needs `--privileged` + `/usr/lib` mount).
- **Serve:** `geniex serve` → `http://127.0.0.1:18181` (Swagger at root). **No auto-download**: `geniex pull` first. Endpoints: `POST /v1/chat/completions`, `POST /v1/completions`, `POST /v1/decisions`.
- **VLM images:** `image_url` part; `url` = local path, http(s) URL, or **base64 data URL** (we use data URLs).
- **Local GGUF:** `geniex pull local/<name> --local-path /path/to/folder`. For VLMs, docs only describe Android (put `mmproj-*.gguf` next to the model). **Assumed to work the same on Linux. Unverified.**
- **Compute:** `--compute npu` (default) · `gpu` (llama.cpp) · `cpu` · `hybrid` (HTP+CPU scheduler, "fast path", must be explicit) · `--vit-compute` for a VLM's vision encoder. **Q4_0 = best Hexagon support.**
- **d1 in GenieX:**
  - `geniex pull local/d1-2b:Q4_K_M --model-hub localfs --local-path ./models/d1-2b --model-type llm`
  - CLI: `geniex decide --kind choice --input "..." --question "..." --choice VALUE=DESC [--compute cpu --nctx 4096 --json]`
  - `POST /v1/decisions`: `model` (name from `geniex list`), `compute`, `nctx`, `input` (string, or messages with `input_text`/`input_image`/`input_audio`), `questions` (≤64; each `name`, `type` ∈ `choice|predicate|score`, `instructions`, plus `choices:[{value,description}]` (2–255) or `levels:[{label}]` (2–10)).
  - Response: ordered `answers`; predicate → probability, choice → selected value, score → zero-based index, plus probabilities/confidence. **The full envelope is not documented.** Our normalizer (§9.4) handles likely shapes.
  - **Decisions are text-only in GenieX.** Chat requests to d1 → `PARAM_NOT_SUPPORTED`.
  - **NPU caps decision questions at 128 tokens on Linux**, so default to `compute: "cpu"` for d1.

### 8.2 llama.cpp (VLM fallback; known-good on IQ-9075)
- `llama-server -m models/LFM3-VL-2B-QAD-Q4_0.gguf --mmproj models/mmproj-LFM3-VL-2B-Q8_0.gguf --host 127.0.0.1 --port 8080 -c 8192`
- Newer builds also ship a unified `llama` binary: `llama serve -hf LiquidAI/LFM3-VL-2B-GGUF:Q4_K_M` (model card). Either works; we only need the OpenAI endpoint.
- IQ9 build: `git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build && cmake --build build -j8 --target llama-server` (minutes, so **start at 6:15 if needed**). Mac: `brew install llama.cpp`.

### 8.3 Transformers (d1 fallback; also Mac testing)
- `decider.py` (§9.5) wraps `system_one` behind `POST :8090/decide` using the **same question schema as GenieX**. CPU float32 ≈ 8 GB RAM (fine on the IQ9). **CPU speed unknown.**

---

## 9. Build spec

### 9.1 Repo layout to create
```
rosetta/
├── rosetta.md               ← this file (the only pre-existing file)
├── AGENTS.md, CLAUDE.md     "Read rosetta.md first." + §12 rules (3–5 lines)
├── app.py                   web server + pipeline (stdlib; OpenCV optional)
├── index.html               single-file UI, no external assets
├── decider.py               d1-2B via Transformers on :8090
├── tools/mock_servers.py    fake VLM :8080, fake decider :8090, fake GenieX :18181
├── scripts/download_models.sh
├── scripts/run_vlm_llamacpp.sh
├── scripts/run_decider.sh
├── .gitignore               models/  __pycache__/  *.pyc  .DS_Store  *.part
└── models/                  (gitignored) weights
```

### 9.2 `app.py`: requirements
- **Python stdlib only** (`http.server.ThreadingHTTPServer`, `urllib.request`, `json`, `base64`, `threading`). **OpenCV optional**: `try: import cv2 except ImportError: cv2 = None`.
- Config via env vars (§10.6). Serve `index.html` from the same directory.
- Routes: `GET /` · `GET /status` · `GET /stream` · `POST /scan` (contracts in §10).
- **Camera:** background thread reads `cv2.VideoCapture(CAMERA)` (int index or `/dev/videoN`), 1280×720 requested, keeps the latest frame under a lock. If OpenCV is missing, `CAMERA=none`, or open fails, run with `server_camera=false`. `/stream` = MJPEG (`multipart/x-mixed-replace; boundary=frame`), ~14 fps, 960 px, q70. Swallow `BrokenPipeError`/`ConnectionResetError`.
- **Image prep:** uploaded data URLs are decoded and, if OpenCV is present, downscaled to `MAX_SIDE`. Webcam frames are downscaled and JPEG-encoded at q88.
- `/scan` = `read_and_translate()` → `decide()` (wrapped in try/except so d1 failure returns `decision: {"error": ...}`), attach `_image` (data URL of what the model saw).
- Error mapping: no image → 400 · no frame yet → 503 · VLM `URLError` → 502 with URL in message · anything else → 500. **Never let the server die.**
- Startup log prints the VLM URL, decider backend/URL, camera status, app URL.

### 9.3 Step 1: read & translate (reference, use verbatim)
```python
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
```
**Request** (OpenAI chat completions to `MODEL_URL`):
```python
user_text = []                                   # only include parts that are non-empty
if about:    user_text.append("About the traveler: " + about)
if question: user_text.append("Traveler's question: " + question)
user_text.append("Read and translate all text in this image. Respond with the JSON object only.")
body = {"model": MODEL_NAME, "temperature": 0.1, "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": [
                         {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
                         {"type": "text", "text": "\n".join(user_text)}]}]}
if NO_THINK: body["chat_template_kwargs"] = {"enable_thinking": False}
```
After parsing: coerce `lines` to a list of non-empty strings (split if it's a string), cap at 40, and record `_vlm = {seconds, raw, completion_tokens}`.

### 9.4 Step 2: decide what matters (reference, use verbatim)
```python
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
    who = f" The traveler says: {about.strip()}." if about.strip() else ""
    qs = [
        {"name": "category", "type": "choice",
         "instructions": "What is this text mainly about, from a traveler's point of view?",
         "choices": [{"value": v, "description": d} for v, d in CATEGORIES]},
        {"name": "severity", "type": "score",
         "instructions": "How serious are the consequences for a traveler who ignores or misunderstands this text?" + who,
         "levels": [{"label": l} for l in SEVERITY]},
        {"name": "action", "type": "predicate",
         "instructions": "Does this text require the reader to do something, or forbid them from doing something?"},
    ]
    if about.strip():
        qs.append({"name": "personal", "type": "predicate",
                   "instructions": f"Does anything in this text specifically affect this traveler?{who}"})
    for i, line in enumerate(lines, 1):
        qs.append({"name": f"line_{i}", "type": "predicate",
                   "instructions": (f'Line {i}: "{line[:300]}". Is this line something the traveler must notice or act on: '
                                    f"a danger, prohibition, requirement, deadline, closure, fee, dosage limit, "
                                    f"health risk, or something that affects them personally?{who}")})
    return qs[:64]

def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def _normalize_answer(q, a):
    """Backend-agnostic: d1 Transformers keys (noul/choice/score) or GenieX keys (probability/value/index)."""
    if a is None: return None
    if not isinstance(a, dict): a = {"value": a}
    t = q["type"]
    if t == "predicate":
        for k in ("noul", "probability", "p", "yes", "value", "answer", "score"):
            v = _num(a.get(k))
            if v is not None: return {"p": v}
        probs = a.get("probabilities")
        if isinstance(probs, dict):
            for k in ("yes", "true", "Yes", "True", "1"):
                if k in probs: return {"p": _num(probs[k])}
        return None
    if t == "choice":
        v = a.get("choice", a.get("value", a.get("answer")))
        return {"value": v, "confidence": _num(a.get("confidence")), "probabilities": a.get("probabilities")}
    if t == "score":
        idx = None
        for k in ("score", "index", "value", "answer"):
            idx = _num(a.get(k))
            if idx is not None: break
        if idx is None: return None
        i = max(0, min(len(SEVERITY) - 1, int(round(idx))))
        return {"index": i, "label": SEVERITY[i], "confidence": _num(a.get("confidence")),
                "probabilities": a.get("probabilities")}
    return a
```
**`decide(lines, about)`:**
- Return `None` if `DECIDER == "none"` or there are no lines.
- `text = "\n".join(f"{i}. {l}" for i, l in enumerate(lines, 1))`.
- **GenieX:** POST `DECIDER_URL` with `{"model": D1_MODEL, "compute": D1_COMPUTE, "nctx": 4096, "input": text, "questions": qs}`. Read `resp.get("answers", resp.get("output", []))`. If it's a **dict**, it's keyed by name. If it's a **list**, zip it with `qs` in order (prefer an answer's own `name` if present).
- **local:** POST `DECIDER_URL` with `{"input": text, "questions": qs}` → `resp["answers"]` keyed by name.
- Normalize every answer. Return `{category, severity, action_p, personal_p, importance: [p or None per line], seconds, backend, raw: resp}`.
- **If the severity banner doesn't appear on real hardware, the fix is almost certainly in `_normalize_answer`.** Read the raw `d1` output in the UI's Debug panel.

### 9.5 `decider.py`: d1 via Transformers (reference)
- Device: CUDA → MPS → CPU. dtype bf16 on GPU/MPS, float32 on CPU. `torch.set_num_threads(os.cpu_count())`. Model path `D1_PATH` (default `LiquidAI/d1-2B`; use a local snapshot for offline).
- Convert the GenieX-style schema to d1 schema:
```python
def to_d1(questions):
    out = {}
    for q in questions:
        if q["type"] == "predicate":
            out[q["name"]] = {"type": "noul", "instructions": q["instructions"]}
        elif q["type"] == "choice":
            out[q["name"]] = {"type": "choice", "instructions": q["instructions"],
                              "criteria": {c["value"]: c.get("description", c["value"]) for c in q["choices"]}}
        elif q["type"] == "score":
            out[q["name"]] = {"type": "score", "instructions": q["instructions"],
                              "criteria": [lv["label"] for lv in q["levels"]]}
    return out
```
- `POST /decide {input, questions}` → under a lock and `torch.inference_mode()`: `out = model.system_one(input, to_d1(questions))` → respond `{"answers": jsonable(out.get("answers", out)), "seconds": ...}` (`jsonable` converts tensors/numpy via `.item()`).
- **Warm-up call at startup** (`system_one("Warm-up.", {"x": {"type": "noul", "instructions": "Is this a warm-up?"}})`) so the first demo scan isn't slow. Bind `127.0.0.1:8090`.

### 9.6 Camera fallbacks
1. **Primary:** webcam on the IQ9 → `/stream`. No browser camera permissions needed, so plain `http://<ip>` works.
2. **Fallback A:** laptop browser camera via `getUserMedia`. **Browsers only allow this on HTTPS or `localhost`**, so tunnel: `ssh -L 8000:localhost:8000 <user>@<iq9>` and open `http://localhost:8000`. The page captures a frame to canvas (≤1024 px) and sends it as `image`.
3. **Fallback B:** "Upload photo" button.

### 9.7 `index.html`: UI spec
- **Single file, inline CSS/JS, zero external requests** (no CDNs, no web fonts; system font stack). Dark theme.
- **Header:** title **"rosetta"** (lowercase) · green pill "● runs on-device · no internet" · pill with model names from `/status` (e.g. "LFM3-VL-2B + d1-2B").
- **Left panel:** camera area (16:10; `<img src="/stream">` if `server_camera`, else `<video>` via getUserMedia, else a message) · big **Scan** button (Space key triggers it when focus isn't in an input) · **Upload photo** (auto-scans) · **"About you (optional)"** text input + quick chips (`allergic to shellfish`, `allergic to nuts`, `on a motorbike`, `traveling with kids`, `no permit`, `pregnant`) that toggle phrases in the input · **"Ask about it (optional)"** input. Persist About-you in `localStorage` (wrap in try/catch).
- **While scanning:** button disabled, spinner, "Reading & deciding on-device…".
- **Right panel, top to bottom:**
  1. Badges: `on-device · read X s · decide Y s` (green), detected languages, d1 category + confidence %.
  2. **Severity banner** (if `decision.severity`): big label; subline "d1-2B decision · NN% confident · action required: NN% · affects you: NN%"; thin probability bar with segments colored by level if `probabilities` exist. Colors by index: 0 gray `#5b6472`, 1 blue `#4f8cff`, 2 amber `#ffb547`, 3 orange `#ff7a3d`, 4 red `#ff4d4d` (tinted dark backgrounds).
  3. If `decision.error`: small gray box "Decision model unavailable, showing translation only."
  4. Summary sentence (bold).
  5. **"Your question"** box (blue) if `answer` is non-empty.
  6. **"⚠ What matters (ranked by d1)"** (red box): lines with importance ≥ 0.5, sorted descending, top 6, each with a % pill.
  7. **"Couldn't read (not guessing)"** (amber box) if `unreadable` is non-empty.
  8. **Full translation:** every line with a left border colored by importance (≥0.75 red, ≥0.5 amber, else gray) and a % pill.
  9. Parse-error notice if `parse_error`.
  10. Collapsible **Debug:** the captured image thumbnail + raw VLM output + raw d1 JSON. **Critical for tuning at the event.**
- **Empty state:** "Point the camera at any sign, notice, menu or label and press Scan. LFM3-VL reads & translates it · d1 decides what matters. Everything runs on this device."
- Escape all model text before inserting into HTML.

### 9.8 `tools/mock_servers.py` (build this FIRST; it unblocks UI work without models)
One script, three threads, stdlib only:
- **:8080 fake VLM** `POST /v1/chat/completions` → after 0.3 s returns `{"choices":[{"message":{"content":"<think>ok</think>" + json.dumps(VLM)}}],"usage":{"completion_tokens":260}}` (the `<think>` prefix tests the stripper).
- **:8090 fake decider** `POST /decide` → answers keyed by name, in d1 Transformers shape: `category {"choice":"safety warning","confidence":.88}`, `severity {"score":4.0,"confidence":.61,"probabilities":[.01,.04,.12,.22,.61]}`, `action {"noul":.96}`, `personal {"noul":.74}`, `line_i {"noul": IMP[i-1]}`.
- **:18181 fake GenieX** `POST /v1/decisions` → **ordered array** in GenieX-like shape: choice `{"name","value":"safety warning","confidence":.84}`, score `{"name","index":3,"confidence":.55,"probabilities":[...]}`, predicate `{"name","probability":p}`.
- Canned `VLM` (Tibetan trailhead):
```json
{"languages":["Chinese","Tibetan"],"summary":"Trailhead visitor notice at 4,650 m altitude.",
 "lines":["Visitor notice","Trail entrance · Altitude 4,650 m","1. There is no mobile phone signal on this entire route.",
  "2. You must descend before 14:00. Thunderstorms and hail are common in the afternoon.",
  "3. If you have headache, vomiting or difficulty breathing (altitude sickness), descend immediately; do not keep climbing.",
  "4. Do not enter herders' pastures; beware of Tibetan mastiffs.","5. Nearest supplies: checkpoint 5 km away (drinking water, oxygen).",
  "6. Fires and camping by the lake are strictly prohibited.","Rescue phone (call where there is signal): 120"],
 "unreadable":["Top line: Tibetan script, cannot read confidently"],
 "answer":"Yes, but be back down before 14:00; there's no signal on the route."}
```
`IMP = [.08,.41,.83,.91,.97,.66,.58,.62,.71]`. **Must pass:** app against each mock backend (`DECIDER=local` and `DECIDER=geniex`) yields a non-null category, severity and 9 importances; the UI shows banner + ranked list + amber box; the browser makes **zero non-localhost requests**.

### 9.9 Scripts
- `scripts/download_models.sh` (run on the Mac **with Wi-Fi**, then copy `models/` to a USB stick):
  - `https://huggingface.co/LiquidAI/LFM3-VL-2B-GGUF/resolve/main/LFM3-VL-2B-QAD-Q4_0.gguf` → `models/`
  - `.../LFM3-VL-2B-GGUF/resolve/main/mmproj-LFM3-VL-2B-Q8_0.gguf` → `models/`
  - `https://huggingface.co/LiquidAI/d1-2B-GGUF/resolve/main/d1-2B-Q4_K_M.gguf` → `models/d1-2b/`
  - Optional (~4 GB, for decider.py): `huggingface_hub.snapshot_download("LiquidAI/d1-2B", local_dir="models/d1-2B-hf")` (skip with `SKIP_TRANSFORMERS=1`)
  - Use `curl -L --fail -o file.part ... && mv`; skip files that already exist.
- `scripts/run_vlm_llamacpp.sh`: `${LLAMA_SERVER:-llama-server} -m models/LFM3-VL-2B-QAD-Q4_0.gguf --mmproj models/mmproj-LFM3-VL-2B-Q8_0.gguf --host 127.0.0.1 --port ${LLAMA_PORT:-8080} -c ${CTX:-8192}`
- `scripts/run_decider.sh`: set `D1_PATH=models/d1-2B-hf` if the folder exists, run `python3 decider.py`.

### 9.10 Build order (priority)
| # | Pri | Item | Owner | Done when |
|---|---|---|---|---|
| B1 | P0 | `tools/mock_servers.py` | Rehan's agent | three ports answer as §9.8 |
| B2 | P0 | `app.py` server + `/status` + `/scan` + step 1 (§9.3) | Rehan's agent | upload scan against mock VLM returns lines |
| B3 | P0 | `index.html` core: camera/upload, Scan, translation list, Debug | Rehan's agent | renders mock result, zero external requests |
| B4 | P0 | VLM serving on IQ9 (GenieX or llama.cpp) + smoke test | Isaac (+agent) | smoke test translates a prop photo |
| B5 | P0 | Webcam capture + `/stream` in `app.py` | Rehan's agent | live preview from IQ9 webcam |
| B6 | P1 | step 2 `decide()` + normalizer (§9.4) | Isaac's agent | mock GenieX and mock local both produce severity + importances |
| B7 | P1 | UI: severity banner, What-matters, unreadable box, per-line colors, timings | Rehan's agent | matches §9.7 with mocks |
| B8 | P1 | d1 serving on IQ9 (GenieX `/v1/decisions`, else `decider.py`) | Isaac | smoke test returns a probability |
| B9 | P1 | Real end-to-end on IQ9 + tune prompt/normalizer vs props | both | §14.4 "Must" passes |
| B10 | P2 | About-you chips + question box | Rehan's agent | answer/personal_p show up |
| B11 | P2 | `decider.py` (only if GenieX d1 fails) | Isaac's agent | `/decide` works on IQ9 CPU |
| B12 | P2 | Polish, readability at demo distance | Rehan | — |

**Cut line:** if B9 isn't green by **7:35**, drop B10/B12, freeze features, and rehearse.

---

## 10. API contracts

Internals may change; **these may not** unless `index.html` and this section are updated in the same change.

### 10.1 `POST /scan` (browser → app)
```json
{"image": "data:image/jpeg;base64,...   (optional; omit to use the IQ9 webcam)",
 "about": "on a motorbike, allergic to shellfish",
 "question": "Can I hike this afternoon?"}
```
**200:**
```json
{"languages": ["Chinese","Tibetan"], "summary": "...", "lines": ["...", "..."],
 "unreadable": ["Top line: Tibetan script, cannot read"], "answer": "...", "parse_error": false,
 "_vlm": {"seconds": 4.2, "raw": "...", "completion_tokens": 260},
 "decision": {"category": {"value": "safety warning", "confidence": 0.88, "probabilities": {}},
              "severity": {"index": 4, "label": "Danger: risk of serious injury or death", "confidence": 0.61, "probabilities": [0.01,0.04,0.12,0.22,0.61]},
              "action_p": 0.96, "personal_p": 0.74, "importance": [0.08, 0.41, 0.83],
              "seconds": 0.9, "backend": "geniex", "raw": {}},
 "_image": "data:image/jpeg;base64,..."}
```
`decision` may be `null` (`DECIDER=none`) or `{"error": "..."}`. Errors: 400 / 502 / 503 / 500 as `{"error": "..."}`.

### 10.2 `GET /status` → `{"server_camera": bool, "model_name": str, "decider": "geniex|local|none", "severity_levels": [5 labels]}`
### 10.3 `GET /stream` → MJPEG, 404 JSON if there's no server camera
### 10.4 app → VLM: OpenAI chat completions (§9.3)
### 10.5 app → d1: GenieX `POST /v1/decisions` or local `POST :8090/decide` (§9.4, §9.5)

### 10.6 Environment variables
| Var | Default | Notes |
|---|---|---|
| `MODEL_URL` | `http://127.0.0.1:8080/v1/chat/completions` | GenieX: port `18181` |
| `MODEL_NAME` | `LFM3-VL-2B` | llama.cpp ignores; GenieX needs the `geniex list` name |
| `DECIDER` | `local` | `geniex` · `local` · `none` |
| `DECIDER_URL` | auto | `http://127.0.0.1:18181/v1/decisions` if geniex, else `http://127.0.0.1:8090/decide` |
| `D1_MODEL` | `local/d1-2b:Q4_K_M` | GenieX model name |
| `D1_COMPUTE` | `cpu` | `npu` only if questions fit 128 tokens |
| `CAMERA` | `0` | index, `/dev/videoN`, or `none` |
| `PORT` / `HOST` | `8000` / `0.0.0.0` | |
| `MAX_SIDE` | `1024` | 768 if slow, 1280 if small text is misread |
| `MAX_TOKENS` | `1500` | room for reasoning + JSON |
| `NO_THINK` | `0` | `1` → `chat_template_kwargs.enable_thinking=false` |
| `MODEL_TIMEOUT` | `180` | seconds |
| `D1_PATH` / `DECIDER_PORT` | `LiquidAI/d1-2B` / `8090` | decider.py |

---

## 11. Runbooks

### 11.0 Now → 6:15 (Wi-Fi ON)
- [ ] **Ask organizers:** is pre-written code allowed? Which IQ9 image, login and IP? Is GenieX preinstalled?
- [ ] Download models (§9.9 URLs; plain `curl` works if the script isn't written yet) to **laptop + USB stick (exFAT)**:
  ```bash
  mkdir -p models/d1-2b && cd models
  curl -LO https://huggingface.co/LiquidAI/LFM3-VL-2B-GGUF/resolve/main/LFM3-VL-2B-QAD-Q4_0.gguf
  curl -LO https://huggingface.co/LiquidAI/LFM3-VL-2B-GGUF/resolve/main/mmproj-LFM3-VL-2B-Q8_0.gguf
  curl -L -o d1-2b/d1-2B-Q4_K_M.gguf https://huggingface.co/LiquidAI/d1-2B-GGUF/resolve/main/d1-2B-Q4_K_M.gguf
  ```
- [ ] Mac: `brew install llama.cpp`; `pip install "transformers>=5.19" torch torchvision pillow huggingface_hub`
- [ ] Quick Mac sanity test: `llama-server -m LFM3-VL-2B-QAD-Q4_0.gguf --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf --port 8080`, then the §14.1 smoke test on a photo of a prop. **Record read time and quality in §16.**
- [ ] Gear: webcam, **Ethernet cable + USB-C Ethernet adapter**, USB stick, chargers, printed props (color), phone for the backup video.
- [ ] 6:00–6:15 workshop: **write down the exact GenieX/IQ9 commands they show** and update §8 and §11.

### 11.1 IQ9 recon (first 10 minutes)
```bash
ssh <user>@<iq9-ip>
cat /etc/os-release; uname -m; nproc; free -h; df -h ~
ls /dev/video*; python3 --version; which geniex llama-server docker
```
Record the results in §15.

### 11.2 IQ9 Path A: GenieX for both models (preferred)
```bash
# install GenieX if missing (§8.1), copy repo + models to ~/rosetta
cd ~/rosetta && mkdir -p models/vl
cp models/LFM3-VL-2B-QAD-Q4_0.gguf models/mmproj-LFM3-VL-2B-Q8_0.gguf models/vl/
geniex pull local/lfm3-vl-2b --local-path ./models/vl            # mmproj in same folder (assumption)
geniex pull local/d1-2b:Q4_K_M --model-hub localfs --local-path ./models/d1-2b --model-type llm
geniex list                                                       # record exact names
tmux new -s rosetta                                               # one window per server
geniex serve                                                      # :18181
pip install --break-system-packages opencv-python-headless
MODEL_URL=http://127.0.0.1:18181/v1/chat/completions MODEL_NAME=<vl name> \
DECIDER=geniex D1_MODEL=<d1 name> python3 app.py
```
**If the workshop shows a different flow, follow the workshop** and just set `MODEL_URL` / `MODEL_NAME` / `D1_MODEL`.

### 11.3 IQ9 Path B: llama.cpp (VLM) + Transformers (d1)
```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
cmake -B build && cmake --build build -j8 --target llama-server && cd ~/rosetta
LLAMA_SERVER=~/llama.cpp/build/bin/llama-server scripts/run_vlm_llamacpp.sh      # tmux window 1
pip install --break-system-packages "transformers>=5.19" torch torchvision pillow opencv-python-headless
scripts/run_decider.sh                                                           # tmux window 2 (needs d1 weights)
python3 app.py                                                                   # tmux window 3
```
Mix and match is fine (e.g. VLM via llama.cpp + d1 via GenieX).

### 11.4 Networking with Wi-Fi OFF (direct Ethernet)
- IQ9: `ip -br link` → wired iface → `sudo ip addr add 10.42.0.2/24 dev <iface> && sudo ip link set <iface> up`
- Mac: System Settings → Network → USB Ethernet adapter → Details → TCP/IP → Configure IPv4 **Manually**: `10.42.0.1` / `255.255.255.0`
- Verify: `ping 10.42.0.2` → `ssh <user>@10.42.0.2` → `http://10.42.0.2:8000`
- **Turn off the Mac's Wi-Fi and run full scans before 8:00.** Make sure nothing on the IQ9 tries to pull models at runtime.

### 11.5 Mac-only dev loop (no IQ9 needed)
`python3 tools/mock_servers.py &` then `CAMERA=none python3 app.py` → `http://localhost:8000` (browser camera works on localhost; or Upload).
Real models on the Mac: `llama-server ... --port 8080` + `scripts/run_decider.sh` (MPS) + `CAMERA=none python3 app.py`. (GenieX doesn't run on macOS.)

---

## 12. Rules for coding agents

1. **Offline at runtime is non-negotiable.** No CDN scripts, fonts or CSS; no remote APIs; no telemetry; no downloads at runtime. The only network calls go to `127.0.0.1` model servers.
2. **Stdlib-first.** No FastAPI/Flask/React/bundlers. OpenCV, and torch/transformers in `decider.py`, are the only extra deps.
3. **Never break §10** without updating `index.html` and this file in the same change.
4. **Fail soft.** d1 failure → translation still shows. Camera failure → upload. No exception kills the server.
5. **No overclaiming in UI copy:** languages, accuracy, NPU. If it's on CPU, it says CPU.
6. **Prompts are code.** Changes to `SYSTEM_PROMPT`, `CATEGORIES`, `SEVERITY` or `build_questions` must be checked against §14.4 and logged in §16.
7. **Mock first, then real.** `python3 -m py_compile app.py decider.py` before handing off.
8. **Small diffs; respect ownership** (§0). `app.py` is shared: Isaac's agent edits the pipeline functions (`read_and_translate`, `decide`, normalizer, constants); Rehan's agent edits the HTTP/camera layer. Pull before editing; don't reformat the other half.
9. **Never commit `models/`**, secrets or large binaries.
10. **Time-box 20 minutes.** If something isn't working, take the §15 fallback and log it.
11. **No fine-tuning, new architectures or audio** tonight.

---

## 13. Timeline and task board

| Time | Isaac | Rehan |
|---|---|---|
| **until 5:00** | Download models (§11.0); Mac sanity test of LFM3-VL-2B; log results in §16 | Print props in color; pack webcam, Ethernet cable + adapter, USB stick, chargers |
| 5:00–6:00 | Ask organizers (rules, IQ9 login/image, GenieX); install Mac deps | Same; set up agent with this file; if pre-building is allowed, start B1–B3 |
| 6:00–6:15 | **Workshop: note exact GenieX/IQ9 commands** → update §8/§11 | Same |
| 6:15–6:30 | §11.1 recon; copy models to IQ9; start GenieX install or llama.cpp build | B1 mocks → B2 app core (agent) |
| 6:30–7:00 | B4 VLM serving + smoke test; B8 d1 serving + smoke test | B3 UI core → B5 webcam; Ethernet link (§11.4) |
| 7:00–7:15 | B6 `decide()` + normalizer (agent) against mocks, then real d1 | B7 UI decision display |
| 7:15–7:35 | **B9** integrate on IQ9, scan every prop, fix normalizer/prompt | B9 with Isaac; B10 if green |
| **7:35** | **Cut line:** freeze features if B9 isn't green | |
| 7:35–7:55 | **Wi-Fi-OFF rehearsal**: 3 scans in a row; record timings in §16 | Record backup video on phone |
| 7:55–8:15 | Buffer; P2 only if everything is green | Rehearse the 60 s script out loud once |
| 8:15– | Demo | Demo |

---

## 14. Testing and acceptance

### 14.1 Smoke tests
```bash
# VLM (llama.cpp :8080 or GenieX :18181; set "model" for GenieX)
python3 - <<'EOF'
import base64, json, urllib.request
img = base64.b64encode(open("test.jpg","rb").read()).decode()
body = {"model":"LFM3-VL-2B","max_tokens":400,"messages":[{"role":"user","content":[
  {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+img}},
  {"type":"text","text":"Read and translate all text in this image."}]}]}
req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", json.dumps(body).encode(), {"Content-Type":"application/json"})
print(json.loads(urllib.request.urlopen(req).read())["choices"][0]["message"]["content"])
EOF
# d1 via GenieX
curl -s localhost:18181/v1/decisions -H 'Content-Type: application/json' -d '{"model":"<d1 name>","compute":"cpu","input":"Road closed 17:00-06:00. Landslide danger.","questions":[{"name":"danger","type":"predicate","instructions":"Is this a safety warning?"}]}'
# d1 via decider.py
curl -s localhost:8090/decide -H 'Content-Type: application/json' -d '{"input":"Road closed 17:00-06:00. Landslide danger.","questions":[{"name":"danger","type":"predicate","instructions":"Is this a safety warning?"}]}'
```
`test.jpg` = a phone photo of a prop, or `pdftoppm -r 100 -f 2 -l 2 -jpeg remote_translator_props.pdf test`.

### 14.2 Mock acceptance (before touching real models)
App with `DECIDER=local` and with `DECIDER=geniex` against `tools/mock_servers.py`: non-null category/severity, 9 importances, UI renders banner + ranked list + amber box, `<think>` stripped, zero external requests.

### 14.3 Performance targets
Read ≤ **8 s**/scan on the IQ9 (levers: `MAX_SIDE=768`, `NO_THINK=1`, GenieX `hybrid`/NPU). Decide ≤ **3 s** (levers: GenieX over Transformers, fewer lines). **Do one throwaway scan after starting the servers** (warm-up).

### 14.4 Prop answer key and acceptance matrix
Expected content (Claude-written translations, not native-checked):

| Prop | Key content | **Must** | Nice |
|---|---|---|---|
| **Tibetan trailhead** (Tibetan + Chinese) | Tibetan top line = greeting "Tashi delek". Visitor notice; trailhead, 4,650 m; **no phone signal on route**; **be down by 14:00** (afternoon storms/hail); **headache/vomiting/breathing trouble → descend immediately**; stay out of herders' pastures, beware mastiffs; supplies at checkpoint 5 km (water, oxygen); no fires/camping by lake; rescue 120 | Chinese translated; **Tibetan line in `unreadable`, not translated**; severity ≥ Caution | Warning/Danger; altitude + 14:00 lines in top 3 |
| **Kyrgyz border** (Russian) | Border zone; **entry without permit prohibited**; **permit arranged in advance in Bishkek, up to 10 working days**; no photos of border facilities; no off-road driving; violators detained; border post 3 km | permit lines correct | category rule or prohibition; permit #1–2 |
| **Ladakh pass** (Hindi) | You're at 5,360 m; don't stay > 20 min; breathless/dizzy/headache → descend; **landslide zone ahead, don't cross after 2 pm**; **Inner Line Permit mandatory, show at next check post**; next medical aid 48 km (army camp) | permit + 2 pm translated | both top 3 |
| **Thai trail** | Nature trail 7 km; **no entry after 15:00**; ranger/guide required; closed Jun 1–Oct 31 (landslides); leeches, leech socks; carry trash out; fee **Thai adult 40 baht (written ๔๐)** vs **foreign adult 300 baht** | 15:00 + both fees, ๔๐ → 40 | fee lines flagged |
| **Vietnamese road** | Pass under construction, landslide danger, Km 32–41; **cars/motorbikes banned 17:00–06:00**; slippery in rain, slow, lights, no overtaking; detour left at Km 30 junction (+25 km); **no gas station for 60 km** | ban hours + no fuel | category transport; personal_p high with "on a motorbike" |
| **Arabic desert** | Nature reserve; no camping outside licensed camps; **don't leave marked track (risk of getting lost)**; **last drinkable water 12 km**; >45 °C by day, 5 °C at night; no entry after sunset | water + track | severity ≥ Warning |
| **French menu** + "allergic to shellfish" | Lunch set €24 (service included); onion soup; goat cheese salad (**walnuts**); snails; **bouillabaisse (shrimp, mussels)**; duck confit; veal blanquette; porcini risotto (vegetarian); crème brûlée; tarte Tatin; **Paris-Brest (hazelnut praline)** | bouillabaisse flagged | personal_p high |
| No-text image | — | no crash, sensible summary | — |

Backup set (`translator_demo_props.pdf`): French menu, Japanese izakaya menu (¥300 cover charge "otoshi", shrimp in chawanmushi, buckwheat soba, peanut in tantanmen), Spanish ibuprofen 400 mg box (max 3 tablets per 24 h; contraindications), German rail-replacement notice (no trains Freiburg–Offenburg Nov 14–17, bus at south exit bay 3, no bikes), Italian cookie label (may contain nuts and sesame), French parking sign (no parking Mon–Sat 7–11 except deliveries, towing €135; paid 9–20, free Sundays).

### 14.5 Definition of done (demo-ready)
- [ ] VLM, d1 and app all run **on the IQ9**, laptop Wi-Fi **off**
- [ ] Webcam preview live; 3 scans in a row without restart
- [ ] Tibetan + (Kyrgyz or Ladakh) + French-menu scans meet "Must"
- [ ] Severity banner + What-matters render; fallback note verified by stopping d1
- [ ] Timings visible; UI tells the truth about runtime/compute
- [ ] Backup video recorded; props ordered; script rehearsed

---

## 15. Risks, fallbacks, known unknowns

| Risk | Likelihood | Fallback |
|---|---|---|
| Pre-built code not allowed | ? | Build from §9 at 6:15; mocks first; cut line 7:35 |
| GenieX won't load LFM3-VL (Linux mmproj undocumented) | Med | llama.cpp Path B |
| llama.cpp build slow/fails on IQ9 | Med | workshop binaries → GenieX → last resort VLM on laptop **and say so** |
| GenieX `/v1/decisions` response shape differs | Med | patch `_normalize_answer` via Debug raw; or `DECIDER=local` |
| d1 Transformers too slow on IQ9 CPU | Med | GenieX decisions; cap lines at ~15 |
| VLM misreads non-Latin text from webcam | Med | `MAX_SIDE=1280`, better light, fill the frame, Upload a clean image, demo the props it reads well |
| VLM "translates" Tibetan anyway | Med | strengthen rule 3; demo it last or skip; never claim Tibetan |
| VLM returns non-JSON / truncated | Med | `MAX_TOKENS` ↑, `NO_THINK=1`; parse_error path still shows lines |
| Webcam not detected | Low | `CAMERA=/dev/videoN` → laptop camera via SSH tunnel (§9.6) → Upload |
| Direct Ethernet doesn't come up | Low-Med | IQ9's own display + browser; phone hotspot with **cellular data off** |
| Wi-Fi off before downloads finish | Med | USB stick with models (do downloads before 6:00) |
| Very short demo slot | High | lead with Tibetan; one sentence per point |

### Known unknowns (fill in tonight)
- Pre-built code allowed? → `____`
- IQ9 OS / Python / GenieX preinstalled? → `____`
- SSH user / password / IP → `____`
- `geniex list` names: VL `____` · d1 `____`
- GenieX accepts gguf + mmproj folder for the VLM? → `____`
- Real `/v1/decisions` response sample → paste into §16
- VLM s/scan on IQ9 @ MAX_SIDE 1024 → `____`; d1 s/scan → `____`
- `NO_THINK=1` works / helps? → `____`
- VLM compute unit actually used (cpu/gpu/npu/hybrid) → `____` (pitch only what's verified)

---

## 16. Decision log

| # | Decision | Why |
|---|---|---|
| D1 | Offline camera translator for travelers | Matches the "Wi-Fi off / airplane" theme; simple, legible demo; past winners were simple utilities |
| D2 | General signs + **d1 decides what matters** (not menu/allergy-only) | Broader real problem (safety, permits, closures); uses Liquid's newest model type for a real reason; plain translation is commodity |
| D3 | Don't claim Tibetan/Swati | LFM3-VL-2B lists 16 languages; Liquid judges would catch it; turn it into an **honesty feature** |
| D4 | LFM3-VL-2B QAD-Q4_0 + mmproj Q8_0 | Q4_0 is the Hexagon-preferred precision; Qualcomm benchmarks this model on IQ-9075 |
| D5 | d1 via GenieX `/v1/decisions` first, Transformers fallback | Native Qualcomm path; Transformers is Liquid's documented runtime |
| D6 | d1 on CPU by default | GenieX NPU caps decision questions at 128 tokens on Linux |
| D7 | Webcam on IQ9, laptop as display over Ethernet | Capture + inference visibly on the IQ9; MJPEG avoids browser camera HTTPS rules; the cable survives Wi-Fi off |
| D8 | stdlib Python + one HTML file | Nothing to install or break on ARM Linux; zero external assets |
| D9 | VLM outputs English lines only (no original text) | Fewer generated tokens → faster |
| D10 | Per-line importance = separate d1 predicates in ONE request | One forward pass per question; gives the ranked list + per-line coloring |
| D11 | Name: **rosetta** (lowercase) | Team decision |
| _add rows tonight (results, numbers, changes)_ | | |

---

## 17. Troubleshooting

| Symptom | Fix |
|---|---|
| "Vision model unreachable at …" | VLM server down / wrong `MODEL_URL` / port 8080 vs 18181 |
| Gray "decision model unavailable" | d1 server down or wrong `DECIDER` / `DECIDER_URL` / `D1_MODEL`; the error text says which |
| No severity banner, no error | d1 answer shape unexpected → Debug → raw `d1` → patch `_normalize_answer` |
| All importances null | same, for predicate answers (find the probability key) |
| "didn't return clean JSON" | `NO_THINK=1`, raise `MAX_TOKENS`, check raw VLM output for truncation |
| First scan very slow | warm-up; do a throwaway scan after starting servers |
| Black or no preview | `ls /dev/video*`; `CAMERA=/dev/video2`; camera held by another process |
| Browser camera blocked | use `http://localhost:8000` via `ssh -L 8000:localhost:8000 …` |
| pip "externally managed" | `--break-system-packages` or a venv |
| GenieX `PARAM_NOT_SUPPORTED` | you sent chat completions to d1; d1 only does `/v1/decisions` |
| GenieX decision length error on NPU | `D1_COMPUTE=cpu` |
| Tibetan line gets translated | strengthen SYSTEM_PROMPT rule 3; demo that prop last |

---

## 18. Pitch and judge Q&A

**One-liner:** *rosetta reads any sign with no internet, and tells you which line could hurt you.*

**Claims (only what's verified tonight):** runs entirely on the Qualcomm IQ9 (webcam + LFM3-VL-2B + d1-2B), Wi-Fi off · LFM3-VL reads and translates; **d1 returns calibrated decisions** (severity, category, action required, per-line importance) in a single forward pass, no text generation · **honest by design:** unsupported scripts flagged, never invented · runtime: GenieX [NPU/CPU] / llama.cpp [CPU/GPU] **(fill in the truth)**.

**Likely questions**
- *Why two models?* Generation is good at reading and translating. d1 gives calibrated probabilities for decisions: no tokens, consistent, thresholdable.
- *Why not ask the VLM to rate severity too?* Free-text ratings are uncalibrated and inconsistent; d1 gives ranked probabilities in one pass.
- *Languages?* The 16 LFM3-VL-2B supports; anything else is flagged unreadable.
- *Latency?* Point at the on-screen timer; quote measured numbers only.
- *What's on the NPU?* Answer from §15, truthfully.
- *What's next?* A phone app (LFM3 targets Snapdragon phones), read-aloud of the top warning with LFM3-Audio, d1 thresholds calibrated on real signage, more languages as Liquid adds them.

---

## 19. Stretch goals
Only after §14.5 is fully checked: (1) VLM on NPU/hybrid via GenieX + show the speedup · (2) auto-scan when the frame is stable for 1 s · (3) original text beside each line · (4) kiosk on the IQ9's own display · (5) read-aloud of the top warning via LFM3-Audio-2B (only if trivially available).

---

## 20. Glossary
**IQ9 / IQ-9075 EVK**: Qualcomm Dragonwing edge dev kit · **Hexagon/HTP**: Qualcomm NPU · **Adreno**: Qualcomm GPU · **GenieX**: Qualcomm on-device GenAI runtime (llama.cpp + QAIRT) with an OpenAI-compatible server and `/v1/decisions` · **Genie (old)**: earlier SDK, no IQ-9075 models; not GenieX · **QAD-Q4_0**: Liquid's Q4_0 GGUF (Hexagon-friendly) · **mmproj**: vision projector GGUF a llama.cpp VLM needs · **d1 / system_one**: Liquid's decision model and its one-pass API · **predicate / noul**: yes/no → P(yes) · **choice**: one of N · **score**: ordered levels.

---

## 21. Sources
- Event: https://luma.com/0nsdnkoa · organizer email "Your pre-flight briefing" (Nov 10)
- LFM3: https://www.liquid.ai/blog/lfm3
- LFM3-VL-2B: https://huggingface.co/LiquidAI/LFM3-VL-2B · GGUFs: https://huggingface.co/LiquidAI/LFM3-VL-2B-GGUF/tree/main
- Qualcomm LFM3-VL-2B (IQ-9075 numbers): https://huggingface.co/qualcomm/LFM3-VL-2B
- d1-2B: https://huggingface.co/LiquidAI/d1-2B · https://huggingface.co/LiquidAI/d1-2B-GGUF
- Liquid docs: https://docs.liquid.ai/
- GenieX: https://github.com/qualcomm/geniex · https://geniex.aihub.qualcomm.com/llms-full.txt · https://geniex.aihub.qualcomm.com/en/run/cli/local-server
- IQ9 Genie note: https://dragonwingdocs.qualcomm.com/Ubuntu/ai-workflows/genie
- IQ-9075 specs: https://developer.ridgerun.com/wiki/index.php/Qualcomm_Dragonwing_Technical_Guide/Introduction/Why_the_Qualcomm_Dragonwing_IQ9 · https://dragonwingdocs.qualcomm.com/Hardware-SoCs/IQ-9075
- Past Liquid hackathons: https://www.liquid.ai/en/blog/hack01-hack-the-edge-take-the-dare · https://www.liquid.ai/blog/hack02-lfms-with-eyes-what-happened-who-won-whats-next · https://www.liquid.ai/blog/hack-the-edge-san-francisco-accelerating-whats-possible-with-edge-native-ai

# rosetta: master plan

> **This file is the single source of truth** (`rosetta-master-plan.md`). Every file in the repo is built from this spec by Isaac, Rehan and their coding agents. Read it fully before writing code.
> When reality disagrees with this file (a command fails, an API answers differently, a number turns out wrong), fix the code **and update this file** (§15 known unknowns, §16 decision log) so the other agent sees it.
> Name: **rosetta** (always lowercase). Team: **Isaac** and **Rehan**. Written 2026-11-13 ~17:00 PT; **rev 2 ~17:45 PT:** inference moved to the **ZETIC engine via the Ixian Hexagon SDK** (both models on the Hexagon NPU), and the organizers' starter repo was merged in (rubric, demo format, board access, submission).

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
8. [Runtime: ZETIC Ixian Hexagon SDK](#8-runtime-zetic-ixian-hexagon-sdk)
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
- **Coding agents:** §5, §8, §9, §10, §12 are your spec. Build in the **priority order of §9.12**. Use the **reference code** in §9: the C++ files were syntax-checked against the real SDK 0.2.2 headers, and the Python files are designed to run against the mocks. Don't re-derive it.
- **Priorities:** **P0** = demo can't happen without it · **P1** = what makes it win · **P2** = polish. Never start P1 while a P0 is broken.
- **Ownership:** Isaac's agent owns the **model/runtime side**: `engine/`, the IQ9 setup, the `app.py` pipeline functions (`read_and_translate`, `decide`, `Engine`, normalizer, constants). Rehan's agent owns the **app shell and UX**: the `app.py` HTTP/camera/log layer, `index.html`, mocks, demo, and the submission. Shared file = `app.py`; coordinate edits (§12).
- **Organizers' starter repo:** <https://github.com/heath0xFF/cleared-for-takeoff-hackathon>, written by Heath Blandford (Qualcomm DevRel, **one of the judges**). Clone it on the laptop (`~/cft`). **On event logistics (board access, demo format, submission), the starter repo and organizers win over this file.** We use our own repo and vendor three MIT-licensed files from it (§9.1).
- **Pre-building:** the rules don't say whether code written before 6:15 is allowed. **Ask an organizer at 5–6 PM.** If it isn't, everything in §9 gets built 6:15–8:00 from this spec. That's feasible with agents, which is why the spec is this detailed.

---

## 1. TL;DR

- **rosetta:** point a webcam at any foreign-language sign, notice, menu, label or medicine box. It **translates** the text, then **decides what matters**: how serious it is, what you must do, which lines are critical. **Zero internet.**
- **Two Liquid models, both on the IQ9's Hexagon NPU through ZETIC's engine (Ixian Hexagon SDK):**
  1. **LFM3-VL-2B** (`ZETIC-ai/LFM3-VL-2B-IQ9`): photo → English lines, a list of scripts it couldn't read, and an answer to the user's optional question.
  2. **d1-2B** (`ZETIC-ai/d1-2B-IQ9`, Liquid's decision model): **one call** over the translation returns calibrated probabilities for **category**, **severity (5 levels)**, **action required**, **affects you**, and **importance of every line**. No tokens are generated: 16 questions per NPU pass, ~0.1 s a pass.
- **Watch mode (always-on, P1-late):** the IQ9 watches the camera and scans automatically when a new sign holds still. d1 acts as the gate, and code raises an alert only when it matters. This targets the flagship **Always-On Local Agent** track.
- **Story:** "Trekking on the Tibetan Plateau, no signal, there's a sign. rosetta reads it, flags it as a *Danger*-level notice, puts 'descend immediately if you get a headache' at the top, and honestly tells you which line it *couldn't* read."
- **Build window ≈ 2 hours (6:15–8:15 PM). Submit 8:00–8:30. Two-minute demo: we switch the board's Wi-Fi off in front of the judge, then run it.**

---

## 2. The event

**On-Device AI Hackathon: Cleared for Takeoff ✈️** (Qualcomm × Liquid AI)

| Item | Detail |
|---|---|
| When / where | Fri **Nov 13, 2026** · **555 Mission St, San Francisco** · 5:00–9:00 PM PT |
| Schedule | 5:00 doors, food · **6:00 on-device AI workshop** · **6:15 build starts** · **8:00 submissions open** · **8:15 build ends, Wi-Fi off, showcase + judging + awards** |
| Hardware | One **Dragonwing IQ-9075 EVK** per team. It arrives with a **fresh Ubuntu 24.04 install and nothing else** (no GenieX, no torch, no weights). Sensors are **BYO**, and **we have a USB webcam**. |
| Board login | **`ubuntu` / `liquidxqualcomm`** (UART and SSH). Upstream `ubuntu/ubuntu` is **not** the event login. If a password-change prompt appears, ask organizers; never reflash. |
| Media | Teams receive **USB drives with model assets** (probably GenieX GGUFs; check for ZETIC packages). **Copy, never move or modify** anything on the drive. Bring **USB-C adapters**. |
| Models | Any **LFM3-family** model |
| Team | Isaac + Rehan (max 4) |
| Prizes | 1st: IQ9s · 2nd: Uno Qs |
| Judges | **Piotr Mazurek, Tianshu Yu, Alex Yuan** (MTS, Liquid AI) · **Charles Coudsi** (Senior Staff Engineer, Qualcomm) · **Heath Blandford** (DevRel, Qualcomm; wrote the starter repo) |

### Scoring rubric (starter repo `docs/judging.md`)
| Weight | Criterion | How rosetta scores |
|---|---|---|
| **25%** | **Edge-native value**: why is this better, or only possible, on-device? | Trekkers have **no signal** exactly where signs matter; photos of medicine, permits and IDs stay private |
| **20%** | **Technical execution**: reliability, integration, local operation | Two models resident on the NPU via ZETIC, fail-soft pipeline, JSONL log, offline-proven |
| **20%** | **Originality**: not another generic chatbot | Translate **+ triage** with d1's calibrated decisions, **honest "couldn't read"** |
| **15%** | **Real-world usefulness**: clear user, real need, next step | Travelers in no-data zones; next step is a phone app (LFM3 + ZETIC target Snapdragon phones) |
| **10%** | **Performance / efficiency** | On-screen TTFT, tok/s, d1 ms/pass, peak memory |
| **10%** | **Demo quality**: concise, clear offline demonstration | 2-minute script (§4), Wi-Fi off live, visible timer, backup video |

**Pillars:** 01 *The Network Has Crashed* (main constraint: our core) · 02 *Always-On Local Agent* (flagship track: watch mode) · 03 *Tiny Agent Olympics* (performance and multimodal: VLM + d1 on the NPU, metrics).

**The first judge question will be: "Why should this not simply be a cloud API call?"** Answer with a **specific constraint** (§18). "It runs on-device" is not an answer.

### Demo format (starter repo)
- **2 minutes per team + 1 judge question.**
- **Turn the board's Wi-Fi off in front of the judge** and unplug any Ethernet, from a session that doesn't depend on Wi-Fi (the **micro-USB UART console** or an **isolated USB-C link**):
  ```bash
  sudo nmcli radio wifi off
  nmcli -p device              # show the judge Wi-Fi is disconnected
  ```
  Over SSH-on-Wi-Fi this command kills your own session. **Rehearse it once.** `sudo nmcli radio wifi on` restores it.
- Show **local inputs, decisions, executed actions and errors from the app's log** (our JSONL, §9.2).
- Have a **visible timer, local sample data (printed props + saved images), and a backup recording**.
- Organizers **review submitted code for anything that calls a service outside the board**.

### Submission (8:00–8:30 PM, form: <https://submissions.loggia.sh/events/cleared-for-takeoff>)
Both links are required:
1. **Public GitHub repo** (ours; push early, flip to public before 8:00).
2. **Arduino Project Hub post** (<https://projecthub.arduino.cc/>) with the **full write-up and the code**, not just a link. **It needs an Arduino account: sign in before 8:00. Draft the post before the event.**

**Implications**
- 3 of the 5 judges are Liquid engineers who know LFM3's language list and limits, so **never overclaim**. Using **d1** for a real reason is a differentiator.
- The Qualcomm judges care that it **visibly runs on the IQ9's NPU**. Running both models on the NPU via ZETIC is our strongest technical story. Back it with **device evidence** from the logs (§8.5), and don't claim "100% NPU" (§18).
- Past Liquid hackathon winners were **simple, single-purpose, obviously useful**. **Keep the story tight.**

---

## 3. Product

### Problem
Travelers with **no data** (mountains, deserts, rural roads, border zones, flights, roaming) hit text they can't read that **actually matters**: closures, curfews, permit rules, altitude warnings, last water or fuel, dosage limits, cover charges, allergens. Cloud translators fail exactly when you're most isolated. Even when they work, they return a wall of text without telling you *which line could hurt you*.

### Solution
**rosetta = offline translate + triage.**
1. **Read & translate** everything (LFM3-VL-2B on the NPU).
2. **Decide what matters** (d1-2B on the NPU): severity banner, ranked "What matters" list with calibrated %, per-line color coding, and "action required" / "affects you" probabilities.
3. **Never guess** unreadable scripts. Say so explicitly (amber box).
4. Optional **"About you"** (e.g. "on a motorbike", "allergic to shellfish", "no permit") personalizes the ranking.
5. Optional **question** ("Can I hike this afternoon?"), answered from the text only.
6. **Watch mode** (P1-late): hands-free. A new sign held steady triggers a scan, and **code** decides whether to alert (severity ≥ Warning, or a calibrated per-line threshold). Every decision lands in the JSONL log.

### Why on-device is the point
- **Offline:** the scenario has no connectivity, which is the event's theme.
- **Latency:** seconds on a 2B model on the NPU, with no round trip.
- **Privacy:** photos of medicine, permits, tickets and IDs never leave the device.
- **Cost:** no per-call inference bill.

### Non-goals (do not build)
Speech in/out, AR overlays, multi-turn chat, accounts, cloud sync, history DB, maps, mobile packaging, fine-tuning, support for languages LFM3-VL-2B doesn't support (we **detect and admit** those instead), and medical/legal advice beyond the text.

---

## 4. Demo script

**Table setup:** IQ9 + USB webcam on a stand pointing down at the table · laptop browser on `http://127.0.0.1:8000` through an **SSH tunnel over the isolated USB-C link** (§11.6) · **UART console open in a second laptop window** (this is where Wi-Fi goes off) · `tail -f logs/rosetta.jsonl` visible · printed props · phone timer · backup video on a phone.

### Props
Two printable PDFs were made earlier (separate from this repo): **`remote_translator_props.pdf`** (primary) and **`translator_demo_props.pdf`** (backup). Print in color, flat, no glare, **large type** (the model sees 512×512, §6). Contents and expected outputs are in §14.4. Primary set:
1. French bistro menu (safe opener)
2. **Tibetan Plateau trailhead:** Tibetan greeting on top + Chinese body (**hero**)
3. Northern Thailand trail sign (Thai)
4. Ha Giang Loop road notice (Vietnamese)
5. Ladakh high pass (Hindi)
6. Kyrgyzstan border zone (Russian)
7. Desert reserve (Arabic)

### 2-minute script
1. **Network off (15 s):** in the UART window: `sudo nmcli radio wifi off && nmcli -p device`. "The board is now offline. Everything you'll see runs on this IQ9's Hexagon NPU."
2. **Hook (10 s):** "No signal on a trek, and a sign could be the difference between a nice hike and a rescue."
3. **Hero scan (30 s):** Tibetan trailhead. Question: "Can I hike this afternoon?" → **Scan**.
   - Point at: **red Danger/Warning banner** with d1 confidence → **What matters**, led by altitude sickness / be down by 14:00 / no signal → amber **"Couldn't read (not guessing): Tibetan line"** → the answer → metrics strip (`NPU · read 4.1 s · TTFT 0.2 s · 55 tok/s · d1 0.2 s, 2 passes`).
   - Line: "Two Liquid models, both on the NPU through ZETIC's engine. LFM3-VL reads and translates. **d1 decides what matters** with calibrated probabilities, no text generation. And when it can't read Tibetan, it *says so* instead of hallucinating."
4. **Watch mode (25 s, if built):** toggle **Watch**, slide the Kyrgyz border sign (Russian) under the camera, hands off. It auto-scans, d1 → "rule or prohibition", the permit line goes to the top, an alert fires, and a new JSONL line appears. "Always-on: it only alerts when d1 says it matters."
   *Otherwise:* a second manual scan (Kyrgyz or Ladakh).
5. **Log (10 s):** point at the JSONL tail: input, decision, action, timings, errors.
6. **Close (10 s):** "No cloud, no data plan, no inference bill. LFM3-VL-2B + d1-2B on the Dragonwing IQ9, ZETIC Ixian Hexagon SDK." **State only what's verified.**
7. **Judge question (remaining):** "why not cloud?" → §18.

If a scan misreads, move to the next prop. Never debug live.

---

## 5. Architecture

```
┌──── Laptop (display only) ─────┐  isolated USB-C link   ┌──────────────────────────── Qualcomm IQ9 (all compute) ────────────────────────────┐
│ Browser → 127.0.0.1:8000       │  ssh -L 8000:...:8000  │ app.py 127.0.0.1:8000 (Python stdlib HTTP server)                                    │
│ live preview (MJPEG)           │───────────────────────►│  ├─ USB webcam (OpenCV thread) → /stream ; watch loop (P1-late)                       │
│ Scan · Watch · About · Ask     │                        │  ├─ image prep → exactly 512×512 PNG in /dev/shm (SDK does not resize)                │
│ results · metrics · log        │  UART console (micro-  │  ├─ Engine "vlm" ──JSONL pipe──► engine/build/rosetta_vlm  (resident LFM3-VL-2B, NPU)  │
│ UART window: nmcli wifi off    │  USB) for Wi-Fi off    │  │                          or   tools/zetic_run.py → zetic_lfm3_cli (one-shot, P0)   │
└────────────────────────────────┘                        │  ├─ Engine "d1"  ──JSONL pipe──► $IXIAN_SDK/bin/zetic_d1_cli serve (resident d1-2B, NPU)│
                                                          │  └─ logs/rosetta.jsonl (flushed per scan) + logs/img/<scan>.png                        │
                                                          └──────────────────────────────────────────────────────────────────────────────────────┘
```

**Why pipes, not HTTP:** the Ixian SDK has **no HTTP server** and allows **one active model per process**. ZETIC's own `zetic_d1_cli serve` uses JSON Lines over stdin/stdout, so we use the same pattern for the VLM (`rosetta_vlm`, ~120 lines of C++ in §9.5). `app.py` owns both child processes and restarts them if they exit.

### Per-scan pipeline (sequential: VLM, then d1)
1. **Capture:** latest webcam frame (or an uploaded image) → **center square crop → resize to exactly 512×512** (`CROP=center`; `letterbox` optional) → PNG in `/dev/shm/rosetta/` (plus a copy in `logs/img/`).
2. **Read & translate (LFM3-VL-2B, NPU):** system prompt §9.3 + image path → JSON `{"languages","summary","lines","unreadable","answer"}`. Thinking **off** (SDK default), greedy, `max_tokens` capped. **Validate:** status Ok, `finish` = Stop, >0 tokens, non-empty text (§12 rule 2). Strip stray `<think>` and code fences; on parse failure, fall back to raw lines plus `parse_error`. Cap at `MAX_LINES` (24).
3. **Decide (d1-2B, NPU):** state = numbered English lines. Questions in d1's native schema (§9.4): `category` (choice), `severity` (score, 5 levels), `action` (noul), `personal` (noul, only if About-you is set), `line_i` (noul per line). ≤ 28 questions → **2 NPU passes**.
4. **Normalize** answers → `{p}` / `{value,confidence}` / `{index,label,confidence,probabilities}`.
5. **Gate + act (code, not the model):** `alert = severity.index ≥ ALERT_SEVERITY or max(importance) ≥ IMPORTANCE_THRESHOLD` → action `ui_alert` (banner + local beep in watch mode).
6. **Log** one flushed JSONL record: input, VLM result/timings, d1 answers/timings, decision, action, errors.
7. **Render** (§9.9).
8. **Fail soft:** d1 down → translation still shows with a gray notice. VLM down → clear error. Camera missing → upload still works. An engine crash → auto-restart on the next call. **No exception kills the server.**

---

## 6. Models

Checked against Liquid, ZETIC, Qualcomm and Hugging Face pages on 2026-11-13 (links in §21).

### LFM3 family (released Oct 27, 2026)
Six open-weight ~2B models on one backbone: LFM3-1.7B (text), **LFM3-VL-2B** (text+image+video → text), LFM3-Audio-2B, LFM3-Omni-2B, and decision models **d1-2B** and d1-Omni-2B. ZETIC publishes all six as IQ9 NPU packages.

### LFM3-VL-2B: reader/translator, `ZETIC-ai/LFM3-VL-2B-IQ9`
- Upstream: 1.92B params, in-house vision encoder, optional reasoning mode (**off by default in the ZETIC SDK**).
- **Supported languages (upstream model card):** English, Arabic, Chinese, French, German, Italian, Japanese, Korean, Portuguese, Spanish, Vietnamese, Thai, Indonesian, Hindi, Russian, Polish. That's **16**.
  - **Not supported:** Tibetan, Swati, Nepali, Kyrgyz, etc. The Tibetan prop is built around this: correct behavior = translate the Chinese, flag the Tibetan as unreadable.
- Model card: "not recommended for coding, multi-turn conversations, or complex reasoning." We do single-turn reading, so that's fine.
- **ZETIC package:** 4-bit block-quantized LM, fp16 vision encoder. Public, **ungated**. Starter-repo pin: revision `4b97823becd3c17a050aef419924af48075eb199`.
  - `v73/`: both NSPs, **3.10 GB**, default. Context 2,048 by default, up to 131,072.
  - `v73-1nsp/`: one NSP, **2.36 GB**. Context up to 4,096. Leaves the other NSP free (insurance for running d1 alongside, §15).
- **ZETIC-reported on IQ9:** image → first token **~200 ms** (vs 710 ms llama.cpp), generation **~59 tok/s** (vs 39). Two-NSP; one NSP ~52 tok/s. **Vendor numbers. Measure our own.**
- **⚠ Images must be exactly 512×512 RGB.** The SDK does not resize, letterbox or tile; any other size → `Status::InvalidArgument`. One image = **256 context rows**. **Small text on a 512 px sign is the #1 quality risk.** Levers: fill the frame, center-crop rather than letterbox, large-type props, and P2 multi-tile mode (§19).
- **Default sampling** (package manifest): temperature 0.1, top-k 50, repetition penalty 1.1. We send **temperature 0** (greedy, NPU argmax) for repeatable demos.

### d1-2B: "what matters" decider, `ZETIC-ai/d1-2B-IQ9`
- Upstream: built on LFM3-VL-2B. **Not a chat model:** decisions in **one pass, no token generation**. Inputs: text and images.
- **ZETIC package `v73/`:** 8-bit LM, fp16 vision, **2.21 GB**, **runs on one NSP**. Ungated. Starter pin: revision `c82c9736e92a3cafcfbac7625ead99ad99138a89`. Ships `calibration.json`; the SDK applies temperature calibration to `probs` by default.
- **Question types** (`zetic_decision.h`, same as Liquid's HF API): `noul` (yes/no → P(yes)) · `choice` (label → description map; `multiple` allowed) · `score` (ordered levels, lowest first → median index + `legend`).
- **Pass budget:** **up to 16 questions per NPU pass**. State + media + that pass's questions must fit **2,048 rows on SDK 0.2.2** (**1,024 on 0.2.1**; with 0.2.1 use `--set-size 8`). More questions → more passes.
- **ZETIC-reported:** ~96 ms per call (demo ticket). Starter-repo measurements with d1-Omni: 117 tokens → 70 ms; with an image → 286 ms.
- **"Probabilities, not verdicts"** (ZETIC's own README): don't read every P(yes) against a fixed 0.5. **Calibrate thresholds on our own props** (§9.11). The starter repo hasn't board-verified the ZETIC d1 route; ZETIC has (release notes).

### Upstream GGUFs (Mac prompt-tuning only, never the demo)
`LiquidAI/LFM3-VL-2B-GGUF` → `LFM3-VL-2B-QAD-Q4_0.gguf` (1.05 GB) + `mmproj-LFM3-VL-2B-Q8_0.gguf` (203 MB). Used with `llama-server` on the Mac to tune the prompt **on 512×512 inputs** before we have the board (§11.7).

### Not using
LFM3-Audio/Omni (stretch only, §19), fine-tuning, GenieX GGUFs on the board (emergency fallback only, §8.6).

---

## 7. Hardware

**Qualcomm Dragonwing IQ-9075 EVK** (starter repo `docs/hardware.md`)
- **QCS9075** · 8-core Kryo CPU · **Hexagon v73 NPU (HTP), two NSPs** · Adreno 663 GPU · **36 GB LPDDR5** · **Ubuntu 24.04 aarch64** · Python 3.12. The board has `git`, `python3`, `g++`, but **no `pip`, `hf` or `gh`**.
- **NPU access** = FastRPC device nodes `/dev/fastrpc-cdsp` and `/dev/fastrpc-cdsp1`, which need **read and write** access: package `qcom-fastrpc1` (udev rules) + user in group `fastrpc` (§11.3). ZETIC's binaries use the board's `/usr/lib/aarch64-linux-gnu/libcdsprpc.so.1` and need glibc ≥ 2.35.
- **⚠ Monitor warning (organizers):** the current Adreno APT update breaks external monitors. **Do not install or update `qcom-adreno1`**, and do not run Qualcomm's `install_ppa_pkgs.sh`. SSH is unaffected. We're headless anyway.
- **Access:** **micro-USB debug UART** (data-capable cable; second FTDI port "Converter B", 115200 baud; macOS `screen /dev/cu.<node> 115200`) → configure Wi-Fi with `nmcli` → SSH. During the demo: UART + an isolated **USB-C network link** (§11.6).
- Webcam → `/dev/video*`.

---

## 8. Runtime: ZETIC Ixian Hexagon SDK

### 8.1 What it is
- **ZETIC's own Hexagon runtime ("the ZETIC engine")**, shipped as the **Ixian Hexagon SDK** for the Dragonwing IQ9. The SDK was renamed from "ZETIC.MLange Hexagon" in 0.2.1 (namespace `zetic::mlange` → `zetic::ixian`, library `libzetic_mlange_hexagon.so` → `libzetic_ixian_hexagon.so`). ZETIC.MLange is the company's broader on-device platform.
- Runs the LFM3 family and d1 on the **Hexagon NPU**. Some work (e.g. the LM head / sampling) stays on the CPU, so **never say "entirely on the NPU."**
- **Runs on the IQ9 only.** On any other device, loading fails with `Status::Unsupported`, so there's **no Mac testing of the SDK** (use mocks, §9.10).
- Distributed as binaries: <https://github.com/zetic-ai/IxianHexagon/releases>. Models: <https://huggingface.co/collections/ZETIC-ai/lfm3-and-d1-on-dragonwing-iq9>.

### 8.2 Versions
| SDK | Released | SHA-256 (tarball) | Notes |
|---|---|---|---|
| **0.2.2** (default) | 2026-11-13 | `0eec13f5ff8464f7ea7f9a8982042df249119aa01605327a4e3fe98e8fbecb05` | d1 passes up to **2,048 rows**; adds `examples/d1_quickstart`. Library otherwise as 0.2.1. **Headers used for §9.5.** |
| **0.2.1** (fallback) | 2026-11-12 | `afb426755bb793efd929fc1a8e37fb7a5bd2ff3133576d5f3e22de8bb7fe8b0b` | The version the starter repo ran on the IQ9. d1 passes 1,024 rows. Same API. |

URL pattern: `https://github.com/zetic-ai/IxianHexagon/releases/download/<v>/ixian-hexagon-<v>-linux-arm64-qcom-iq9.tar.gz` (+ `.sha256`). Model packages are unchanged across 0.2.x.

### 8.3 SDK layout
| Path | Content |
|---|---|
| `lib/libzetic_ixian_hexagon.so` | SDK library (C++ API: `LLM`, `Decision`) |
| `lib/libhexrt_v73_skel.so` | DSP library: keep it next to the SDK lib, or pass `native_lib_dir` / `--lib-dir` |
| `include/` | `zetic_llm.h`, `zetic_decision.h`, `zetic_media.h`, `zetic_types.h`, `zetic_selection.h` |
| `lib/cmake/IxianHexagon/` | `find_package(IxianHexagon 0.2 CONFIG REQUIRED)` → target `zetic::ixian_hexagon` |
| `bin/zetic_lfm3_cli` | `chat \| eval \| bench \| info` · `chat --model <dir> [--system S] [--media a.png] [--temp T] [--max-tokens N] [--think]`, common `--target vNN --lib-dir --ctx --verbose` |
| `bin/zetic_d1_cli` | `info \| demo \| ask \| serve \| seq` · **`serve --model <dir>`** = JSON Lines in/out (one request per stdin line), common `--target --lib-dir --set-size N --no-calibrate --verify --verbose` |
| `bin/zetic_quickstart`, `bin/zetic_d1_quickstart` | prebuilt smoke tests |
| `examples/quickstart`, `examples/d1_quickstart` | CMake example sources |

### 8.4 C++ API (what we use)
```cpp
#include <zetic_llm.h>          // LLM, Message, Part, Image, GenerationConfig, Response
#include <zetic_decision.h>     // Decision, Question, State, DecisionResult
using namespace zetic::ixian;

LLM::Options opt; opt.max_context = 4096; opt.target = "";        // "" = v73 (two NSPs); "v73-1nsp" = one NSP
LLM vl = LLM::fromPath("models/lfm3-vl-2b", opt);                  // throws zetic::ixian::Error on load failure
GenerationConfig g; g.temperature = 0; g.max_tokens = 768;         // enable_thinking defaults to false
Response r = vl.chat({Message::System(SYS),
                      Message::User({Part::Img(Image::fromFile("/dev/shm/rosetta/scan.png")),   // must be 512x512
                                     Part::Text(prompt)})}, g);
// r.status, r.error, r.text, r.finish_reason, r.usage.{prompt_rows,cached_rows,completion_tokens},
// r.timings.{ttft, encode, prefill, decode, tokens_per_second}  (ms)

Decision d1 = Decision::fromPath("models/d1-2b");
DecisionResult out = d1.systemOne(State::Text(lines), {
    {"category", Question::Choice("...", {{"safety warning", "danger, hazard..."}, /*...*/})},
    {"severity", Question::Score("...", {"Just information", /*...*/ "Danger: ..."})},
    {"action",   Question::Noul("...")}});
// out.answers[i] = {name, Answer{noul, choice, confidence, score, legend, labels, probs}}; out.passes; out.timings.prefill
```
- Requests **never throw**: check `Response::status` / `DecisionResult::status`. Factories (`fromPath`, `Image::fromFile`) **throw** `Error`. Check both.
- `Status::DeviceError` → call `reload()` on the object (or restart the process).
- **One active model per process.** Destroy the object to free the NPU.

### 8.5 Device evidence (what proves NPU execution)
- The CLIs with `--verbose` print a load line containing **`hexrt open … v73 … HEXRT_NSP2=1`** (two-NSP generator) and `loaded <package> v73`. The starter repo's wrapper treats a missing line as a failure.
- Our engines print a ready event with `target`, `nsp_count`, `soc`, `sdk_version` from `ModelInfo`, and `app.py` shows it in `/status` and the UI header.
- ZETIC doesn't use GenieX's `HTP0` label, so don't look for it.

### 8.6 Emergency fallback (NOT the plan)
Only if the ZETIC SDK won't load after the **20-minute time-box**, and the pitch then says so:
- **VLM:** GenieX v0.10.0 + `LiquidAI/LFM3-VL-2B-GGUF` (or the organizers' USB drive model) behind `geniex serve` → `tools/openai_vlm_bridge.py` (§9.10) speaks our VLM JSONL protocol to it. Install per the starter repo §3.3 (`sh install.sh --version v0.10.0`). **No `qcom-adreno1`.**
- **d1:** `DECIDER=none` (translation only, gray notice). The starter repo's reference d1 is Transformers on CPU (`examples/system-one-decision`), but that's a torch install we shouldn't need.

---

## 9. Build spec

### 9.1 Repo layout to create
```
rosetta/
├── rosetta-master-plan.md   ← this file
├── README.md                what it is, how to run, measured metrics (judges read this)
├── AGENTS.md, CLAUDE.md     "Read rosetta-master-plan.md first." + §12 rules (3–5 lines)
├── app.py                   web server + camera + JSONL log (stdlib; OpenCV optional)
├── pipeline.py              model pipeline + Engine supervisor (Isaac-owned boundary)
├── index.html               single-file UI, no external assets
├── engine/
│   ├── CMakeLists.txt       builds rosetta_vlm (+ rosetta_d1) against the Ixian SDK
│   ├── rosetta_vlm.cpp      resident LFM3-VL-2B, JSONL stdin/stdout (P1)
│   ├── rosetta_d1.cpp       resident d1-2B, same protocol as zetic_d1_cli serve (P2, only if needed)
│   └── third_party/nlohmann/json.hpp   (staged before the event; fallback if apt lacks nlohmann-json3-dev)
├── tools/
│   ├── mock_engine.py       fake VLM / d1 engines speaking the JSONL protocols (Mac dev)
│   ├── zetic_run.py         VENDORED from starter repo examples/zetic-lfm/run.py (MIT): one-shot CLI, P0 VLM path
│   ├── offline_audit.py     VENDORED from starter repo skills/iq9-offline-rehearsal/scripts/ (MIT)
│   ├── openai_vlm_bridge.py VLM JSONL ↔ OpenAI chat server (Mac llama-server tuning; emergency GenieX)
│   ├── calibrate.py         picks IMPORTANCE_THRESHOLD from logged prop scans + labels (P2)
│   ├── make_labels.py       §14.4 Must check per scan + drafts labels.json (answer key: prop_key.json)
│   └── metrics.py           README median table from logs/rosetta.jsonl (+ peak RSS via /status)
├── scripts/
│   ├── preflight.sh         VENDORED from starter repo skills/iq9-preflight/scripts/ (MIT)
│   ├── stage_zetic.sh       laptop: download SDK + pinned ZETIC packages (+ checksums)
│   ├── setup_board.sh       board: apt packages, fastrpc group check, build engine (prints sudo cmds)
│   └── run.sh               board: env + `python3 app.py` (engines are started by app.py)
├── logs/                    rosetta.jsonl + img/ (NOT gitignored: judges may look; keep it small)
├── .gitignore               models/  sdk/  engine/build/  __pycache__/  *.pyc  .DS_Store  *.part
├── models/                  (gitignored) lfm3-vl-2b/v73/…, d1-2b/v73/…
└── sdk/                     (gitignored) extracted ixian-hexagon-0.2.2-linux-arm64-qcom-iq9/
```
Vendored files keep their MIT header + a line `# Vendored from heath0xFF/cleared-for-takeoff-hackathon (MIT)`.

### 9.2 `app.py`: requirements
- **Python stdlib only** (`http.server.ThreadingHTTPServer`, `subprocess`, `queue`, `threading`, `json`, `base64`, `shlex`). **OpenCV optional** via `try: import cv2, numpy as np except ImportError: cv2 = None`. On the board: `sudo apt install python3-opencv`; no pip needed.
- Config via env vars (§10.6). Serve `index.html` from the same directory. Bind `HOST=127.0.0.1` by default (laptop reaches it via SSH tunnel).
- Routes: `GET /` · `GET /status` · `GET /stream` · `POST /scan` · `GET /log?n=20` · `POST /watch` · `GET /latest` (contracts in §10).
- **Engines:** two `Engine` instances (`vlm`, `d1`) started **sequentially in a background thread at startup** (VLM first, then d1) so the first scan is warm. `VLM_MODE=engine` → `Engine(VLM_CMD)`. `VLM_MODE=cli` → no child process; each scan calls `tools/zetic_run.run(...)`. `VLM_MODE=mock` / `D1_CMD=python3 tools/mock_engine.py d1` for the Mac.
- **Camera:** background thread reads `cv2.VideoCapture(CAMERA)` (int index or `/dev/videoN`), requests 1280×720, keeps the latest frame under a lock. If OpenCV is missing, `CAMERA=none`, or open fails, run with `server_camera=false`. `/stream` = MJPEG (`multipart/x-mixed-replace; boundary=frame`), ~14 fps, 960 px, q70, **with the 512 crop square drawn on it** so users frame the sign. Swallow `BrokenPipeError`/`ConnectionResetError`.
- **Image prep (reference):**
```python
def to_model_image(img):
    """BGR ndarray -> exactly 512x512 BGR. The SDK rejects any other size and never resizes."""
    h, w = img.shape[:2]
    if CROP == "center":                       # default: square from the middle = more pixels on the sign
        s = min(h, w); y, x = (h - s) // 2, (w - s) // 2
        return cv2.resize(img[y:y + s, x:x + s], (512, 512), interpolation=cv2.INTER_AREA)
    scale = 512 / max(h, w)                    # letterbox: whole frame, black bars
    img = cv2.resize(img, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((512, 512, 3), np.uint8)
    y, x = (512 - img.shape[0]) // 2, (512 - img.shape[1]) // 2
    canvas[y:y + img.shape[0], x:x + img.shape[1]] = img
    return canvas

def save_model_image(img, scan_id):
    """PNG (lossless: text edges matter) in /dev/shm for the engine + a copy in logs/img for the judges."""
    os.makedirs(SHM_DIR, exist_ok=True); os.makedirs("logs/img", exist_ok=True)
    path = os.path.join(SHM_DIR, f"scan-{scan_id}.png")
    cv2.imwrite(path, img); cv2.imwrite(f"logs/img/{scan_id}.png", img)
    return path
```
  Uploaded data URLs arrive **already 512×512 PNG from the browser** (§9.9). If `cv2` exists, decode and pass through `to_model_image` anyway; if not, write the bytes as-is.
- **Engine supervisor (reference, use verbatim):**
```python
class Engine:
    """One ZETIC model per process (SDK limit). JSON Lines over stdin/stdout. Restarts on exit or timeout."""
    def __init__(self, name, cmd, timeout):
        self.name, self.cmd, self.timeout = name, cmd, timeout
        self.proc, self.q, self.ready, self.n, self.lock = None, None, None, 0, threading.Lock()

    def _start(self):
        env = dict(os.environ, LD_LIBRARY_PATH=f"{IXIAN_SDK}/lib:" + os.environ.get("LD_LIBRARY_PATH", ""))
        self.proc = subprocess.Popen(shlex.split(self.cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=None, text=True, bufsize=1, env=env)   # stderr → app console (device logs)
        self.q = queue.Queue()
        threading.Thread(target=self._pump, args=(self.proc, self.q), daemon=True).start()
        self.ready = self._next(ENGINE_LOAD_TIMEOUT)          # first line: {"event": "ready", ...}
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
            except Exception:
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
```
  If loading fails with `DeviceError … map: 0x1` (DSP still releasing after another NPU process), wait 3 s and retry once.
- `/scan` = `read_and_translate()` → `decide()` (wrapped in try/except so d1 failure returns `decision: {"error": ...}`) → `gate()` → `log_scan()`. Attach `_image` (data URL of the 512 PNG the model saw) and `_metrics`.
- **JSONL log (reference shape):** append one line to `logs/rosetta.jsonl` per scan, `flush()` + `os.fsync()`, under a lock:
```json
{"ts": "2026-11-13T19:42:03.512-08:00", "scan_id": 12, "trigger": "button|watch|upload",
 "input": {"source": "webcam", "image": "logs/img/12.png", "about": "on a motorbike", "question": ""},
 "vlm": {"ok": true, "mode": "engine", "seconds": 4.1, "ttft_ms": 212, "tok_s": 55.3, "completion_tokens": 263,
         "finish": "Stop", "lines": 9, "unreadable": 1, "parse_error": false},
 "d1": {"ok": true, "seconds": 0.21, "passes": 2, "category": "safety warning", "severity": 4,
        "action_p": 0.96, "top": [[5, 0.97], [4, 0.91], [3, 0.83]]},
 "decision": {"alert": true, "reason": "severity 4 >= 3"},
 "action": {"type": "ui_alert", "executed": true},
 "errors": []}
```
  Proposals vs actions: the models only *propose* (lines, probabilities). `decision`/`action` are **code's** records.
- Error mapping: no image → 400 · no frame yet → 503 · VLM engine down/timeout → 502 with the engine name · anything else → 500. **Never let the server die.**
- Startup log prints the VLM mode/cmd, d1 cmd, camera status, app URL, then each engine's ready event.
- **Watch loop (P1-late, B10):** thread, active only when `/watch {"on": true}`. Every 250 ms: gray 160×90 thumbnail of the latest frame. **Trigger** when the mean abs diff vs the last *scanned* thumbnail is > `WATCH_CHANGE` (12) **and** the frame has been stable (diff vs previous < 3) for `WATCH_STABLE_S` (1.2 s) **and** the Laplacian variance (sharpness) is > `WATCH_SHARP` (60). Never while a scan is running; min 3 s between scans. Results go to `/latest` (UI polls every 500 ms); `trigger: "watch"` in the log.

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
**User text** (only non-empty parts):
```python
user_text = []
if about:    user_text.append("About the traveler: " + about)
if question: user_text.append("Traveler's question: " + question)
user_text.append("Read and translate all text in this image. Respond with the JSON object only.")
prompt = "\n".join(user_text)
```
**`VLM_MODE=engine`** → `VLM.call({"system": SYSTEM_PROMPT, "prompt": prompt, "images": [png_path], "max_tokens": MAX_TOKENS, "temperature": 0, "think": THINK})` (protocol §10.4).
**`VLM_MODE=cli`** (P0, no compile) → `zetic_run.run(IXIAN_SDK, VL_MODEL, SYSTEM_PROMPT + "\n\n" + prompt, image=png_path, max_tokens=MAX_TOKENS, timeout=VLM_TIMEOUT)`. The wrapper has no `--system`, so the system prompt is prepended. It reloads the model on every call (**~3.3 s extra**), forces `v73` two-NSP and ctx 2048, and returns `{ok, text, completion_tokens, finish_reason, timings{runtime_ttft_ms, runtime_decode_tok_s, model_load_ms, wall_s}, device_evidence, errors}`. Map it into the same internal shape.

**Validate before parsing** (§12 rule 2): status `Ok` (cli: `ok`), `completion_tokens > 0`, text non-empty. If `finish` ≠ Stop (Length = hit the cap), still parse but add `"truncated": true` and log the error. On empty text, retry **once**. After parsing, coerce `lines` to a list of non-empty strings (split if it's a string), cap at `MAX_LINES`, and record `_vlm = {mode, seconds, raw, completion_tokens, ttft_ms, tok_s, finish}`.

### 9.4 Step 2: decide what matters (reference, use verbatim)
Questions are built directly in **d1's native schema** (the same JSON `zetic_d1_cli serve` reads, see `samples/requests.jsonl` in the SDK repo).
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
        return {"index": i, "label": SEVERITY[i], "confidence": _num(a.get("confidence")), "probabilities": p}
    return a
```
**`decide(lines, about)`:**
- Return `None` if `DECIDER == "none"` or there are no lines.
- `state = "\n".join(f"{i}. {l}" for i, l in enumerate(lines, 1))`; `qs = build_questions(lines, about)`.
- `resp = D1.call({"state": state, "questions": qs})`. If `resp` has `error`, or a `status` other than `Ok`/`ok`, raise.
- `answers = resp.get("answers", {})`. If it's a **list**, convert to a dict: items may be `[name, ans]` pairs, dicts with `name`, or bare answers in request order (zip with `qs`).
- `norm = {n: _normalize_answer(q["type"], answers.get(n)) for n, q in qs.items()}`.
- Return `{category, severity, action_p, personal_p, importance: [p or None per line], passes, seconds, backend: "zetic-d1", raw: resp}`.
- **If the severity banner doesn't appear on real hardware, the fix is almost certainly in `_normalize_answer`.** Read the raw `d1` output in the UI's Debug panel.

**`gate(decision)`** (code authorizes the action):
```python
def gate(d):
    if not d or d.get("error"): return {"alert": False, "reason": "no decision"}
    sev = (d.get("severity") or {}).get("index", -1)
    top = max([p for p in d.get("importance", []) if p is not None], default=0)
    if sev >= ALERT_SEVERITY: return {"alert": True, "reason": f"severity {sev} >= {ALERT_SEVERITY}"}
    if top >= IMPORTANCE_THRESHOLD and (d.get("action_p") or 0) >= 0.5:
        return {"alert": True, "reason": f"line importance {top:.2f} >= {IMPORTANCE_THRESHOLD}"}
    return {"alert": False, "reason": f"severity {sev}, top line {top:.2f}"}
```
`IMPORTANCE_THRESHOLD` starts at 0.5 as a **placeholder**. Tune it with `tools/calibrate.py` on the props (§9.11) and log the value in §16.

### 9.5 `engine/rosetta_vlm.cpp` (reference, syntax-checked against SDK 0.2.2 headers)
```cpp
// rosetta_vlm: LFM3-VL-2B resident on the IQ9 Hexagon NPU via the ZETIC Ixian Hexagon SDK.
// Protocol: JSON Lines on stdin -> JSON Lines on stdout (same pattern as zetic_d1_cli serve). Logs go to stderr.
//   usage: rosetta_vlm <model dir> [target ("" = v73, or v73-1nsp)] [max_context]
//   in:  {"id":1,"system":"...","prompt":"...","images":["/dev/shm/rosetta/scan-1.png"],"max_tokens":768,"temperature":0,"think":false}
//   out: {"id":1,"status":"Ok","text":"...","finish":"Stop","usage":{...},"timings":{...}}
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>
#include <zetic_llm.h>

using namespace zetic::ixian;
using json = nlohmann::ordered_json;

static void emit(const json& j) {
  std::cout << j.dump(-1, ' ', false, json::error_handler_t::replace) << '\n' << std::flush;
}

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <model dir> [target] [max_context]\n", argv[0]);
    return 2;
  }
  LLM::Options opt;
  opt.target = argc > 2 ? argv[2] : "";
  opt.max_context = argc > 3 ? std::stoi(argv[3]) : 4096;
  opt.max_new_tokens = 768;
  try {
    LLM llm = LLM::fromPath(argv[1], opt);
    const ModelInfo& info = llm.info();
    emit({{"event", "ready"}, {"model", info.model_id}, {"target", info.target}, {"nsp_count", info.nsp_count},
          {"soc", info.soc}, {"sdk", info.sdk_version}, {"package", info.package_version},
          {"max_context", llm.capabilities().max_context}});
    std::string line;
    while (std::getline(std::cin, line)) {
      if (line.empty()) continue;
      json out = {{"id", nullptr}};
      try {
        json req = json::parse(line);
        out["id"] = req.value("id", json());
        std::vector<Part> parts;
        if (req.contains("images"))
          for (const auto& p : req["images"]) parts.push_back(Part::Img(Image::fromFile(p.get<std::string>())));
        parts.push_back(Part::Text(req.value("prompt", std::string())));
        std::vector<Message> msgs;
        if (req.contains("system")) msgs.push_back(Message::System(req["system"].get<std::string>()));
        msgs.push_back(Message::User(std::move(parts)));

        GenerationConfig cfg;
        cfg.max_tokens = req.value("max_tokens", 768);
        cfg.temperature = req.value("temperature", 0.0f);
        cfg.enable_thinking = req.value("think", false);

        Response r = llm.chat(msgs, cfg);
        out["status"] = statusName(r.status);
        if (r.status != Status::Ok) out["error"] = r.error;
        out["text"] = r.text;
        out["reasoning"] = r.reasoning_content;
        out["finish"] = finishReasonName(r.finish_reason);
        out["usage"] = {{"prompt_rows", r.usage.prompt_rows}, {"cached_rows", r.usage.cached_rows},
                        {"completion_tokens", r.usage.completion_tokens}};
        out["timings"] = {{"ttft_ms", r.timings.ttft}, {"encode_ms", r.timings.encode},
                          {"prefill_ms", r.timings.prefill}, {"decode_ms", r.timings.decode},
                          {"tokens_per_second", r.timings.tokens_per_second}};
        if (r.status == Status::DeviceError) llm.reload();
        else if (r.status == Status::ContextExceeded) llm.reset();
      } catch (const Error& e) {
        out["status"] = statusName(e.status());
        out["error"] = e.what();
      } catch (const std::exception& e) {
        out["status"] = "InvalidArgument";
        out["error"] = e.what();
      }
      emit(out);
    }
  } catch (const Error& e) {
    fprintf(stderr, "rosetta_vlm: load failed (%s): %s\n", statusName(e.status()), e.what());
    return 1;
  }
  return 0;
}
```
**`engine/CMakeLists.txt`:**
```cmake
cmake_minimum_required(VERSION 3.18)
project(rosetta_engine CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(IxianHexagon 0.2 CONFIG REQUIRED)   # cmake -DCMAKE_PREFIX_PATH=$IXIAN_SDK/lib/cmake
find_package(nlohmann_json 3 QUIET)              # apt: nlohmann-json3-dev
foreach(t rosetta_vlm rosetta_d1)
  add_executable(${t} ${t}.cpp)
  target_link_libraries(${t} PRIVATE zetic::ixian_hexagon)
  if(nlohmann_json_FOUND)
    target_link_libraries(${t} PRIVATE nlohmann_json::nlohmann_json)
  else()
    target_include_directories(${t} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/third_party)
  endif()
endforeach()
```
Build on the board: `cmake -S engine -B engine/build -DCMAKE_PREFIX_PATH=$IXIAN_SDK/lib/cmake && cmake --build engine/build -j8`. When the SDK path changes, use a **new** build dir (CMake caches the old path).

### 9.6 d1 engine
- **Primary: `$IXIAN_SDK/bin/zetic_d1_cli serve --model models/d1-2b`** (ZETIC's own resident server, no code). Add `--set-size 8` on SDK 0.2.1.
  - First stdout line `{"event": "ready", ...}`. Then, per request line `{"id", "state", "questions"}` (+ optional `images` as base64 data URLs), one response line carrying the request's `id`. It contains `answers` (per-question `noul`/`choice`/`confidence`/`probabilities`/`legend`…), `usage`, `passes`. **Exact answer keys are not documented, so the normalizer is tolerant; paste a real response into §16.**
  - On a DSP failure it **exits** ("so the caller can restart"). `Engine` restarts it on the next call.
- **Fallback (P2, only if serve's output can't be normalized): `engine/rosetta_d1.cpp`**, same protocol, output shape fully ours:
```cpp
// rosetta_d1: d1-2B resident on the IQ9 NPU via the ZETIC Ixian Hexagon SDK (Decision::systemOne).
// Same JSON Lines protocol as `zetic_d1_cli serve`:
//   in:  {"id":1,"state":"1. ...","questions":{"severity":{"type":"score","instructions":"...","criteria":["a","b"]}}}
//   out: {"id":1,"status":"Ok","answers":{"severity":{"type":"score","score":1,"legend":"b",...}},"passes":1,...}
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>
#include <zetic_decision.h>

using namespace zetic::ixian;
using json = nlohmann::ordered_json;

static void emit(const json& j) {
  std::cout << j.dump(-1, ' ', false, json::error_handler_t::replace) << '\n' << std::flush;
}

static const char* typeName(Question::Type t) {
  return t == Question::Type::Noul ? "noul" : t == Question::Type::Choice ? "choice" : "score";
}

int main(int argc, char** argv) {
  if (argc < 2) {
    fprintf(stderr, "usage: %s <d1 model dir>\n", argv[0]);
    return 2;
  }
  try {
    Decision d1 = Decision::fromPath(argv[1]);
    const ModelInfo& info = d1.info();
    emit({{"event", "ready"}, {"model", info.model_id}, {"target", info.target}, {"nsp_count", info.nsp_count},
          {"soc", info.soc}, {"sdk", info.sdk_version}, {"max_context", d1.capabilities().max_context}});
    std::string line;
    while (std::getline(std::cin, line)) {
      if (line.empty()) continue;
      json out = {{"id", nullptr}};
      try {
        json req = json::parse(line);
        out["id"] = req.value("id", json());
        State state = State::None();
        if (req.contains("state")) {
          const json& s = req["state"];
          if (s.is_string()) state = State::Text(s.get<std::string>());
          else if (!s.is_null()) state = State::Json(s.dump());
        }
        std::vector<std::pair<std::string, Question>> qs;
        const json& questions = req.at("questions");
        for (auto it = questions.begin(); it != questions.end(); ++it) {
          const json& q = it.value();
          const std::string type = q.value("type", std::string("noul"));
          const std::string instr = q.value("instructions", std::string());
          if (type == "noul") {
            qs.emplace_back(it.key(), Question::Noul(instr));
          } else if (type == "choice") {
            std::vector<std::pair<std::string, std::string>> crit;
            const json& c = q.at("criteria");
            for (auto ci = c.begin(); ci != c.end(); ++ci)
              crit.emplace_back(ci.key(), ci.value().is_string() ? ci.value().get<std::string>() : std::string());
            qs.emplace_back(it.key(), Question::Choice(instr, crit, q.value("multiple", false)));
          } else if (type == "score") {
            qs.emplace_back(it.key(), Question::Score(instr, q.at("criteria").get<std::vector<std::string>>()));
          } else {
            throw std::invalid_argument("unsupported question type: " + type);
          }
        }
        DecisionResult r = d1.systemOne(state, qs);
        out["status"] = statusName(r.status);
        if (r.status != Status::Ok) out["error"] = r.error;
        json answers = json::object();
        for (const auto& na : r.answers) {
          const Answer& a = na.second;
          answers[na.first] = {{"type", typeName(a.type)}, {"noul", a.noul}, {"choice", a.choice},
                               {"choices", a.choices}, {"confidence", a.confidence}, {"score", a.score},
                               {"legend", a.legend}, {"labels", a.labels}, {"probabilities", a.probs}};
        }
        out["answers"] = answers;
        out["passes"] = r.passes;
        out["input_tokens"] = r.input_tokens;
        out["timings"] = {{"encode_ms", r.timings.encode}, {"d1_ms", r.timings.prefill}, {"ttft_ms", r.timings.ttft}};
      } catch (const Error& e) {
        out["status"] = statusName(e.status());
        out["error"] = e.what();
      } catch (const std::exception& e) {
        out["status"] = "InvalidArgument";
        out["error"] = e.what();
      }
      emit(out);
    }
  } catch (const Error& e) {
    fprintf(stderr, "rosetta_d1: load failed (%s): %s\n", statusName(e.status()), e.what());
    return 1;
  }
  return 0;
}
```

### 9.7 Camera fallbacks
1. **Primary:** webcam on the IQ9 → `/stream`. No browser camera permissions needed.
2. **Fallback A:** laptop browser camera via `getUserMedia`. Browsers allow it only on HTTPS or `localhost`, and our SSH tunnel *is* `127.0.0.1:8000`, so it works. The page crops a 512×512 square to canvas and sends it as `image`.
3. **Fallback B:** "Upload photo" button (browser crops to 512 too).
4. **Demo-safety:** `samples/` holds 512×512 PNGs of every prop for an upload-based demo if the camera dies.

### 9.8 Metrics surfaced (Performance 10%, Tiny Agent Olympics)
Per scan: VLM `ttft_ms`, `tokens_per_second`, `completion_tokens`, wall seconds (cli mode adds `model_load_ms`); d1 wall seconds, `passes`, `d1_ms`; end-to-end seconds. Per engine (`/status`): `peak_rss_mb` (VmHWM), target, NSPs, SDK version. README gets the **medians of ≥5 successful scans** of our own workload with sample counts, measured on the board. Never quote vendor numbers as ours.

### 9.9 `index.html`: UI spec
- **Single file, inline CSS/JS, zero external requests** (no CDNs, no web fonts; system font stack). Dark theme.
- **Header:** title **"rosetta"** (lowercase) · green pill "● on-device · no internet" · pill from `/status` engines: e.g. **"LFM3-VL-2B + d1-2B · Hexagon NPU (ZETIC)"**. It shows the **real** target/NSPs; if a fallback runtime is active, say which.
- **Left panel:** camera area (16:10; `<img src="/stream">` if `server_camera`, else `<video>` via getUserMedia, else a message) **with the 512 crop square overlaid** · big **Scan** button (Space triggers it when focus isn't in an input) · **Watch** toggle (P1-late; shows "watching…" + last trigger time) · **Upload photo** (auto-scans; client-side center-crop to 512×512 PNG) · **"About you (optional)"** text input + quick chips (`allergic to shellfish`, `allergic to nuts`, `on a motorbike`, `traveling with kids`, `no permit`, `pregnant`) that toggle phrases in the input · **"Ask about it (optional)"** input. Persist About-you in `localStorage` (wrap in try/catch).
- **While scanning:** button disabled, spinner, "Reading & deciding on the NPU…".
- **Right panel, top to bottom:**
  1. **Metrics strip** (green): `NPU · read X s · TTFT Y ms · Z tok/s · d1 W s (N passes)`, detected languages, d1 category + confidence %.
  2. **Severity banner** (if `decision.severity`): big label; subline "d1-2B decision · NN% confident · action required: NN% · affects you: NN%"; thin probability bar with segments colored by level if `probabilities` exist. Colors by index: 0 gray `#5b6472`, 1 blue `#4f8cff`, 2 amber `#ffb547`, 3 orange `#ff7a3d`, 4 red `#ff4d4d` (tinted dark backgrounds). If `gate.alert`: pulsing border; in watch mode also a short WebAudio beep (generated, no asset).
  3. If `decision.error`: small gray box "Decision model unavailable, showing translation only."
  4. Summary sentence (bold).
  5. **"Your question"** box (blue) if `answer` is non-empty.
  6. **"⚠ What matters (ranked by d1)"** (red box): lines with importance ≥ `importance_threshold` (from `/status`), sorted descending, top 6, each with a % pill.
  7. **"Couldn't read (not guessing)"** (amber box) if `unreadable` is non-empty.
  8. **Full translation:** every line with a left border colored by importance (≥0.75 red, ≥ threshold amber, else gray) and a % pill.
  9. Parse-error / truncated notice if flagged.
  10. **Log** (collapsible, open by default during the demo): last 10 JSONL records from `/log` (time, trigger, category, severity, alert, action, errors).
  11. Collapsible **Debug:** the 512 image the model saw + raw VLM output + raw d1 JSON. **Critical for tuning at the event.**
- **Empty state:** "Point the camera at any sign, notice, menu or label and press Scan. LFM3-VL reads & translates it · d1 decides what matters. Both run on this IQ9's NPU."
- Escape all model text before inserting it into HTML.

### 9.10 `tools/mock_engine.py` (build this FIRST; it unblocks all app/UI work on the Mac)
One stdlib script, `python3 tools/mock_engine.py vlm|d1 [--shape dict|list] [--delay 0.3] [--fail-every N]`:
- Prints `{"event":"ready","model":"mock-<kind>","target":"v73","nsp_count":2,"soc":"MOCK","sdk":"0.2.2-mock","max_context":4096}`, then answers each stdin line after `--delay`, echoing `id`.
- **vlm:** `{"id","status":"Ok","text": "```json\n" + json.dumps(VLM) + "\n```","finish":"Stop","usage":{"prompt_rows":700,"cached_rows":420,"completion_tokens":260},"timings":{"ttft_ms":205,"tokens_per_second":57.2,...}}`. The fence tests the stripper.
- **d1, `--shape dict`:** `answers` keyed by name: `category {"choice":"safety warning","confidence":.88,"labels":[...],"probabilities":[...]}`, `severity {"score":4,"legend":SEVERITY[4],"confidence":.61,"probabilities":[.01,.04,.12,.22,.61]}`, `action {"noul":.96}`, `personal {"noul":.74}`, `line_i {"noul": IMP[i-1]}`; `"passes": 2`.
- **d1, `--shape list`:** `answers` = ordered `[[name, ans], ...]` with GenieX-ish keys (`value`, `index`, `probability`) to exercise the normalizer's other branches.
- `--fail-every N`: exit the process on every Nth request (tests `Engine` restart).
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
`IMP = [.08,.41,.83,.91,.97,.66,.58,.62,.71]`. **Must pass:** the app against both d1 shapes yields a non-null category, severity and 9 importances; the UI shows banner + ranked list + amber box + log entry; `--fail-every 3` recovers on the next scan; the browser makes **zero non-localhost requests**.

**`tools/openai_vlm_bridge.py`** (P2): speaks the VLM protocol, reads the PNG, POSTs an OpenAI chat request (`image_url` data URL + system + prompt, `max_tokens`, `temperature`) to `--url` (default `http://127.0.0.1:8080/v1/chat/completions`), and returns `text`/`finish`/`usage`/timings. Uses: Mac prompt tuning against `llama-server`; emergency GenieX on the board.

### 9.11 Scripts and tools
- **`scripts/stage_zetic.sh` (laptop, Wi-Fi on):** in a new dir `stage/`: download the SDK 0.2.2 tarball + `.sha256` (and 0.2.1) → `shasum -a 256 -c` → `tar -tvzf` review → extract to `stage/sdk/`. `hf download ZETIC-ai/LFM3-VL-2B-IQ9 --revision 4b97823becd3c17a050aef419924af48075eb199 --include 'v73/*' LICENSE README.md --local-dir stage/models/lfm3-vl-2b` (optionally also `'v73-1nsp/*'`). `hf download ZETIC-ai/d1-2B-IQ9 --revision c82c9736e92a3cafcfbac7625ead99ad99138a89 --include 'v73/*' LICENSE README.md --local-dir stage/models/d1-2b`. Then `(cd stage/models/<m>/v73 && shasum -a 256 -c SHA256SUMS)`. If a pinned revision 404s, drop `--revision` and record the actual commit in §16. Also fetch `nlohmann/json.hpp` v3.12.0 into `engine/third_party/nlohmann/`.
- **`scripts/setup_board.sh` (board):** prints, without running, the sudo commands of §11.3 for the human to paste. Then checks `/dev/fastrpc-cdsp*` rw, `id -nG | grep fastrpc`, `cmake --version`, `python3 -c 'import cv2'`, `ls $IXIAN_SDK/bin`, the model manifests, and builds `engine/`.
- **`scripts/run.sh` (board):** `export IXIAN_SDK=$HOME/rosetta/sdk; export HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1; exec python3 app.py`. Set `VLM_MODE`/`D1_CMD` here.
- **`tools/calibrate.py` (P2):** reads `logs/rosetta.jsonl` + `tools/labels.json` (`{prop_scan_id: [indices of lines that must be flagged]}`, from §14.4) → sweeps thresholds → prints precision/recall/F1 for each → recommends `IMPORTANCE_THRESHOLD`. Calibrate on 4 props and check on the other 3 (held out). Log the result in §16.
- **`tools/offline_audit.py`:** run `python3 tools/offline_audit.py .` before submitting. Review every finding.

### 9.12 Build order (priority)
| # | Pri | Item | Owner | Done when |
|---|---|---|---|---|
| B1 | P0 | `tools/mock_engine.py` | Rehan's agent | both kinds answer per §9.10 |
| B2 | P0 | `app.py`: server, `Engine`, `/status`, `/scan` (upload), step 1 (§9.3), JSONL log | Rehan's agent (Engine/step 1: Isaac's agent) | upload scan against mock VLM returns lines + writes a log line |
| B3 | P0 | `index.html` core: camera/upload (512 crop), Scan, translation list, metrics, Debug | Rehan's agent | renders mock result, zero external requests |
| B4 | P0 | IQ9: access, fastrpc, SDK + models staged + `info --verify` + **`zetic_quickstart` on a 512 prop image** | Isaac | NPU answer + `HEXRT_NSP2=1` evidence **by 7:00** |
| B5 | P0 | Webcam capture + `/stream` + 512 prep in `app.py` | Rehan's agent | live preview from IQ9 webcam, crop square shown |
| B6 | P0 | `VLM_MODE=cli` via `tools/zetic_run.py` on the board | Isaac's agent | real scan through app.py returns lines |
| B7 | P1 | step 2 `decide()` + normalizer + `gate()` (§9.4) | Isaac's agent | both mock d1 shapes → severity + importances |
| B8 | P1 | d1 on the board: `zetic_d1_cli serve` via `Engine` | Isaac | real decision; raw response pasted in §16 |
| B9 | P1 | UI: severity banner, What-matters, unreadable box, per-line colors, log panel | Rehan's agent | matches §9.9 with mocks |
| B10 | P1 | `engine/rosetta_vlm` built + `VLM_MODE=engine` (resident, ~3 s faster) | Isaac's agent | engine mode scan works; both engines resident |
| B11 | P1 | Real end-to-end on IQ9 + tune prompt/normalizer vs props | both | §14.4 "Must" passes |
| B12 | P1 | Watch mode (loop + `/watch` + `/latest` + UI toggle + beep) | Rehan's agent | hands-free scan + alert + log line |
| B13 | P2 | About-you chips + question box | Rehan's agent | answer/personal_p show up |
| B14 | P2 | `tools/calibrate.py` + threshold | Isaac's agent | threshold logged in §16 |
| B15 | P2 | `engine/rosetta_d1` (only if serve output is unusable) | Isaac's agent | same results via our shape |
| B16 | P2 | README metrics, polish, readability at demo distance | Rehan | — |

**Cut line:** if B11 isn't green by **7:40**, drop B12–B16, freeze features, rehearse Wi-Fi-off, and submit.

---

## 10. API contracts

Internals may change; **these may not** unless `index.html` and this section are updated in the same change.

### 10.1 `POST /scan` (browser → app)
```json
{"image": "data:image/png;base64,...   (optional, 512x512; omit to use the IQ9 webcam)",
 "about": "on a motorbike, allergic to shellfish",
 "question": "Can I hike this afternoon?"}
```
**200:**
```json
{"scan_id": 12, "languages": ["Chinese","Tibetan"], "summary": "...", "lines": ["...", "..."],
 "unreadable": ["Top line: Tibetan script, cannot read"], "answer": "...", "parse_error": false, "truncated": false,
 "_vlm": {"mode": "engine", "seconds": 4.2, "ttft_ms": 210, "tok_s": 55.3, "completion_tokens": 260, "finish": "Stop", "raw": "..."},
 "decision": {"category": {"value": "safety warning", "confidence": 0.88, "probabilities": {}},
              "severity": {"index": 4, "label": "Danger: risk of serious injury or death", "confidence": 0.61, "probabilities": [0.01,0.04,0.12,0.22,0.61]},
              "action_p": 0.96, "personal_p": 0.74, "importance": [0.08, 0.41, 0.83],
              "passes": 2, "seconds": 0.21, "backend": "zetic-d1", "raw": {}},
 "gate": {"alert": true, "reason": "severity 4 >= 3"},
 "_metrics": {"total_s": 4.5},
 "_image": "data:image/png;base64,..."}
```
`decision` may be `null` (`DECIDER=none`) or `{"error": "..."}`. Errors: 400 / 502 / 503 / 500 as `{"error": "..."}`.

### 10.2 `GET /status`
`{"server_camera": bool, "watch": bool, "vlm_mode": "engine|cli|mock", "decider": "zetic|none", "severity_levels": [5 labels], "importance_threshold": 0.5, "engines": {"vlm": {<ready event>, "peak_rss_mb": int, "alive": bool}, "d1": {...}}}`

### 10.3 Other routes
- `GET /stream` → MJPEG; 404 JSON if there's no server camera.
- `GET /log?n=20` → `{"records": [last n JSONL records]}`.
- `POST /watch {"on": bool}` → `{"watch": bool}`.
- `GET /latest?after=<scan_id>` → the newest `/scan`-shaped result with `scan_id > after`, or `{}`.

### 10.4 app ↔ VLM engine (JSON Lines over stdin/stdout)
- Ready (first line): `{"event":"ready","model","target","nsp_count","soc","sdk","package","max_context"}`
- Request: `{"id": int, "system": str, "prompt": str, "images": [abs PNG path, 512x512], "max_tokens": int, "temperature": float, "think": bool}`
- Response: `{"id", "status": "Ok|InvalidArgument|ContextExceeded|DeviceError|...", "error"?, "text", "reasoning", "finish": "Stop|Length|...", "usage": {"prompt_rows","cached_rows","completion_tokens"}, "timings": {"ttft_ms","encode_ms","prefill_ms","decode_ms","tokens_per_second"}}`

### 10.5 app ↔ d1 engine (JSON Lines; `zetic_d1_cli serve` format)
- Ready: `{"event":"ready", ...}`
- Request: `{"id": int, "state": str, "questions": {name: {"type": "noul|choice|score", "instructions": str, "criteria": {label: desc} | [levels]}}}`
- Response: `{"id", "answers": {name: {...}} | [...], "passes"?, "usage"?, "status"?, "error"?}`. Normalize per §9.4. Real serve: dict `answers`, no `status` on success, `{"error"}` on failure (§16 D17).

### 10.6 Environment variables
| Var | Default | Notes |
|---|---|---|
| `IXIAN_SDK` | `./sdk` | extracted SDK root (bin/, lib/) |
| `VL_MODEL` | `models/lfm3-vl-2b` | parent of `v73/` |
| `D1_MODEL` | `models/d1-2b` | parent of `v73/` |
| `VLM_MODE` | `engine` | `engine` (resident C++) · `cli` (zetic_run.py one-shot) · `mock` |
| `VLM_CMD` | `engine/build/rosetta_vlm $VL_MODEL "" 4096` | target `""`=v73, `v73-1nsp` if NSPs contend; mock: `python3 tools/mock_engine.py vlm` |
| `D1_CMD` | `$IXIAN_SDK/bin/zetic_d1_cli serve --model $D1_MODEL` | add `--set-size 8` on SDK 0.2.1; alt `engine/build/rosetta_d1 $D1_MODEL` |
| `DECIDER` | `zetic` | `zetic` · `none` |
| `MAX_TOKENS` | `768` | cap; raise if `finish=Length` on dense signs |
| `MAX_LINES` | `24` | VLM lines kept = d1 line questions (≤ 2 passes) |
| `THINK` | `0` | `1` → `enable_thinking` (slower; only if quality needs it) |
| `CROP` | `center` | `center` · `letterbox` |
| `ALERT_SEVERITY` | `3` | gate: Warning and up |
| `IMPORTANCE_THRESHOLD` | `0.5` | placeholder until calibrated (§9.11) |
| `VLM_TIMEOUT` / `D1_TIMEOUT` | `60` / `20` | seconds per request |
| `ENGINE_LOAD_TIMEOUT` | `120` | seconds for the ready line |
| `CAMERA` | `0` | index, `/dev/videoN`, or `none` |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | `0.0.0.0` only for the monitor/Ethernet fallback |
| `SHM_DIR` | `/dev/shm/rosetta` | model input PNGs |
| `WATCH_CHANGE` / `WATCH_STABLE_S` / `WATCH_SHARP` | `12` / `1.2` / `60` | watch trigger tuning |

---

## 11. Runbooks

Every command says where it runs: **[laptop]** or **[board]**.

### 11.0 Now → 5:00 PM (Wi-Fi ON)
- [ ] **[laptop]** `git clone https://github.com/heath0xFF/cleared-for-takeoff-hackathon ~/cft` and read `docs/judging.md` + `examples/zetic-lfm/README.md`.
- [ ] **[laptop]** Stage ZETIC (≈5.5 GB; ≈7.9 GB with `v73-1nsp`): `pipx install huggingface_hub` (or `pip install -U huggingface_hub`), then `scripts/stage_zetic.sh`, or by hand:
  ```bash
  mkdir -p stage && cd stage
  V=0.2.2; R=https://github.com/zetic-ai/IxianHexagon/releases/download/$V; A=ixian-hexagon-$V-linux-arm64-qcom-iq9.tar.gz
  curl -fSLO $R/$A && curl -fSLO $R/$A.sha256 && shasum -a 256 -c $A.sha256
  mkdir sdk && tar -xzf $A --strip-components=1 -C sdk
  hf download ZETIC-ai/LFM3-VL-2B-IQ9 --revision 4b97823becd3c17a050aef419924af48075eb199 --include 'v73/*' LICENSE README.md --local-dir models/lfm3-vl-2b
  hf download ZETIC-ai/d1-2B-IQ9 --revision c82c9736e92a3cafcfbac7625ead99ad99138a89 --include 'v73/*' LICENSE README.md --local-dir models/d1-2b
  (cd models/lfm3-vl-2b/v73 && shasum -a 256 -c SHA256SUMS); (cd models/d1-2b/v73 && shasum -a 256 -c SHA256SUMS)
  ```
  Also grab the SDK 0.2.1 tarball (fallback). Copy `stage/` to a **USB stick (exFAT; the largest file is 1.16 GB)** as a second source.
- [ ] **[laptop]** `engine/third_party/nlohmann/json.hpp` (v3.12.0 single header).
- [ ] **[laptop, optional]** `brew install llama.cpp` + the two GGUFs (§6) for 512-px prompt tests (§11.7). **Record read quality on 512×512 prop crops in §16.** This tells us early whether 512 px is enough.
- [ ] **Rehan:** create an **Arduino account** and **draft the Project Hub post** (problem, solution, architecture diagram, models/runtime, how to run, metrics placeholders, code). Create the **GitHub repo** (private until ~7:55).
- [ ] **Gear:** webcam + stand, **data-capable micro-USB cable (UART)**, **USB-C cable(s)/adapters** for the board↔laptop link and the organizers' USB drive, USB stick, chargers, printed props (color, large type), phone for the backup video and timer.

### 11.1 5:00–6:15
- [ ] **Ask organizers:** (1) Is pre-written code allowed? (2) **How exactly is the "isolated USB-C network link" set up** on these boards (gadget mode? adapter?) (3) Is a **direct laptop↔board Ethernet cable with no uplink** acceptable in the demo, given "unplug any Ethernet"? (4) What's on the **USB model drive** (any ZETIC packages)? (5) Is ZETIC present tonight (separate prize? support person)?
- [ ] Set up agents with this file. If pre-building is allowed, Rehan starts B1–B3 and Isaac's agent writes `engine/` + `Engine`.
- [ ] 6:00–6:15 workshop: **write down every board/NPU/ZETIC command they show** → update §8/§11.

### 11.2 Board access (first 10 minutes) [Isaac]
```bash
# [laptop] UART: data micro-USB to the board's debug port, second FTDI port, 115200
ls /dev/cu.*          ;  screen /dev/cu.<observed-node> 115200     # login ubuntu / liquidxqualcomm
# [board, UART]
uname -m; cat /etc/os-release; nproc; free -h; df -h /; ls /dev/video* /dev/fastrpc-cdsp*
nmcli -p device; nmcli dev wifi list
sudo nmcli --ask dev wifi connect '<venue SSID>'                 # setup internet only
ip -br address                                                    # note the board IP
# [laptop]
export IQ9_HOST=ubuntu@<board-ip>; ssh "$IQ9_HOST"
ssh "$IQ9_HOST" 'bash -s -- --profile board --json' < scripts/preflight.sh   # vendored, read-only
```
Record results in §15.

### 11.3 Board setup [Isaac; human types sudo]
```bash
# [board] NPU packages. NO qcom-adreno1, NO install_ppa_pkgs.sh, NO apt upgrade.
sudo apt-get update
apt-get -s install --no-install-recommends libatomic1 qcom-fastrpc1 libqnn1        # simulate, read the plan
sudo apt-get install --no-install-recommends libatomic1 qcom-fastrpc1 libqnn1
sudo usermod -aG fastrpc "$USER"          # then RECONNECT ssh; check: id -nG | grep fastrpc
for n in /dev/fastrpc-cdsp /dev/fastrpc-cdsp1; do [ -r $n ] && [ -w $n ] && echo "rw ok $n" || echo "NO rw $n"; done
# [board] app/build deps (no pip needed)
sudo apt-get install --no-install-recommends cmake g++ make python3-opencv nlohmann-json3-dev tmux
```
**Stage SDK + models onto board storage** (copy, never move; nothing runs from removable media):
```bash
# [laptop] over SSH (fast on the same network)
ssh "$IQ9_HOST" 'mkdir -p ~/rosetta'
scp -r stage/sdk stage/models "$IQ9_HOST":rosetta/
# or from the USB stick on the board: lsblk -o NAME,TRAN,SIZE,FSTYPE,LABEL,MOUNTPOINTS → cp -r <mnt>/stage/{sdk,models} ~/rosetta/
# [board] verify + smoke test = FIRST NPU RESPONSE (target 7:00)
cd ~/rosetta && export IXIAN_SDK=$PWD/sdk LD_LIBRARY_PATH=$PWD/sdk/lib
(cd models/lfm3-vl-2b/v73 && sha256sum -c SHA256SUMS) && (cd models/d1-2b/v73 && sha256sum -c SHA256SUMS)
sdk/bin/zetic_lfm3_cli info --model models/lfm3-vl-2b --verify --verbose
sdk/bin/zetic_d1_cli  info --model models/d1-2b --verify
sdk/bin/zetic_lfm3_cli chat --model models/lfm3-vl-2b --media samples/tibet_512.png --max-tokens 400 --temp 0 --verbose \
  "Read and translate all text in this image into English."          # look for: hexrt open ... v73 ... HEXRT_NSP2=1
sdk/bin/zetic_d1_quickstart models/d1-2b                              # refund / team / urgency decisions
```
Make prop PNGs with `ffmpeg -i photo.jpg -vf "crop=min(iw\,ih):min(iw\,ih),scale=512:512" -frames:v 1 tibet_512.png`, or let `app.py` save them.

### 11.4 Build and run the app [both]
```bash
# [board]
git clone <our repo> ~/rosetta/app && cd ~/rosetta/app && ln -s ../sdk sdk && ln -s ../models models
cmake -S engine -B engine/build -DCMAKE_PREFIX_PATH=$IXIAN_SDK/lib/cmake && cmake --build engine/build -j8
tmux new -s rosetta
VLM_MODE=engine scripts/run.sh                 # P0 fallback: VLM_MODE=cli scripts/run.sh
# [laptop] tunnel (over the USB-C link IP once it exists; Wi-Fi IP during build)
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8000:127.0.0.1:8000 "$IQ9_HOST"
open http://127.0.0.1:8000
```
**One throwaway scan after every start** (warm-up). If d1 fails to load while the VLM is resident (NSP contention), switch the VLM to `v73-1nsp` (`VLM_CMD=… "v73-1nsp" 4096`, needs that package) or use `VLM_MODE=cli`.

### 11.5 Measure (Performance 10%)
5 scans of the hero prop + 5 mixed → medians from `logs/rosetta.jsonl` (`ttft_ms`, `tok_s`, VLM s, d1 s, total s) + `peak_rss_mb` from `/status`. Write them in README + §16. `/usr/bin/time -v engine/build/rosetta_vlm …` once if time allows.

### 11.6 Network-off: control path, display, rehearsal
- **Control path that survives Wi-Fi off:** the **UART console** (always works) and/or an **isolated USB-C network link** (per organizers' answer, §11.1). Set up and test it **while Wi-Fi is still on**.
- **Display:** laptop browser via `ssh -L` over the USB-C link. **Laptop internet sharing/bridging OFF.** Fallbacks: (a) direct Ethernet cable if organizers OK it (static IPs `10.42.0.1/24` laptop, `10.42.0.2/24` board via `sudo ip addr add … dev <iface>`); (b) monitor on the board (we never installed the Adreno update, but **test it first**).
- **Rehearsal (by 8:00):** from UART: `sudo nmcli radio wifi off && nmcli -p device` → stop and restart the app **cold** in tmux → 3 scans in a row + watch mode → check the JSONL → `sudo nmcli radio wifi on`. Nothing may try to download at startup.

### 11.7 Mac-only dev loop (no IQ9 needed)
```bash
VLM_MODE=engine VLM_CMD="python3 tools/mock_engine.py vlm" D1_CMD="python3 tools/mock_engine.py d1" CAMERA=none python3 app.py
# real-model prompt tuning (not ZETIC; quality proxy only), images must be the same 512x512 PNGs:
llama-server -m LFM3-VL-2B-QAD-Q4_0.gguf --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf --port 8080 &
VLM_CMD="python3 tools/openai_vlm_bridge.py --url http://127.0.0.1:8080/v1/chat/completions" D1_CMD="python3 tools/mock_engine.py d1" CAMERA=none python3 app.py
```
The ZETIC SDK and C++ engines can't run on macOS. Syntax-check the C++ with `clang++ -std=c++17 -fsyntax-only -I stage/sdk/include -I engine/third_party engine/*.cpp`.

---

## 12. Rules for coding agents

(Our rules + the starter repo's `AGENTS.md` non-negotiables.)
1. **Offline at runtime is non-negotiable.** No CDN scripts, fonts or CSS; no remote APIs; no telemetry; no downloads or installs at runtime. The only IPC is to our child engine processes; the only network is loopback + the SSH tunnel. Set `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`. Run `tools/offline_audit.py` before submitting.
2. **Cap and validate every LFM call:** always send `max_tokens`. Reject status ≠ Ok, zero tokens, empty or reasoning-only text. Flag `finish ≠ Stop`. Retry at most once. Errors are **data** (logged + shown), never crashes.
3. **Verify NPU execution** from current device evidence (§8.5). **Never claim "entirely on the NPU"** (CPU does some work). Never silently switch runtime or compute; if a fallback is active, the UI and pitch say so.
4. **Code authorizes actions.** Models propose (lines, probabilities); `gate()` decides; the log records proposals, decisions, actions and errors separately, as flushed JSONL.
5. **Calibrate, don't assume:** no hard-coded 0.5 for d1 decisions in the final demo; use the calibrated `IMPORTANCE_THRESHOLD` (§9.11).
6. **Keep models sequential:** VLM finishes, then d1 runs. No concurrent NPU calls.
7. **Stdlib-first.** No FastAPI/Flask/React/bundlers. OpenCV (apt) and the Ixian SDK + nlohmann/json (C++) are the only extra deps.
8. **Never break §10** without updating `index.html` and this file in the same change.
9. **Fail soft.** d1 failure → translation still shows. Camera failure → upload. Engine crash → restart. No exception kills the server.
10. **No overclaiming in UI copy:** languages, accuracy, NPU, runtime.
11. **Prompts are code.** Changes to `SYSTEM_PROMPT`, `CATEGORIES`, `SEVERITY`, `build_questions` or thresholds must be checked against §14.4 and logged in §16.
12. **Mock first, then real.** `python3 -m py_compile app.py tools/*.py` and the clang syntax check before handing off.
13. **Small diffs; respect ownership** (§0). Pull before editing `app.py`; don't reformat the other half.
14. **Ask before system changes on the board** (installs, network, groups, deleting files). Passwords are typed by humans, never in commands, chat or logs. Never `chmod` device nodes, never install `qcom-adreno1`, never `apt upgrade`. **Copy, never move** from the USB drive.
15. **Never commit `models/`, `sdk/`**, secrets or large binaries. `logs/` is committed but kept small.
16. **Time-box 20 minutes.** If something isn't working, take the §15 fallback and log it.
17. **No fine-tuning, new architectures or audio** tonight.

---

## 13. Timeline and task board

| Time | Isaac | Rehan |
|---|---|---|
| **until 5:00** | Stage ZETIC SDK + models (§11.0), copy to USB stick; optional 512-px Mac test → §16 | Print props; pack gear (UART cable!); Arduino account + Project Hub draft; GitHub repo |
| 5:00–6:00 | Ask organizers (§11.1) | Same; set up agent; if pre-building is allowed, B1–B3 |
| 6:00–6:15 | **Workshop: note exact commands** → update §8/§11 | Same |
| 6:15–6:35 | §11.2 UART → Wi-Fi → SSH → preflight; §11.3 apt + fastrpc group | B1 mocks → B2 app core (agent) |
| 6:35–7:00 | Copy SDK/models, `info --verify`, **first NPU response (B4)**, d1 quickstart | B3 UI core → B5 webcam; set up the USB-C link per organizers |
| 7:00–7:20 | B6 cli-mode scan on board → B8 d1 serve → B10 build `rosetta_vlm` | B7/B9 decision UI + log panel (agent) |
| 7:20–7:40 | **B11** integrate on IQ9, scan every prop, fix normalizer/prompt; B11 measurements | B12 watch mode if B11 is moving |
| **7:40** | **Cut line:** freeze features if B11 isn't green | |
| 7:40–8:00 | **Wi-Fi-off rehearsal from UART** (§11.6), cold start, 3 scans, JSONL check | Record backup video; run `offline_audit.py`; README metrics; push; repo **public** |
| 8:00–8:15 | Buffer; P2 only if everything is green | **Submit** (form: GitHub + Project Hub links); rehearse the 2-min script |
| 8:15– | Demo | Demo |

---

## 14. Testing and acceptance

### 14.1 Smoke tests (board)
```bash
cd ~/rosetta && export LD_LIBRARY_PATH=$PWD/sdk/lib
# VLM, NPU, device evidence
sdk/bin/zetic_lfm3_cli chat --model models/lfm3-vl-2b --media samples/tibet_512.png --max-tokens 400 --temp 0 --verbose "Read and translate all text in this image into English." 2>&1 | grep -E "hexrt open|finish|ttft"
# d1 via serve (one JSON line in, one out)
printf '%s\n' '{"id":1,"state":"Road closed 17:00-06:00. Landslide danger.","questions":{"danger":{"type":"noul","instructions":"Is this a safety warning?"},"sev":{"type":"score","instructions":"How serious?","criteria":["low","medium","high"]}}}' \
  | sdk/bin/zetic_d1_cli serve --model models/d1-2b
# our VLM engine
printf '%s\n' '{"id":1,"prompt":"Read and translate all text in this image.","images":["'$PWD'/samples/tibet_512.png"],"max_tokens":400}' \
  | app/engine/build/rosetta_vlm models/lfm3-vl-2b "" 4096
```

### 14.2 Mock acceptance (before touching real models)
App with `VLM_CMD`/`D1_CMD` = mock engines, d1 `--shape dict` and `--shape list`: non-null category/severity, 9 importances, UI renders banner + ranked list + amber box + log row, code fence stripped, `--fail-every 3` recovers, zero external requests, `logs/rosetta.jsonl` gets one valid line per scan.

### 14.3 Performance targets (board, our workload)
Read ≤ **6 s**/scan in engine mode (ZETIC reports TTFT ~0.2 s, ~55–59 tok/s, so ~260 tokens ≈ 5 s) · cli mode adds ~3.3 s load · decide ≤ **1 s** (2 passes) · end-to-end ≤ **7 s**. Levers: lower `MAX_TOKENS`/`MAX_LINES`, `THINK=0`, VLM `v73` (2 NSPs). **Do one throwaway scan after starting the engines.**

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
| No-text image | — | no crash, sensible summary, gate: no alert | — |

Backup set (`translator_demo_props.pdf`): French menu, Japanese izakaya menu (¥300 cover charge "otoshi", shrimp in chawanmushi, buckwheat soba, peanut in tantanmen), Spanish ibuprofen 400 mg box (max 3 tablets per 24 h; contraindications), German rail-replacement notice (no trains Freiburg–Offenburg Nov 14–17, bus at south exit bay 3, no bikes), Italian cookie label (may contain nuts and sesame), French parking sign (no parking Mon–Sat 7–11 except deliveries, towing €135; paid 9–20, free Sundays).

### 14.5 Definition of done (demo-ready)
- [ ] VLM and d1 run **on the IQ9 NPU via the ZETIC SDK**; device evidence captured; app on the board
- [ ] **Wi-Fi off from UART** (`nmcli -p device` shows it), cold start, webcam preview live, 3 scans in a row without restart
- [ ] Tibetan + (Kyrgyz or Ladakh) + French-menu scans meet "Must"
- [ ] Severity banner + What-matters render; fallback note verified by killing the d1 engine
- [ ] `logs/rosetta.jsonl` shows input, decision, action, timings, errors per scan
- [ ] Metrics visible; UI tells the truth about runtime/compute
- [ ] `offline_audit.py` reviewed; repo **public**; **both links submitted** by 8:15
- [ ] Backup video recorded; props ordered; 2-min script rehearsed once

---

## 15. Risks, fallbacks, known unknowns

| Risk | Likelihood | Fallback |
|---|---|---|
| Pre-built code not allowed | ? | Build from §9 at 6:15; mocks first; cut line 7:40 |
| Board setup eats the first hour (fresh image, apt 404s, fastrpc group) | Med | Follow §11.3 exactly; stale-index 404 → `apt-get update` again, never add PPAs; reconnect SSH after `usermod` |
| ZETIC SDK fails to load (FastRPC/DSP) | Low-Med | rw on `/dev/fastrpc-cdsp*`, new login after the group change; `DeviceError map: 0x1` → wait 3 s, retry; try SDK 0.2.1; then §8.6 GenieX + bridge **and say so** |
| `rosetta_vlm` build fails (cmake/nlohmann) | Low | `third_party/json.hpp`; else **`VLM_MODE=cli`** (zero compile, +3.3 s/scan) |
| VLM + d1 can't both be resident (NSP contention) | Med | VLM `v73-1nsp` (d1 gets the other NSP), or `VLM_MODE=cli` (frees the NPU after each scan) |
| 512×512 too small to read the sign text | **Med-High** | Fill the frame, center crop, large-type props, good light, upload a clean 512 crop; P2 tiles (§19); demo the props it reads well |
| `zetic_d1_cli serve` output shape differs | Med | Debug raw → patch `_normalize_answer`; or build `rosetta_d1` (our shape) |
| d1 pass over budget (`ContextExceeded`) | Low (0.2.2) / Med (0.2.1) | Shorter line quotes, `MAX_LINES` ↓, `--set-size 8` |
| VLM "translates" Tibetan anyway | Med | Strengthen rule 3; demo it last or skip; never claim Tibetan |
| VLM returns non-JSON / truncated | Med | `MAX_TOKENS` ↑; parse_error path still shows lines |
| USB-C link method unclear / not working | Med | UART for control + Ethernet direct cable if OK'd, or board monitor (test first) |
| Webcam not detected | Low | `CAMERA=/dev/videoN` → laptop camera via tunnel (§9.7) → Upload `samples/` |
| Downloads not finished before the venue | Med | Stage at home (§11.0); USB stick copy; the board can also `hf download` during build Wi-Fi (`python3 -m venv .venv && .venv/bin/pip install huggingface_hub`) |
| Submission rush at 8:00 | Med | Project Hub post drafted beforehand; repo public by 7:55 |
| Very short demo slot (2 min) | High | Lead with Wi-Fi off + Tibetan; one sentence per point |

### Known unknowns (fill in tonight)
- ~~Rehan app-shell Python unverified on Windows~~ → **§14.2 mock acceptance PASSES on Isaac's Mac (19:06):** both d1 shapes → category/severity + 9 importances, `--fail-every 3` recovers via retry, one JSONL line per scan, `py_compile` clean.
- **Models are NOT staged on Isaac's Mac** (SDK 0.2.2 is, in the orca `gorgonian` worktree `stage/sdk`). Rehan (on the IQ9) downloads them on the board: `scripts/stage_zetic.sh` or the §9.11 `hf download` lines (venv for `huggingface_hub`, §15 risk row).
- The app shell now imports model functions from `pipeline.py` (same §10 HTTP contract). This lets Isaac own and replace runtime functions without editing Rehan's HTTP/camera/log code in `app.py`. Real SDK/model behavior remains unverified.
- `tools/offline_audit.py` + `scripts/*` are now vendored/merged; `python3 tools/offline_audit.py .` on the Mac = 0 errors, 3 expected warnings (setup-time download URLs in `stage_zetic.sh`/`preflight.sh`). Re-run before submitting. Board rehearsal still pending.
- Pre-built code allowed? → `____`
- USB-C link setup method / Ethernet direct allowed? → `____`
- USB drive contents (ZETIC packages?) → `____`
- Board IP (Wi-Fi) `____` · USB-C link IPs `____`
- fastrpc rw OK after group change? → `____`
- `info --verify` both models OK on SDK `____`? → `____`
- VLM + d1 resident together on `v73`? → `____`
- Real `zetic_d1_cli serve` response sample → paste into §16 (expected shape in D17; open question: per-answer `probabilities` dict `{label:p}` or list?)
- VLM s/scan (engine) `____` · (cli) `____` · TTFT `____` · tok/s `____` · d1 s/scan `____` · passes `____` · peak RSS VLM `____` d1 `____`
- 512 center crop reads the props? Which fail? → `____`
- Device evidence line copied → `____`

---

## 16. Decision log

| # | Decision | Why |
|---|---|---|
| D1 | Offline camera translator for travelers | Matches the "network has crashed" pillar; simple, legible demo; past winners were simple utilities |
| D2 | General signs + **d1 decides what matters** (not menu/allergy-only) | Broader real problem (safety, permits, closures); uses Liquid's newest model type for a real reason; plain translation is commodity |
| D3 | Don't claim Tibetan/Swati | LFM3-VL-2B lists 16 languages; Liquid judges would catch it; turn it into an **honesty feature** |
| D4 | **Both models on the NPU via ZETIC Ixian Hexagon SDK** (`ZETIC-ai/LFM3-VL-2B-IQ9`, `ZETIC-ai/d1-2B-IQ9`) | Team requirement; vendor-reported 3.6× faster image→first token and 1.5× decode vs llama.cpp on IQ9; d1 natively on the NPU (~0.1 s/pass) instead of CPU Transformers; the strongest "runs on the IQ9" story for the Qualcomm judges |
| D5 | SDK **0.2.2** default, 0.2.1 staged as fallback | 0.2.2 doubles the d1 pass budget (2,048 rows); 0.2.1 is the version the starter repo ran on the board |
| D6 | Resident engines over JSON Lines pipes (`rosetta_vlm`, `zetic_d1_cli serve`); `VLM_MODE=cli` as P0 | SDK: no HTTP server, one model per process; one-shot CLI reloads ~3.3 s per call; serve is ZETIC's own pattern |
| D7 | Webcam on IQ9, laptop as display via **SSH tunnel over an isolated USB-C link**; UART for Wi-Fi off | Starter repo demo format (unplug Ethernet, Wi-Fi off live); capture + inference visibly on the IQ9 |
| D8 | stdlib Python + one HTML file; OpenCV from apt | Board has no pip; nothing to break on ARM; zero external assets |
| D9 | VLM outputs English lines only (no original text) | Fewer generated tokens → faster |
| D10 | Per-line importance = separate d1 noul questions in ONE request (≤ 2 passes) | 16 questions/pass; gives the ranked list + per-line coloring |
| D11 | Name: **rosetta** (lowercase) | Team decision |
| D12 | 512×512 center-crop PNG | SDK hard requirement; center crop puts more pixels on the sign than letterboxing a 16:9 frame; PNG keeps text edges |
| D13 | Thinking off, temperature 0, `max_tokens` 768 | SDK default; repeatable; starter rule: cap every call |
| D14 | JSONL decision log + `gate()` in code + watch mode | Judges must see inputs/decisions/actions/errors; flagship Always-On track; starter rule "code authorizes actions" |
| D15 | Own repo + vendored starter files (`zetic_run.py`, `offline_audit.py`, `preflight.sh`, MIT) | Keeps our layout; reuses the judge-authored, board-tested tooling |
| D16 | Split the Python app into `app.py` shell and `pipeline.py` model boundary | The shared-file ownership split in §0 needed a stable interface while the repository had no implementation; §10 response shapes remain unchanged. Rehan provided the mock-compatible adapter; Isaac can replace its runtime code. |
| D17 | UI JavaScript syntax checked with Node; Python execution pending | This Windows workspace has no installed Python or WSL, so `py_compile` and §14.2 cannot be run here. No board performance or NPU evidence is claimed. |
| D18 | `engine/*.cpp` + CMake used **verbatim**; compile-checked against the real SDK 0.2.2 headers (Apple clang 21, `-fsyntax-only`, exit 0, 2026-11-13 ~18:50) | No API drift between plan and headers. SDK bundles nlohmann/json 3.12.0, same as `engine/third_party` |
| D19 | `zetic_d1_cli serve` shape (from 0.2.2 README, `samples/requests.jsonl`, binary strings; **not yet seen on board**): ready `{event,protocol:"zetic-d1-serve/1",model,target,load_ms,runtime,soc,sdk_version,runtime_commit,package_dir,max_rows,inputs}` (note `sdk_version`/`max_rows`, no `nsp_count`: d1 is always 1 NSP); response `{id,model,answers:{name:{type,noul,choice,choices,confidence,score,legend,probabilities}},usage:{input_tokens,output_tokens},passes,timings:{sdk_ms,…,prefill_ms,dsp_ms,…}}`; **no `status` on success**, errors as `{"error": …}`; serve `images` must be base64 data URLs (file paths rejected) | `decide()` treats a missing status as Ok, accepts dict or list answers; normalizer converts a score `probabilities` `{label: p}` dict into the 5-element list the UI bar expects |
| D20 | `tools/zetic_run.run(sdk, model, prompt, *, image=None, audio=None, max_tokens=256, timeout=120)`; `max_tokens` 1..1024; `finish_reason` is **lowercase** (`stop`/`length`); `ok=False` on a length finish or a missing NSP evidence line | `pipeline.py` cli mode capitalizes finish, treats "generation did not finish naturally" and "missing current-request Hexagon" as **warnings** (parse + `truncated` / logged), not scan failures |
| D21 | JSONL `d1` record also carries the full per-line `importance` list (Rehan's `_record` already does this); `pipeline.py` also has `vlm_log()`, `d1_log()`, `scan_errors()` helpers | `tools/calibrate.py` needs every line's p, not just `top` |
| D22 | VLM retried once on crash/timeout/empty; d1 also restarted + retried once on crash/timeout before falling back to `decision: {"error"}` | §12 rule 2 (retry at most once); a single serve DSP exit shouldn't cost the scan its banner |
| D23 | Isaac's runtime code replaces Rehan's `pipeline.py` adapter behind the same interface (`read_and_translate`, `decide`, `gate`, `status`, `warm_engines`); `app.py`'s `scan_lock` keeps scans sequential. `pipeline.analyze()` (with its own `PIPELINE_LOCK`) is an optional one-call wrapper | §0 ownership split without touching the HTTP shell; §12 rule 6 |
| D24 | `app.py` resumes `scan_id` from the max in `logs/rosetta.jsonl` at startup; JSONL record gains `metrics: {total_s}` (additive) | Restarts reset ids to 1 → `logs/img/N.png` overwritten, duplicate ids broke `calibrate.py` labels; README end-to-end median needs total_s in the log |
| D25 | `samples/*_512.png` (12 props + `notext_512.png`) rendered from the prop PDFs: page → trim to the sign → pad square with page bg → 512×512 RGB PNG | §9.7 upload safety net + §14.1 smoke-test inputs (`tibet_512.png`). Clean renders = best case; the webcam will be worse |
| D26 | `tools/prop_key.json` (§14.4 as regexes) + `tools/make_labels.py` (prop auto-detect, Must-item acceptance report, drafts `labels.json`) + `tools/metrics.py` (README median table) | Turns B11 acceptance + B14 labels + §11.5 measurement into one command each at the board, instead of hand work during 7:20–7:40. Regexes are drafts: eyeball the printout |
| _add rows tonight (results, numbers, changes)_ | | |

---

## 17. Troubleshooting

| Symptom | Fix |
|---|---|
| `error while loading shared libraries: libzetic_ixian_hexagon.so` | `export LD_LIBRARY_PATH=$IXIAN_SDK/lib` (Engine sets it; check `IXIAN_SDK`) |
| `Unsupported` at load | Not on the IQ9, or wrong package/target; check `models/<m>/v73/manifest.json` exists |
| `DeviceError: hexrt_lib_open: map: 0x1` at load | DSP still releasing after another NPU process exited → wait a few seconds, retry |
| FastRPC / NPU open fails, "permission denied" | `ls -l /dev/fastrpc-cdsp*`; `id -nG` lacks `fastrpc` → `usermod -aG fastrpc`, **new SSH login**, restart the app |
| `InvalidArgument: an image is WxH; images must be exactly 512x512 RGB` | Image prep bypassed → check `to_model_image` / browser crop |
| `ContextExceeded` (VLM) | Raise `max_context` (engine arg 3), lower `MAX_TOKENS` |
| `ContextExceeded: rows: question N … a d1 pass holds …` | Shorter line quotes, `MAX_LINES` ↓, `--set-size 8` (SDK 0.2.1 = 1,024 rows) |
| `… is a d1 decision package: load it with Decision::fromPath` | d1 model passed to the VLM engine; swap `VL_MODEL`/`D1_MODEL` |
| `[vlm] engine exited` / timeout | Read the app console (engine stderr); Engine restarts on the next scan; check `VLM_CMD` path and `engine/build` |
| Gray "decision model unavailable" | d1 engine down or `D1_CMD` wrong; the error text says which |
| No severity banner, no error | d1 answer shape unexpected → Debug → raw `d1` → patch `_normalize_answer` |
| All importances null | Same, for noul answers (find the probability key) |
| "didn't return clean JSON" / `truncated` | Raise `MAX_TOKENS`; check raw VLM output |
| First scan very slow | Warm-up: do a throwaway scan after starting the engines |
| Black or no preview | `ls /dev/video*`; `CAMERA=/dev/video2`; camera held by another process |
| Browser camera blocked | Use `http://127.0.0.1:8000` via `ssh -L` (localhost is allowed) |
| `nmcli radio wifi off` killed my session | You ran it over Wi-Fi SSH; use the UART console or the USB-C link |
| External monitor broken | Someone installed the Adreno update; use the headless path; ask organizers about rollback |
| apt `404 Not Found` | Stale index: `sudo apt-get update`, simulate again; never add PPAs or `--fix-missing` |
| CMake picks the old SDK path | New build dir: `-B engine/build2` |

---

## 18. Pitch and judge Q&A

**One-liner:** *rosetta reads any sign with no internet, and tells you which line could hurt you.*

**"Why not just a cloud API call?"** (two sentences, specific constraint): "The people who need this most are trekkers and drivers in places with **no signal**: the Tibetan Plateau, the Ha Giang Loop, a Kyrgyz border zone. That's exactly where a cloud translator returns nothing. And the photos are often **private** (medicine boxes, permits, passports), so on-device means they never leave the board, with a flat cost per scan."

**Claims (only what's verified tonight):** runs entirely offline on the Qualcomm IQ9 (webcam + LFM3-VL-2B + d1-2B), Wi-Fi off live · both models on the **Hexagon NPU via ZETIC's Ixian Hexagon SDK** (show the device evidence; "the heavy compute runs on the NPU, with a little host-side work") · **d1 returns calibrated decisions** (severity, category, action required, per-line importance) in ~2 NPU passes with no text generation · **honest by design:** unsupported scripts flagged, never invented · **measured** TTFT / tok/s / d1 ms / peak memory **(fill in the truth)**.

**Likely questions**
- *Why two models?* Generation is good at reading and translating. d1 gives calibrated probabilities for decisions: no tokens, consistent, thresholdable, 16 questions per NPU pass.
- *Why not ask the VLM to rate severity too?* Free-text ratings are uncalibrated and inconsistent; d1 gives ranked probabilities in one pass, and code gates on them.
- *Why ZETIC rather than GenieX?* Vendor-reported 3.6× faster image-to-first-token and 1.5× decode on this board, and d1 runs natively on the NPU instead of the CPU. Quote our own numbers.
- *What's the threshold?* Calibrated on our props with a held-out check (`tools/calibrate.py`), not a default 0.5.
- *Languages?* The 16 LFM3-VL-2B supports; anything else is flagged unreadable.
- *What does the agent do on its own?* Watch mode: scans when a new sign holds still, and alerts only when the gate fires. Every decision is in the JSONL log.
- *What's next?* A phone app (LFM3 and ZETIC target Snapdragon phones), read-aloud of the top warning with LFM3-Audio (ZETIC supports TTS), thresholds calibrated on real signage, more languages as Liquid adds them.

---

## 19. Stretch goals
Only after §14.5 is fully checked: (1) **tile mode**: overview + 2×2 zoomed 512 tiles in one VLM turn (5 images = 1,280 rows, needs `max_context` 4096) for small text · (2) d1 also sees the 512 image (`images` in the serve request) for visual danger cues · (3) original text beside each line · (4) read-aloud of the top warning via `ZETIC-ai/LFM3-Audio-2B-IQ9` TTS (one model per process → separate engine) · (5) watch-mode endurance run (10 min) with RSS/latency over time for the Olympics pillar.

---

## 20. Glossary
**IQ9 / IQ-9075 EVK**: Qualcomm Dragonwing edge dev kit (QCS9075) · **Hexagon / HTP / NSP**: Qualcomm NPU; the IQ9 has two NSPs (`v73` package = both, `v73-1nsp` = one) · **ZETIC engine**: ZETIC's own Hexagon runtime · **Ixian Hexagon SDK**: ZETIC's SDK for it on the IQ9 (C++ `LLM` / `Decision`, CLIs); formerly "ZETIC.MLange Hexagon" · **ZETIC.MLange**: ZETIC's broader on-device AI platform · **FastRPC**: the CPU↔DSP RPC layer (`/dev/fastrpc-cdsp*`, group `fastrpc`) · **device evidence**: `hexrt open … v73 … HEXRT_NSP2=1` log line · **GenieX**: Qualcomm's GenAI runtime (the starter repo's reference; our emergency fallback) · **d1 / systemOne**: Liquid's decision model and its one-pass API · **noul**: yes/no → P(yes) · **choice**: one of N · **score**: ordered levels · **pass**: one d1 NPU forward over state + ≤16 questions · **UART**: micro-USB serial console to the board · **JSONL**: one JSON object per line.

---

## 21. Sources
- Event: https://luma.com/0nsdnkoa · organizer email "Your pre-flight briefing" (Nov 10)
- **Organizers' starter repo:** https://github.com/heath0xFF/cleared-for-takeoff-hackathon (`README.md`, `AGENTS.md`, `docs/judging.md`, `docs/developer-guide.md`, `docs/hardware.md`, `docs/offline-readiness.md`, `examples/zetic-lfm/`)
- Submission form: https://submissions.loggia.sh/events/cleared-for-takeoff · Arduino Project Hub: https://projecthub.arduino.cc/
- **Ixian Hexagon SDK:** https://github.com/zetic-ai/IxianHexagon (README, releases 0.2.0/0.2.1/0.2.2, `samples/requests.jsonl`); headers read from the 0.2.2 tarball
- **ZETIC IQ9 models:** https://huggingface.co/collections/ZETIC-ai/lfm3-and-d1-on-dragonwing-iq9 · https://huggingface.co/ZETIC-ai/LFM3-VL-2B-IQ9 · https://huggingface.co/ZETIC-ai/d1-2B-IQ9
- ZETIC sample apps (fixtures only; older gated layout): https://github.com/zetic-ai/LFM3-zetic-apps
- LFM3: https://www.liquid.ai/blog/lfm3 · LFM3-VL-2B: https://huggingface.co/LiquidAI/LFM3-VL-2B · GGUFs: https://huggingface.co/LiquidAI/LFM3-VL-2B-GGUF
- d1-2B: https://huggingface.co/LiquidAI/d1-2B
- GenieX (fallback): https://github.com/qualcomm/geniex · https://geniex.aihub.qualcomm.com/
- IQ-9075 setup: https://dragonwingdocs.qualcomm.com/Ubuntu/devices/iq9075-evk/set-up-the-device
- Past Liquid hackathons: https://www.liquid.ai/en/blog/hack01-hack-the-edge-take-the-dare · https://www.liquid.ai/blog/hack02-lfms-with-eyes-what-happened-who-won-whats-next

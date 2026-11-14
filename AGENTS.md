# AGENTS.md

**Read `rosetta-master-plan.md` first.** It is the single source of truth. When reality disagrees with it (a command fails, an API answers differently, a number is wrong), fix the code **and** update the plan (§15 known unknowns, §16 decision log) so the other agent sees it.

## What this is
**rosetta** (always lowercase): point a USB webcam on a Qualcomm Dragonwing IQ-9075 (IQ9) at a foreign-language sign, menu, label or medicine box. It **translates** the text, then **decides what matters** (severity, category, action required, per-line importance). **Zero internet.** Built for the Qualcomm × Liquid AI "Cleared for Takeoff" hackathon, Nov 13 2026 (build 6:15–8:15 PM PT, submit 8:00–8:30).

Two Liquid LFM3 models, both on the IQ9 Hexagon NPU via **ZETIC's Ixian Hexagon SDK 0.2.2** (0.2.1 fallback):
1. **LFM3-VL-2B** (`ZETIC-ai/LFM3-VL-2B-IQ9`): 512×512 photo → JSON `{languages, summary, lines, unreadable, answer}`.
2. **d1-2B** (`ZETIC-ai/d1-2B-IQ9`): one call over the English lines → calibrated `category`, `severity` (5 levels), `action`, `personal`, `line_i` importance. No token generation; ≤16 questions per NPU pass.

Pipeline per scan (sequential): capture → center-crop to **exactly 512×512 PNG** in `/dev/shm/rosetta/` → VLM → d1 → normalize → `gate()` (code decides alert) → one flushed JSONL record in `logs/rosetta.jsonl` → render.

## Where the spec is (plan sections)
- §5 architecture · §8 SDK/C++ API · §9 build spec with **reference code to use verbatim** (`Engine`, `parse_model_json`, `SYSTEM_PROMPT`, `build_questions`, `_normalize_answer`, `gate`, `rosetta_vlm.cpp`) · §10 API contracts · §12 rules · §14 acceptance.
- Build in the **priority order of §9.12** (B1 mocks → B2 app core → B3 UI core → …). P0 = demo can't happen without it, P1 = what wins, P2 = polish. Never start P1 while a P0 is broken. **Cut line 7:40 PM.**

## Ownership (§0)
- **Isaac's agent:** model/runtime side: `engine/`, IQ9 setup, `app.py` pipeline functions (`read_and_translate`, `decide`, `Engine`, normalizer, constants).
- **Rehan's agent:** app shell and UX: `app.py` HTTP/camera/log layer, `index.html`, `tools/mock_engine.py`, demo, submission.
- `app.py` is shared: pull before editing, small diffs, don't reformat the other half.

## Layout
```
app.py            stdlib HTTP server + pipeline + Engine supervisor + JSONL log (OpenCV optional)
index.html        single file, inline CSS/JS, zero external requests
engine/           rosetta_vlm.cpp (+ rosetta_d1.cpp, P2), CMakeLists.txt, third_party/nlohmann/json.hpp
tools/            mock_engine.py, zetic_run.py*, offline_audit.py*, openai_vlm_bridge.py, calibrate.py, make_labels.py + prop_key.json, metrics.py
scripts/          preflight.sh*, stage_zetic.sh, setup_board.sh, run.sh
samples/          512×512 PNGs of every prop (upload-demo safety net)
logs/             rosetta.jsonl + img/ (committed, keep small)
models/ sdk/ stage/   gitignored, never commit
```
`*` = vendored from `heath0xFF/cleared-for-takeoff-hackathon` (MIT): keep the MIT header + `# Vendored from heath0xFF/cleared-for-takeoff-hackathon (MIT)`.

## Non-negotiable rules (full list: plan §12)
1. **Offline at runtime.** No CDNs, web fonts, remote APIs, telemetry, or runtime downloads. Only loopback + SSH tunnel + child engine pipes. `HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1`. Run `python3 tools/offline_audit.py .` before submitting.
2. **Cap and validate every LFM call:** always send `max_tokens`; reject status ≠ Ok / zero tokens / empty text; flag `finish ≠ Stop`; retry once max. Errors are data (logged + shown), never crashes.
3. **Stdlib-first.** No FastAPI/Flask/React/bundlers. Only extra deps: OpenCV (apt), Ixian SDK, nlohmann/json.
4. **Don't break §10 contracts** without updating `index.html` and the plan in the same change.
5. **Code authorizes actions.** Models propose; `gate()` decides; log proposals, decisions, actions, errors separately.
6. **Models run sequentially** (VLM, then d1). One model per process (SDK limit). Images must be exactly 512×512 RGB.
7. **Fail soft.** d1 down → translation still shows. Camera down → upload. Engine crash → restart. No exception kills the server.
8. **No overclaiming:** never "entirely on the NPU", never claim unsupported languages (Tibetan etc. → `unreadable`), never quote vendor numbers as ours. If a fallback runtime is active, UI says so.
9. **Prompts are code:** changes to `SYSTEM_PROMPT`, `CATEGORIES`, `SEVERITY`, `build_questions`, thresholds → check against §14.4 and log in §16. No hard-coded 0.5 in the final demo; use calibrated `IMPORTANCE_THRESHOLD`.
10. **Board safety:** ask before installs/network/group changes/deletes. Never `apt upgrade`, never install `qcom-adreno1`, never `chmod` device nodes, never type passwords into commands. Copy, never move, from USB drives.
11. **Time-box 20 minutes,** then take the §15 fallback and log it.

## Dev loop (Mac, no IQ9; SDK only runs on the IQ9)
```bash
VLM_MODE=engine VLM_CMD="python3 tools/mock_engine.py vlm" D1_CMD="python3 tools/mock_engine.py d1" CAMERA=none python3 app.py
python3 -m py_compile app.py tools/*.py                                              # before handoff
clang++ -std=c++17 -fsyntax-only -I stage/sdk/include -I engine/third_party engine/*.cpp   # C++ syntax check
```
Mock acceptance (§14.2): both d1 shapes (`--shape dict|list`) → non-null category/severity + 9 importances; `--fail-every 3` recovers; zero non-localhost requests; one JSONL line per scan.

## Board
Login `ubuntu` / typed by a human. Run: `scripts/run.sh` (sets `IXIAN_SDK`, offline env, `python3 app.py`). Laptop views it via `ssh -N -L 127.0.0.1:8000:127.0.0.1:8000 "$IQ9_HOST"`. Env vars: plan §10.6. Troubleshooting: plan §17.

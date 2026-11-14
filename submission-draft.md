# rosetta — Arduino Project Hub draft

## What it does

rosetta helps travelers understand foreign-language signs when they have no connection. A USB webcam captures a sign, menu, notice, label, or medicine box. LFM3-VL-2B reads and translates the text. d1-2B assesses category, severity, required action, and the importance of each translated line. The page puts the lines that matter most at the top and calls out any script it could not read confidently.

The target device is a Qualcomm Dragonwing IQ-9075 EVK. The planned inference runtime is ZETIC's Ixian Hexagon SDK. The page and app make no external requests at runtime. The browser connects to the board over a local SSH tunnel.

## Why it matters

A cloud translator is unavailable on a remote trail, on a rural road, or when roaming fails. Even a plain translation leaves the traveler to spot the important deadline, hazard, permit requirement, fee, or dosage limit. rosetta gives a short next step while preserving the full translation. Its decision model proposes probabilities; application code decides whether to show an alert.

## How it works

1. The board camera or browser upload provides an image. The app center-crops it to a lossless 512×512 PNG.
2. The VLM translates the text to English lines and reports unreadable regions.
3. d1 evaluates the translated lines in one JSONL request and returns calibrated decisions.
4. The app applies its alert gate and writes one flushed JSONL record with input, model proposals, decision, action, timings, and errors.
5. The local page shows the severity, ranked lines, full translation, unreadable regions, and debug data. Watch mode can scan a stable new sign automatically.

## Parts and software

- Qualcomm Dragonwing IQ-9075 EVK
- USB webcam
- LFM3-VL-2B and d1-2B IQ9 packages
- ZETIC Ixian Hexagon SDK 0.2.2 (0.2.1 fallback)
- Python 3 stdlib, OpenCV from Ubuntu packages, C++ engine for the resident VLM

## Run

Follow `README.md` and `rosetta-master-plan.md` in the public repository. On the board, run `scripts/run.sh`, then open `http://127.0.0.1:8000` over the SSH tunnel. The model files and SDK are staged locally before disconnecting the network.

## Evidence to fill after board testing

- Repository link: [public GitHub URL]
- Model and SDK verification: [command output]
- NPU device evidence: [HEXRT line]
- Five-scan medians: VLM [ ] s, TTFT [ ] ms, decode [ ] tok/s, d1 [ ] s, end to end [ ] s
- Peak memory: VLM [ ] MB, d1 [ ] MB
- Offline rehearsal: [Wi-Fi-off cold start and three successful scans]
- Photo/video: [actual device demo]

## Code

Paste the full source listing in the Project Hub post as required by the event, along with the public repository link. Include `app.py`, `pipeline.py`, `index.html`, the engine source, mock engine, and scripts after board integration is complete.

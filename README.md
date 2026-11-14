# rosetta

**rosetta reads any sign with no internet, and tells you which line could hurt you.**

Point a webcam at a foreign-language sign, notice, menu, label or medicine box. rosetta translates the text, then decides what matters: how serious it is, what you must do, and which lines are critical. It runs fully offline on a Qualcomm Dragonwing IQ-9075.

- **LFM3-VL-2B** (`ZETIC-ai/LFM3-VL-2B-IQ9`) reads and translates the image.
- **d1-2B** (`ZETIC-ai/d1-2B-IQ9`) returns calibrated decisions: category, severity, action required, and importance per line.
- The intended board runtime uses ZETIC's Ixian Hexagon SDK on the IQ9 Hexagon NPU. Board execution has not yet been verified in this workspace.
- Scripts the model can't read (e.g. Tibetan) are flagged as unreadable, never guessed.

## Run

```bash
# Mac, with mock engines
VLM_MODE=engine VLM_CMD="python3 tools/mock_engine.py vlm" D1_CMD="python3 tools/mock_engine.py d1" CAMERA=none python3 app.py

# IQ9
scripts/run.sh
```

Open <http://127.0.0.1:8000> (through an SSH tunnel when running on the board). The app also accepts a client-cropped 512×512 PNG upload when the board camera is unavailable. If OpenCV is missing, only RGB/RGBA 512×512 PNG uploads are accepted.

## Implementation status

- **Done, verified on a Mac with mock engines:** HTTP/camera/log shell (`app.py`), model pipeline + engine supervisor (`pipeline.py`), single-file UI (`index.html`), watch mode. Plan §14.2 mock acceptance passes with both d1 response shapes, engine crash recovery (`--fail-every 3`) and one JSONL line per scan. `tools/offline_audit.py .`: 0 errors.
- **Not yet verified:** execution on the IQ9 NPU, real model output quality, and the board metrics below. Until then, nothing here claims NPU numbers.
- `samples/`: 512×512 PNGs of every prop (upload fallback, smoke-test inputs), plus the source PDFs.

## Tools

| Tool | Use |
|---|---|
| `tools/mock_engine.py vlm\|d1` | fake engines for Mac development |
| `tools/make_labels.py` | after prop scans: checks each scan against the plan §14.4 "Must" list and drafts `tools/labels.json` (answer key in `tools/prop_key.json`) |
| `tools/calibrate.py` | picks `IMPORTANCE_THRESHOLD` from labeled scans |
| `tools/metrics.py` | prints the metrics table below from `logs/rosetta.jsonl` (`--url` adds peak RSS) |
| `tools/offline_audit.py .` | flags anything that could reach the network |

## Metrics

_Measured on the board, medians of ≥5 scans. To be filled in with `python3 tools/metrics.py --since <first real scan> --skip-first --url http://127.0.0.1:8000`._

| Metric | Value |
|---|---|
| VLM read (s/scan) | — |
| TTFT (ms) | — |
| Decode (tok/s) | — |
| d1 (s/scan, passes) | — |
| End-to-end (s) | — |
| Peak RSS VLM / d1 (MB) | — |

Runtime: ZETIC Ixian Hexagon SDK 0.2.2 (0.2.1 fallback). Models: `ZETIC-ai/LFM3-VL-2B-IQ9` and `ZETIC-ai/d1-2B-IQ9`, precision as shipped in those IQ9 packages. Numbers above are filled only from our own board runs; none are quoted from vendor docs.

## Decision log

Written automatically, no extra step. Every scan appends one flushed and fsynced JSONL line to `logs/rosetta.jsonl` with separate fields for the input (`input`, plus the 512×512 image saved as `logs/img/<scan_id>.png`), the model proposals (`vlm.proposal`, `d1` scores), the code decision (`decision`, from `gate()`), the executed action (`action`), `errors`, and timing (`metrics`). Follow-up chat goes to `logs/chat.jsonl`. Errors are recorded as data, and the server keeps running.

## Thresholds

`IMPORTANCE_THRESHOLD` and the `action_p` cut in `gate()` default to 0.5 as **uncalibrated placeholders**. `tools/calibrate.py` sets the threshold from labeled prop scans; until that runs on board output, treat the alert decision as uncalibrated.

## Offline status

- No CDNs, web fonts, remote APIs or telemetry. The UI is one local file, and the server binds to loopback only. The laptop reaches it through an SSH tunnel.
- `python3 tools/offline_audit.py .` reports 0 errors. Its 3 warnings are URLs in `scripts/stage_zetic.sh` and `scripts/preflight.sh`, which are one-time setup scripts run with internet *before* the demo, never at runtime.
- `scripts/run.sh` sets `HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1`.
- Demo: board Wi-Fi off (`sudo nmcli radio wifi off`, Ethernet unplugged) from the UART console, then scan.

See [`rosetta-master-plan.md`](rosetta-master-plan.md) for the full design.

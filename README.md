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

The mock engines, HTTP/camera/log shell, model adapter, watch loop, and single-file UI are present. `pipeline.py` is the model boundary for Isaac's board integration. Python acceptance and real NPU execution have not been run here because this Windows workspace has no Python installation. The inline JavaScript passed a Node syntax check. Use §14.2 of the master plan on a machine with Python, then complete the IQ9 smoke tests and offline audit before submission.

## Metrics

_Measured on the board, medians of ≥5 scans. To be filled in._

| Metric | Value |
|---|---|
| VLM read (s/scan) | — |
| TTFT (ms) | — |
| Decode (tok/s) | — |
| d1 (s/scan, passes) | — |
| End-to-end (s) | — |
| Peak RSS VLM / d1 (MB) | — |

See [`rosetta-master-plan.md`](rosetta-master-plan.md) for the full design.

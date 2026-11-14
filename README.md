# rosetta

**rosetta reads any sign with no internet, and tells you which line could hurt you.**

Point a webcam at a foreign-language sign, notice, menu, label or medicine box. rosetta translates the text, then decides what matters: how serious it is, what you must do, and which lines are critical. It runs fully offline on a Qualcomm Dragonwing IQ-9075.

- **LFM3-VL-2B** (`ZETIC-ai/LFM3-VL-2B-IQ9`) reads and translates the image.
- **d1-2B** (`ZETIC-ai/d1-2B-IQ9`) returns calibrated decisions: category, severity, action required, and importance per line.
- Both run on the IQ9 Hexagon NPU through ZETIC's Ixian Hexagon SDK.
- Scripts the model can't read (e.g. Tibetan) are flagged as unreadable, never guessed.

## Run

```bash
# Mac, with mock engines
VLM_MODE=engine VLM_CMD="python3 tools/mock_engine.py vlm" D1_CMD="python3 tools/mock_engine.py d1" CAMERA=none python3 app.py

# IQ9
scripts/run.sh
```

Open <http://127.0.0.1:8000> (through an SSH tunnel when running on the board).

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

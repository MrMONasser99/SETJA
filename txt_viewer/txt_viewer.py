import os, tempfile
AR_OUT_PATH = os.path.join(tempfile.gettempdir(), "setja_ar.txt")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge.bridge_ocr_t import BridgeConfig, run_bridge, wait_for_ports

_last_err = {"key": None}

def _print_error(kind: str, info: str):
    if info == _last_err["key"]:
        return
    _last_err["key"] = info
    print(info)


def _print_result(cur_text: str, mt_j: dict):
    lines = mt_j.get("lines")
    if not lines and mt_j.get("text"):
        lines = [mt_j.get("text")]

    ms = float(mt_j.get("ms") or 0.0)
    waiting = bool(mt_j.get("waiting_for_stability", False))

    if waiting or not lines:
        ar_text = ""
    else:
        ar_text = " ".join(
            ln.strip() for ln in lines if (ln or "").strip()
        )

    tmp = AR_OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(ar_text)
    os.replace(tmp, AR_OUT_PATH)

    print("-" * 60)
    print(f"EN: {cur_text}")

    if waiting or not lines:
        print("AR: (waiting_for_stability)")
    else:
        print("AR:")
        for ln in lines:
            if (ln or "").strip():
                print(ln)

    print(f"MT_time: {ms:.2f} ms")
    print("-" * 60)


def main():
    cfg = BridgeConfig(
        ocr_url="http://127.0.0.1:15188/ocr_shm",
        mt_url="http://127.0.0.1:15199/translate",
        lang="en",
        gpu=1,
        poll_interval_ms=80,
        skip_empty=True,
        unique_stream_per_text=True,
        stream_id="bridge_ocr",
        similarity_threshold=0.8,
        cooldown_sec=1.0,
    )

    wait_for_ports(
        [
            ("OCR", "127.0.0.1", 15188),
            ("Translator", "127.0.0.1", 15199),
        ],
        label="[WAIT]",
        check_interval=0.4,
    )
    print("SETJA Ready to Translate")

    run_bridge(cfg, on_result=_print_result, on_error=_print_error)


if __name__ == "__main__":
    main()

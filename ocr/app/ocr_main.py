import os
# Disable PIR to prevent RuntimeError in newer Paddle versions (must be set before imports)
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runtime.ocr_bootstrap import bootstrap_env
bootstrap_env(app_folder="ocr", venv_folder="ocr_env")

import paddle
try:
    paddle.set_flags({'FLAGS_enable_pir_api': 0, 'FLAGS_enable_pir_in_executor': 0})
except Exception:
    pass

import argparse

import core.runtime.ocr_config as CFG
import core.runtime.ocr_engine as OCR
import core.services.ocr_poller as ocr_poller
import core.api.ocr_api


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=CFG.HOST)
    ap.add_argument("--port", type=int, default=CFG.PORT)
    args = ap.parse_args()

    ocr_poller.start()

    OCR.POOL.get(lang="en", use_gpu=True, use_angle_cls=False)
    print("OCR RUNNING | GPU READY", flush=True)

    httpd = core.api.ocr_api.create_server(args.host, args.port)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

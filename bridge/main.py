import os
import subprocess
import sys
from pathlib import Path

from bridge_ocr_t import wait_for_ports

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

CAPTURE_CMD = ROOT / "capture" / "capture_launcher.cmd"
OCR_PY = ROOT / "ocr" / "app" / "ocr_main.py"
TRANSLATOR_DIR = ROOT / "translator"
VIEWER_PY = ROOT / "txt_viewer" / "txt_viewer.py"


def _run_background(args: list, cwd: Path):
    subprocess.Popen(args, cwd=str(cwd), shell=False)


def main():
    # 1) Capture (C++ executables)
    _run_background(["cmd.exe", "/c", "call", str(CAPTURE_CMD)], CAPTURE_CMD.parent)

    # 2) OCR
    _run_background([PYTHON, "-u", str(OCR_PY)], ROOT)

    # 3) Translator
    _run_background([PYTHON, "-u", "-m", "app.t_main"], TRANSLATOR_DIR)

    wait_for_ports(
        [
            ("OCR", "127.0.0.1", 15188),
            ("Translator", "127.0.0.1", 15199),
        ],
        label="[WAIT]",
        check_interval=0.4,
    )

    # 4) Viewer (needs PYTHONPATH=ROOT to import bridge)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    subprocess.call(
        [PYTHON, "-u", str(VIEWER_PY)],
        cwd=str(VIEWER_PY.parent),
        shell=False,
        env=env,
    )


if __name__ == "__main__":
    main()

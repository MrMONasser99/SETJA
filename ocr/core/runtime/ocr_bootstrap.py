import os
import sys
from pathlib import Path

def bootstrap_env(app_folder: str, venv_folder: str):
    localapp = os.environ.get("LOCALAPPDATA") or str(Path.home())

    root = Path(localapp) / "SETJA" / app_folder
    cache = root / f"{app_folder}_cache"

    root.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)

    os.environ["USERPROFILE"] = str(cache)
    os.environ["HOME"] = str(cache)

    os.chdir(str(root))

    venv_python = root / venv_folder / "Scripts" / "python.exe"
    if venv_python.exists():
        cur = Path(sys.executable).resolve()
        target = venv_python.resolve()
        if cur != target:
            os.execv(str(target), [str(target), *sys.argv])

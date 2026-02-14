import os
import json
import time
import tempfile

REGION_FILE = os.environ.get("SETJA_REGION_FILE") or os.path.join(
    tempfile.gettempdir(), "setja_region.json"
)

SETTINGS_FILE = os.environ.get("SETJA_SETTINGS_FILE") or os.path.join(
    os.path.dirname(REGION_FILE), "setja_settings.json"
)


def _atomic_write_json(path: str, data: dict) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read_settings(path: str = SETTINGS_FILE) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def clear_on_exit_enabled() -> bool:
    s = _read_settings()
    v = s.get("clear_region_on_exit", None)
    if isinstance(v, bool):
        return v

    env_v = os.environ.get("SETJA_CLEAR_REGION_ON_EXIT", "").strip().lower()
    return env_v in ("1", "true", "yes", "on")


def clear_region_cache(path: str = REGION_FILE) -> bool:
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
    except Exception:
        pass
    return False


def xywh_to_ltrb(x: int, y: int, w: int, h: int):
    x = int(x); y = int(y); w = int(w); h = int(h)
    return x, y, x + w, y + h


def write_region_xywh(x: int, y: int, w: int, h: int, path: str = REGION_FILE) -> dict:
    l, t, r, b = xywh_to_ltrb(x, y, w, h)
    payload = {
        "x": int(x), "y": int(y), "width": int(w), "height": int(h),
        "left": int(l), "top": int(t), "right": int(r), "bottom": int(b),
        "ts": time.time(),
    }
    _atomic_write_json(path, payload)
    return payload


def read_region_ltrb(path: str = REGION_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if all(k in d for k in ("left", "top", "right", "bottom")):
            return (int(d["left"]), int(d["top"]), int(d["right"]), int(d["bottom"]))
        if all(k in d for k in ("x", "y", "width", "height")):
            return xywh_to_ltrb(d["x"], d["y"], d["width"], d["height"])
        return None
    except Exception:
        return None

def format_region_user(payload: dict) -> str:
    return (
        "Selection saved"
    )

def region_file_mtime(path: str = REGION_FILE):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None

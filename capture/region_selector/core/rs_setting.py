import os
import json
from typing import Any, Dict, Optional


# Path

def get_settings_path() -> str:
    override = os.environ.get("SETJA_SETTINGS_FILE")
    if override:
        return override

    localapp = os.environ.get("LOCALAPPDATA")
    if not localapp:
        raise RuntimeError("LOCALAPPDATA not found")

    return os.path.join(localapp, "SETJA", "capture", "setja_settings.json")


# Core IO (Atomic)

def _atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp, path)


def read_settings(path: Optional[str] = None) -> Dict[str, Any]:
    path = path or get_settings_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def write_settings(settings: Dict[str, Any], path: Optional[str] = None) -> None:
    path = path or get_settings_path()
    _atomic_write_json(path, settings)


# Typed helpers

def get_bool(key: str, default: bool = False, path: Optional[str] = None) -> bool:
    s = read_settings(path)
    v = s.get(key, default)
    return v if isinstance(v, bool) else default


def set_bool(key: str, value: bool, path: Optional[str] = None) -> None:
    s = read_settings(path)
    s[key] = bool(value)
    write_settings(s, path)


def get_str(key: str, default: str = "", path: Optional[str] = None) -> str:
    s = read_settings(path)
    v = s.get(key, default)
    if isinstance(v, str) and v.strip():
        return v.strip()
    return default


def set_str(key: str, value: str, path: Optional[str] = None) -> None:
    s = read_settings(path)
    s[key] = str(value).strip()
    write_settings(s, path)


# Cache settings

def is_clear_region_on_exit_enabled(path: Optional[str] = None) -> bool:
    return get_bool("clear_region_on_exit", default=False, path=path)


def set_clear_region_on_exit(enabled: bool, path: Optional[str] = None) -> None:
    set_bool("clear_region_on_exit", enabled, path=path)


# Hotkey settings

DEFAULT_HOTKEY = "ctrl+f12"

def get_hotkey(path: Optional[str] = None, default: str = DEFAULT_HOTKEY) -> str:
    return get_str("hotkey", default=default, path=path).lower()


def set_hotkey(hotkey: str, path: Optional[str] = None) -> None:
    set_str("hotkey", hotkey.lower(), path=path)

SAFE_HOTKEY_PRESETS = [
    "ctrl+f12",
    "ctrl+f11",
    "ctrl+f10",
    "ctrl+f9",
    "ctrl+f8",
    "ctrl+f7",
    "ctrl+f6",
]

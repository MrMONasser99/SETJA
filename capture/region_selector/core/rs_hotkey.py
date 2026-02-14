import ctypes
from ctypes import wintypes
from PySide6.QtCore import QAbstractNativeEventFilter, QTimer
from core.rs_setting import get_hotkey

user32 = ctypes.windll.user32

WM_HOTKEY = 0x0312
HOTKEY_ID = 1

MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000


def _vk_from_fkey(n: int) -> int:
    if 1 <= n <= 12:
        return 0x70 + (n - 1)
    raise ValueError("F key must be between F1 and F12")

def pretty_hotkey(hk: str) -> str:
    return "+".join(p.capitalize() for p in (hk or "").split("+"))

def _parse_hotkey(s: str) -> int:
    s = (s or "").strip().lower().replace(" ", "")
    if not s:
        s = "ctrl+f12"

    parts = s.split("+")
    if len(parts) != 2 or parts[0] != "ctrl" or not parts[1].startswith("f"):
        raise ValueError("Only 'ctrl+f1' .. 'ctrl+f12' supported")

    try:
        n = int(parts[1][1:])
    except Exception:
        raise ValueError("Invalid F key")

    return _vk_from_fkey(n)


class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey):
        super().__init__()
        self.on_hotkey = on_hotkey

    def nativeEventFilter(self, eventType, message):
        if "windows" not in str(eventType):
            return False, 0

        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
        except Exception:
            return False, 0

        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            QTimer.singleShot(0, self.on_hotkey)
            return True, 0

        return False, 0


def register() -> str:
    hotkey_str = get_hotkey()

    try:
        vk = _parse_hotkey(hotkey_str)
        effective = hotkey_str
    except Exception:
        effective = "ctrl+f12"
        vk = _parse_hotkey(effective)
        print(f"[WARN] Invalid hotkey '{hotkey_str}', fallback to Ctrl+F12")

    ok = user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_NOREPEAT, vk)
    if not ok:
        err = ctypes.get_last_error()
        pretty_eff = "+".join(p.capitalize() for p in effective.split("+"))
        raise SystemExit(f"Failed to register {pretty_eff}. WinError={err}")

    pretty = "+".join(p.capitalize() for p in effective.split("+"))
    print(f"Global hotkey registered: {pretty}")

    return effective


def unregister():
    user32.UnregisterHotKey(None, HOTKEY_ID)
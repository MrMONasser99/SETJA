import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from ui.rs_overlay import RegionSelector
from core.rs_hotkey import HotkeyFilter, register, unregister, pretty_hotkey

from core.rs_cache import (
    write_region_xywh,
    REGION_FILE,
    clear_on_exit_enabled,
    clear_region_cache,
    format_region_user,
)

def run_blocking(min_size: int = 5) -> int:
    if sys.platform != "win32":
        raise SystemExit("Windows only")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = RegionSelector(min_size=min_size)

    effective_hotkey = register()
    pretty = pretty_hotkey(effective_hotkey)

    if os.environ.get("SETJA_DEBUG") == "1":
        print(f"Sharing region via: {REGION_FILE}")

    def on_selected(r: dict):
        payload = write_region_xywh(r["x"], r["y"], r["width"], r["height"])

        print(format_region_user(payload))

        if os.environ.get("SETJA_DEBUG") == "1":
            print(payload)

        window.cancel(reopen_hint=pretty)

    window.selected.connect(on_selected)

    hotkey_filter = HotkeyFilter(window.show_selector)
    app.installNativeEventFilter(hotkey_filter)

    def cleanup():
        unregister()
        if clear_on_exit_enabled():
            if clear_region_cache():
                print("Region cache cleared")

    app.aboutToQuit.connect(cleanup)

    QTimer.singleShot(0, window.show_selector)
    return app.exec()
import sys

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QLabel, QComboBox, QPushButton
)

from core.rs_setting import (
    SAFE_HOTKEY_PRESETS,
    set_hotkey,
    get_hotkey,
)

from core.rs_hotkey import register, unregister


class HotkeyTestUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SETJA Hotkey Test")
        self.setFixedSize(260, 120)

        layout = QVBoxLayout(self)

        self.label = QLabel("Choose hotkey for Region Selector:")
        layout.addWidget(self.label)

        self.combo = QComboBox()
        self.combo.addItems(
            [hk.upper().replace("+", " + ") for hk in SAFE_HOTKEY_PRESETS]
        )
        layout.addWidget(self.combo)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_hotkey)
        layout.addWidget(self.apply_btn)

        # select current hotkey
        current = get_hotkey()
        if current in SAFE_HOTKEY_PRESETS:
            self.combo.setCurrentIndex(SAFE_HOTKEY_PRESETS.index(current))

    def apply_hotkey(self):
        chosen_pretty = self.combo.currentText()
        chosen = chosen_pretty.lower().replace(" ", "")

        print(f"[UI] User selected: {chosen}")

        set_hotkey(chosen)
        print("[UI] Saved. Restart rs_main to apply.")

        pretty = "+".join(p.capitalize() for p in chosen.split("+"))
        print(f"[UI] Effective hotkey now: {pretty}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = HotkeyTestUI()
    w.show()
    sys.exit(app.exec())

import os
import json
import tempfile

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QCheckBox, QMessageBox
)

from core.rs_setting import (
    get_settings_path,
    is_clear_region_on_exit_enabled,
    set_clear_region_on_exit,
)

REGION_FILE = os.environ.get("SETJA_REGION_FILE") or os.path.join(
    tempfile.gettempdir(), "setja_region.json"
)


def region_exists() -> bool:
    return os.path.exists(REGION_FILE)


def read_region_text() -> str:
    try:
        with open(REGION_FILE, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), ensure_ascii=False, indent=2)
    except Exception:
        return "(no region file or invalid json)"


def clear_region_file() -> bool:
    try:
        if os.path.exists(REGION_FILE):
            os.remove(REGION_FILE)
            return True
    except Exception:
        pass
    return False


class SettingsTestUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SETJA Settings Test (Cache)")

        layout = QVBoxLayout(self)

        self.path_lbl = QLabel(f"Settings: {get_settings_path()}")
        layout.addWidget(self.path_lbl)

        self.region_lbl = QLabel(f"Region file: {REGION_FILE}")
        layout.addWidget(self.region_lbl)

        self.toggle = QCheckBox("Clear region cache on exit")
        self.toggle.setChecked(is_clear_region_on_exit_enabled())
        self.toggle.stateChanged.connect(self.on_toggle_changed)
        layout.addWidget(self.toggle)

        self.status = QLabel("")
        layout.addWidget(self.status)

        btn_refresh = QPushButton("Refresh status")
        btn_refresh.clicked.connect(self.refresh_status)
        layout.addWidget(btn_refresh)

        btn_show = QPushButton("Show region.json contents")
        btn_show.clicked.connect(self.show_region)
        layout.addWidget(btn_show)

        btn_clear = QPushButton("Delete region.json now")
        btn_clear.clicked.connect(self.delete_region_now)
        layout.addWidget(btn_clear)

        self.refresh_status()

    def on_toggle_changed(self):
        enabled = self.toggle.isChecked()
        set_clear_region_on_exit(enabled)
        self.refresh_status()

    def refresh_status(self):
        enabled = is_clear_region_on_exit_enabled()
        exists = region_exists()
        self.status.setText(
            f"clear_on_exit = {enabled} | region_exists = {exists}"
        )

    def show_region(self):
        text = read_region_text()
        QMessageBox.information(self, "Region file contents", text)

    def delete_region_now(self):
        ok = clear_region_file()
        QMessageBox.information(self, "Delete region.json", "Deleted" if ok else "Not found")
        self.refresh_status()


if __name__ == "__main__":
    app = QApplication([])
    w = SettingsTestUI()
    w.resize(520, 200)
    w.show()
    app.exec()

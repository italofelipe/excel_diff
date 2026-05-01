import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from pathlib import Path

from .ui.hub_window import HubWindow


def _assets_dir() -> Path:
    # sys._MEIPASS is set by PyInstaller at runtime; fallback for dev mode
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'assets'
    return Path(__file__).parent.parent.parent / 'assets'


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName('Excel Diff')
    app.setOrganizationName('ExcelDiff')

    icon_path = _assets_dir() / 'icon.ico'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = HubWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

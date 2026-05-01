import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from pathlib import Path

from .ui.hub_window import HubWindow


def _assets_dir() -> Path:
    # sys._MEIPASS is set by PyInstaller at runtime; fallback for dev mode
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / 'assets'
    return Path(__file__).parent.parent.parent / 'assets'


def _handle_exception(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    details = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle('Erro inesperado')
    msg.setText('O Excel Diff encontrou um erro inesperado.')
    msg.setInformativeText('Copie os detalhes abaixo e entre em contato com o suporte.')
    msg.setDetailedText(details)
    msg.exec()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName('Excel Diff')
    app.setOrganizationName('ExcelDiff')

    sys.excepthook = _handle_exception

    icon_path = _assets_dir() / 'icon.ico'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = HubWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

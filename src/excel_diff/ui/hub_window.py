from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .tools.diff_tool import DiffTool
from .tools.merge_tool import MergeTool
from .tools.splitter_tool import SplitterTool


_SIDEBAR_WIDTH = 180

_NAV_ITEMS = [
    ('Comparar', 'Comparacao de planilhas com fuzzy matching'),
    ('Mesclar', 'Unir linhas de dois arquivos em um so'),
    ('Separar Colunas', 'Dividir colunas com dados compactados'),
]

_SIDEBAR_STYLE = """
QWidget#sidebar {
    background: #1e2430;
}
QPushButton#nav_btn {
    background: transparent;
    color: #b0b8c8;
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
}
QPushButton#nav_btn:hover {
    background: #2a3347;
    color: #e8ecf4;
}
QPushButton#nav_btn:checked {
    background: #2e6be6;
    color: #ffffff;
    font-weight: bold;
}
"""


class HubWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Excel Diff — Hub de Planilhas')
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(_SIDEBAR_WIDTH)
        sidebar.setStyleSheet(_SIDEBAR_STYLE)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 16)
        sidebar_layout.setSpacing(4)

        app_title = QLabel('Excel Diff')
        app_title.setStyleSheet('color:#e8ecf4; font-size:16px; font-weight:bold; padding:0 4px 12px 4px;')
        sidebar_layout.addWidget(app_title)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet('color:#2a3347; margin-bottom:8px;')
        sidebar_layout.addWidget(divider)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for i, (name, tooltip) in enumerate(_NAV_ITEMS):
            btn = QPushButton(name)
            btn.setObjectName('nav_btn')
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._btn_group.addButton(btn, i)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        version_label = QLabel('v1.0')
        version_label.setStyleSheet('color:#4a5568; font-size:10px; padding:0 4px;')
        sidebar_layout.addWidget(version_label)

        root.addWidget(sidebar)

        # Content stack
        self._stack = QStackedWidget()
        self._stack.addWidget(DiffTool())
        self._stack.addWidget(MergeTool())
        self._stack.addWidget(SplitterTool())
        root.addWidget(self._stack)

        # Wire navigation
        self._btn_group.idClicked.connect(self._stack.setCurrentIndex)
        self._btn_group.button(0).setChecked(True)

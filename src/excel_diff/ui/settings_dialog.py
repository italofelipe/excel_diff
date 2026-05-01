from __future__ import annotations

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from ..core.normalizer import NormConfig

DEFAULTS = {
    'threshold': 75,
    'lowercase': True,
    'remove_accents': True,
    'expand_units': True,
    'strip_quantities': True,
}


def load_settings() -> dict:
    s = QSettings('ExcelDiff', 'ExcelDiff')
    return {
        'threshold': int(s.value('threshold', DEFAULTS['threshold'])),
        'lowercase': s.value('lowercase', DEFAULTS['lowercase']) in (True, 'true'),
        'remove_accents': s.value('remove_accents', DEFAULTS['remove_accents']) in (True, 'true'),
        'expand_units': s.value('expand_units', DEFAULTS['expand_units']) in (True, 'true'),
        'strip_quantities': s.value('strip_quantities', DEFAULTS['strip_quantities']) in (True, 'true'),
    }


def save_settings(data: dict):
    s = QSettings('ExcelDiff', 'ExcelDiff')
    for k, v in data.items():
        s.setValue(k, v)


def settings_to_norm_config(data: dict) -> NormConfig:
    return NormConfig(
        lowercase=data.get('lowercase', True),
        remove_accents=data.get('remove_accents', True),
        expand_units=data.get('expand_units', True),
        strip_quantities=data.get('strip_quantities', True),
    )


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configurações')
        self.setMinimumWidth(400)
        self._data = load_settings()
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Threshold group
        threshold_group = QGroupBox('Similaridade mínima para considerar igual')
        threshold_layout = QVBoxLayout(threshold_group)

        slider_row = QHBoxLayout()
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(50, 100)
        self._slider.setTickInterval(5)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._threshold_label = QLabel('75%')
        self._threshold_label.setMinimumWidth(40)
        self._slider.valueChanged.connect(self._on_threshold_changed)
        slider_row.addWidget(self._slider)
        slider_row.addWidget(self._threshold_label)
        threshold_layout.addLayout(slider_row)

        hint = QLabel(
            'Valores mais baixos = mais coincidências (risco de falsos positivos)\n'
            'Valores mais altos = apenas coincidências muito parecidas'
        )
        hint.setStyleSheet('color: #666; font-size: 11px;')
        hint.setWordWrap(True)
        threshold_layout.addWidget(hint)
        layout.addWidget(threshold_group)

        # Normalization group
        norm_group = QGroupBox('Normalização de texto')
        norm_layout = QFormLayout(norm_group)
        self._cb_lowercase = QCheckBox('Ignorar maiúsculas/minúsculas')
        self._cb_accents = QCheckBox('Ignorar acentos (ã, é, ç...)')
        self._cb_units = QCheckBox('Normalizar unidades (1L → 1 litro)')
        self._cb_strip_qty = QCheckBox('Remover quantidades ao comparar (recomendado)')
        norm_layout.addRow(self._cb_lowercase)
        norm_layout.addRow(self._cb_accents)
        norm_layout.addRow(self._cb_units)
        norm_layout.addRow(self._cb_strip_qty)
        layout.addWidget(norm_group)

        # Buttons
        reset_btn = QPushButton('Restaurar padrões')
        reset_btn.clicked.connect(self._reset)
        layout.addWidget(reset_btn)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_values(self):
        self._slider.setValue(self._data['threshold'])
        self._cb_lowercase.setChecked(self._data['lowercase'])
        self._cb_accents.setChecked(self._data['remove_accents'])
        self._cb_units.setChecked(self._data['expand_units'])
        self._cb_strip_qty.setChecked(self._data['strip_quantities'])

    def _on_threshold_changed(self, value: int):
        self._threshold_label.setText(f'{value}%')

    def _reset(self):
        self._data = dict(DEFAULTS)
        self._load_values()

    def _accept(self):
        self._data = {
            'threshold': self._slider.value(),
            'lowercase': self._cb_lowercase.isChecked(),
            'remove_accents': self._cb_accents.isChecked(),
            'expand_units': self._cb_units.isChecked(),
            'strip_quantities': self._cb_strip_qty.isChecked(),
        }
        save_settings(self._data)
        self.accept()

    def get_settings(self) -> dict:
        return dict(self._data)

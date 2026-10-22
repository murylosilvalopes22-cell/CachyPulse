"""
Sensors View for CachyPulse.
Live hardware sensor grid with category filters, real-time search,
and continuous 1-second telemetry refresh.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer

class SensorsView(QWidget):
    def __init__(self, sensor_monitor, parent=None):
        super().__init__(parent)
        self.monitor = sensor_monitor
        self.current_filter = "Todos"
        self.search_text = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header & Filters
        top_layout = QHBoxLayout()

        # Category filter buttons
        self.btn_group = []
        for cat in ["Todos", "CPU", "GPU", "RAM", "Armazenamento"]:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            if cat == "Todos":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, c=cat: self._set_filter(c))
            top_layout.addWidget(btn)
            self.btn_group.append(btn)

        top_layout.addStretch()

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar sensor (ex: temp, clock, carga)...")
        self.search_input.setFixedWidth(260)
        self.search_input.textChanged.connect(self._on_search)
        top_layout.addWidget(self.search_input)

        layout.addLayout(top_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Categoria", "Sensor", "Valor Atual", "Unidade"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.table)

        # Refresh Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_table)
        self.timer.start(1000)

        self._refresh_table()

    def _set_filter(self, cat):
        self.current_filter = cat
        for btn in self.btn_group:
            btn.setChecked(btn.text() == cat)
        self._refresh_table()

    def _on_search(self, text):
        self.search_text = text.strip()
        self._refresh_table()

    def _refresh_table(self):
        rows = self.monitor.get_rows(category_filter=self.current_filter, search=self.search_text)
        self.table.setRowCount(len(rows))

        for i, r in enumerate(rows):
            item_cat = QTableWidgetItem(r.category)
            item_name = QTableWidgetItem(r.name)
            item_val = QTableWidgetItem(str(r.value))
            item_val.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_unit = QTableWidgetItem(r.unit)

            self.table.setItem(i, 0, item_cat)
            self.table.setItem(i, 1, item_name)
            self.table.setItem(i, 2, item_val)
            self.table.setItem(i, 3, item_unit)

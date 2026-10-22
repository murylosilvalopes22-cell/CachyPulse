"""
Main Window for CachyPulse.
Assembles the responsive dashboard with sidebar navigation, live footer telemetry,
Dark/Light theme switching, and seamless tabbed views.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QStackedWidget, QLabel, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
import os

from core.sensors import SensorMonitor
from .theme import DARK_THEME_QSS, LIGHT_THEME_QSS

from .views.dashboard_view import DashboardView
from .views.system_view import SystemView
from .views.sensors_view import SensorsView
from .views.bench_view import BenchView
from .views.stress_view import StressView
from .views.games_view import GamesView
from .views.optimizer_view import OptimizerView
from .views.tools_view import ToolsView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CachyPulse — Suíte de Benchmarks & Diagnóstico de Hardware")
        self.resize(1240, 820)
        self.setMinimumSize(1000, 700)

        # Set Application Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets/icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Start continuous sensor monitor
        self.sensor_monitor = SensorMonitor()
        self.sensor_monitor.start()

        # Theme state
        self.is_dark = True
        self.setStyleSheet(DARK_THEME_QSS)

        # Central layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ------------------ SIDEBAR ------------------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 16, 12, 16)
        sb_layout.setSpacing(10)

        # Brand Title
        brand_layout = QVBoxLayout()
        lbl_title = QLabel("CACHYPULSE")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 900; color: #00d2ff; letter-spacing: 1px;")
        lbl_sub = QLabel("Benchmark & Otimização")
        lbl_sub.setStyleSheet("font-size: 11px; color: #8b949e; font-weight: bold;")
        brand_layout.addWidget(lbl_title)
        brand_layout.addWidget(lbl_sub)
        sb_layout.addLayout(brand_layout)

        # Navigation List
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")
        nav_items = [
            "  📊  Visão Geral",
            "  💻  Sistema & Hardware",
            "  ⚡  Sensores ao Vivo",
            "  ⏱️  Benchmarks",
            "  🔥  Testes de Estresse",
            "  🎮  Jogos & Gargalo",
            "  🚀  Otimizador CachyOS",
            "  🛠️  Ferramentas & Maker"
        ]
        self.nav_list.addItems(nav_items)
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._change_page)
        sb_layout.addWidget(self.nav_list)

        sb_layout.addStretch()

        # Footer Live Telemetry Pills
        footer_frame = QFrame()
        footer_frame.setProperty("class", "Card")
        ff_layout = QVBoxLayout(footer_frame)
        ff_layout.setContentsMargins(8, 8, 8, 8)
        self.lbl_foot_cpu = QLabel("CPU: --% | --°C")
        self.lbl_foot_cpu.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 11px;")
        self.lbl_foot_gpu = QLabel("GPU: --% | --°C")
        self.lbl_foot_gpu.setStyleSheet("color: #3fb950; font-weight: bold; font-size: 11px;")
        ff_layout.addWidget(self.lbl_foot_cpu)
        ff_layout.addWidget(self.lbl_foot_gpu)
        sb_layout.addWidget(footer_frame)

        # Theme toggle button
        self.btn_theme = QPushButton("Alternar Tema Claro/Escuro")
        self.btn_theme.clicked.connect(self._toggle_theme)
        sb_layout.addWidget(self.btn_theme)

        main_layout.addWidget(sidebar)

        # ------------------ STACKED VIEWS ------------------
        self.stack = QStackedWidget()
        self.view_dashboard = DashboardView(self.sensor_monitor)
        self.view_system = SystemView()
        self.view_sensors = SensorsView(self.sensor_monitor)
        self.view_bench = BenchView()
        self.view_stress = StressView(self.sensor_monitor)
        self.view_games = GamesView(self.sensor_monitor)
        self.view_optimizer = OptimizerView()
        self.view_tools = ToolsView()

        self.stack.addWidget(self.view_dashboard)
        self.stack.addWidget(self.view_system)
        self.stack.addWidget(self.view_sensors)
        self.stack.addWidget(self.view_bench)
        self.stack.addWidget(self.view_stress)
        self.stack.addWidget(self.view_games)
        self.stack.addWidget(self.view_optimizer)
        self.stack.addWidget(self.view_tools)

        main_layout.addWidget(self.stack, stretch=1)

        # Footer polling timer
        self.footer_timer = QTimer(self)
        self.footer_timer.timeout.connect(self._update_footer)
        self.footer_timer.start(1000)

    def _change_page(self, index):
        self.stack.setCurrentIndex(index)

    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        self.setStyleSheet(DARK_THEME_QSS if self.is_dark else LIGHT_THEME_QSS)

    def _update_footer(self):
        snap = self.sensor_monitor.get_snapshot()
        if snap:
            cpu_load = snap.get("cpu_load", 0)
            cpu_temp = snap.get("cpu_temp", 0)
            gpu_load = snap.get("gpu_load", 0)
            gpu_temp = snap.get("gpu_temp", 0)
            self.lbl_foot_cpu.setText(f"CPU: {cpu_load:.0f}% | {cpu_temp:.1f}°C")
            self.lbl_foot_gpu.setText(f"GPU: {gpu_load}% | {gpu_temp}°C")

    def closeEvent(self, event):
        self.sensor_monitor.stop()
        super().closeEvent(event)

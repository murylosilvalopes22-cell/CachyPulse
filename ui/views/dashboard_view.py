"""
Dashboard View for CachyPulse (Faithful to ResetExplode's Monochromatic & Neon Aesthetic).
Real-time CPU/GPU telemetry, smooth live chart, horizontal meters, and health status.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen
from core.sys_info import get_cpu_info, get_gpu_info, get_ram_info, get_storage_info, get_os_info

class LiveChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.cpu_history = []
        self.gpu_history = []

    def update_data(self, cpu_history, gpu_history):
        self.cpu_history = list(cpu_history)[-60:]
        self.gpu_history = list(gpu_history)[-60:]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Deep OLED background
        painter.fillRect(0, 0, w, h, QColor(6, 6, 6))

        # Grid lines (25%, 50%, 75%)
        pen_grid = QPen(QColor(22, 22, 22), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen_grid)
        for pct in [0.25, 0.50, 0.75]:
            y = int(h * (1.0 - pct))
            painter.drawLine(0, y, w, y)

        if len(self.cpu_history) < 2:
            return

        step_x = w / max(len(self.cpu_history) - 1, 1)

        # Draw GPU Load (Emerald Green)
        if self.gpu_history:
            pen_gpu = QPen(QColor(63, 185, 80), 2)
            painter.setPen(pen_gpu)
            points_gpu = []
            for i, val in enumerate(self.gpu_history):
                x = i * step_x
                y = h - (val / 100.0 * (h - 20)) - 10
                points_gpu.append(QPointF(x, y))
            for i in range(len(points_gpu) - 1):
                painter.drawLine(points_gpu[i], points_gpu[i+1])

        # Draw CPU Load (Pure Cyan / White)
        pen_cpu = QPen(QColor(0, 210, 255), 2)
        painter.setPen(pen_cpu)
        points_cpu = []
        for i, val in enumerate(self.cpu_history):
            x = i * step_x
            y = h - (val / 100.0 * (h - 20)) - 10
            points_cpu.append(QPointF(x, y))
        for i in range(len(points_cpu) - 1):
            painter.drawLine(points_cpu[i], points_cpu[i+1])

class DashboardView(QWidget):
    def __init__(self, sensor_monitor, parent=None):
        super().__init__(parent)
        self.monitor = sensor_monitor

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Header Banner
        os_info = get_os_info()
        header_frame = QFrame()
        header_frame.setProperty("class", "Card")
        h_layout = QHBoxLayout(header_frame)
        h_title = QLabel(f"<b>CACHYPULSE</b> &nbsp;|&nbsp; {os_info['distro']} &nbsp;•&nbsp; Kernel {os_info['kernel']}")
        h_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        h_layout.addWidget(h_title)
        h_layout.addStretch()

        self.lbl_health = QLabel("SAÚDE DO PC: EXCELENTE")
        self.lbl_health.setStyleSheet("background: #141414; border: 1px solid #282828; color: #3FB950; padding: 5px 12px; border-radius: 8px; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        h_layout.addWidget(self.lbl_health)
        layout.addWidget(header_frame)

        # 2. Four Key Telemetry Cards
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(14)

        # CPU Card
        self.card_cpu = QFrame()
        self.card_cpu.setProperty("class", "Card")
        cpu_l = QVBoxLayout(self.card_cpu)
        cpu_l.setSpacing(4)
        cpu_title = QLabel("PROCESSADOR (CPU)")
        cpu_title.setStyleSheet("color: #737373; font-size: 10.5px; font-weight: 700; text-transform: uppercase;")
        self.lbl_cpu_val = QLabel("-- %")
        self.lbl_cpu_val.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 26px; font-weight: 800; color: #00D2FF;")
        self.lbl_cpu_sub = QLabel("AMD Ryzen 5 5600")
        self.lbl_cpu_sub.setStyleSheet("color: #737373; font-size: 12px;")
        cpu_l.addWidget(cpu_title)
        cpu_l.addWidget(self.lbl_cpu_val)
        cpu_l.addWidget(self.lbl_cpu_sub)
        metrics_grid.addWidget(self.card_cpu, 0, 0)

        # GPU Card
        self.card_gpu = QFrame()
        self.card_gpu.setProperty("class", "Card")
        gpu_l = QVBoxLayout(self.card_gpu)
        gpu_l.setSpacing(4)
        gpu_title = QLabel("PLACA DE VÍDEO (GPU)")
        gpu_title.setStyleSheet("color: #737373; font-size: 10.5px; font-weight: 700; text-transform: uppercase;")
        self.lbl_gpu_val = QLabel("-- %")
        self.lbl_gpu_val.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 26px; font-weight: 800; color: #3FB950;")
        self.lbl_gpu_sub = QLabel("NVIDIA GeForce RTX 2060")
        self.lbl_gpu_sub.setStyleSheet("color: #737373; font-size: 12px;")
        gpu_l.addWidget(gpu_title)
        gpu_l.addWidget(self.lbl_gpu_val)
        gpu_l.addWidget(self.lbl_gpu_sub)
        metrics_grid.addWidget(self.card_gpu, 0, 1)

        # RAM Card
        self.card_ram = QFrame()
        self.card_ram.setProperty("class", "Card")
        ram_l = QVBoxLayout(self.card_ram)
        ram_l.setSpacing(4)
        ram_title = QLabel("MEMÓRIA RAM")
        ram_title.setStyleSheet("color: #737373; font-size: 10.5px; font-weight: 700; text-transform: uppercase;")
        self.lbl_ram_val = QLabel("-- %")
        self.lbl_ram_val.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 26px; font-weight: 800; color: #FFFFFF;")
        self.lbl_ram_sub = QLabel("-- GB usados")
        self.lbl_ram_sub.setStyleSheet("color: #737373; font-size: 12px;")
        ram_l.addWidget(ram_title)
        ram_l.addWidget(self.lbl_ram_val)
        ram_l.addWidget(self.lbl_ram_sub)
        metrics_grid.addWidget(self.card_ram, 0, 2)

        # VRAM Card
        self.card_vram = QFrame()
        self.card_vram.setProperty("class", "Card")
        vram_l = QVBoxLayout(self.card_vram)
        vram_l.setSpacing(4)
        vram_title = QLabel("MEMÓRIA VRAM")
        vram_title.setStyleSheet("color: #737373; font-size: 10.5px; font-weight: 700; text-transform: uppercase;")
        self.lbl_vram_val = QLabel("-- MB")
        self.lbl_vram_val.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 26px; font-weight: 800; color: #FFAA00;")
        self.lbl_vram_sub = QLabel("-- MB livres")
        self.lbl_vram_sub.setStyleSheet("color: #737373; font-size: 12px;")
        vram_l.addWidget(vram_title)
        vram_l.addWidget(self.lbl_vram_val)
        vram_l.addWidget(self.lbl_vram_sub)
        metrics_grid.addWidget(self.card_vram, 0, 3)

        layout.addLayout(metrics_grid)

        # 3. Live Activity Chart Card
        chart_card = QFrame()
        chart_card.setProperty("class", "Card")
        chart_l = QVBoxLayout(chart_card)
        chart_header = QHBoxLayout()
        chart_title = QLabel("Atividade em Tempo Real (60s)")
        chart_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #FFFFFF; text-transform: uppercase;")
        chart_header.addWidget(chart_title)
        chart_header.addStretch()

        leg_cpu = QLabel("CPU (%)")
        leg_cpu.setStyleSheet("background: #0C1E2B; border: 1px solid #00D2FF; color: #00D2FF; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;")
        leg_gpu = QLabel("GPU (%)")
        leg_gpu.setStyleSheet("background: #0E2416; border: 1px solid #3FB950; color: #3FB950; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; margin-left: 8px;")
        chart_header.addWidget(leg_cpu)
        chart_header.addWidget(leg_gpu)
        chart_l.addLayout(chart_header)

        self.chart = LiveChartWidget()
        chart_l.addWidget(self.chart)
        layout.addWidget(chart_card)

        # 4. Storage Usage Cards (Sleek horizontal meters)
        storage_card = QFrame()
        storage_card.setProperty("class", "Card")
        store_l = QVBoxLayout(storage_card)
        store_l.setSpacing(12)
        store_title = QLabel("Armazenamento & Partições")
        store_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #FFFFFF; text-transform: uppercase;")
        store_l.addWidget(store_title)

        disks = get_storage_info()
        for d in disks:
            for part in d.get("partitions", []):
                v_sub = QVBoxLayout()
                v_sub.setSpacing(4)
                v_header = QHBoxLayout()
                p_label = QLabel(f"<b>{part['mountpoint']}</b> &nbsp; <span style='color: #666;'>({part['fstype']})</span>")
                p_label.setStyleSheet("color: #F0F0F0; font-size: 12.5px;")
                p_size = QLabel(f"{part['used_gb']} GB / {part['total_gb']} GB ({part['percent']}%)")
                p_size.setStyleSheet("color: #737373; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 11.5px;")
                v_header.addWidget(p_label)
                v_header.addStretch()
                v_header.addWidget(p_size)

                p_bar = QProgressBar()
                p_bar.setValue(int(part['percent']))
                p_bar.setMaximumHeight(4)

                v_sub.addLayout(v_header)
                v_sub.addWidget(p_bar)
                store_l.addLayout(v_sub)

        layout.addWidget(storage_card)
        layout.addStretch()

        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_l.addWidget(scroll)

        # Refresh Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_ui)
        self.timer.start(1000)

        # Titles
        cpu_info = get_cpu_info()
        gpu_info = get_gpu_info()
        self.lbl_cpu_sub.setText(cpu_info['model'])
        self.lbl_gpu_sub.setText(f"{gpu_info['name']} ({gpu_info['driver']})")

    def _refresh_ui(self):
        snap = self.monitor.get_snapshot()
        if not snap:
            return

        cpu_load = snap.get("cpu_load", 0)
        cpu_temp = snap.get("cpu_temp", 0)
        self.lbl_cpu_val.setText(f"{cpu_load:.0f}%  <span style='font-size: 18px; color: #737373;'>{cpu_temp:.0f}°C</span>")

        gpu_load = snap.get("gpu_load", 0)
        gpu_temp = snap.get("gpu_temp", 0)
        power_w = snap.get("power_w", 0)
        self.lbl_gpu_val.setText(f"{gpu_load}%  <span style='font-size: 18px; color: #737373;'>{gpu_temp}°C</span>")

        ram_pct = snap.get("ram_pct", 0)
        ram_used = snap.get("ram_used_gb", 0)
        ram_total = snap.get("ram_total_gb", 0)
        self.lbl_ram_val.setText(f"{ram_pct:.0f}%")
        self.lbl_ram_sub.setText(f"{ram_used:.1f} GB de {ram_total:.1f} GB")

        vram_used = snap.get("vram_used_mb", 0)
        vram_total = snap.get("vram_total_mb", 0)
        self.lbl_vram_val.setText(f"{vram_used} MB")
        self.lbl_vram_sub.setText(f"{vram_total - vram_used} MB livres de {vram_total} MB")

        hist = self.monitor.get_history()
        self.chart.update_data(hist.get("cpu_load", []), hist.get("gpu_load", []))

"""
Stress Testing View for CachyPulse.
Provides:
1. Native C-compiled Multi-Threaded CPU & Memory synthetic stress test (zero Python GIL freeze).
2. Hardware-accelerated OpenGL 3D GPU Stress Burner (FurMark style) with thermal safety shutdown.
"""

import time
import ctypes
import threading
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSpinBox, QCheckBox, QGridLayout, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from benchmarks.gpu_stress import GpuStressDialog

class StressView(QWidget):
    def __init__(self, sensor_monitor, parent=None):
        super().__init__(parent)
        self.monitor = sensor_monitor

        # Native C library bindings for CPU stress
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        lib_path = os.path.join(base_dir, "libcachypulse_native.so")
        self.native_lib = ctypes.CDLL(lib_path)
        self.c_stop_flag = ctypes.c_int(0)
        self.stress_worker_thread = None

        self.cpu_stress_running = False
        self.start_time = 0

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # 1. CPU & RAM Stress Card
        cpu_card = QFrame()
        cpu_card.setProperty("class", "Card")
        cl = QVBoxLayout(cpu_card)
        cl.setSpacing(14)

        ctitle = QLabel("Teste de Estresse de CPU & Estabilidade")
        ctitle.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
        cl.addWidget(ctitle)

        cdesc = QLabel(
            "Executa carga máxima em todos os núcleos da CPU via C nativo com OpenMP (FPU + FMA + Inteiros), "
            "sem travar a interface. Inclui corte automático de segurança se atingir o limite térmico configurado."
        )
        cdesc.setStyleSheet("color: #8C8C8C; font-size: 13px; line-height: 1.4;")
        cdesc.setWordWrap(True)
        cl.addWidget(cdesc)

        # Controls & Safety Limit
        opts_layout = QHBoxLayout()
        self.chk_cpu = QCheckBox("Estressar CPU (100% de carga em todas as threads)")
        self.chk_cpu.setChecked(True)
        self.chk_cpu.setStyleSheet("color: #E0E0E0; font-size: 13px;")

        opts_layout.addWidget(self.chk_cpu)
        opts_layout.addStretch()

        opts_layout.addWidget(QLabel("Limite Térmico:"))
        self.spin_cpu_limit = QSpinBox()
        self.spin_cpu_limit.setRange(60, 98)
        self.spin_cpu_limit.setValue(90)
        self.spin_cpu_limit.setSuffix(" °C")
        self.spin_cpu_limit.setFixedWidth(100)
        opts_layout.addWidget(self.spin_cpu_limit)

        cl.addLayout(opts_layout)

        # Live Metrics Grid
        stat_grid = QGridLayout()
        stat_grid.setSpacing(14)

        self.card_time = self._stat_tile("TEMPO DECORRIDO", "00:00")
        self.card_temp = self._stat_tile("TEMPERATURA DA CPU", "-- °C")
        self.card_load = self._stat_tile("CARGA TOTAL DA CPU", "-- %")

        stat_grid.addWidget(self.card_time, 0, 0)
        stat_grid.addWidget(self.card_temp, 0, 1)
        stat_grid.addWidget(self.card_load, 0, 2)
        cl.addLayout(stat_grid)

        # Toggle Button (White Pill)
        self.btn_toggle_cpu_stress = QPushButton("Iniciar Estresse de CPU")
        self.btn_toggle_cpu_stress.setProperty("class", "Primary")
        self.btn_toggle_cpu_stress.clicked.connect(self._toggle_cpu_stress)
        cl.addWidget(self.btn_toggle_cpu_stress)

        layout.addWidget(cpu_card)

        # 2. GPU 3D Stress Burner Card (FurMark style)
        gpu_card = QFrame()
        gpu_card.setProperty("class", "Card")
        gl = QVBoxLayout(gpu_card)
        gl.setSpacing(14)

        gtitle = QLabel("Teste de Estresse de GPU 3D (Estilo FurMark)")
        gtitle.setStyleSheet("font-size: 18px; font-weight: 700; color: #FFFFFF;")
        gl.addWidget(gtitle)

        gdesc = QLabel(
            "Renderização acelerada por hardware via OpenGL nativo (driver NVIDIA). "
            "Renderiza um torus 3D com loops pesados de shaders aritméticos e overdraw, "
            "medindo FPS, temperatura, consumo em Watts e estabilidade dos clocks."
        )
        gdesc.setStyleSheet("color: #8C8C8C; font-size: 13px; line-height: 1.4;")
        gdesc.setWordWrap(True)
        gl.addWidget(gdesc)

        self.btn_open_gpu_stress = QPushButton("Abrir GPU Stress Burner (OpenGL 3D)")
        self.btn_open_gpu_stress.setProperty("class", "Primary")
        self.btn_open_gpu_stress.clicked.connect(self._open_gpu_burner)
        gl.addWidget(self.btn_open_gpu_stress)

        layout.addWidget(gpu_card)
        layout.addStretch()

        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_l.addWidget(scroll)

        # Monitor timer for stress loop (keeps UI updating every second)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._stress_tick)
        self.timer.start(1000)

    def _stat_tile(self, label, value):
        f = QFrame()
        f.setStyleSheet("background: #060606; border: 1px solid #1A1A1A; border-radius: 12px; padding: 14px;")
        vl = QVBoxLayout(f)
        vl.setSpacing(4)
        t = QLabel(label)
        t.setStyleSheet("color: #737373; font-size: 10.5px; font-weight: 700; text-transform: uppercase;")
        v = QLabel(value)
        v.setStyleSheet("color: #FFFFFF; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 24px; font-weight: 700;")
        vl.addWidget(t)
        vl.addWidget(v)
        f.val_label = v
        return f

    def _toggle_cpu_stress(self):
        if not self.cpu_stress_running:
            # Start native C stress
            self.cpu_stress_running = True
            self.c_stop_flag.value = 0
            self.start_time = time.time()
            self.btn_toggle_cpu_stress.setText("Interromper Estresse")
            self.btn_toggle_cpu_stress.setProperty("class", "Danger")
            self.btn_toggle_cpu_stress.style().unpolish(self.btn_toggle_cpu_stress)
            self.btn_toggle_cpu_stress.style().polish(self.btn_toggle_cpu_stress)

            def c_runner():
                # Native OpenMP execution in C releases Python's GIL
                self.native_lib.cpu_stress_worker(ctypes.byref(self.c_stop_flag), 0)

            self.stress_worker_thread = threading.Thread(target=c_runner, daemon=True)
            self.stress_worker_thread.start()
        else:
            # Stop native C stress
            self.cpu_stress_running = False
            self.c_stop_flag.value = 1
            self.btn_toggle_cpu_stress.setText("Iniciar Estresse de CPU")
            self.btn_toggle_cpu_stress.setProperty("class", "Primary")
            self.btn_toggle_cpu_stress.style().unpolish(self.btn_toggle_cpu_stress)
            self.btn_toggle_cpu_stress.style().polish(self.btn_toggle_cpu_stress)

    def _stress_tick(self):
        snap = self.monitor.get_snapshot()
        cpu_temp = snap.get("cpu_temp", 0)
        cpu_load = snap.get("cpu_load", 0)

        self.card_temp.val_label.setText(f"{cpu_temp:.1f} °C")
        self.card_load.val_label.setText(f"{cpu_load:.0f} %")

        if self.cpu_stress_running:
            elapsed = int(time.time() - self.start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.card_time.val_label.setText(f"{mins:02d}:{secs:02d}")

            # Safety Cutoff
            if cpu_temp >= self.spin_cpu_limit.value():
                self._toggle_cpu_stress()
                QMessageBox.warning(
                    self, "Alerta Térmico",
                    f"O estresse foi interrompido automaticamente porque a CPU atingiu {cpu_temp:.1f}°C "
                    f"(limite seguro: {self.spin_cpu_limit.value()}°C)!"
                )

    def _open_gpu_burner(self):
        dialog = GpuStressDialog(self)
        dialog.exec()

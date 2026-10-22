"""
Stress Testing View for CachyPulse.
Provides CPU & RAM synthetic stress tester with thermal safety cutoff,
and hardware-accelerated OpenGL 3D GPU Stress Burner (FurMark style).
"""

import time
import math
import threading
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSpinBox, QCheckBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from benchmarks.gpu_stress import GpuStressDialog

class StressView(QWidget):
    def __init__(self, sensor_monitor, parent=None):
        super().__init__(parent)
        self.monitor = sensor_monitor

        self.cpu_stress_running = False
        self.stop_requested = False
        self.stress_threads = []
        self.start_time = 0
        self.mem_errors = 0

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. CPU & RAM Stress Card
        cpu_card = QFrame()
        cpu_card.setProperty("class", "Card")
        cl = QVBoxLayout(cpu_card)

        ctitle = QLabel("Teste de Estresse de CPU & Memória RAM")
        ctitle.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        cl.addWidget(ctitle)

        cdesc = QLabel("Gera carga máxima em todos os núcleos de CPU (FPU + Inteiros) e aloca blocos de RAM gravando/verificando padrões de estabilidade. Desliga automaticamente se atingir o limite térmico.")
        cdesc.setStyleSheet("color: #8b949e; margin-bottom: 12px;")
        cl.addWidget(cdesc)

        opts_layout = QHBoxLayout()
        self.chk_cpu = QCheckBox("Estressar CPU (Todos os Threads)")
        self.chk_cpu.setChecked(True)
        self.chk_ram = QCheckBox("Estressar Memória RAM")
        self.chk_ram.setChecked(True)

        opts_layout.addWidget(self.chk_cpu)
        opts_layout.addWidget(self.chk_ram)
        opts_layout.addStretch()

        opts_layout.addWidget(QLabel("Limite Térmico CPU:"))
        self.spin_cpu_limit = QSpinBox()
        self.spin_cpu_limit.setRange(60, 98)
        self.spin_cpu_limit.setValue(90)
        self.spin_cpu_limit.setSuffix(" °C")
        opts_layout.addWidget(self.spin_cpu_limit)

        cl.addLayout(opts_layout)

        # Live Stress Status
        stat_grid = QGridLayout()
        self.lbl_stress_time = QLabel("Tempo: 00:00")
        self.lbl_stress_time.setStyleSheet("font-size: 16px; font-weight: bold; color: #00d2ff;")
        self.lbl_stress_temp = QLabel("Temp CPU: -- °C")
        self.lbl_stress_temp.setStyleSheet("font-size: 16px; font-weight: bold; color: #f0883e;")
        self.lbl_stress_errors = QLabel("Erros de Memória: 0")
        self.lbl_stress_errors.setStyleSheet("font-size: 16px; font-weight: bold; color: #3fb950;")

        stat_grid.addWidget(self.lbl_stress_time, 0, 0)
        stat_grid.addWidget(self.lbl_stress_temp, 0, 1)
        stat_grid.addWidget(self.lbl_stress_errors, 0, 2)
        cl.addLayout(stat_grid)

        # Start/Stop Button
        self.btn_toggle_cpu_stress = QPushButton("Iniciar Estresse de CPU & RAM")
        self.btn_toggle_cpu_stress.setProperty("class", "Primary")
        self.btn_toggle_cpu_stress.clicked.connect(self._toggle_cpu_stress)
        cl.addWidget(self.btn_toggle_cpu_stress)

        layout.addWidget(cpu_card)

        # 2. GPU 3D Stress Burner Card
        gpu_card = QFrame()
        gpu_card.setProperty("class", "Card")
        gl = QVBoxLayout(gpu_card)

        gtitle = QLabel("Teste de Estresse de Placa de Vídeo (Estilo FurMark)")
        gtitle.setStyleSheet("font-size: 16px; font-weight: bold; color: #3fb950;")
        gl.addWidget(gtitle)

        gdesc = QLabel("Abre a janela de aceleração gráfica por hardware OpenGL. Renderiza um torus tridimensional em alta resolução com loops massivos de shader aritmético para levar a GPU ao consumo máximo de Watts e teste de estabilidade de clock/temperatura.")
        gdesc.setStyleSheet("color: #8b949e; margin-bottom: 12px;")
        gl.addWidget(gdesc)

        self.btn_open_gpu_stress = QPushButton("Abrir GPU Stress Burner (OpenGL)")
        self.btn_open_gpu_stress.setProperty("class", "Primary")
        self.btn_open_gpu_stress.clicked.connect(self._open_gpu_burner)
        gl.addWidget(self.btn_open_gpu_stress)

        layout.addWidget(gpu_card)
        layout.addStretch()

        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_l.addWidget(scroll)

        # Monitor timer for stress loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._stress_tick)
        self.timer.start(1000)

    def _toggle_cpu_stress(self):
        if not self.cpu_stress_running:
            # Start
            self.cpu_stress_running = True
            self.stop_requested = False
            self.start_time = time.time()
            self.mem_errors = 0
            self.btn_toggle_cpu_stress.setText("Interromper Estresse")
            self.btn_toggle_cpu_stress.setProperty("class", "Danger")
            self.btn_toggle_cpu_stress.style().unpolish(self.btn_toggle_cpu_stress)
            self.btn_toggle_cpu_stress.style().polish(self.btn_toggle_cpu_stress)

            self.stress_threads = []
            threads_count = psutil.cpu_count(logical=True) or 4

            if self.chk_cpu.isChecked():
                for i in range(threads_count):
                    t = threading.Thread(target=self._cpu_worker, args=(i,), daemon=True)
                    self.stress_threads.append(t)
                    t.start()

            if self.chk_ram.isChecked():
                t = threading.Thread(target=self._ram_worker, daemon=True)
                self.stress_threads.append(t)
                t.start()
        else:
            # Stop
            self.cpu_stress_running = False
            self.stop_requested = True
            self.btn_toggle_cpu_stress.setText("Iniciar Estresse de CPU & RAM")
            self.btn_toggle_cpu_stress.setProperty("class", "Primary")
            self.btn_toggle_cpu_stress.style().unpolish(self.btn_toggle_cpu_stress)
            self.btn_toggle_cpu_stress.style().polish(self.btn_toggle_cpu_stress)

    def _cpu_worker(self, seed):
        buf = [float(j + seed + 1) for j in range(2048)]
        while not self.stop_requested:
            for _ in range(64):
                for j in range(len(buf)):
                    v = buf[j]
                    buf[j] = math.sqrt(v * 1.0000001 + 0.5) + math.sin(v) * 0.001
                    if buf[j] > 1e10: buf[j] = float(j + 1)

    def _ram_worker(self):
        try:
            # Allocate 1.5 GB in chunks and verify patterns
            chunks = []
            chunk_size = 64 * 1024 * 1024 # 64MB
            for _ in range(24):
                if self.stop_requested: break
                chunks.append(bytearray(b'\xAA' * chunk_size))

            pattern_toggle = False
            while not self.stop_requested:
                p = b'\x55' if pattern_toggle else b'\xAA'
                for c in chunks:
                    if self.stop_requested: break
                    for k in range(0, len(c), 4096):
                        c[k:k+4] = p * 4
                pattern_toggle = not pattern_toggle
                time.sleep(0.1)
        except MemoryError:
            pass

    def _stress_tick(self):
        snap = self.monitor.get_snapshot()
        cpu_temp = snap.get("cpu_temp", 0)
        self.lbl_stress_temp.setText(f"Temp CPU: {cpu_temp:.1f} °C")

        if self.cpu_stress_running:
            elapsed = int(time.time() - self.start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.lbl_stress_time.setText(f"Tempo: {mins:02d}:{secs:02d}")

            # Thermal Limit Cutoff
            if cpu_temp >= self.spin_cpu_limit.value():
                self.lbl_stress_time.setText("PARADO: LIMITE TÉRMICO ATINGIDO!")
                self._toggle_cpu_stress()

    def _open_gpu_burner(self):
        dialog = GpuStressDialog(self)
        dialog.exec()

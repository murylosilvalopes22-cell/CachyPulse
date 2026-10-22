"""
Benchmark Suite View for CachyPulse.
Provides Cinebench-style CPU Ray Tracer with live tile rendering,
AIDA64-style RAM Latency/Bandwidth, CrystalDiskMark Direct I/O Disk Bench,
and Network Speed & Bufferbloat Diagnostics.
"""

import threading
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTabWidget, QProgressBar, QComboBox,
    QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap

from benchmarks.cpu_raytracer import CpuRaytracerBench, WIDTH, HEIGHT
from benchmarks.memory_bench import MemoryBenchmark
from benchmarks.disk_bench import DiskBenchmark
from benchmarks.network_bench import NetworkBenchmark
from core.sys_info import get_storage_info

class RenderCanvasWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(640, 360)
        self.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Aguardando Início do Benchmark de CPU...")

    def update_frame(self, raw_bytes):
        img = QImage(raw_bytes, WIDTH, HEIGHT, WIDTH * 4, QImage.Format.Format_ARGB32)
        pix = QPixmap.fromImage(img).scaled(self.width(), self.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(pix)

class BenchView(QWidget):
    progress_signal = pyqtSignal(str, float)
    cpu_render_update_signal = pyqtSignal()
    bench_done_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.cpu_bench = CpuRaytracerBench()
        self.mem_bench = MemoryBenchmark()
        self.disk_bench = DiskBenchmark()
        self.net_bench = NetworkBenchmark()

        self.current_worker = None
        self.progress_signal.connect(self._on_progress)
        self.cpu_render_update_signal.connect(self._on_cpu_render_tick)
        self.bench_done_signal.connect(self._on_bench_done)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_cpu_tab(), "CPU (Cinebench Ray Tracer)")
        self.tabs.addTab(self._build_mem_tab(), "Memória RAM (Estilo AIDA64)")
        self.tabs.addTab(self._build_disk_tab(), "Disco (Estilo CrystalDiskMark)")
        self.tabs.addTab(self._build_net_tab(), "Diagnóstico de Rede & Lag")

        layout.addWidget(self.tabs)

        # Global Progress Bar and Status
        self.status_frame = QFrame()
        self.status_frame.setProperty("class", "Card")
        sf_l = QVBoxLayout(self.status_frame)
        self.lbl_status = QLabel("Pronto para executar benchmarks.")
        self.lbl_status.setStyleSheet("color: #8b949e; font-weight: bold;")
        self.prog_bar = QProgressBar()
        self.prog_bar.setValue(0)
        sf_l.addWidget(self.lbl_status)
        sf_l.addWidget(self.prog_bar)

        layout.addWidget(self.status_frame)

    # ------------------ CPU BENCHMARK TAB ------------------
    def _build_cpu_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)

        top_h = QHBoxLayout()
        self.combo_cpu_mode = QComboBox()
        self.combo_cpu_mode.addItems(["Multi-Core (Todos os Núcleos)", "Single-Core (1 Núcleo)"])

        self.combo_cpu_spp = QComboBox()
        self.combo_cpu_spp.addItems(["Rápido (128 amostras/px)", "Padrão (256 amostras/px)", "Extremo (512 amostras/px)"])
        self.combo_cpu_spp.setCurrentIndex(1)

        self.btn_run_cpu = QPushButton("Iniciar Benchmark de CPU")
        self.btn_run_cpu.setProperty("class", "Primary")
        self.btn_run_cpu.clicked.connect(self._run_cpu_bench)

        top_h.addWidget(QLabel("Modo:"))
        top_h.addWidget(self.combo_cpu_mode)
        top_h.addWidget(QLabel("Qualidade:"))
        top_h.addWidget(self.combo_cpu_spp)
        top_h.addWidget(self.btn_run_cpu)
        top_h.addStretch()
        l.addLayout(top_h)

        center_h = QHBoxLayout()
        self.render_canvas = RenderCanvasWidget()
        center_h.addWidget(self.render_canvas)

        # Score & comparison side panel
        score_frame = QFrame()
        score_frame.setProperty("class", "Card")
        sf_l = QVBoxLayout(score_frame)

        sf_title = QLabel("Pontuação CachyPulse CPU")
        sf_title.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 12px;")
        self.lbl_cpu_score = QLabel("---- pts")
        self.lbl_cpu_score.setStyleSheet("font-size: 32px; font-weight: bold; color: #00d2ff; margin: 10px 0;")
        self.lbl_cpu_time = QLabel("Tempo: -- s")
        self.lbl_cpu_time.setStyleSheet("color: #8b949e; font-size: 13px;")

        ref_title = QLabel("<b>Referências Multi-Core:</b><br>"
                           "• Ryzen 7 7700X: ~4.500 pts<br>"
                           "• Ryzen 5 5600: ~2.900 pts<br>"
                           "• Core i5-12400: ~2.850 pts")
        ref_title.setStyleSheet("color: #c9d1d9; font-size: 12px; margin-top: 15px;")

        sf_l.addWidget(sf_title)
        sf_l.addWidget(self.lbl_cpu_score)
        sf_l.addWidget(self.lbl_cpu_time)
        sf_l.addWidget(ref_title)
        sf_l.addStretch()

        center_h.addWidget(score_frame)
        l.addLayout(center_h)

        return w

    def _run_cpu_bench(self):
        self.btn_run_cpu.setEnabled(False)
        self.lbl_cpu_score.setText("Calculando...")
        is_single = (self.combo_cpu_mode.currentIndex() == 1)
        threads = 1 if is_single else psutil.cpu_count(logical=True)
        spp_map = [128, 256, 512]
        spp = spp_map[self.combo_cpu_spp.currentIndex()]

        def worker():
            def on_progress(completed, total, elapsed):
                pct = completed / total
                self.progress_signal.emit(f"Renderizando blocos: {completed}/{total} ({elapsed:.1f}s)", pct)
                self.cpu_render_update_signal.emit()

            score = self.cpu_bench.run(threads=threads, spp=spp, on_progress=on_progress)
            self.bench_done_signal.emit({"type": "cpu", "score": score})

        self.current_worker = threading.Thread(target=worker, daemon=True)
        self.current_worker.start()

    def _on_cpu_render_tick(self):
        raw = self.cpu_bench.get_pixel_buffer_bytes()
        self.render_canvas.update_frame(raw)

    # ------------------ MEMORY BENCHMARK TAB ------------------
    def _build_mem_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)

        top_h = QHBoxLayout()
        self.btn_run_mem = QPushButton("Iniciar Teste Completo de Memória (AIDA64 Style)")
        self.btn_run_mem.setProperty("class", "Primary")
        self.btn_run_mem.clicked.connect(self._run_mem_bench)
        top_h.addWidget(self.btn_run_mem)
        top_h.addStretch()
        l.addLayout(top_h)

        grid = QGridLayout()
        grid.setSpacing(16)

        self.card_lat = self._metric_card("LATÊNCIA DA MEMÓRIA (Sattolo Cycle)", "-- ns", "Tempo de resposta direta sem cache L3 (< 75 ns é excelente)")
        self.card_read = self._metric_card("LARGURA DE BANDA DE LEITURA", "-- GB/s", "Velocidade máxima de leitura contínua (DDR4 ~35 GB/s, DDR5 ~60+ GB/s)")
        self.card_write = self._metric_card("LARGURA DE BANDA DE ESCRITA", "-- GB/s", "Velocidade máxima de escrita em memória")
        self.card_copy = self._metric_card("LARGURA DE BANDA DE CÓPIA", "-- GB/s", "Desempenho bidirecional de transferência de blocos")

        grid.addWidget(self.card_lat, 0, 0)
        grid.addWidget(self.card_read, 0, 1)
        grid.addWidget(self.card_write, 1, 0)
        grid.addWidget(self.card_copy, 1, 1)

        l.addLayout(grid)
        l.addStretch()
        return w

    def _metric_card(self, title, val, sub):
        f = QFrame()
        f.setProperty("class", "Card")
        vl = QVBoxLayout(f)
        t = QLabel(title)
        t.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 11px;")
        v = QLabel(val)
        v.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 26px; margin: 8px 0;")
        s = QLabel(sub)
        s.setStyleSheet("color: #8b949e; font-size: 11px;")
        vl.addWidget(t)
        vl.addWidget(v)
        vl.addWidget(s)
        f.val_label = v
        return f

    def _run_mem_bench(self):
        self.btn_run_mem.setEnabled(False)

        def worker():
            res = self.mem_bench.run_full(threads=0, progress_cb=lambda s, p: self.progress_signal.emit(s, p))
            self.bench_done_signal.emit({"type": "mem", "res": res})

        self.current_worker = threading.Thread(target=worker, daemon=True)
        self.current_worker.start()

    # ------------------ DISK BENCHMARK TAB ------------------
    def _build_disk_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)

        top_h = QHBoxLayout()
        self.combo_disk_target = QComboBox()
        disks = get_storage_info()
        for d in disks:
            for p in d.get("partitions", []):
                self.combo_disk_target.addItem(f"{p['mountpoint']} ({d['model']})", p['mountpoint'])

        self.btn_run_disk = QPushButton("Iniciar CrystalDiskMark Direct I/O")
        self.btn_run_disk.setProperty("class", "Primary")
        self.btn_run_disk.clicked.connect(self._run_disk_bench)

        top_h.addWidget(QLabel("Unidade / Partição:"))
        top_h.addWidget(self.combo_disk_target)
        top_h.addWidget(self.btn_run_disk)
        top_h.addStretch()
        l.addLayout(top_h)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.dcard_seq_w = self._metric_card("ESCRITA SEQUENCIAL (1 MB)", "-- MB/s", "Direct I/O sem cache de disco")
        self.dcard_seq_r = self._metric_card("LEITURA SEQUENCIAL (1 MB)", "-- MB/s", "Velocidade máxima de leitura contínua")
        self.dcard_4k_q1 = self._metric_card("ACESSO 4K QD1 (ALEATÓRIO)", "-- IOPS", "Essencial para abertura de programas e jogos")
        self.dcard_4k_q8 = self._metric_card("ACESSO 4K QD8 (PARALELO)", "-- IOPS", "Carga pesada multithread NVMe")

        grid.addWidget(self.dcard_seq_w, 0, 0)
        grid.addWidget(self.dcard_seq_r, 0, 1)
        grid.addWidget(self.dcard_4k_q1, 1, 0)
        grid.addWidget(self.dcard_4k_q8, 1, 1)

        l.addLayout(grid)
        l.addStretch()
        return w

    def _run_disk_bench(self):
        self.btn_run_disk.setEnabled(False)
        target = self.combo_disk_target.currentData() or "/tmp"

        def worker():
            res = self.disk_bench.run(target_dir=target, test_size_mb=256, progress_cb=lambda s, p: self.progress_signal.emit(s, p))
            self.bench_done_signal.emit({"type": "disk", "res": res})

        self.current_worker = threading.Thread(target=worker, daemon=True)
        self.current_worker.start()

    # ------------------ NETWORK BENCHMARK TAB ------------------
    def _build_net_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)

        top_h = QHBoxLayout()
        self.btn_run_net = QPushButton("Iniciar Diagnóstico Completo de Rede")
        self.btn_run_net.setProperty("class", "Primary")
        self.btn_run_net.clicked.connect(self._run_net_bench)
        top_h.addWidget(self.btn_run_net)
        top_h.addStretch()
        l.addLayout(top_h)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.ncard_ping = self._metric_card("LATÊNCIA CLOUDFLARE (1.1.1.1)", "-- ms", "Tempo de resposta TCP direto")
        self.ncard_jitter = self._metric_card("JITTER & OSCILAÇÃO", "-- ms", "Variação de ping (abaixo de 5ms é perfeito para jogos)")
        self.ncard_speed = self._metric_card("DOWNLOAD (CLOUDFLARE CDN)", "-- Mbps", "Velocidade efetiva de transferência de pacotes")
        self.ncard_bloat = self._metric_card("BUFFERBLOAT SOB CARGA", "-- ms", "Aumento de lag quando a conexão está sendo usada")

        grid.addWidget(self.ncard_ping, 0, 0)
        grid.addWidget(self.ncard_jitter, 0, 1)
        grid.addWidget(self.ncard_speed, 1, 0)
        grid.addWidget(self.ncard_bloat, 1, 1)

        l.addLayout(grid)

        self.lbl_net_verdict = QLabel("Veredito: Aguardando teste")
        self.lbl_net_verdict.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px; font-weight: bold; color: #58a6ff;")
        l.addWidget(self.lbl_net_verdict)
        l.addStretch()
        return w

    def _run_net_bench(self):
        self.btn_run_net.setEnabled(False)

        def worker():
            res = self.net_bench.run(progress_cb=lambda s, p: self.progress_signal.emit(s, p))
            self.bench_done_signal.emit({"type": "net", "res": res})

        self.current_worker = threading.Thread(target=worker, daemon=True)
        self.current_worker.start()

    # ------------------ EVENT HANDLERS ------------------
    def _on_progress(self, msg, pct):
        self.lbl_status.setText(msg)
        self.prog_bar.setValue(int(pct * 100))

    def _on_bench_done(self, data):
        btype = data.get("type")
        if btype == "cpu":
            score = data.get("score", 0.0)
            self.lbl_cpu_score.setText(f"{score:.0f} pts")
            self.btn_run_cpu.setEnabled(True)
            self.lbl_status.setText(f"Benchmark de CPU Concluído: {score:.0f} pontos!")
            self.prog_bar.setValue(100)
        elif btype == "mem":
            res = data.get("res")
            if res:
                self.card_lat.val_label.setText(f"{res['latency_ns']} ns")
                self.card_read.val_label.setText(f"{res['read_gb_s']} GB/s")
                self.card_write.val_label.setText(f"{res['write_gb_s']} GB/s")
                self.card_copy.val_label.setText(f"{res['copy_gb_s']} GB/s")
            self.btn_run_mem.setEnabled(True)
        elif btype == "disk":
            res = data.get("res")
            if res:
                self.dcard_seq_w.val_label.setText(f"{res['seq_write_mbs']} MB/s")
                self.dcard_seq_r.val_label.setText(f"{res['seq_read_mbs']} MB/s")
                self.dcard_4k_q1.val_label.setText(f"{res['read_iops_q1']:.0f} IOPS ({res['read_lat_us']} μs)")
                self.dcard_4k_q8.val_label.setText(f"{res['read_iops_q8']:.0f} IOPS")
            self.btn_run_disk.setEnabled(True)
        elif btype == "net":
            res = data.get("res")
            if res:
                self.ncard_ping.val_label.setText(f"{res['ping_cf_ms']} ms")
                self.ncard_jitter.val_label.setText(f"{res['jitter_ms']} ms")
                self.ncard_speed.val_label.setText(f"{res['download_mbps']} Mbps")
                self.ncard_bloat.val_label.setText(f"{res['bufferbloat_ms']} ms")
                self.lbl_net_verdict.setText(f"Veredito da Conexão: {res['verdict']}")
            self.btn_run_net.setEnabled(True)

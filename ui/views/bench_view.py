"""
Benchmark Suite View for CachyPulse (Faithful to ResetExplode's Monochromatic Aesthetic).
Includes:
- CPU Cinebench Ray Tracer (Photorealistic tile visualizer)
- CPU Geekbench-Style Multi-Core & Single-Core Integer Throughput
- AIDA64-Grade RAM Latency & Bandwidth
- CrystalDiskMark Direct I/O Storage
- Network Latency, Jitter & Bufferbloat
"""

import threading
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTabWidget, QProgressBar, QComboBox,
    QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

from benchmarks.cpu_raytracer import CpuRaytracerBench, WIDTH, HEIGHT
from benchmarks.cpu_geekbench import CpuGeekbench
from benchmarks.memory_bench import MemoryBenchmark
from benchmarks.disk_bench import DiskBenchmark
from benchmarks.network_bench import NetworkBenchmark
from core.sys_info import get_storage_info

class RenderCanvasWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 270)
        self.setMaximumHeight(340)
        self.setStyleSheet("background-color: #050505; border: 1px solid #1C1C1C; border-radius: 12px;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Aguardando Início do Ray Tracer...")

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
        self.geek_bench = CpuGeekbench()
        self.mem_bench = MemoryBenchmark()
        self.disk_bench = DiskBenchmark()
        self.net_bench = NetworkBenchmark()

        self.current_worker = None
        self.progress_signal.connect(self._on_progress)
        self.cpu_render_update_signal.connect(self._on_cpu_render_tick)
        self.bench_done_signal.connect(self._on_bench_done)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_geekbench_tab(), "CPU (Estilo Geekbench)")
        self.tabs.addTab(self._build_cinebench_tab(), "CPU (Cinebench Ray Tracer)")
        self.tabs.addTab(self._build_mem_tab(), "Memória (AIDA64)")
        self.tabs.addTab(self._build_disk_tab(), "Disco (CrystalDiskMark)")
        self.tabs.addTab(self._build_net_tab(), "Diagnóstico de Rede")

        layout.addWidget(self.tabs)

        # Global Status Bar
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("background-color: #070707; border: 1px solid #181818; border-radius: 12px; padding: 12px;")
        sf_l = QVBoxLayout(self.status_frame)
        self.lbl_status = QLabel("Selecione um teste acima e clique em Executar.")
        self.lbl_status.setStyleSheet("color: #8C8C8C; font-weight: 600; font-size: 12px;")
        self.prog_bar = QProgressBar()
        self.prog_bar.setValue(0)
        self.prog_bar.setMaximumHeight(4)
        sf_l.addWidget(self.lbl_status)
        sf_l.addWidget(self.prog_bar)

        layout.addWidget(self.status_frame)

        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_l.addWidget(scroll)

    # ------------------ GEEKBENCH CPU TAB ------------------
    def _build_geekbench_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(16)

        top_h = QHBoxLayout()
        self.btn_run_geek = QPushButton("Executar Benchmark CPU (Geekbench)")
        self.btn_run_geek.setProperty("class", "Primary")
        self.btn_run_geek.clicked.connect(self._run_geekbench)
        top_h.addWidget(self.btn_run_geek)
        top_h.addStretch()
        l.addLayout(top_h)

        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_multi = self._tile("MULTI-CORE SCORE", "---- pts", "Desempenho com todos os 12 threads simultâneos")
        self.card_single = self._tile("SINGLE-CORE SCORE", "---- pts", "Desempenho de instrução por núcleo individual")
        self.card_mips = self._tile("CAPACIDADE TOTAL (MIPS)", "-- MIPS", "Milhões de instruções executadas por segundo")
        self.card_comp = self._tile("TAXA DE COMPRESSÃO", "-- MIPS", "Taxa de processamento inteiro pesado")

        grid.addWidget(self.card_multi, 0, 0)
        grid.addWidget(self.card_single, 0, 1)
        grid.addWidget(self.card_mips, 1, 0)
        grid.addWidget(self.card_comp, 1, 1)
        l.addLayout(grid)

        # Comparative Benchmarks Table Card
        ref_card = QFrame()
        ref_card.setProperty("class", "Card")
        rl = QVBoxLayout(ref_card)
        rtitle = QLabel("Ranking de Referência (Multi-Core)")
        rtitle.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF; margin-bottom: 8px;")
        rl.addWidget(rtitle)

        ref_text = QLabel(
            "• AMD Ryzen 9 7950X: ~19.500 pts Multi / ~2.950 pts Single<br>"
            "• Intel Core i7-13700K: ~16.800 pts Multi / ~2.800 pts Single<br>"
            "• AMD Ryzen 7 7700X: ~13.200 pts Multi / ~2.650 pts Single<br>"
            "• <b>Seu AMD Ryzen 5 5600: ~7.850 pts Multi / ~1.920 pts Single</b><br>"
            "• Intel Core i5-12400: ~7.200 pts Multi / ~1.750 pts Single<br>"
            "• AMD Ryzen 5 3600: ~5.600 pts Multi / ~1.450 pts Single"
        )
        ref_text.setStyleSheet("color: #8C8C8C; font-size: 12.5px; line-height: 1.5;")
        rl.addWidget(ref_text)
        l.addWidget(ref_card)
        l.addStretch()

        return w

    def _run_geekbench(self):
        self.btn_run_geek.setEnabled(False)

        def worker():
            res = self.geek_bench.run(threads=0, progress_cb=lambda s, p: self.progress_signal.emit(s, p))
            self.bench_done_signal.emit({"type": "geek", "res": res})

        self.current_worker = threading.Thread(target=worker, daemon=True)
        self.current_worker.start()

    # ------------------ CINEBENCH CPU TAB ------------------
    def _build_cinebench_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(16)

        top_h = QHBoxLayout()
        self.combo_cpu_mode = QComboBox()
        self.combo_cpu_mode.addItems(["Multi-Core (12 Threads)", "Single-Core (1 Thread)"])

        self.combo_cpu_spp = QComboBox()
        self.combo_cpu_spp.addItems(["Rápido (128 amostras)", "Padrão (256 amostras)", "Alta Precisão (512 amostras)"])
        self.combo_cpu_spp.setCurrentIndex(1)

        self.btn_run_cpu = QPushButton("Iniciar Ray Tracer")
        self.btn_run_cpu.setProperty("class", "Primary")
        self.btn_run_cpu.clicked.connect(self._run_cpu_bench)

        top_h.addWidget(QLabel("Modo:"))
        top_h.addWidget(self.combo_cpu_mode)
        top_h.addWidget(QLabel("Amostragem:"))
        top_h.addWidget(self.combo_cpu_spp)
        top_h.addWidget(self.btn_run_cpu)
        top_h.addStretch()
        l.addLayout(top_h)

        center_h = QHBoxLayout()
        self.render_canvas = RenderCanvasWidget()
        center_h.addWidget(self.render_canvas, stretch=2)

        # Score side panel
        score_frame = QFrame()
        score_frame.setProperty("class", "Card")
        sf_l = QVBoxLayout(score_frame)

        sf_title = QLabel("Pontuação Cinebench CPU")
        sf_title.setStyleSheet("color: #737373; font-weight: 700; font-size: 11px; text-transform: uppercase;")
        self.lbl_cpu_score = QLabel("---- pts")
        self.lbl_cpu_score.setStyleSheet("font-size: 34px; font-weight: 800; color: #FFFFFF; font-family: 'JetBrains Mono', Consolas, monospace; margin: 8px 0;")
        self.lbl_cpu_time = QLabel("Tempo: -- s")
        self.lbl_cpu_time.setStyleSheet("color: #737373; font-size: 12px;")

        ref_title = QLabel("<b>Referências Cinebench Multi:</b><br>"
                           "• Ryzen 7 7700X: ~4.500 pts<br>"
                           "• <b>Ryzen 5 5600: ~4.300 pts</b><br>"
                           "• Core i5-12400: ~2.850 pts")
        ref_title.setStyleSheet("color: #8C8C8C; font-size: 12px; margin-top: 15px; line-height: 1.4;")

        sf_l.addWidget(sf_title)
        sf_l.addWidget(self.lbl_cpu_score)
        sf_l.addWidget(self.lbl_cpu_time)
        sf_l.addWidget(ref_title)
        sf_l.addStretch()

        center_h.addWidget(score_frame, stretch=1)
        l.addLayout(center_h)
        l.addStretch()

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
                self.progress_signal.emit(f"Renderizando tiles: {completed}/{total} ({elapsed:.1f}s)", pct)
                self.cpu_render_update_signal.emit()

            score = self.cpu_bench.run(threads=threads, spp=spp, on_progress=on_progress)
            self.bench_done_signal.emit({"type": "cpu", "score": score})

        self.current_worker = threading.Thread(target=worker, daemon=True)
        self.current_worker.start()

    def _on_cpu_render_tick(self):
        raw = self.cpu_bench.get_pixel_buffer_bytes()
        self.render_canvas.update_frame(raw)

    # ------------------ MEMORY TAB ------------------
    def _build_mem_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(16)

        top_h = QHBoxLayout()
        self.btn_run_mem = QPushButton("Executar Teste de Memória (AIDA64)")
        self.btn_run_mem.setProperty("class", "Primary")
        self.btn_run_mem.clicked.connect(self._run_mem_bench)
        top_h.addWidget(self.btn_run_mem)
        top_h.addStretch()
        l.addLayout(top_h)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.card_lat = self._tile("LATÊNCIA DA MEMÓRIA (Sattolo Cycle)", "-- ns", "Tempo direto de ida à RAM (abaixo de 80 ns é excelente)")
        self.card_read = self._tile("LARGURA DE BANDA DE LEITURA", "-- GB/s", "Velocidade máxima de leitura contínua (DDR4 ~35 GB/s)")
        self.card_write = self._tile("LARGURA DE BANDA DE ESCRITA", "-- GB/s", "Taxa máxima de escrita contínua")
        self.card_copy = self._tile("LARGURA DE BANDA DE CÓPIA", "-- GB/s", "Transferência bidirecional entre blocos")

        grid.addWidget(self.card_lat, 0, 0)
        grid.addWidget(self.card_read, 0, 1)
        grid.addWidget(self.card_write, 1, 0)
        grid.addWidget(self.card_copy, 1, 1)
        l.addLayout(grid)
        l.addStretch()
        return w

    def _run_mem_bench(self):
        self.btn_run_mem.setEnabled(False)

        def worker():
            res = self.mem_bench.run_full(threads=0, progress_cb=lambda s, p: self.progress_signal.emit(s, p))
            self.bench_done_signal.emit({"type": "mem", "res": res})

        self.current_worker = threading.Thread(target=worker, daemon=True)
        self.current_worker.start()

    # ------------------ DISK TAB ------------------
    def _build_disk_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(16)

        top_h = QHBoxLayout()
        self.combo_disk_target = QComboBox()
        disks = get_storage_info()
        for d in disks:
            for p in d.get("partitions", []):
                self.combo_disk_target.addItem(f"{p['mountpoint']} ({d['model']})", p['mountpoint'])

        self.btn_run_disk = QPushButton("Executar CrystalDiskMark Direct I/O")
        self.btn_run_disk.setProperty("class", "Primary")
        self.btn_run_disk.clicked.connect(self._run_disk_bench)

        top_h.addWidget(QLabel("Unidade:"))
        top_h.addWidget(self.combo_disk_target)
        top_h.addWidget(self.btn_run_disk)
        top_h.addStretch()
        l.addLayout(top_h)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.dcard_seq_w = self._tile("ESCRITA SEQUENCIAL (1 MB)", "-- MB/s", "Direct I/O sem cache de sistema")
        self.dcard_seq_r = self._tile("LEITURA SEQUENCIAL (1 MB)", "-- MB/s", "Velocidade contínua de hardware")
        self.dcard_4k_q1 = self._tile("ACESSO 4K QD1 (ALEATÓRIO)", "-- IOPS", "Velocidade para inicializar o sistema e carregar jogos")
        self.dcard_4k_q8 = self._tile("ACESSO 4K QD8 (PARALELO)", "-- IOPS", "Fila profunda de múltiplas requisições NVMe")

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

    # ------------------ NETWORK TAB ------------------
    def _build_net_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(16)

        top_h = QHBoxLayout()
        self.btn_run_net = QPushButton("Executar Diagnóstico de Rede")
        self.btn_run_net.setProperty("class", "Primary")
        self.btn_run_net.clicked.connect(self._run_net_bench)
        top_h.addWidget(self.btn_run_net)
        top_h.addStretch()
        l.addLayout(top_h)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.ncard_ping = self._tile("LATÊNCIA CLOUDFLARE (1.1.1.1)", "-- ms", "Tempo de resposta de pacote direto")
        self.ncard_jitter = self._tile("JITTER & OSCILAÇÃO", "-- ms", "Estabilidade do ping (< 5ms ideal para eSports)")
        self.ncard_speed = self._tile("DOWNLOAD CDN", "-- Mbps", "Taxa de transferência em servidor público")
        self.ncard_bloat = self._tile("BUFFERBLOAT", "-- ms", "Aumento de latência sob tráfego concorrente")

        grid.addWidget(self.ncard_ping, 0, 0)
        grid.addWidget(self.ncard_jitter, 0, 1)
        grid.addWidget(self.ncard_speed, 1, 0)
        grid.addWidget(self.ncard_bloat, 1, 1)
        l.addLayout(grid)

        self.lbl_net_verdict = QLabel("Veredito: Aguardando teste")
        self.lbl_net_verdict.setStyleSheet("background: #0B0B0B; border: 1px solid #1C1C1C; border-radius: 12px; padding: 14px; font-weight: 700; color: #FFFFFF;")
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

    # ------------------ HELPERS ------------------
    def _tile(self, label, value, sub):
        f = QFrame()
        f.setProperty("class", "Card")
        vl = QVBoxLayout(f)
        vl.setSpacing(4)
        t = QLabel(label)
        t.setStyleSheet("color: #737373; font-size: 10.5px; font-weight: 700; text-transform: uppercase;")
        v = QLabel(value)
        v.setStyleSheet("color: #FFFFFF; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 26px; font-weight: 800; margin: 4px 0;")
        s = QLabel(sub)
        s.setStyleSheet("color: #737373; font-size: 11.5px;")
        vl.addWidget(t)
        vl.addWidget(v)
        vl.addWidget(s)
        f.val_label = v
        return f

    def _on_progress(self, msg, pct):
        self.lbl_status.setText(msg)
        self.prog_bar.setValue(int(pct * 100))

    def _on_bench_done(self, data):
        btype = data.get("type")
        if btype == "geek":
            res = data.get("res")
            if res:
                self.card_multi.val_label.setText(f"{res['score_multi']} pts")
                self.card_single.val_label.setText(f"{res['score_single']} pts")
                self.card_mips.val_label.setText(f"{res['total_mips']:,} MIPS")
                self.card_comp.val_label.setText(f"{res['comp_mips']:,} MIPS")
                self.lbl_status.setText(f"Benchmark Geekbench Concluído: {res['score_multi']} pts Multi / {res['score_single']} pts Single!")
            self.btn_run_geek.setEnabled(True)
            self.prog_bar.setValue(100)
        elif btype == "cpu":
            score = data.get("score", 0.0)
            self.lbl_cpu_score.setText(f"{score:.0f} pts")
            self.btn_run_cpu.setEnabled(True)
            self.lbl_status.setText(f"Benchmark Cinebench Concluído: {score:.0f} pts!")
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
                self.dcard_4k_q1.val_label.setText(f"{res['read_iops_q1']:.0f} IOPS")
                self.dcard_4k_q8.val_label.setText(f"{res['read_iops_q8']:.0f} IOPS")
            self.btn_run_disk.setEnabled(True)
        elif btype == "net":
            res = data.get("res")
            if res:
                self.ncard_ping.val_label.setText(f"{res['ping_cf_ms']} ms")
                self.ncard_jitter.val_label.setText(f"{res['jitter_ms']} ms")
                self.ncard_speed.val_label.setText(f"{res['download_mbps']} Mbps")
                self.ncard_bloat.val_label.setText(f"{res['bufferbloat_ms']} ms")
                self.lbl_net_verdict.setText(f"Veredito: {res['verdict']}")
            self.btn_run_net.setEnabled(True)

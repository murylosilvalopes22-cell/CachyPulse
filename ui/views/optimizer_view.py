"""
System and Gaming Optimizer View for CachyPulse (Faithful to ResetExplode's Monochromatic Aesthetic).
Provides memory cache flushing, ZRAM compaction, CPU scaling governor switcher,
CachyOS service status (ananicy-cpp / gamemoded), and heavy process terminator.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt
from core.optimizer import SystemOptimizer

class OptimizerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Quick Tweaks Card
        card_quick = QFrame()
        card_quick.setProperty("class", "Card")
        ql = QVBoxLayout(card_quick)
        ql.setSpacing(10)

        qtitle = QLabel("OTIMIZAÇÕES DE MEMÓRIA & CACHE (CACHYOS / LINUX)")
        qtitle.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        ql.addWidget(qtitle)

        qdesc = QLabel(
            "Libere memória em espera (pagecache, dentries e inodes) e execute a compactação "
            "imediata dos blocos de ZRAM para manter o sistema com máxima RAM livre para jogos."
        )
        qdesc.setStyleSheet("color: #8C8C8C; font-size: 12.5px; line-height: 1.4;")
        qdesc.setWordWrap(True)
        ql.addWidget(qdesc)

        btn_row = QHBoxLayout()
        self.btn_drop_caches = QPushButton("Limpar Memória em Espera (drop_caches)")
        self.btn_drop_caches.setProperty("class", "Primary")
        self.btn_drop_caches.clicked.connect(self._on_drop_caches)
        btn_row.addWidget(self.btn_drop_caches)

        self.btn_compact_zram = QPushButton("Compactar Memória ZRAM")
        self.btn_compact_zram.clicked.connect(self._on_compact_zram)
        btn_row.addWidget(self.btn_compact_zram)
        btn_row.addStretch()

        ql.addLayout(btn_row)
        layout.addWidget(card_quick)

        # 2. CPU Governor & CachyOS Daemons Card
        card_cpu = QFrame()
        card_cpu.setProperty("class", "Card")
        cl = QVBoxLayout(card_cpu)
        cl.setSpacing(12)

        ctitle = QLabel("GOVERNADOR DA CPU & SERVIÇOS CACHYOS")
        ctitle.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        cl.addWidget(ctitle)

        gov_row = QHBoxLayout()
        gov_row.addWidget(QLabel("Governador:"))
        self.combo_gov = QComboBox()
        gov_data = SystemOptimizer.get_governors()
        self.combo_gov.addItems(gov_data["available"])
        if gov_data["current"] in gov_data["available"]:
            self.combo_gov.setCurrentText(gov_data["current"])

        gov_row.addWidget(self.combo_gov)

        self.btn_apply_gov = QPushButton("Aplicar")
        self.btn_apply_gov.setProperty("class", "Primary")
        self.btn_apply_gov.clicked.connect(self._on_apply_governor)
        gov_row.addWidget(self.btn_apply_gov)
        gov_row.addStretch()
        cl.addLayout(gov_row)

        # Service badges
        srv = SystemOptimizer.get_cachyos_services()
        srv_row = QHBoxLayout()
        lbl_ananicy = QLabel(f"ananicy-cpp (Auto-Nice): {'ATIVO' if srv.get('ananicy-cpp') else 'INATIVO'}")
        lbl_ananicy.setStyleSheet(f"background: #141414; border: 1px solid #282828; color: {'#3FB950' if srv.get('ananicy-cpp') else '#DC2626'}; padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 800;")

        lbl_gamemode = QLabel(f"Feral GameMode: {'DISPONÍVEL' if srv.get('gamemoded') else 'NÃO INICIADO'}")
        lbl_gamemode.setStyleSheet(f"background: #141414; border: 1px solid #282828; color: {'#00D2FF' if srv.get('gamemoded') else '#737373'}; padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 800;")

        srv_row.addWidget(lbl_ananicy)
        srv_row.addWidget(lbl_gamemode)
        srv_row.addStretch()
        cl.addLayout(srv_row)

        layout.addWidget(card_cpu)

        # 3. Heavy Processes Card
        card_proc = QFrame()
        card_proc.setProperty("class", "Card")
        pl = QVBoxLayout(card_proc)
        pl.setSpacing(12)

        ph_layout = QHBoxLayout()
        ph_title = QLabel("PROCESSOS COM ALTO CONSUMO DE RAM (> 150 MB)")
        ph_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        ph_layout.addWidget(ph_title)
        ph_layout.addStretch()

        self.btn_refresh_procs = QPushButton("Atualizar")
        self.btn_refresh_procs.clicked.connect(self._refresh_processes)
        ph_layout.addWidget(self.btn_refresh_procs)

        self.btn_kill_proc = QPushButton("Encerrar Processo")
        self.btn_kill_proc.setProperty("class", "Danger")
        self.btn_kill_proc.clicked.connect(self._terminate_selected_process)
        ph_layout.addWidget(self.btn_kill_proc)
        pl.addLayout(ph_layout)

        self.proc_table = QTableWidget()
        self.proc_table.setColumnCount(4)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Nome do Processo", "RAM Usada (MB)", "% da RAM"])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proc_table.verticalHeader().setVisible(False)
        self.proc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.proc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        pl.addWidget(self.proc_table)

        layout.addWidget(card_proc)
        layout.addStretch()

        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_l.addWidget(scroll)

        self._refresh_processes()

    def _on_drop_caches(self):
        ok = SystemOptimizer.drop_caches()
        if ok:
            QMessageBox.information(self, "Sucesso", "Caches de memória liberados com sucesso!")
        else:
            QMessageBox.warning(self, "Aviso", "Memória sincronizada. Para drop_caches completo, forneça a autenticação de administrador.")

    def _on_compact_zram(self):
        ok, msg = SystemOptimizer.compact_zram()
        if ok:
            QMessageBox.information(self, "Sucesso", msg)
        else:
            QMessageBox.warning(self, "Aviso", msg)

    def _on_apply_governor(self):
        gov = self.combo_gov.currentText()
        ok = SystemOptimizer.set_governor(gov)
        if ok:
            QMessageBox.information(self, "Sucesso", f"Governador da CPU alterado para '{gov}'!")
        else:
            QMessageBox.warning(self, "Aviso", "Falha ou permissão negada ao alterar o governador da CPU.")

    def _refresh_processes(self):
        procs = SystemOptimizer.get_heavy_processes()
        self.proc_table.setRowCount(len(procs))
        for i, p in enumerate(procs):
            item_pid = QTableWidgetItem(str(p["pid"]))
            item_name = QTableWidgetItem(p["name"])
            item_mb = QTableWidgetItem(f"{p['mem_mb']:.1f} MB")
            item_mb.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pct = QTableWidgetItem(f"{p['mem_pct']:.1f}%")
            item_pct.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.proc_table.setItem(i, 0, item_pid)
            self.proc_table.setItem(i, 1, item_name)
            self.proc_table.setItem(i, 2, item_mb)
            self.proc_table.setItem(i, 3, item_pct)

    def _terminate_selected_process(self):
        row = self.proc_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Aviso", "Selecione um processo na tabela.")
            return

        pid_text = self.proc_table.item(row, 0).text()
        name_text = self.proc_table.item(row, 1).text()
        ans = QMessageBox.question(self, "Confirmar Encerramento", f"Tem certeza que deseja encerrar '{name_text}' (PID {pid_text})?")
        if ans == QMessageBox.StandardButton.Yes:
            SystemOptimizer.terminate_process(int(pid_text))
            self._refresh_processes()

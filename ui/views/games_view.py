"""
Gaming & Bottleneck Diagnostics View for CachyPulse.
Provides real-time Bottleneck Detection (CPU vs GPU vs VRAM vs Thermal),
Steam game library parser, and One-Click Game Launcher with MangoHud, GameMode, and Gamescope.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QComboBox, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from core.bottleneck import analyze_bottleneck
from core.game_library import GameLibrary

class GamesView(QWidget):
    def __init__(self, sensor_monitor, parent=None):
        super().__init__(parent)
        self.monitor = sensor_monitor
        self.game_lib = GameLibrary()

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(18)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Bottleneck Diagnostics Card
        self.bn_card = QFrame()
        self.bn_card.setProperty("class", "Card")
        bn_l = QVBoxLayout(self.bn_card)

        self.lbl_bn_title = QLabel("Detector de Gargalo em Tempo Real")
        self.lbl_bn_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        bn_l.addWidget(self.lbl_bn_title)

        self.lbl_bn_desc = QLabel("Analisando telemetria de CPU, GPU, VRAM e temperaturas...")
        self.lbl_bn_desc.setStyleSheet("color: #e6edf3; font-size: 14px; margin: 4px 0;")
        bn_l.addWidget(self.lbl_bn_desc)

        self.lbl_bn_advice = QLabel("Dica: Inicie um jogo para verificar se há limitações de hardware.")
        self.lbl_bn_advice.setStyleSheet("color: #8b949e; font-size: 12px; background: #0d1117; padding: 10px; border-radius: 6px; border: 1px solid #21262d;")
        self.lbl_bn_advice.setWordWrap(True)
        bn_l.addWidget(self.lbl_bn_advice)

        layout.addWidget(self.bn_card)

        # 2. Game Launcher Optimizer Options Card
        opts_card = QFrame()
        opts_card.setProperty("class", "Card")
        ol = QVBoxLayout(opts_card)

        otitle = QLabel("Otimizador de Inicialização de Jogos (Linux & CachyOS)")
        otitle.setStyleSheet("font-size: 14px; font-weight: bold; color: #e6edf3;")
        ol.addWidget(otitle)

        toggles_l = QHBoxLayout()
        self.chk_mangohud = QCheckBox("Ativar MangoHud (Overlay de FPS & Sensores)")
        self.chk_mangohud.setChecked(True)

        self.chk_gamemode = QCheckBox("Ativar GameMode (gamemoderun)")
        self.chk_gamemode.setChecked(False)

        self.chk_gamescope = QCheckBox("Ativar Gamescope (Upscaling / Resolução Isolada)")
        self.chk_gamescope.setChecked(False)

        self.combo_gamescope_res = QComboBox()
        self.combo_gamescope_res.addItems(["1920x1080", "2560x1440", "1280x720"])

        toggles_l.addWidget(self.chk_mangohud)
        toggles_l.addWidget(self.chk_gamemode)
        toggles_l.addWidget(self.chk_gamescope)
        toggles_l.addWidget(self.combo_gamescope_res)
        toggles_l.addStretch()
        ol.addLayout(toggles_l)

        layout.addWidget(opts_card)

        # 3. Game Library Table
        lib_card = QFrame()
        lib_card.setProperty("class", "Card")
        ll = QVBoxLayout(lib_card)

        lh_layout = QHBoxLayout()
        lh_title = QLabel("Biblioteca de Jogos Instalados (Steam & Nativos)")
        lh_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e6edf3;")
        lh_layout.addWidget(lh_title)
        lh_layout.addStretch()

        self.btn_refresh_games = QPushButton("Escanear Jogos")
        self.btn_refresh_games.clicked.connect(self._scan_games)
        lh_layout.addWidget(self.btn_refresh_games)

        self.btn_play = QPushButton("JOGAR COM OTIMIZAÇÕES")
        self.btn_play.setProperty("class", "Primary")
        self.btn_play.clicked.connect(self._launch_selected_game)
        lh_layout.addWidget(self.btn_play)
        ll.addLayout(lh_layout)

        self.game_table = QTableWidget()
        self.game_table.setColumnCount(3)
        self.game_table.setHorizontalHeaderLabels(["Nome do Jogo", "Plataforma", "Tamanho em Disco"])
        self.game_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.game_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.game_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.game_table.verticalHeader().setVisible(False)
        self.game_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.game_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.game_table.doubleClicked.connect(self._launch_selected_game)

        ll.addWidget(self.game_table)
        layout.addWidget(lib_card)

        layout.addStretch()

        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        main_l.addWidget(scroll)

        # Bottleneck polling timer
        self.bn_timer = QTimer(self)
        self.bn_timer.timeout.connect(self._update_bottleneck)
        self.bn_timer.start(1500)

        self._scan_games()

    def _update_bottleneck(self):
        snap = self.monitor.get_snapshot()
        res = analyze_bottleneck(snap)
        self.lbl_bn_title.setText(f"Detector de Gargalo: {res.title}")
        self.lbl_bn_desc.setText(res.description)
        self.lbl_bn_advice.setText(f"Recomendação CachyPulse: {res.advice}")

        if res.severity == "critical":
            self.lbl_bn_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #da3633;")
        elif res.severity == "warning":
            self.lbl_bn_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f0883e;")
        elif res.severity == "good":
            self.lbl_bn_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3fb950;")
        else:
            self.lbl_bn_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")

    def _scan_games(self):
        games = self.game_lib.scan_steam_games()
        self.game_table.setRowCount(len(games))
        for i, g in enumerate(games):
            item_name = QTableWidgetItem(g["name"])
            item_name.setData(Qt.ItemDataRole.UserRole, g["id"])
            item_plat = QTableWidgetItem(g["platform"])
            item_size = QTableWidgetItem(f"{g['size_gb']} GB")
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.game_table.setItem(i, 0, item_name)
            self.game_table.setItem(i, 1, item_plat)
            self.game_table.setItem(i, 2, item_size)

        if games:
            self.game_table.selectRow(0)

    def _launch_selected_game(self):
        row = self.game_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Aviso", "Selecione um jogo da lista para iniciar.")
            return

        item = self.game_table.item(row, 0)
        appid = item.data(Qt.ItemDataRole.UserRole)
        name = item.text()

        mangohud = self.chk_mangohud.isChecked()
        gamemode = self.chk_gamemode.isChecked()
        gamescope = self.chk_gamescope.isChecked()
        gamescope_res = self.combo_gamescope_res.currentText()

        ok, msg = GameLibrary.launch_game(
            appid=appid,
            mangohud=mangohud,
            gamemode=gamemode,
            gamescope=gamescope,
            gamescope_res=gamescope_res
        )

        if ok:
            QMessageBox.information(self, "Iniciando Jogo", f"Iniciando {name} com MangoHud={mangohud}, GameMode={gamemode}...")
        else:
            QMessageBox.critical(self, "Erro", msg)

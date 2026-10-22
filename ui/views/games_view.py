"""
Gaming & Bottleneck Diagnostics View for CachyPulse (Faithful to ResetExplode's Monochromatic Aesthetic).
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
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Bottleneck Diagnostics Card
        self.bn_card = QFrame()
        self.bn_card.setProperty("class", "Card")
        bn_l = QVBoxLayout(self.bn_card)
        bn_l.setSpacing(10)

        self.lbl_bn_title = QLabel("DETECTOR DE GARGALO EM TEMPO REAL")
        self.lbl_bn_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;")
        bn_l.addWidget(self.lbl_bn_title)

        self.lbl_bn_desc = QLabel("Analisando telemetria de CPU, GPU, VRAM e temperaturas...")
        self.lbl_bn_desc.setStyleSheet("color: #E0E0E0; font-size: 13.5px; line-height: 1.4;")
        self.lbl_bn_desc.setWordWrap(True)
        bn_l.addWidget(self.lbl_bn_desc)

        self.lbl_bn_advice = QLabel("Dica: Inicie um jogo para verificar se há limitações de hardware.")
        self.lbl_bn_advice.setStyleSheet("color: #8C8C8C; font-size: 12px; background: #060606; padding: 12px; border-radius: 8px; border: 1px solid #1C1C1C;")
        self.lbl_bn_advice.setWordWrap(True)
        bn_l.addWidget(self.lbl_bn_advice)

        layout.addWidget(self.bn_card)

        # 2. Game Launcher Optimizer Options Card
        opts_card = QFrame()
        opts_card.setProperty("class", "Card")
        ol = QVBoxLayout(opts_card)
        ol.setSpacing(10)

        otitle = QLabel("OTIMIZADOR DE INICIALIZAÇÃO DE JOGOS")
        otitle.setStyleSheet("font-size: 12px; font-weight: 700; color: #737373; text-transform: uppercase;")
        ol.addWidget(otitle)

        toggles_l = QHBoxLayout()
        self.chk_mangohud = QCheckBox("MangoHud (Overlay de FPS & Sensores)")
        self.chk_mangohud.setChecked(True)
        self.chk_mangohud.setStyleSheet("color: #E0E0E0; font-size: 13px;")

        self.chk_gamemode = QCheckBox("Feral GameMode")
        self.chk_gamemode.setChecked(False)
        self.chk_gamemode.setStyleSheet("color: #E0E0E0; font-size: 13px;")

        self.chk_gamescope = QCheckBox("Gamescope (Upscaling)")
        self.chk_gamescope.setChecked(False)
        self.chk_gamescope.setStyleSheet("color: #E0E0E0; font-size: 13px;")

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
        ll.setSpacing(12)

        lh_layout = QHBoxLayout()
        lh_title = QLabel("BIBLIOTECA DE JOGOS INSTALADOS")
        lh_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #737373; text-transform: uppercase;")
        lh_layout.addWidget(lh_title)
        lh_layout.addStretch()

        self.btn_refresh_games = QPushButton("Escanear")
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
        scroll.setWidget(container)
        main_l.addWidget(scroll)

        # Bottleneck polling timer
        self.bn_timer = QTimer(self)
        self.bn_timer.timeout.connect(self._update_bottleneck)
        self.bn_timer.start(1500)

        self._scan_games()

    def _update_bottleneck(self):
        snap = self.monitor.get_snapshot()
        res = analyze_bottleneck(snap)
        self.lbl_bn_title.setText(f"DETECTOR DE GARGALO: {res.title.upper()}")
        self.lbl_bn_desc.setText(res.description)
        self.lbl_bn_advice.setText(f"Recomendação CachyPulse: {res.advice}")

        if res.severity == "critical":
            self.lbl_bn_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #DC2626;")
        elif res.severity == "warning":
            self.lbl_bn_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #F59E0B;")
        elif res.severity == "good":
            self.lbl_bn_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #10B981;")
        else:
            self.lbl_bn_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")

    def _scan_games(self):
        games = self.game_lib.scan_steam_games()
        self.game_table.setRowCount(len(games))
        for i, g in enumerate(games):
            item_name = QTableWidgetItem(g["name"])
            item_name.setData(Qt.ItemDataRole.UserRole, g["id"])
            item_plat = QTableWidgetItem(g["platform"])
            item_plat.setForeground(Qt.GlobalColor.gray)
            item_size = QTableWidgetItem(f"{g['size_gb']} GB")
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_size.setForeground(Qt.GlobalColor.white)

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

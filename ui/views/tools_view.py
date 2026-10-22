"""
Tools, Startup Manager, App Installer & Maker Serial View for CachyPulse.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt
from core.startup_manager import StartupManager
from core.app_installer import AppInstaller
from core.maker_serial import MakerSerial

class ToolsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_startup_tab(), "Inicialização do Sistema")
        self.tabs.addTab(self._build_apps_tab(), "Instalar Aplicativos Úteis")
        self.tabs.addTab(self._build_maker_tab(), "Maker & Portas Seriais (Arduino/ESP)")

        layout.addWidget(self.tabs)

    # ------------------ STARTUP TAB ------------------
    def _build_startup_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)

        top_h = QHBoxLayout()
        top_h.addWidget(QLabel("Aplicativos que iniciam junto com o ambiente gráfico:"))
        top_h.addStretch()
        self.btn_refresh_startup = QPushButton("Atualizar")
        self.btn_refresh_startup.clicked.connect(self._refresh_startup)
        self.btn_toggle_startup = QPushButton("Ativar / Desativar Selecionado")
        self.btn_toggle_startup.setProperty("class", "Primary")
        self.btn_toggle_startup.clicked.connect(self._toggle_startup)

        top_h.addWidget(self.btn_refresh_startup)
        top_h.addWidget(self.btn_toggle_startup)
        l.addLayout(top_h)

        self.table_startup = QTableWidget()
        self.table_startup.setColumnCount(4)
        self.table_startup.setHorizontalHeaderLabels(["Status", "Nome do Programa", "Comando de Execução", "Tipo"])
        self.table_startup.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_startup.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_startup.verticalHeader().setVisible(False)
        self.table_startup.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_startup.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        l.addWidget(self.table_startup)
        self._refresh_startup()
        return w

    def _refresh_startup(self):
        entries = StartupManager.list_entries()
        self.table_startup.setRowCount(len(entries))
        self.startup_entries = entries
        for i, e in enumerate(entries):
            st_text = "ATIVO" if e.enabled else "DESATIVADO"
            item_st = QTableWidgetItem(st_text)
            if e.enabled:
                item_st.setForeground(Qt.GlobalColor.green)
            else:
                item_st.setForeground(Qt.GlobalColor.red)

            item_name = QTableWidgetItem(e.name)
            item_cmd = QTableWidgetItem(e.exec_cmd)
            item_type = QTableWidgetItem("Usuário" if e.is_user else "Sistema")

            self.table_startup.setItem(i, 0, item_st)
            self.table_startup.setItem(i, 1, item_name)
            self.table_startup.setItem(i, 2, item_cmd)
            self.table_startup.setItem(i, 3, item_type)

    def _toggle_startup(self):
        row = self.table_startup.currentRow()
        if row < 0 or row >= len(self.startup_entries):
            return
        entry = self.startup_entries[row]
        StartupManager.toggle_entry(entry)
        self._refresh_startup()

    # ------------------ APPS INSTALLER TAB ------------------
    def _build_apps_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)

        top_h = QHBoxLayout()
        top_h.addWidget(QLabel("Catálogo de ferramentas essenciais de Jogos, Benchmark e Maker para CachyOS / Arch:"))
        top_h.addStretch()
        self.btn_refresh_apps = QPushButton("Atualizar")
        self.btn_refresh_apps.clicked.connect(self._refresh_apps)
        top_h.addWidget(self.btn_refresh_apps)
        l.addLayout(top_h)

        self.table_apps = QTableWidget()
        self.table_apps.setColumnCount(4)
        self.table_apps.setHorizontalHeaderLabels(["Aplicativo", "Categoria", "Descrição", "Ação"])
        self.table_apps.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_apps.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_apps.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_apps.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_apps.verticalHeader().setVisible(False)
        self.table_apps.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        l.addWidget(self.table_apps)
        self._refresh_apps()
        return w

    def _refresh_apps(self):
        apps = AppInstaller.get_apps()
        self.table_apps.setRowCount(len(apps))
        for i, a in enumerate(apps):
            item_name = QTableWidgetItem(a["name"])
            item_cat = QTableWidgetItem(a["category"])
            item_desc = QTableWidgetItem(a["desc"])

            self.table_apps.setItem(i, 0, item_name)
            self.table_apps.setItem(i, 1, item_cat)
            self.table_apps.setItem(i, 2, item_desc)

            if a["installed"]:
                btn = QPushButton("Instalado")
                btn.setEnabled(False)
            else:
                btn = QPushButton("Instalar")
                btn.setProperty("class", "Primary")
                btn.clicked.connect(lambda ch, aid=a["id"]: self._install_app(aid))

            self.table_apps.setCellWidget(i, 3, btn)

    def _install_app(self, app_id):
        ans = QMessageBox.question(self, "Instalação", f"Deseja iniciar a instalação do pacote para {app_id}?")
        if ans == QMessageBox.StandardButton.Yes:
            ok, msg = AppInstaller.install_app(app_id)
            if ok:
                QMessageBox.information(self, "Sucesso", msg)
            else:
                QMessageBox.warning(self, "Aviso", msg)
            self._refresh_apps()

    # ------------------ MAKER / SERIAL TAB ------------------
    def _build_maker_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)

        card_perm = QFrame()
        card_perm.setProperty("class", "Card")
        cpl = QVBoxLayout(card_perm)

        has_perm, groups = MakerSerial.check_permissions()
        perm_title = QLabel("Permissões de Usuário para Portas Seriais (uucp / dialout)")
        perm_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
        cpl.addWidget(perm_title)

        st_text = "Seu usuário tem permissão para ler e gravar em dispositivos seriais." if has_perm else \
                  "ATENÇÃO: Seu usuário NÃO está no grupo 'uucp'. O Arduino IDE ou monitor serial podem dar 'Permissão negada'."
        lbl_status = QLabel(st_text)
        lbl_status.setStyleSheet("color: #3fb950; font-weight: bold;" if has_perm else "color: #f0883e; font-weight: bold;")
        cpl.addWidget(lbl_status)

        if not has_perm:
            btn_fix = QPushButton("Corrigir Permissões (Adicionar aos grupos uucp e dialout)")
            btn_fix.setProperty("class", "Primary")
            btn_fix.clicked.connect(self._fix_serial_perm)
            cpl.addWidget(btn_fix)

        l.addWidget(card_perm)

        # Serial ports table
        card_ports = QFrame()
        card_ports.setProperty("class", "Card")
        cpt = QVBoxLayout(card_ports)

        pth_l = QHBoxLayout()
        pth_l.addWidget(QLabel("Dispositivos USB-Serial Conectados (/dev/ttyUSB*, /dev/ttyACM*):"))
        pth_l.addStretch()
        btn_ref_ports = QPushButton("Atualizar Portas")
        btn_ref_ports.clicked.connect(self._refresh_ports)
        pth_l.addWidget(btn_ref_ports)
        cpt.addLayout(pth_l)

        self.table_ports = QTableWidget()
        self.table_ports.setColumnCount(3)
        self.table_ports.setHorizontalHeaderLabels(["Porta", "Dispositivo / Chip", "Identificador USB"])
        self.table_ports.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_ports.verticalHeader().setVisible(False)
        self.table_ports.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cpt.addWidget(self.table_ports)

        l.addWidget(card_ports)
        l.addStretch()

        self._refresh_ports()
        return w

    def _refresh_ports(self):
        ports = MakerSerial.list_ports()
        self.table_ports.setRowCount(len(ports))
        for i, p in enumerate(ports):
            self.table_ports.setItem(i, 0, QTableWidgetItem(p["port"]))
            self.table_ports.setItem(i, 1, QTableWidgetItem(p["desc"]))
            self.table_ports.setItem(i, 2, QTableWidgetItem(p["hw_id"]))

    def _fix_serial_perm(self):
        ok = MakerSerial.fix_permissions()
        if ok:
            QMessageBox.information(self, "Sucesso", "Permissões corrigidas com sucesso!\nFaça logout e login novamente para aplicar os novos grupos ao seu usuário.")
        else:
            QMessageBox.warning(self, "Aviso", "Falha ou permissão negada.")

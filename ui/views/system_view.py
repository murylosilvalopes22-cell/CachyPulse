"""
Detailed System Specs View for CachyPulse.
Displays Motherboard/BIOS, CPU architectural specs, GPU-Z style GPU specs,
RAM/ZRAM details, and Report Exporting.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QFileDialog, QMessageBox
)
from core.sys_info import (
    get_cpu_info, get_gpu_info, get_motherboard_info,
    get_ram_info, get_storage_info, get_os_info
)
from core.report_export import export_html, export_json

class SystemView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with Export Buttons
        header_layout = QHBoxLayout()
        title = QLabel("Especificações Detalhadas do Hardware")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        btn_export_html = QPushButton("Exportar Relatório HTML")
        btn_export_html.setProperty("class", "Primary")
        btn_export_html.clicked.connect(self._export_html_report)
        header_layout.addWidget(btn_export_html)

        btn_export_json = QPushButton("Exportar JSON")
        btn_export_json.clicked.connect(self._export_json_report)
        header_layout.addWidget(btn_export_json)

        layout.addLayout(header_layout)

        # Data sources
        mb = get_motherboard_info()
        cpu = get_cpu_info()
        gpu = get_gpu_info()
        ram = get_ram_info()

        # 1. Motherboard Card
        card_mb = self._create_card("Placa-Mãe & BIOS", [
            ("Fabricante", mb["vendor"]),
            ("Modelo da Placa", mb["board_name"]),
            ("Versão da BIOS", mb["bios_version"]),
            ("Data da BIOS", mb["bios_date"]),
            ("Formato do Chassi", mb["chassis"])
        ])
        layout.addWidget(card_mb)

        # 2. CPU Architecture Card
        card_cpu = self._create_card("Processador (CPU)", [
            ("Nome do Modelo", cpu["model"]),
            ("Arquitetura", cpu["arch"]),
            ("Núcleos Físicos / Lógicos", f"{cpu['cores']} Cores / {cpu['threads']} Threads"),
            ("Governador de Escala", cpu["governor"]),
            ("Cache L1 (Dados/Instruções)", f"{cpu['l1d']} / {cpu['l1i']}"),
            ("Cache L2", cpu["l2"]),
            ("Cache L3 Compartilhado", cpu["l3"]),
            ("Frequência Máxima Turbo", f"{cpu['max_mhz']} MHz")
        ])
        layout.addWidget(card_cpu)

        # 3. GPU-Z Style GPU Card
        card_gpu = self._create_card("Placa de Vídeo (Estilo GPU-Z)", [
            ("Nome da GPU", gpu["name"]),
            ("Chip / Arquitetura", f"{gpu['chip']} ({gpu['arch']})"),
            ("Processo de Fabricação", gpu["process"]),
            ("Shaders / CUDA Cores", str(gpu["shaders"])),
            ("ROPs / TMUs", f"{gpu['rops']} / {gpu['tmus']}"),
            ("Tensor Cores / RT Cores", f"{gpu['tensor']} / {gpu['rt_cores']}"),
            ("Memória de Vídeo (VRAM)", f"{gpu['vram_total_mb']} MB {gpu['mem_type']}"),
            ("Barramento de Memória", f"{gpu['bus_bit']} bits ({gpu['bandwidth_gbs']} GB/s)"),
            ("Limite de Energia (TDP)", f"{gpu['tdp_w']} W"),
            ("Driver Gráfico Linux", gpu["driver"])
        ])
        layout.addWidget(card_gpu)

        # 4. RAM & ZRAM Card
        card_ram = self._create_card("Memória RAM & ZRAM", [
            ("Capacidade Total", f"{ram['total_gb']} GB"),
            ("Memória Disponível", f"{ram['available_gb']} GB"),
            ("ZRAM Swap Ativo", f"Sim ({ram['zram_size_gb']} GB)" if ram["has_zram"] else "Não"),
            ("Swap Total", f"{ram['swap_total_gb']} GB"),
            ("Swappiness do Kernel", ram["swappiness"])
        ])
        layout.addWidget(card_ram)

        layout.addStretch()

        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(container)
        main_l.addWidget(scroll)

    def _create_card(self, title, items):
        frame = QFrame()
        frame.setProperty("class", "Card")
        l = QVBoxLayout(frame)

        h = QLabel(title)
        h.setStyleSheet("font-size: 14px; font-weight: bold; color: #e6edf3; border-bottom: 1px solid #30363d; padding-bottom: 6px; margin-bottom: 10px;")
        l.addWidget(h)

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, (k, v) in enumerate(items):
            row = i // 2
            col = (i % 2) * 2
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet("color: #8b949e; font-weight: 500;")
            lbl_v = QLabel(str(v))
            lbl_v.setStyleSheet("color: #f0f6fc; font-weight: bold;")
            grid.addWidget(lbl_k, row, col)
            grid.addWidget(lbl_v, row, col + 1)

        l.addLayout(grid)
        return frame

    def _get_full_report_data(self):
        return {
            "os": get_os_info(),
            "motherboard": get_motherboard_info(),
            "cpu": get_cpu_info(),
            "gpu": get_gpu_info(),
            "ram": get_ram_info(),
            "storage": get_storage_info()
        }

    def _export_html_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório HTML", "cachypulse_relatorio.html", "HTML Files (*.html)")
        if path:
            export_html(self._get_full_report_data(), path)
            QMessageBox.information(self, "Sucesso", f"Relatório salvo com sucesso em:\n{path}")

    def _export_json_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório JSON", "cachypulse_relatorio.json", "JSON Files (*.json)")
        if path:
            export_json(self._get_full_report_data(), path)
            QMessageBox.information(self, "Sucesso", f"Relatório salvo com sucesso em:\n{path}")

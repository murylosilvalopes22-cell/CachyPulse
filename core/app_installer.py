"""
Application Installer for CachyPulse (CachyOS / Arch Linux).
Installs essential gaming, benchmark, and maker software via pacman / paru / yay / flatpak.
"""

import shutil
import subprocess

APP_CATALOG = [
    {
        "id": "steam",
        "name": "Steam",
        "category": "Jogos",
        "desc": "Principal plataforma de jogos para PC com suporte nativo ao Proton.",
        "bin": "steam",
        "pkg_pacman": "steam"
    },
    {
        "id": "heroic",
        "name": "Heroic Games Launcher",
        "category": "Jogos",
        "desc": "Gerenciador nativo para jogos da Epic Games e GOG no Linux.",
        "bin": "heroic",
        "pkg_pacman": "heroic-games-launcher-bin"
    },
    {
        "id": "lutris",
        "name": "Lutris",
        "category": "Jogos",
        "desc": "Plataforma aberta para gerenciar e executar jogos Windows e emuladores.",
        "bin": "lutris",
        "pkg_pacman": "lutris"
    },
    {
        "id": "mangohud",
        "name": "MangoHud",
        "category": "Jogos",
        "desc": "Overlay de desempenho (FPS, temperaturas, frametime) para Vulkan e OpenGL.",
        "bin": "mangohud",
        "pkg_pacman": "mangohud"
    },
    {
        "id": "protonup-qt",
        "name": "ProtonUp-Qt",
        "category": "Jogos",
        "desc": "Instale e gerencie facilmente versões do GE-Proton, Wine-GE e Luxtorpeda.",
        "bin": "protonup-qt",
        "pkg_pacman": "protonup-qt"
    },
    {
        "id": "discord",
        "name": "Discord",
        "category": "Comunicação",
        "desc": "Chat de voz, vídeo e texto para comunidades e jogos.",
        "bin": "discord",
        "pkg_pacman": "discord"
    },
    {
        "id": "obs",
        "name": "OBS Studio",
        "category": "Mídia",
        "desc": "Software profissional para gravação de vídeo e transmissão ao vivo.",
        "bin": "obs",
        "pkg_pacman": "obs-studio"
    },
    {
        "id": "vlc",
        "name": "VLC Media Player",
        "category": "Mídia",
        "desc": "Reprodutor multimídia completo compatível com quase todos os codecs.",
        "bin": "vlc",
        "pkg_pacman": "vlc"
    },
    {
        "id": "arduino",
        "name": "Arduino IDE",
        "category": "Maker",
        "desc": "Ambiente de desenvolvimento oficial para placas Arduino e microcontroladores.",
        "bin": "arduino-ide",
        "pkg_pacman": "arduino-ide-bin"
    },
    {
        "id": "fastfetch",
        "name": "Fastfetch",
        "category": "Sistema",
        "desc": "Exibição rápida e moderna de especificações do sistema no terminal.",
        "bin": "fastfetch",
        "pkg_pacman": "fastfetch"
    },
    {
        "id": "code",
        "name": "Visual Studio Code",
        "category": "Desenvolvimento",
        "desc": "Editor de código fonte com suporte a milhares de extensões.",
        "bin": "code",
        "pkg_pacman": "visual-studio-code-bin"
    }
]

class AppInstaller:
    @staticmethod
    def get_apps():
        apps = []
        for a in APP_CATALOG:
            installed = shutil.which(a["bin"]) is not None
            app_copy = dict(a)
            app_copy["installed"] = installed
            apps.append(app_copy)
        return apps

    @staticmethod
    def install_app(app_id):
        app = next((a for a in APP_CATALOG if a["id"] == app_id), None)
        if not app:
            return False, "Aplicativo não encontrado no catálogo."

        pkg = app["pkg_pacman"]

        # Check if paru or yay is available
        aur_helper = shutil.which("paru") or shutil.which("yay")
        if aur_helper:
            # Run in terminal or background
            cmd = [aur_helper, "-S", "--noconfirm", "--needed", pkg]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                if res.returncode == 0:
                    return True, f"{app['name']} instalado com sucesso!"
                else:
                    return False, f"Falha ao instalar: {res.stderr}"
            except Exception as e:
                return False, str(e)

        # Fallback to pkexec pacman
        cmd = ["pkexec", "pacman", "-S", "--noconfirm", "--needed", pkg]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if res.returncode == 0:
                return True, f"{app['name']} instalado com sucesso!"
            else:
                return False, f"Falha ao instalar via pacman: {res.stderr}"
        except Exception as e:
            return False, str(e)

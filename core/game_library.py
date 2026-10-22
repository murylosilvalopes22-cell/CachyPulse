"""
Game Library and Optimizer Launcher for CachyPulse.
Scans Steam library folders, detects installed games, and launches them
with MangoHud, GameMode, Gamescope, and process priority tweaks.
"""

import os
import re
import glob
import subprocess

def parse_vdf_simple(text):
    data = {}
    matches = re.findall(r'"([^"]+)"\s+"([^"]+)"', text)
    for k, v in matches:
        data[k] = v
    return data

class GameLibrary:
    def __init__(self):
        self.games = []

    def scan_steam_games(self):
        games = []
        steam_paths = [
            os.path.expanduser("~/.local/share/Steam"),
            os.path.expanduser("~/.steam/steam"),
            os.path.expanduser("~/.steam/root")
        ]

        library_dirs = set()
        for sp in steam_paths:
            vdf_path = os.path.join(sp, "config/libraryfolders.vdf")
            if not os.path.exists(vdf_path):
                vdf_path = os.path.join(sp, "steamapps/libraryfolders.vdf")
            if os.path.exists(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    # Find all "path" "..."
                    paths = re.findall(r'"path"\s+"([^"]+)"', content)
                    for p in paths:
                        library_dirs.add(p)
                except Exception:
                    pass

        # Also check common default paths and /mnt/jogos
        library_dirs.add(os.path.expanduser("~/.local/share/Steam"))
        if os.path.exists("/mnt/jogos/SteamLibrary"):
            library_dirs.add("/mnt/jogos/SteamLibrary")

        for lib in library_dirs:
            steamapps = os.path.join(lib, "steamapps")
            if not os.path.exists(steamapps):
                continue
            for acf in glob.glob(os.path.join(steamapps, "appmanifest_*.acf")):
                try:
                    with open(acf, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    data = parse_vdf_simple(text)
                    appid = data.get("appid")
                    name = data.get("name")
                    if appid and name and not name.startswith("Proton") and not name.startswith("Steam Linux"):
                        size_bytes = int(data.get("SizeOnDisk", "0"))
                        size_gb = round(size_bytes / (1024 ** 3), 1)
                        games.append({
                            "id": appid,
                            "name": name,
                            "platform": "Steam",
                            "size_gb": size_gb,
                            "install_dir": data.get("installdir", ""),
                            "path": os.path.join(steamapps, "common", data.get("installdir", ""))
                        })
                except Exception:
                    continue

        # Sort alphabetically
        games.sort(key=lambda g: g["name"].lower())
        self.games = games
        return games

    @staticmethod
    def launch_game(appid, mangohud=True, gamemode=False, gamescope=False, gamescope_res="1920x1080", extra_env=None):
        """Launches a Steam game with user-selected performance wraps."""
        cmd = []
        env = os.environ.copy()

        if mangohud:
            env["MANGOHUD"] = "1"
        if extra_env:
            env.update(extra_env)

        if gamescope:
            w, h = gamescope_res.split("x") if "x" in gamescope_res else ("1920", "1080")
            cmd.extend(["gamescope", "-w", w, "-h", h, "-f", "--"])

        if gamemode:
            cmd.append("gamemoderun")

        cmd.extend(["steam", f"steam://rungameid/{appid}"])

        try:
            subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "Jogo iniciado com sucesso!"
        except Exception as e:
            return False, f"Erro ao iniciar jogo: {str(e)}"

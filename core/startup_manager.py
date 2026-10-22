"""
Startup Manager for CachyPulse (Linux).
Lists and manages autostart desktop entries in ~/.config/autostart and /etc/xdg/autostart.
Allows enabling, disabling (Hidden=true), and removing startup apps.
"""

import os
import glob

class StartupEntry:
    def __init__(self, filepath, name, exec_cmd, comment, enabled=True, is_user=True):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.name = name or self.filename.replace(".desktop", "")
        self.exec_cmd = exec_cmd
        self.comment = comment
        self.enabled = enabled
        self.is_user = is_user

class StartupManager:
    @staticmethod
    def list_entries():
        entries = []
        user_dir = os.path.expanduser("~/.config/autostart")
        sys_dir = "/etc/xdg/autostart"

        files = []
        if os.path.exists(user_dir):
            for f in glob.glob(os.path.join(user_dir, "*.desktop*")):
                files.append((f, True))
        if os.path.exists(sys_dir):
            for f in glob.glob(os.path.join(sys_dir, "*.desktop*")):
                files.append((f, False))

        for filepath, is_user in files:
            try:
                name, exec_cmd, comment = "", "", ""
                hidden = False
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("Name=") and not name:
                            name = line.split("=", 1)[1]
                        elif line.startswith("Exec=") and not exec_cmd:
                            exec_cmd = line.split("=", 1)[1]
                        elif line.startswith("Comment=") and not comment:
                            comment = line.split("=", 1)[1]
                        elif line.startswith("Hidden=true") or line.startswith("X-GNOME-Autostart-enabled=false"):
                            hidden = True

                enabled = not hidden and not filepath.endswith(".disabled")
                entries.append(StartupEntry(filepath, name, exec_cmd, comment, enabled, is_user))
            except Exception:
                continue

        # Sort alphabetically
        entries.sort(key=lambda e: e.name.lower())
        return entries

    @staticmethod
    def toggle_entry(entry):
        user_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(user_dir, exist_ok=True)
        user_file = os.path.join(user_dir, entry.filename.replace(".disabled", ""))

        # If system entry, copy to user dir first with Hidden=true to override
        if not entry.is_user:
            try:
                with open(entry.filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "Hidden=" in content:
                    content = content.replace("Hidden=false", "Hidden=true")
                else:
                    content += "\nHidden=true\n"
                with open(user_file, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            except Exception:
                return False

        # User entry
        try:
            if entry.enabled:
                # Disable it
                with open(entry.filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                has_hidden = False
                new_lines = []
                for l in lines:
                    if l.startswith("Hidden="):
                        new_lines.append("Hidden=true\n")
                        has_hidden = True
                    else:
                        new_lines.append(l)
                if not has_hidden:
                    new_lines.append("Hidden=true\n")
                with open(entry.filepath, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
            else:
                # Enable it
                with open(entry.filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                new_lines = [l for l in lines if not l.startswith("Hidden=")]
                with open(entry.filepath, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
            return True
        except Exception:
            return False

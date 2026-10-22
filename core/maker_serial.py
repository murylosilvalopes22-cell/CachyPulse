"""
Maker & Serial Port Inspector for CachyPulse (Linux).
Detects Arduino, ESP32, CH340, CP2102, FTDI serial devices, checks user group
permissions (uucp / dialout), and resolves access permissions.
"""

import os
import glob
import subprocess
import grp

KNOWN_CHIPS = {
    "1a86:7523": "CH340 Serial Converter (Arduino Clone / ESP8266)",
    "10c4:ea60": "CP210x USB to UART Bridge (Silicon Labs / NodeMCU / ESP32)",
    "0403:6001": "FTDI FT232R USB UART",
    "2341:0043": "Arduino Uno R3 (Original)",
    "2341:0042": "Arduino Mega 2560 R3 (Original)",
    "303a:1001": "Espressif USB-JTAG/Serial (ESP32-S3 / C3)",
}

class MakerSerial:
    @staticmethod
    def check_permissions():
        """Checks if current user has permissions to access /dev/ttyUSB* /dev/ttyACM*."""
        user = os.environ.get("USER", "")
        # On Arch/CachyOS, serial group is usually 'uucp', on Debian/Ubuntu 'dialout'
        groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
        has_uucp = "uucp" in groups or "dialout" in groups
        return has_uucp, groups

    @staticmethod
    def fix_permissions():
        """Adds current user to uucp and dialout groups via pkexec."""
        user = os.environ.get("USER", "")
        cmd = f"usermod -a -G uucp,dialout {user}"
        try:
            res = subprocess.run(["pkexec", "sh", "-c", cmd], capture_output=True, text=True)
            return res.returncode == 0
        except Exception:
            return False

    @staticmethod
    def list_ports():
        ports = []
        for dev_path in glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"):
            name = os.path.basename(dev_path)
            sys_path = f"/sys/class/tty/{name}/device"
            chip_desc = "Dispositivo Serial Genérico"
            hw_id = ""

            try:
                # Walk up to find idVendor and idProduct
                p = sys_path
                for _ in range(4):
                    p = os.path.dirname(p)
                    v_file = os.path.join(p, "idVendor")
                    p_file = os.path.join(p, "idProduct")
                    if os.path.exists(v_file) and os.path.exists(p_file):
                        with open(v_file) as vf, open(p_file) as pf:
                            hw_id = f"{vf.read().strip()}:{pf.read().strip()}".lower()
                            chip_desc = KNOWN_CHIPS.get(hw_id, f"USB Serial ({hw_id})")
                        break
            except Exception:
                pass

            ports.append({
                "port": dev_path,
                "name": name,
                "desc": chip_desc,
                "hw_id": hw_id
            })

        return ports

"""
System Info Collector for CachyPulse.
Extracts comprehensive hardware, OS, Kernel, CPU, GPU, RAM, and Disk specifications on Linux/CachyOS.
Works directly with sysfs, procfs, NVML, and DMI without requiring root.
"""

import os
import re
import glob
import psutil
from .nvml_client import NvmlClient

GPU_SPEC_DB = {
    # NVIDIA Turing
    "10DE:1F03": {
        "chip": "TU106", "arch": "Turing", "process": "TSMC 12 nm", "die_mm2": 445,
        "transistors_bi": 10.8, "shaders": 2176, "rops": 48, "tmus": 136, "tensor": 272, "rt_cores": 34,
        "mem_type": "GDDR6", "bus_bit": 192, "bandwidth_gbs": 336.0,
        "base_mhz": 1470, "boost_mhz": 1650, "tdp_w": 184, "release": "07/12/2021"
    },
    "10DE:1F08": {
        "chip": "TU106", "arch": "Turing", "process": "TSMC 12 nm", "die_mm2": 445,
        "transistors_bi": 10.8, "shaders": 1920, "rops": 48, "tmus": 120, "tensor": 240, "rt_cores": 30,
        "mem_type": "GDDR6", "bus_bit": 192, "bandwidth_gbs": 336.0,
        "base_mhz": 1365, "boost_mhz": 1680, "tdp_w": 160, "release": "15/01/2019"
    },
    # NVIDIA Ampere
    "10DE:2204": {"chip": "GA102", "arch": "Ampere", "process": "Samsung 8 nm", "die_mm2": 628, "transistors_bi": 28.3, "shaders": 10496, "rops": 112, "tmus": 328, "mem_type": "GDDR6X", "bus_bit": 384, "bandwidth_gbs": 936.0, "base_mhz": 1395, "boost_mhz": 1695, "tdp_w": 350, "release": "24/09/2020"},
    "10DE:2484": {"chip": "GA104", "arch": "Ampere", "process": "Samsung 8 nm", "die_mm2": 392, "transistors_bi": 17.4, "shaders": 5888, "rops": 96, "tmus": 184, "mem_type": "GDDR6", "bus_bit": 256, "bandwidth_gbs": 448.0, "base_mhz": 1500, "boost_mhz": 1725, "tdp_w": 220, "release": "29/10/2020"},
    "10DE:2503": {"chip": "GA106", "arch": "Ampere", "process": "Samsung 8 nm", "die_mm2": 276, "transistors_bi": 12.0, "shaders": 3584, "rops": 48, "tmus": 112, "mem_type": "GDDR6", "bus_bit": 192, "bandwidth_gbs": 360.0, "base_mhz": 1320, "boost_mhz": 1777, "tdp_w": 170, "release": "25/02/2021"},
    # NVIDIA Ada Lovelace
    "10DE:2684": {"chip": "AD102", "arch": "Ada Lovelace", "process": "TSMC 4N", "die_mm2": 609, "transistors_bi": 76.3, "shaders": 16384, "rops": 176, "tmus": 512, "mem_type": "GDDR6X", "bus_bit": 384, "bandwidth_gbs": 1008.0, "base_mhz": 2235, "boost_mhz": 2520, "tdp_w": 450, "release": "12/10/2022"},
    "10DE:2704": {"chip": "AD103", "arch": "Ada Lovelace", "process": "TSMC 4N", "die_mm2": 379, "transistors_bi": 45.9, "shaders": 9728, "rops": 112, "tmus": 304, "mem_type": "GDDR6X", "bus_bit": 256, "bandwidth_gbs": 716.8, "base_mhz": 2205, "boost_mhz": 2505, "tdp_w": 320, "release": "16/11/2022"},
    "10DE:2782": {"chip": "AD104", "arch": "Ada Lovelace", "process": "TSMC 4N", "die_mm2": 295, "transistors_bi": 35.8, "shaders": 7680, "rops": 80, "tmus": 240, "mem_type": "GDDR6X", "bus_bit": 192, "bandwidth_gbs": 504.2, "base_mhz": 2310, "boost_mhz": 2610, "tdp_w": 285, "release": "05/01/2023"},
    "10DE:2786": {"chip": "AD104", "arch": "Ada Lovelace", "process": "TSMC 4N", "die_mm2": 295, "transistors_bi": 35.8, "shaders": 5888, "rops": 64, "tmus": 184, "mem_type": "GDDR6X", "bus_bit": 192, "bandwidth_gbs": 504.2, "base_mhz": 1920, "boost_mhz": 2475, "tdp_w": 200, "release": "13/04/2023"},
    # NVIDIA Blackwell
    "10DE:2B85": {"chip": "GB202", "arch": "Blackwell", "process": "TSMC 4N", "die_mm2": 750, "transistors_bi": 92.2, "shaders": 21760, "rops": 176, "tmus": 680, "mem_type": "GDDR7", "bus_bit": 512, "bandwidth_gbs": 1792.0, "base_mhz": 2017, "boost_mhz": 2407, "tdp_w": 575, "release": "30/01/2025"},
    "10DE:2C02": {"chip": "GB203", "arch": "Blackwell", "process": "TSMC 4N", "die_mm2": 378, "transistors_bi": 45.6, "shaders": 10752, "rops": 112, "tmus": 336, "mem_type": "GDDR7", "bus_bit": 256, "bandwidth_gbs": 896.0, "base_mhz": 2295, "boost_mhz": 2617, "tdp_w": 360, "release": "30/01/2025"},
    # AMD RDNA 3 / 2
    "1002:744C": {"chip": "Navi 31", "arch": "RDNA 3", "process": "TSMC 5 nm", "die_mm2": 529, "transistors_bi": 57.7, "shaders": 6144, "rops": 192, "tmus": 384, "mem_type": "GDDR6", "bus_bit": 384, "bandwidth_gbs": 960.0, "base_mhz": 1855, "boost_mhz": 2499, "tdp_w": 355, "release": "13/12/2022"},
    "1002:747E": {"chip": "Navi 32", "arch": "RDNA 3", "process": "TSMC 5 nm", "die_mm2": 346, "transistors_bi": 28.1, "shaders": 3840, "rops": 96, "tmus": 240, "mem_type": "GDDR6", "bus_bit": 256, "bandwidth_gbs": 624.0, "base_mhz": 1295, "boost_mhz": 2430, "tdp_w": 263, "release": "06/09/2023"}
}

def _read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""

def get_cpu_info():
    info = {
        "model": "Processador Desconhecido",
        "vendor": "Desconhecido",
        "cores": psutil.cpu_count(logical=False) or 1,
        "threads": psutil.cpu_count(logical=True) or 1,
        "arch": os.uname().machine,
        "l1d": "",
        "l1i": "",
        "l2": "",
        "l3": "",
        "governor": "",
        "cur_mhz": 0,
        "max_mhz": 0,
        "flags": []
    }

    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    info["model"] = line.split(":", 1)[1].strip()
                elif "vendor_id" in line:
                    info["vendor"] = line.split(":", 1)[1].strip()
                elif "flags" in line and not info["flags"]:
                    info["flags"] = line.split(":", 1)[1].strip().split()
    except Exception:
        pass

    gov_files = glob.glob("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if gov_files:
        info["governor"] = _read_file(gov_files[0])

    freq_files = glob.glob("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    if freq_files:
        try:
            info["cur_mhz"] = int(_read_file(freq_files[0])) // 1000
        except Exception:
            pass

    max_files = glob.glob("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq")
    if max_files:
        try:
            info["max_mhz"] = int(_read_file(max_files[0])) // 1000
        except Exception:
            pass

    # Cache sizes
    for c_idx in range(4):
        p = f"/sys/devices/system/cpu/cpu0/cache/index{c_idx}"
        if os.path.exists(p):
            lvl = _read_file(os.path.join(p, "level"))
            ctype = _read_file(os.path.join(p, "type"))
            size = _read_file(os.path.join(p, "size"))
            if lvl == "1" and ctype == "Data":
                info["l1d"] = size
            elif lvl == "1" and ctype == "Instruction":
                info["l1i"] = size
            elif lvl == "2":
                info["l2"] = size
            elif lvl == "3":
                info["l3"] = size

    return info

def get_motherboard_info():
    dmi = "/sys/class/dmi/id"
    return {
        "vendor": _read_file(os.path.join(dmi, "board_vendor")) or "Desconhecido",
        "board_name": _read_file(os.path.join(dmi, "board_name")) or "Placa-mãe Padrão",
        "bios_version": _read_file(os.path.join(dmi, "bios_version")) or "N/D",
        "bios_date": _read_file(os.path.join(dmi, "bios_date")) or "N/D",
        "chassis": _read_file(os.path.join(dmi, "chassis_type")) or "Desktop"
    }

def get_ram_info():
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    swappiness = _read_file("/proc/sys/vm/swappiness") or "60"

    # ZRAM detection
    has_zram = os.path.exists("/sys/block/zram0")
    zram_size_gb = 0.0
    if has_zram:
        try:
            sectors = int(_read_file("/sys/block/zram0/size"))
            zram_size_gb = round(sectors / (1024 ** 3), 1)
        except Exception:
            pass

    return {
        "total_gb": round(vm.total / (1024 ** 3), 1),
        "used_gb": round(vm.used / (1024 ** 3), 1),
        "available_gb": round(vm.available / (1024 ** 3), 1),
        "used_pct": vm.percent,
        "swap_total_gb": round(swap.total / (1024 ** 3), 1),
        "swap_used_gb": round(swap.used / (1024 ** 3), 1),
        "has_zram": has_zram,
        "zram_size_gb": zram_size_gb,
        "swappiness": swappiness
    }

def get_gpu_info():
    client = NvmlClient()
    telemetry = client.get_telemetry()
    pci_id = ""
    subsystem = ""

    # Search sysfs DRM / PCI
    for dev_path in glob.glob("/sys/bus/pci/devices/*"):
        class_file = os.path.join(dev_path, "class")
        if os.path.exists(class_file):
            c = _read_file(class_file)
            if c.startswith("0x0300") or c.startswith("0x0302"): # Display controller
                vendor = _read_file(os.path.join(dev_path, "vendor")).replace("0x", "").upper()
                device = _read_file(os.path.join(dev_path, "device")).replace("0x", "").upper()
                pci_id = f"{vendor}:{device}"
                break

    client.close()

    spec = GPU_SPEC_DB.get(pci_id, {})
    name = (telemetry and telemetry.get("name")) or "GPU Dedicada"

    return {
        "name": name,
        "driver": (telemetry and telemetry.get("driver")) or "Driver Gráfico Linux",
        "pci_id": pci_id,
        "chip": spec.get("chip", "N/D"),
        "arch": spec.get("arch", "Moderna"),
        "process": spec.get("process", "N/D"),
        "die_mm2": spec.get("die_mm2", "N/D"),
        "transistors_bi": spec.get("transistors_bi", "N/D"),
        "shaders": spec.get("shaders", "N/D"),
        "rops": spec.get("rops", "N/D"),
        "tmus": spec.get("tmus", "N/D"),
        "tensor": spec.get("tensor", "N/D"),
        "rt_cores": spec.get("rt_cores", "N/D"),
        "mem_type": spec.get("mem_type", "GDDR6"),
        "bus_bit": spec.get("bus_bit", 192),
        "bandwidth_gbs": spec.get("bandwidth_gbs", 0.0),
        "vram_total_mb": (telemetry and telemetry.get("vram_total_mb")) or 0,
        "tdp_w": spec.get("tdp_w", 184),
        "release": spec.get("release", "N/D")
    }

def get_storage_info():
    disks = []
    # Identify unique physical disks
    for disk_name in os.listdir("/sys/class/block"):
        if disk_name.startswith("loop") or disk_name.startswith("ram") or disk_name.startswith("zram"):
            continue
        # Only base disks (e.g. nvme0n1, nvme1n1, sda), not partitions
        if re.search(r'p\d+$|\d+$', disk_name) and not disk_name.startswith("nvme"):
            continue
        if disk_name.startswith("nvme") and "p" in disk_name:
            continue

        model_path = f"/sys/class/block/{disk_name}/device/model"
        model = _read_file(model_path) or f"Disco {disk_name}"

        size_path = f"/sys/class/block/{disk_name}/size"
        size_gb = 0.0
        if os.path.exists(size_path):
            try:
                sectors = int(_read_file(size_path))
                size_gb = round(sectors * 512 / (1024 ** 3), 1)
            except Exception:
                pass

        # Find mountpoints on this disk
        partitions = []
        for part in psutil.disk_partitions(all=False):
            if disk_name in part.device:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    partitions.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024 ** 3), 1),
                        "used_gb": round(usage.used / (1024 ** 3), 1),
                        "free_gb": round(usage.free / (1024 ** 3), 1),
                        "percent": usage.percent
                    })
                except Exception:
                    pass

        disks.append({
            "name": disk_name,
            "model": model,
            "size_gb": size_gb,
            "is_nvme": disk_name.startswith("nvme"),
            "partitions": partitions
        })

    return disks

def get_os_info():
    os_release = {}
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os_release[k] = v.strip('"')

    uname = os.uname()
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "KDE")
    session = os.environ.get("XDG_SESSION_TYPE", "wayland")

    return {
        "distro": os_release.get("PRETTY_NAME", "CachyOS Linux"),
        "kernel": uname.release,
        "desktop": f"{desktop} ({session})",
        "hostname": uname.nodename
    }

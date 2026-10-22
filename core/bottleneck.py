"""
Bottleneck Analyzer for CachyPulse.
Analyzes real-time CPU, GPU, VRAM, RAM, and Thermal metrics to pinpoint
performance bottlenecks in games and workloads, with actionable tuning advice for Linux.
"""

from enum import Enum

class Limiter(Enum):
    GPU = "gpu"
    CPU = "cpu"
    VRAM = "vram"
    RAM = "ram"
    THERMAL = "thermal"
    CAPPED = "capped"

class BottleneckResult:
    def __init__(self, limiter, title, description, advice, severity="normal"):
        self.limiter = limiter
        self.title = title
        self.description = description
        self.advice = advice
        self.severity = severity # "good", "warning", "critical", "normal"

def analyze_bottleneck(snapshot):
    if not snapshot:
        return BottleneckResult(
            Limiter.CAPPED,
            "Coletando Métricas...",
            "Aguardando leitura estável dos sensores.",
            "Inicie um jogo ou benchmark para ver a análise ao vivo."
        )

    gpu_load = snapshot.get("gpu_load", 0)
    cpu_load = snapshot.get("cpu_load", 0)
    per_core = snapshot.get("per_core", [])
    max_core = max(per_core) if per_core else cpu_load
    busiest_core_idx = per_core.index(max_core) if per_core else 0

    ram_pct = snapshot.get("ram_pct", 0)
    vram_used = snapshot.get("vram_used_mb", 0)
    vram_total = snapshot.get("vram_total_mb", 1)
    vram_pct = (vram_used / vram_total * 100) if vram_total > 0 else 0

    cpu_temp = snapshot.get("cpu_temp", 0)
    gpu_temp = snapshot.get("gpu_temp", 0)
    thermal_slowdown = snapshot.get("thermal_slowdown", False)

    # 1. Thermal Throttling
    if thermal_slowdown or cpu_temp >= 90 or gpu_temp >= 86:
        return BottleneckResult(
            Limiter.THERMAL,
            "Superaquecimento Térmico Detectado!",
            f"Temperaturas elevadas (CPU: {cpu_temp:.1f}°C, GPU: {gpu_temp:.1f}°C) estão forçando o hardware a reduzir os clocks.",
            "Verifique as curvas de ventoinha, fluxo de ar do gabinete e pasta térmica. Considere ativar curva agressiva na GPU.",
            severity="critical"
        )

    # 2. VRAM Saturation
    if vram_pct >= 95:
        return BottleneckResult(
            Limiter.VRAM,
            "Memória de Vídeo (VRAM) Esgotada",
            f"O jogo está usando {vram_used} MB de {vram_total} MB ({vram_pct:.1f}%). Isso causa micro-engasgos (stuttering).",
            "Reduza a resolução das texturas no jogo ou ative upscaling DLSS/FSR com preset Balanceado ou Desempenho.",
            severity="warning"
        )

    # 3. GPU Bound (Ideal for heavy games)
    if gpu_load >= 90:
        return BottleneckResult(
            Limiter.GPU,
            "GPU no Limite Máximo (Cenário Ideal)",
            f"A placa de vídeo está a {gpu_load}% de carga. O sistema está extraindo todo o potencial gráfico.",
            "Se desejar mais FPS: ative DLSS/FSR no jogo, reduza sombras e oclusão de ambiente ou pós-processamento pesado.",
            severity="good"
        )

    # 4. CPU / Single-Core Bottleneck
    if (max_core >= 85 or cpu_load >= 80) and gpu_load < 80:
        return BottleneckResult(
            Limiter.CPU,
            f"Gargalo no Processador (Núcleo #{busiest_core_idx} em {max_core:.0f}%)",
            f"Um ou mais núcleos da CPU atingiram o limite enquanto a GPU está com folga ({gpu_load}% de uso).",
            "No Linux/CachyOS: certifique-se de que o governador da CPU está em 'performance', ative o GameMode (gamemoderun) e reduza opções de multidão, física e distância de visão no jogo.",
            severity="warning"
        )

    # 5. System RAM Saturation
    if ram_pct >= 90:
        return BottleneckResult(
            Limiter.RAM,
            "Memória RAM Quase Esgotada",
            f"Uso de RAM em {ram_pct:.1f}%. O sistema está dependendo do ZRAM/SWAP.",
            "Feche navegadores com muitas abas e aplicativos em segundo plano usando a aba Otimizador do CachyPulse.",
            severity="warning"
        )

    # 6. Capped / Idle
    return BottleneckResult(
        Limiter.CAPPED,
        "Sem Gargalo Ativo / Taxa Limitada",
        f"CPU ({cpu_load:.0f}%) e GPU ({gpu_load}%) operando com folga.",
        "Se estiver em um jogo, o FPS pode estar travado pelo V-Sync, taxa do monitor ou limite de quadros interno.",
        severity="normal"
    )

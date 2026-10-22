"""
Diagnostic and Benchmark Report Exporter for CachyPulse.
Generates comprehensive HTML and JSON reports.
"""

import json
import time

def export_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def export_html(data, filepath):
    cpu = data.get("cpu", {})
    gpu = data.get("gpu", {})
    ram = data.get("ram", {})
    os_info = data.get("os", {})
    benchmarks = data.get("benchmarks", {})

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>CachyPulse — Relatório de Diagnóstico de Hardware</title>
    <style>
        body {{
            background-color: #0f111a;
            color: #e2e8f0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 2px solid #238636;
            padding-bottom: 15px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        h1 {{
            color: #00d2ff;
            margin: 0;
            font-size: 28px;
        }}
        .badge {{
            background: #1f6feb;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .card h2 {{
            margin-top: 0;
            color: #58a6ff;
            font-size: 18px;
            border-bottom: 1px solid #21262d;
            padding-bottom: 10px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
        }}
        .metric {{
            background: #0d1117;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #21262d;
        }}
        .metric-title {{
            font-size: 12px;
            color: #8b949e;
            text-transform: uppercase;
        }}
        .metric-val {{
            font-size: 18px;
            font-weight: bold;
            color: #f0f6fc;
            margin-top: 4px;
        }}
        .footer {{
            text-align: center;
            color: #484f58;
            font-size: 12px;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>CachyPulse</h1>
                <div style="color: #8b949e; font-size: 14px; margin-top: 4px;">Relatório de Benchmark & Diagnóstico do Sistema</div>
            </div>
            <div class="badge">{time.strftime("%d/%m/%Y %H:%M:%S")}</div>
        </div>

        <div class="card">
            <h2>Visão Geral do Sistema</h2>
            <div class="grid">
                <div class="metric"><div class="metric-title">Sistema Operacional</div><div class="metric-val">{os_info.get("distro", "Linux")}</div></div>
                <div class="metric"><div class="metric-title">Kernel</div><div class="metric-val">{os_info.get("kernel", "N/D")}</div></div>
                <div class="metric"><div class="metric-title">Ambiente Gráfico</div><div class="metric-val">{os_info.get("desktop", "Wayland")}</div></div>
                <div class="metric"><div class="metric-title">Governador de CPU</div><div class="metric-val">{cpu.get("governor", "performance")}</div></div>
            </div>
        </div>

        <div class="card">
            <h2>Processador (CPU)</h2>
            <div class="grid">
                <div class="metric"><div class="metric-title">Modelo</div><div class="metric-val">{cpu.get("model", "N/D")}</div></div>
                <div class="metric"><div class="metric-title">Cores / Threads</div><div class="metric-val">{cpu.get("cores", 0)}C / {cpu.get("threads", 0)}T</div></div>
                <div class="metric"><div class="metric-title">Cache L3</div><div class="metric-val">{cpu.get("l3", "N/D")}</div></div>
                <div class="metric"><div class="metric-title">Frequência Máxima</div><div class="metric-val">{cpu.get("max_mhz", 0)} MHz</div></div>
            </div>
        </div>

        <div class="card">
            <h2>Placa de Vídeo (GPU)</h2>
            <div class="grid">
                <div class="metric"><div class="metric-title">Modelo</div><div class="metric-val">{gpu.get("name", "N/D")}</div></div>
                <div class="metric"><div class="metric-title">Arquitetura</div><div class="metric-val">{gpu.get("arch", "N/D")} ({gpu.get("chip", "")})</div></div>
                <div class="metric"><div class="metric-title">VRAM Total</div><div class="metric-val">{gpu.get("vram_total_mb", 0)} MB {gpu.get("mem_type", "")}</div></div>
                <div class="metric"><div class="metric-title">Driver Gráfico</div><div class="metric-val">{gpu.get("driver", "N/D")}</div></div>
            </div>
        </div>

        <div class="card">
            <h2>Resultados de Benchmarks</h2>
            <div class="grid">
                <div class="metric"><div class="metric-title">Cinebench CPU (Multi-core)</div><div class="metric-val">{benchmarks.get("cpu_multi", "Não Executado")}</div></div>
                <div class="metric"><div class="metric-title">Cinebench CPU (Single-core)</div><div class="metric-val">{benchmarks.get("cpu_single", "Não Executado")}</div></div>
                <div class="metric"><div class="metric-title">Latência de Memória RAM</div><div class="metric-val">{benchmarks.get("mem_latency", "Não Executado")}</div></div>
                <div class="metric"><div class="metric-title">Banda de Leitura da RAM</div><div class="metric-val">{benchmarks.get("mem_read", "Não Executado")}</div></div>
            </div>
        </div>

        <div class="footer">Gerado automaticamente pelo CachyPulse — Otimizado para Linux & CachyOS.</div>
    </div>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

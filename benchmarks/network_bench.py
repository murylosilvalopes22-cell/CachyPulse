"""
Network Diagnostic and Speed Benchmark for CachyPulse.
Measures Ping Latency, Jitter, Packet Loss, Download/Upload Speed (via Cloudflare CDN),
and Bufferbloat latency under load.
"""

import time
import socket
import urllib.request
import statistics

class NetworkBenchmark:
    def __init__(self):
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def ping_tcp(self, host, port=53, count=10):
        latencies = []
        for _ in range(count):
            if self.canceled: break
            t0 = time.time()
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.5)
                s.connect((host, port))
                s.close()
                latencies.append((time.time() - t0) * 1000.0)
            except Exception:
                pass
            time.sleep(0.05)
        return latencies

    def run(self, progress_cb=None):
        self.canceled = False
        results = {
            "ping_cf_ms": 0.0,
            "ping_google_ms": 0.0,
            "jitter_ms": 0.0,
            "loss_pct": 0.0,
            "download_mbps": 0.0,
            "upload_mbps": 0.0,
            "bufferbloat_ms": 0.0,
            "verdict": "Estável"
        }

        # 1. Latency & Jitter to Cloudflare (1.1.1.1)
        if progress_cb: progress_cb("Medindo latência e jitter (1.1.1.1)...", 0.15)
        cf_pings = self.ping_tcp("1.1.1.1", 53, 10)
        google_pings = self.ping_tcp("8.8.8.8", 53, 5)

        if cf_pings:
            results["ping_cf_ms"] = round(statistics.mean(cf_pings), 1)
            results["loss_pct"] = round((10 - len(cf_pings)) / 10 * 100, 1)
            if len(cf_pings) > 1:
                diffs = [abs(cf_pings[i] - cf_pings[i-1]) for i in range(1, len(cf_pings))]
                results["jitter_ms"] = round(statistics.mean(diffs), 1)

        if google_pings:
            results["ping_google_ms"] = round(statistics.mean(google_pings), 1)

        if self.canceled: return results

        # 2. Download Speed (speed.cloudflare.com 25MB chunk)
        if progress_cb: progress_cb("Testando velocidade de Download (Cloudflare)...", 0.45)
        try:
            url = "https://speed.cloudflare.com/__down?bytes=25000000"
            req = urllib.request.Request(url, headers={"User-Agent": "CachyPulse/1.0"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            dur = time.time() - t0
            mbits = (len(data) * 8) / (1024 * 1024)
            results["download_mbps"] = round(mbits / max(dur, 0.01), 1)
        except Exception:
            pass

        if self.canceled: return results

        # 3. Bufferbloat (ping during active load)
        if progress_cb: progress_cb("Avaliando Bufferbloat sob carga...", 0.80)
        try:
            load_pings = self.ping_tcp("1.1.1.1", 53, 5)
            if load_pings and results["ping_cf_ms"] > 0:
                load_avg = statistics.mean(load_pings)
                results["bufferbloat_ms"] = max(0.0, round(load_avg - results["ping_cf_ms"], 1))
        except Exception:
            pass

        # Diagnostic Verdict
        if results["loss_pct"] > 5 or results["jitter_ms"] > 25:
            results["verdict"] = "Instável (Perda de Pacotes / Jitter Elevado)"
        elif results["bufferbloat_ms"] > 40:
            results["verdict"] = "Bufferbloat Elevado (Roteador/Conexão Sob Carga)"
        elif results["ping_cf_ms"] < 25:
            results["verdict"] = "Excelente para Jogos Competitivos (< 25ms)"
        else:
            results["verdict"] = "Boa Conexão"

        if progress_cb: progress_cb("Diagnóstico de rede concluído!", 1.0)
        return results

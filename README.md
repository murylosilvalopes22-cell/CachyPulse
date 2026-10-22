# CACHYPULSE — Suíte de Benchmarks, Monitoramento e Otimização para Linux & CachyOS

> **Projeto derivado e reimaginado a partir do ResetExplode**, totalmente reconstruído em **C Nativo (OpenMP SIMD)** e **PyQt6 (Hardware Accelerated)** para oferecer máxima performance e integração profunda com o **Linux**, especialmente distribuições voltadas a desempenho como o **CachyOS** e Arch Linux.

---

## ⚡ O que mudou em relação ao ResetExplode original?

O projeto original (**ResetExplode**) foi desenvolvido exclusivamente para Windows em C# / .NET 8 com WPF, Direct3D 11/12 (Vortice), WMI e registros Win32. 

No **CachyPulse**, o código foi completamente reescrito e otimizado para a arquitetura Linux:

1. **Kernel Nativo em C com OpenMP & SIMD**:
   - O renderizador de Ray Tracing (modelo Cinebench) e os testes de largura de banda / latência de memória (estilo AIDA64) foram reescritos em **C99 otimizado com `-O3 -march=native -fopenmp`**, garantindo taxa de amostras determinística e sub-nanossegundos de precisão.
2. **Acesso Direto à Telemetria por NVML**:
   - Integração C-types de nível direto com `libnvidia-ml.so.1` (driver proprietário NVIDIA), fornecendo leitura instantânea em microssegundos de uso de GPU, VRAM, consumo em Watts, clocks reais, ventoinhas e flags de *thermal throttling*.
   - Suporte a sensores do kernel Linux via `sysfs` e `hwmon` (`k10temp` para AMD Ryzen, `nvme` para SSDs NVMe e placa-mãe ASUS).
3. **Benchmark de Disco com Direct I/O (`O_DIRECT`)**:
   - Ao contrário de benchmarks que sofrem interferência do cache de páginas de RAM do Linux, o CachyPulse utiliza buffers alinhados em página com flags `O_DIRECT | O_SYNC`, medindo a verdadeira velocidade do hardware do disco (Sequential 1MB e 4K QD1/QD8 IOPS).
4. **Otimizador Nativo CachyOS & Jogos**:
   - Limpeza de memória cache (`drop_caches`) e compactação ativa de **ZRAM** em 1 clique.
   - Alternância dinâmica de governador de energia da CPU (`performance` / `schedutil` / `powersave`).
   - Detecção do daemon **ananicy-cpp** (auto-nice de processos) e **Feral GameMode**.
   - Integração direta de lançamento de jogos com **MangoHud**, **GameMode** e **Gamescope**.
5. **Maker & Portas Seriais (Arduino / ESP32)**:
   - Diagnóstico automático de placas seriais (`/dev/ttyUSB*`, `/dev/ttyACM*`) e verificação automática de permissões (`uucp` / `dialout`), com botão de 1 clique para conceder acesso ao usuário sem complicação.
6. **Interface Moderna PyQt6**:
   - Totalmente compatível com **Wayland** e **X11**, dimensionamento High-DPI nativo, suporte a tema Escuro/Claro e atalho direto no menu de aplicativos do KDE Plasma e GNOME.

---

## 🚀 Funcionalidades Principais

### 📊 1. Visão Geral (Dashboard)
- Gráfico de área em tempo real com uso de CPU e GPU nos últimos 60 segundos.
- Cartões de telemetria ao vivo com temperaturas, porcentagens e consumo em Watts.
- Medidores de armazenamento por partição montada (`/`, `/home`, `/mnt/jogos`).
- Indicador de saúde geral do computador.

### 💻 2. Sistema & Hardware (Estilo GPU-Z / AIDA64)
- **Placa-mãe & BIOS**: Modelo (ex: ASUS TUF GAMING B550M-E), versão e data da BIOS.
- **CPU**: Arquitetura, cores/threads, governador ativo, caches L1d, L1i, L2 e L3.
- **Placa de Vídeo**: Chip (ex: TU106 Turing), Shaders (2176), ROPs, TMUs, Tensor/RT cores, VRAM (12GB GDDR6 192-bit 336 GB/s), driver e TDP.
- **Exportação de Relatórios**: Exporte diagnósticos completos em **HTML estilizado** ou **JSON** em 1 clique.

### ⏱️ 3. Benchmarks de Alto Desempenho
- **CPU Ray Tracer (Cinebench)**: Path tracer monocromático determinístico (960x540) com visualização ao vivo dos blocos renderizados (tiles) do centro para fora. Suporte a Multi-Core (todas as threads) e Single-Core.
- **Memória RAM (AIDA64)**:
  - Latência com algoritmo de ciclo Sattolo (acesso randômico fora de cache).
  - Largura de banda multithread de **Leitura**, **Escrita** e **Cópia** em GB/s.
- **Armazenamento (CrystalDiskMark)**:
  - Leitura e escrita sequencial (1 MB).
  - Leitura e escrita aleatória 4K (QD1) com medição de latência em microssegundos.
  - Leitura paralela 4K (QD8).
- **Diagnóstico de Rede & Bufferbloat**:
  - Latência TCP direta e Jitter (Cloudflare 1.1.1.1 e Google 8.8.8.8).
  - Velocidade de download real via CDN Cloudflare.
  - Teste de Bufferbloat (aumento de latência sob carga pesada).

### 🔥 4. Testes de Estresse & Estabilidade
- **CPU & RAM**: Carga sintética intensa misturando cálculos FPU (FMA, raiz quadrada, seno) com verificação de integridade de memória. Inclui corte automático de segurança se a CPU atingir o limite térmico configurado.
- **GPU Stress Burner (Estilo FurMark)**: Janela de renderização 3D acelerada por hardware via **OpenGL**, com torus rotativo, múltiplas camadas de relevo e shader aritmético pesado para estressar a placa de vídeo ao limite, exibindo FPS em tempo real e corte térmico de segurança.

### 🎮 5. Jogos & Detector de Gargalo (Bottleneck)
- **Detector de Gargalo**: Diagnóstico em tempo real que analisa VRAM, térmico, núcleos mais ocupados da CPU e carga da GPU para apontar se o gargalo está na placa de vídeo, no processador, na VRAM esgotada ou em trava de FPS/V-Sync.
- **Biblioteca de Jogos**: Detecta automaticamente seus jogos instalados da Steam (incluindo bibliotecas em outros discos como `/mnt/jogos`).
- **Launcher Gamer Otimizado**: Inicie qualquer jogo aplicando em 1 clique MangoHud, GameMode e resolução personalizada via Gamescope.

### 🚀 6. Otimizador CachyOS & Ferramentas
- Limpeza de memória cache (`sync && drop_caches`).
- Compactação imediata de ZRAM.
- Seletor de governadores da CPU (`performance`, `schedutil`, `powersave`).
- Monitor de status do `ananicy-cpp` e `gamemoded`.
- Gerenciador de inicialização (ativar/desativar programas no boot).
- Instalador de pacotes essenciais (Steam, Discord, OBS, Heroic, Lutris, ProtonUp-Qt, MangoHud, Arduino IDE, etc.).
- Inspetor de portas seriais e ajuste de permissões `uucp`.

---

## 🛠️ Como Executar

### 1. Pelo Menu de Aplicativos
Abra o menu de aplicativos do KDE Plasma ou KRunner (Alt+Espaço) e procure por **CachyPulse**.

### 2. Pelo Terminal
Você pode executar diretamente pelo comando:
```bash
cachypulse
```
Ou dentro do diretório do projeto:
```bash
cd /home/murylo/Downloads/bench/CachyPulse
./cachypulse
```

### 3. Recompilar a Biblioteca Nativa (Opcional)
Se desejar recompilar os módulos nativos C:
```bash
cd /home/murylo/Downloads/bench/CachyPulse/native
make clean && make
```

---

## 📜 Licença
Código aberto sob a licença **MIT**.
Baseado nos conceitos arquiteturais do projeto ResetExplode, adaptado e expandido para o ecossistema GNU/Linux e CachyOS.

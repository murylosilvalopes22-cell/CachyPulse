"""
GPU Stress Test / FurMark-Style Burner for CachyPulse (Linux).
Uses hardware-accelerated OpenGL with high-load GLSL fragment shaders,
real-time FPS counter, and safety thermal cutoff.
"""

import time
import math
import ctypes
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QVector2D
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLShader, QOpenGLShaderProgram
from core.nvml_client import NvmlClient

try:
    libgl = ctypes.CDLL('libGL.so.1')
except Exception:
    libgl = None

VERTEX_SHADER_SRC = """#version 330 core
layout (location = 0) in vec2 aPos;
out vec2 vUv;
void main() {
    vUv = aPos * 0.5 + 0.5;
    gl_Position = vec4(aPos, 0.0, 1.0);
}
"""

FRAGMENT_SHADER_SRC = """#version 330 core
in vec2 vUv;
out vec4 FragColor;

uniform float uTime;
uniform vec2 uResolution;
uniform int uIntensity;

// Torus distance field
float sdTorus(vec3 p, vec2 t) {
    vec2 q = vec2(length(p.xz) - t.x, p.y);
    return length(q) - t.y;
}

// Scene raymarching
float map(vec3 p) {
    float c = cos(uTime * 0.9);
    float s = sin(uTime * 0.9);
    mat3 rotX = mat3(1.0, 0.0, 0.0, 0.0, c, -s, 0.0, s, c);
    mat3 rotY = mat3(c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c);
    p = rotX * rotY * p;
    return sdTorus(p, vec2(1.15, 0.45));
}

vec3 calcNormal(vec3 p) {
    float eps = 0.001;
    vec2 h = vec2(eps, 0.0);
    return normalize(vec3(
        map(p + h.xyy) - map(p - h.xyy),
        map(p + h.yxy) - map(p - h.yxy),
        map(p + h.yyx) - map(p - h.yyx)
    ));
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * uResolution) / min(uResolution.x, uResolution.y);
    vec3 ro = vec3(0.0, 0.0, 3.2);
    vec3 rd = normalize(vec3(uv, -1.3));

    float t = 0.0;
    float d = 0.0;
    for (int i = 0; i < 96; i++) {
        vec3 p = ro + rd * t;
        d = map(p);
        if (d < 0.001 || t > 10.0) break;
        t += d;
    }

    vec3 col = vec3(0.02, 0.02, 0.03); // Deep space background
    if (t < 10.0) {
        vec3 p = ro + rd * t;
        vec3 n = calcNormal(p);
        vec3 light = normalize(vec3(1.2, 2.0, 1.5));
        float diff = max(dot(n, light), 0.0);
        float spec = pow(max(dot(reflect(-light, n), -rd), 0.0), 32.0);

        // FurMark styled procedural heating colors (Orange/Yellow flame burn)
        float pulse = sin(uTime * 2.5 + p.y * 3.5) * 0.5 + 0.5;
        vec3 furColor = mix(vec3(1.0, 0.25, 0.02), vec3(1.0, 0.85, 0.15), pulse);
        col = furColor * diff + vec3(1.0) * spec * 0.7;
    }

    // Heavy GPU ALU burn loop
    int iters = uIntensity * 128;
    vec4 burn = vec4(col, 1.0);
    for (int k = 0; k < iters; k++) {
        burn = sin(burn * 1.0001 + float(k) * 0.002) * cos(burn * 0.9998);
    }

    FragColor = vec4(col + burn.xyz * 0.00001, 1.0);
}
"""

class GpuBurnGLWidget(QOpenGLWidget):
    stats_updated = pyqtSignal(float, float) # fps, frametime_ms

    def __init__(self, intensity=2, parent=None):
        super().__init__(parent)
        self.intensity = intensity
        self.program = None
        self.start_time = time.time()
        self.frame_count = 0
        self.last_time = time.time()
        self.running = True

    def initializeGL(self):
        self.program = QOpenGLShaderProgram(self)
        self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX_SHADER_SRC)
        self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT_SHADER_SRC)
        self.program.link()

    def resizeGL(self, w, h):
        if libgl:
            libgl.glViewport(0, 0, w, h)

    def paintGL(self):
        if not self.running or not self.program:
            return

        now = time.time()
        elapsed = now - self.start_time
        self.frame_count += 1

        dt = now - self.last_time
        if dt >= 0.5:
            fps = self.frame_count / dt
            frametime = (dt / self.frame_count) * 1000.0
            self.frame_count = 0
            self.last_time = now
            self.stats_updated.emit(fps, frametime)

        self.program.bind()
        self.program.setUniformValue("uTime", float(elapsed))
        self.program.setUniformValue("uResolution", float(self.width()), float(self.height()))
        self.program.setUniformValue("uIntensity", int(self.intensity))

        # Quad vertices
        coords = [QVector2D(-1.0, -1.0), QVector2D(1.0, -1.0), QVector2D(-1.0, 1.0), QVector2D(1.0, 1.0)]
        self.program.setAttributeArray(0, coords)
        self.program.enableAttributeArray(0)

        # Draw full screen triangle strip
        if libgl:
            libgl.glDrawArrays(0x0005, 0, 4) # GL_TRIANGLE_STRIP = 0x0005

        self.program.disableAttributeArray(0)
        self.program.release()

        # Continuous loop for max GPU stress
        self.update()

class GpuStressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CACHYPULSE — GPU STRESS BURNER (FURMARK)")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #000000; color: #FFFFFF;")

        self.nvml = NvmlClient()
        self.max_temp_limit = 86

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Control Bar
        ctrl_bar = QFrame()
        ctrl_bar.setStyleSheet("background-color: #0A0A0A; border: 1px solid #1C1C1C; border-radius: 12px; padding: 8px 16px;")
        ctrl_l = QHBoxLayout(ctrl_bar)

        lbl_logo = QLabel("GPU BURNER")
        lbl_logo.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: 1px;")
        ctrl_l.addWidget(lbl_logo)

        ctrl_l.addStretch()

        ctrl_l.addWidget(QLabel("Intensidade:"))
        self.combo_intensity = QComboBox()
        self.combo_intensity.addItems(["Normal (1x)", "Alta (2x)", "Extrema (3x)"])
        self.combo_intensity.setCurrentIndex(1)
        self.combo_intensity.currentIndexChanged.connect(self._change_intensity)
        ctrl_l.addWidget(self.combo_intensity)

        ctrl_l.addWidget(QLabel("Limite Térmico:"))
        self.spin_temp = QSpinBox()
        self.spin_temp.setRange(60, 95)
        self.spin_temp.setValue(86)
        self.spin_temp.setSuffix(" °C")
        self.spin_temp.valueChanged.connect(lambda v: setattr(self, "max_temp_limit", v))
        ctrl_l.addWidget(self.spin_temp)

        self.btn_stop = QPushButton("Encerrar")
        self.btn_stop.setStyleSheet("background-color: #FFFFFF; color: #000000; font-weight: bold; padding: 6px 18px; border-radius: 8px;")
        self.btn_stop.clicked.connect(self.close)
        ctrl_l.addWidget(self.btn_stop)

        layout.addWidget(ctrl_bar)

        # 3D Viewport
        self.gl_widget = GpuBurnGLWidget(intensity=2, parent=self)
        self.gl_widget.stats_updated.connect(self._on_stats_updated)
        layout.addWidget(self.gl_widget, stretch=1)

        # HUD Footer Bar
        hud_bar = QFrame()
        hud_bar.setStyleSheet("background-color: #0A0A0A; border: 1px solid #1C1C1C; border-radius: 12px; padding: 12px 20px;")
        hud_l = QHBoxLayout(hud_bar)

        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fps.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 20px; font-weight: 700; color: #FFFFFF;")
        hud_l.addWidget(self.lbl_fps)

        self.lbl_frametime = QLabel("Frametime: -- ms")
        self.lbl_frametime.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 14px; color: #8C8C8C;")
        hud_l.addWidget(self.lbl_frametime)

        hud_l.addStretch()

        self.lbl_temp = QLabel("Temp: -- °C")
        self.lbl_temp.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 16px; font-weight: 700; color: #FFAA00;")
        hud_l.addWidget(self.lbl_temp)

        self.lbl_power = QLabel("Consumo: -- W")
        self.lbl_power.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 16px; font-weight: 700; color: #00D2FF;")
        hud_l.addWidget(self.lbl_power)

        self.lbl_clock = QLabel("Clock: -- MHz")
        self.lbl_clock.setStyleSheet("font-family: 'JetBrains Mono', Consolas, monospace; font-size: 16px; font-weight: 700; color: #E0E0E0;")
        hud_l.addWidget(self.lbl_clock)

        layout.addWidget(hud_bar)

        # Polling hardware telemetry
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_gpu)
        self.timer.start(1000)

    def _change_intensity(self, idx):
        self.gl_widget.intensity = idx + 1

    def _on_stats_updated(self, fps, frametime):
        self.lbl_fps.setText(f"FPS: {fps:.0f}")
        self.lbl_frametime.setText(f"Frametime: {frametime:.1f} ms")

    def _poll_gpu(self):
        telem = self.nvml.get_telemetry()
        if telem:
            temp = telem["temp_c"]
            self.lbl_temp.setText(f"Temp: {temp} °C")
            self.lbl_power.setText(f"Consumo: {telem['power_w']} W")
            self.lbl_clock.setText(f"Clock: {telem['clock_core_mhz']} MHz")

            # Thermal safety trigger
            if temp >= self.max_temp_limit:
                self.gl_widget.running = False
                self.lbl_fps.setText("PARADO: LIMITE TÉRMICO ATINGIDO!")
                self.lbl_fps.setStyleSheet("color: red; font-weight: bold; font-size: 18px;")
                QTimer.singleShot(2500, self.close)

    def closeEvent(self, event):
        self.gl_widget.running = False
        self.timer.stop()
        self.nvml.close()
        super().closeEvent(event)

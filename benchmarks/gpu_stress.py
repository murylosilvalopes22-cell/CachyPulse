"""
GPU Stress Test / FurMark-Style Burner for CachyPulse (Linux).
Uses PyQt6 hardware-accelerated QOpenGLWidget with high-load GLSL fragment shaders,
real-time FPS counter, and safety thermal cutoff.
"""

import time
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QSurfaceFormat, QPainter, QColor, QFont
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLShader, QOpenGLShaderProgram
from core.nvml_client import NvmlClient

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
uniform int uIntensity; // 1 = Normal, 2 = High, 3 = Extreme

// Torus distance field
float sdTorus(vec3 p, vec2 t) {
    vec2 q = vec2(length(p.xz) - t.x, p.y);
    return length(q) - t.y;
}

// Scene raymarching
float map(vec3 p) {
    // Rotation
    float c = cos(uTime * 0.8);
    float s = sin(uTime * 0.8);
    mat3 rotX = mat3(1.0, 0.0, 0.0, 0.0, c, -s, 0.0, s, c);
    mat3 rotY = mat3(c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c);
    p = rotX * rotY * p;
    return sdTorus(p, vec2(1.1, 0.45));
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

    vec3 col = vec3(0.05, 0.06, 0.08); // Background
    if (t < 10.0) {
        vec3 p = ro + rd * t;
        vec3 n = calcNormal(p);
        vec3 light = normalize(vec3(1.0, 2.0, 1.5));
        float diff = max(dot(n, light), 0.0);
        float spec = pow(max(dot(reflect(-light, n), -rd), 0.0), 32.0);

        // FurMark styled procedural heating colors
        float pulse = sin(uTime * 2.0 + p.y * 3.0) * 0.5 + 0.5;
        vec3 furColor = mix(vec3(1.0, 0.3, 0.05), vec3(1.0, 0.8, 0.1), pulse);
        col = furColor * diff + vec3(1.0) * spec * 0.6;
    }

    // Heavy GPU ALU burn loop (scaled by intensity)
    int iters = uIntensity * 128;
    vec4 burn = vec4(col, 1.0);
    for (int k = 0; k < iters; k++) {
        burn = sin(burn * 1.0001 + float(k) * 0.002) * cos(burn * 0.9998);
    }

    FragColor = vec4(col + burn.xyz * 0.00001, 1.0);
}
"""

class GpuBurnGLWidget(QOpenGLWidget):
    stats_updated = pyqtSignal(float, int, float) # fps, frames, elapsed

    def __init__(self, intensity=2, parent=None):
        super().__init__(parent)
        self.intensity = intensity # 1, 2, 3
        self.program = None
        self.start_time = time.time()
        self.frames = 0
        self.last_fps_time = time.time()
        self.fps = 0.0
        self.running = True

    def initializeGL(self):
        self.program = QOpenGLShaderProgram(self)
        self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX_SHADER_SRC)
        self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT_SHADER_SRC)
        self.program.link()

    def resizeGL(self, w, h):
        pass

    def paintGL(self):
        if not self.running or not self.program:
            return

        now = time.time()
        elapsed = now - self.start_time
        self.frames += 1

        # Calculate FPS every 0.5 seconds
        if now - self.last_fps_time >= 0.5:
            self.fps = self.frames / (now - self.last_fps_time)
            self.frames = 0
            self.last_fps_time = now
            self.stats_updated.emit(self.fps, int(self.frames), elapsed)

        self.program.bind()
        self.program.setUniformValue("uTime", float(elapsed))
        self.program.setUniformValue("uResolution", float(self.width()), float(self.height()))
        self.program.setUniformValue("uIntensity", int(self.intensity))

        # Quad vertices: (-1, -1), (1, -1), (-1, 1), (1, 1)
        coords = [-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
        self.program.setAttributeArray(0, coords, 2)
        self.program.enableAttributeArray(0)

        # Draw full screen triangle strip
        from PyQt6.QtGui import QOpenGLFunctions
        gl = self.context().functions()
        gl.glDrawArrays(0x0005, 0, 4) # GL_TRIANGLE_STRIP = 0x0005

        self.program.disableAttributeArray(0)
        self.program.release()

        # Immediate loop for maximum GPU stress
        self.update()

class GpuStressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CachyPulse — GPU Stress Burner (FurMark Style)")
        self.resize(960, 600)
        self.setStyleSheet("background-color: #0f111a; color: white;")

        self.nvml = NvmlClient()
        self.max_temp_limit = 85

        layout = QVBoxLayout(self)

        # Top Control Bar
        ctrl_layout = QHBoxLayout()
        self.lbl_info = QLabel("Stress de GPU: Carga máxima de ALU e Shader")
        self.lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
        ctrl_layout.addWidget(self.lbl_info)

        ctrl_layout.addStretch()

        ctrl_layout.addWidget(QLabel("Intensidade:"))
        self.combo_intensity = QComboBox()
        self.combo_intensity.addItems(["Normal (1x)", "Alta (2x)", "Extrema (3x)"])
        self.combo_intensity.setCurrentIndex(1)
        self.combo_intensity.currentIndexChanged.connect(self._change_intensity)
        ctrl_layout.addWidget(self.combo_intensity)

        ctrl_layout.addWidget(QLabel("Limite Térmico:"))
        self.spin_temp = QSpinBox()
        self.spin_temp.setRange(60, 95)
        self.spin_temp.setValue(85)
        self.spin_temp.setSuffix(" °C")
        self.spin_temp.valueChanged.connect(lambda v: setattr(self, "max_temp_limit", v))
        ctrl_layout.addWidget(self.spin_temp)

        self.btn_stop = QPushButton("Encerrar Teste")
        self.btn_stop.setStyleSheet("background-color: #da3633; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px;")
        self.btn_stop.clicked.connect(self.close)
        ctrl_layout.addWidget(self.btn_stop)

        layout.addLayout(ctrl_layout)

        # OpenGL Stress Viewport
        self.gl_widget = GpuBurnGLWidget(intensity=2, parent=self)
        self.gl_widget.stats_updated.connect(self._on_stats_updated)
        layout.addWidget(self.gl_widget, stretch=1)

        # Bottom HUD
        hud_layout = QHBoxLayout()
        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fps.setStyleSheet("font-size: 16px; font-weight: bold; color: #3fb950;")
        hud_layout.addWidget(self.lbl_fps)

        self.lbl_temp = QLabel("Temp GPU: -- °C")
        self.lbl_temp.setStyleSheet("font-size: 16px; font-weight: bold; color: #f0883e;")
        hud_layout.addWidget(self.lbl_temp)

        self.lbl_power = QLabel("Consumo: -- W")
        self.lbl_power.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        hud_layout.addWidget(self.lbl_power)

        self.lbl_clock = QLabel("Clock: -- MHz")
        self.lbl_clock.setStyleSheet("font-size: 16px; font-weight: bold; color: #d2a8ff;")
        hud_layout.addWidget(self.lbl_clock)

        layout.addLayout(hud_layout)

        # Periodic hardware monitor timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_gpu)
        self.timer.start(1000)

    def _change_intensity(self, idx):
        self.gl_widget.intensity = idx + 1

    def _on_stats_updated(self, fps, frames, elapsed):
        self.lbl_fps.setText(f"FPS: {fps:.0f}")

    def _poll_gpu(self):
        telem = self.nvml.get_telemetry()
        if telem:
            temp = telem["temp_c"]
            self.lbl_temp.setText(f"Temp GPU: {temp} °C")
            self.lbl_power.setText(f"Consumo: {telem['power_w']} W")
            self.lbl_clock.setText(f"Clock: {telem['clock_core_mhz']} MHz")

            # Thermal safety trigger
            if temp >= self.max_temp_limit:
                self.lbl_info.setText("ALERTA: LIMITE TÉRMICO ATINGIDO! INTERROMPENDO...")
                self.lbl_info.setStyleSheet("color: red; font-weight: bold;")
                self.gl_widget.running = False
                QTimer.singleShot(2000, self.close)

    def closeEvent(self, event):
        self.gl_widget.running = False
        self.timer.stop()
        self.nvml.close()
        super().closeEvent(event)

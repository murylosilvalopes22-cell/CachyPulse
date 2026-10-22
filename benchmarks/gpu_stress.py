"""
GPU Stress Test / FurMark-Style Torus with Real 3D Fur Geometry & Instancing for CachyPulse.
Direct port of ResetExplode's GpuBurn:
- Real 3D Torus mesh (160 segs x 64 sides)
- Instanced Shell Rendering (96 to 256 layers)
- High-frequency procedural fur noise discard
- Heavy FMA (Fused Multiply Add) ALU burn chains to hit 99-100% GPU TDP
- Zero V-Sync swap interval for maximum framerate and GPU saturation
"""

import time
import math
import ctypes
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QSurfaceFormat, QMatrix4x4, QVector3D
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLShader, QOpenGLShaderProgram
from core.nvml_client import NvmlClient

# Native OpenGL Bindings
libgl = ctypes.CDLL('libGL.so.1')
libgl.glGenVertexArrays.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]
libgl.glBindVertexArray.argtypes = [ctypes.c_uint]
libgl.glGenBuffers.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]
libgl.glBindBuffer.argtypes = [ctypes.c_uint, ctypes.c_uint]
libgl.glBufferData.argtypes = [ctypes.c_uint, ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint]
libgl.glVertexAttribPointer.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_uint, ctypes.c_ubyte, ctypes.c_int, ctypes.c_void_p]
libgl.glEnableVertexAttribArray.argtypes = [ctypes.c_uint]
libgl.glDrawElementsInstanced.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_int]

VERTEX_SHADER_SRC = """#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUv;

uniform mat4 uWorld;
uniform mat4 uViewProj;
uniform float uShellCount;
uniform float uFurLength;
uniform float uTime;

out vec3 vNormal;
out vec2 vUv;
out float vShell;

void main() {
    float s = float(gl_InstanceID) / uShellCount; // 0 = root, 1 = tip
    vec3 p = aPos + aNormal * (uFurLength * s);
    vec4 w = uWorld * vec4(p, 1.0);
    w.y -= 0.12 * s * s; // gravity sag on fur
    w.xyz += 0.025 * s * sin(uTime * 3.2 + aPos.yzx * 8.0); // wind ripple
    gl_Position = uViewProj * w;
    vNormal = normalize(mat3(uWorld) * aNormal);
    vUv = aUv;
    vShell = s;
}
"""

FRAGMENT_SHADER_SRC = """#version 330 core
in vec3 vNormal;
in vec2 vUv;
in float vShell;

uniform int uIterations;
out vec4 FragColor;

float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

void main() {
    // Dense procedural fur hairs
    float h = hash(floor(vUv * vec2(900.0, 380.0)));

    // Heavy FMA ALU burn loop (stresses tensor and CUDA ALUs to pull max Watts)
    vec4 a = vec4(h, vUv, vShell);
    vec4 b = a.wzyx + 0.5;
    for (int k = 0; k < uIterations; k++) {
        a = a * 1.0001 + (b * 0.0003);
        b = b * 0.9997 + (a * 0.0002);
    }
    float acc = fract(dot(a, b));

    // Discard to create tapered hair follicles
    if (vShell > 0.0 && h + acc * 1e-6 < vShell) discard;

    vec3 L = normalize(vec3(-0.4, 0.8, -0.5));
    float diff = clamp(dot(vNormal, L), 0.0, 1.0) * 0.75 + 0.25;
    float ao = mix(0.18, 1.0, vShell); // dark roots, bright tips
    float c = diff * ao * (0.9 + 0.1 * acc);

    // Warm golden FurMark fur palette
    vec3 fur = vec3(c * 1.15, c * 0.65, c * 0.22);
    FragColor = vec4(fur, mix(1.0, 0.55, vShell));
}
"""

def generate_torus_geometry(seg=160, sides=64, R=1.0, r=0.42):
    u = np.linspace(0, 2*np.pi, seg + 1, dtype=np.float32)
    v = np.linspace(0, 2*np.pi, sides + 1, dtype=np.float32)
    uu, vv = np.meshgrid(u, v, indexing='ij')

    nx = np.cos(uu) * np.cos(vv)
    ny = np.sin(vv)
    nz = np.sin(uu) * np.cos(vv)

    px = np.cos(uu) * R + nx * r
    py = ny * r
    pz = np.sin(uu) * R + nz * r

    u_coord = uu / (2 * np.pi)
    v_coord = vv / (2 * np.pi)

    verts = np.stack([px, py, pz, nx, ny, nz, u_coord, v_coord], axis=-1).reshape(-1, 8).astype(np.float32)

    indices = []
    for i in range(seg):
        for j in range(sides):
            a = i * (sides + 1) + j
            b = (i + 1) * (sides + 1) + j
            indices.extend([a, b, a + 1, a + 1, b, b + 1])
    inds = np.array(indices, dtype=np.uint32)

    return verts, inds

class FurmarkWidget(QOpenGLWidget):
    stats_updated = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.prog = None
        self.vao = 0
        self.num_indices = 0
        self.start_time = time.time()
        self.frame_count = 0
        self.last_time = time.time()
        self.running = True

        # Stress settings
        self.shell_count = 128
        self.iterations = 512
        self.fur_length = 0.16

        # Disable VSync for unconstrained GPU saturation
        fmt = QSurfaceFormat()
        fmt.setSwapInterval(0)
        self.setFormat(fmt)

    def initializeGL(self):
        self.prog = QOpenGLShaderProgram(self)
        self.prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX_SHADER_SRC)
        self.prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT_SHADER_SRC)
        self.prog.link()

        verts, inds = generate_torus_geometry(160, 64, 1.0, 0.42)
        self.num_indices = len(inds)

        vao = (ctypes.c_uint * 1)()
        libgl.glGenVertexArrays(1, vao)
        self.vao = vao[0]
        libgl.glBindVertexArray(self.vao)

        vbo = (ctypes.c_uint * 1)()
        libgl.glGenBuffers(1, vbo)
        libgl.glBindBuffer(0x8892, vbo[0])
        libgl.glBufferData(0x8892, verts.nbytes, verts.ctypes.data, 0x88E4)

        libgl.glVertexAttribPointer(0, 3, 0x1406, 0, 32, None)
        libgl.glEnableVertexAttribArray(0)
        libgl.glVertexAttribPointer(1, 3, 0x1406, 0, 32, ctypes.c_void_p(12))
        libgl.glEnableVertexAttribArray(1)
        libgl.glVertexAttribPointer(2, 2, 0x1406, 0, 32, ctypes.c_void_p(24))
        libgl.glEnableVertexAttribArray(2)

        ebo = (ctypes.c_uint * 1)()
        libgl.glGenBuffers(1, ebo)
        libgl.glBindBuffer(0x8893, ebo[0])
        libgl.glBufferData(0x8893, inds.nbytes, inds.ctypes.data, 0x88E4)

    def resizeGL(self, w, h):
        libgl.glViewport(0, 0, w, h)

    def paintGL(self):
        if not self.running or not self.prog:
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

        libgl.glEnable(0x0B71) # GL_DEPTH_TEST
        libgl.glEnable(0x0BE2) # GL_BLEND
        libgl.glBlendFunc(0x0302, 0x0303)
        libgl.glClear(0x00004000 | 0x00000100)

        self.prog.bind()

        # Dynamic 3D rotation
        world = QMatrix4x4()
        world.rotate(elapsed * 25.0, 1, 0, 0)
        world.rotate(elapsed * 35.0, 0, 1, 0)

        aspect = float(self.width()) / float(max(self.height(), 1))
        viewproj = QMatrix4x4()
        viewproj.perspective(45.0, aspect, 0.1, 100.0)
        viewproj.lookAt(QVector3D(0, 1.2, 3.2), QVector3D(0, 0, 0), QVector3D(0, 1, 0))

        self.prog.setUniformValue("uWorld", world)
        self.prog.setUniformValue("uViewProj", viewproj)
        self.prog.setUniformValue("uShellCount", float(self.shell_count))
        self.prog.setUniformValue("uFurLength", float(self.fur_length))
        self.prog.setUniformValue("uTime", float(elapsed))
        self.prog.setUniformValue("uIterations", int(self.iterations))

        # Massive instanced draw call: renders 2.6+ million fur polygons per frame
        libgl.glBindVertexArray(self.vao)
        libgl.glDrawElementsInstanced(0x0004, self.num_indices, 0x1405, None, int(self.shell_count))
        libgl.glBindVertexArray(0)

        self.prog.release()

        # Continuous refresh for max GPU load
        self.update()

class GpuStressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CACHYPULSE — GPU STRESS BURNER (FURMARK)")
        self.resize(1120, 720)
        self.setMinimumSize(850, 520)
        self.setStyleSheet("background-color: #000000; color: #FFFFFF;")

        self.nvml = NvmlClient()
        self.max_temp_limit = 86

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header Control Bar
        ctrl_bar = QFrame()
        ctrl_bar.setStyleSheet("background-color: #080808; border: 1px solid #1C1C1C; border-radius: 12px; padding: 10px 18px;")
        ctrl_l = QHBoxLayout(ctrl_bar)

        lbl_logo = QLabel("GPU BURNER")
        lbl_logo.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: 1.5px;")
        ctrl_l.addWidget(lbl_logo)

        ctrl_l.addStretch()

        ctrl_l.addWidget(QLabel("Intensidade:"))
        self.combo_intensity = QComboBox()
        self.combo_intensity.addItems(["Normal (96 Camadas)", "Alta (160 Camadas)", "Extrema (256 Camadas)"])
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
        self.btn_stop.setStyleSheet("background-color: #FFFFFF; color: #000000; font-weight: 700; padding: 8px 22px; border-radius: 8px;")
        self.btn_stop.clicked.connect(self.close)
        ctrl_l.addWidget(self.btn_stop)

        layout.addWidget(ctrl_bar)

        # FurMark 3D OpenGL Viewport
        self.gl_widget = FurmarkWidget(parent=self)
        self.gl_widget.stats_updated.connect(self._on_stats_updated)
        layout.addWidget(self.gl_widget, stretch=1)

        # HUD Footer Bar
        hud_bar = QFrame()
        hud_bar.setStyleSheet("background-color: #080808; border: 1px solid #1C1C1C; border-radius: 12px; padding: 14px 22px;")
        hud_l = QHBoxLayout(hud_bar)

        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fps.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 22px; font-weight: 800; color: #FFFFFF;")
        hud_l.addWidget(self.lbl_fps)

        self.lbl_frametime = QLabel("Frametime: -- ms")
        self.lbl_frametime.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 13px; color: #737373;")
        hud_l.addWidget(self.lbl_frametime)

        hud_l.addStretch()

        self.lbl_gpu_load = QLabel("Carga: -- %")
        self.lbl_gpu_load.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 16px; font-weight: 800; color: #3FB950;")
        hud_l.addWidget(self.lbl_gpu_load)

        self.lbl_temp = QLabel("Temp: -- °C")
        self.lbl_temp.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 16px; font-weight: 800; color: #FFAA00;")
        hud_l.addWidget(self.lbl_temp)

        self.lbl_power = QLabel("Consumo: -- W")
        self.lbl_power.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 16px; font-weight: 800; color: #00D2FF;")
        hud_l.addWidget(self.lbl_power)

        self.lbl_clock = QLabel("Clock: -- MHz")
        self.lbl_clock.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 16px; font-weight: 800; color: #E0E0E0;")
        hud_l.addWidget(self.lbl_clock)

        layout.addWidget(hud_bar)

        # Polling hardware telemetry
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_gpu)
        self.timer.start(1000)

        # Initial intensity setting
        self._change_intensity(1)

    def _change_intensity(self, idx):
        if idx == 0: # Normal
            self.gl_widget.shell_count = 96
            self.gl_widget.iterations = 256
        elif idx == 1: # Alta
            self.gl_widget.shell_count = 160
            self.gl_widget.iterations = 512
        else: # Extrema
            self.gl_widget.shell_count = 256
            self.gl_widget.iterations = 1024

    def _on_stats_updated(self, fps, frametime):
        self.lbl_fps.setText(f"FPS: {fps:.0f}")
        self.lbl_frametime.setText(f"Frametime: {frametime:.1f} ms")

    def _poll_gpu(self):
        telem = self.nvml.get_telemetry()
        if telem:
            temp = telem["temp_c"]
            load = telem["gpu_load"]
            self.lbl_gpu_load.setText(f"Carga: {load}%")
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

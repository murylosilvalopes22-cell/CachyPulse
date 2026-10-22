"""
GPU Stress Test / Authentic 3D FurMark Torus with Instanced Shells & Deep Graphics Controls for CachyPulse.
Direct high-performance port and enhancement of ResetExplode's GpuBurn:
- Parametric 3D Torus mesh (160 segs x 64 sides = 10,465 vertices, 61,440 indices)
- Instanced Shell Rendering (64 to 320 concentric layers)
- Solid, non-transparent core body (Shell 0) with rich ambient lighting
- Thick procedural hair follicle cutout with customizable density exponent
- Glossy specular sheen and ambient occlusion along hair strands
- Heavy FMA (Fused Multiply Add) ALU burn chains (up to 2048 iterations) to saturate 100% GPU TDP
- Comprehensive graphics settings: Resolution, Fullscreen, MSAA, V-Sync, Fur Density, Length,
  Color Themes, Physical Gravity, Wind Flutter, and Rotation Speed.
"""

import time
import ctypes
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QSurfaceFormat, QMatrix4x4, QVector3D, QKeySequence, QShortcut
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

libgl.glClearColor.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
libgl.glClear.argtypes = [ctypes.c_uint]
libgl.glViewport.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
libgl.glEnable.argtypes = [ctypes.c_uint]
libgl.glDisable.argtypes = [ctypes.c_uint]
libgl.glCullFace.argtypes = [ctypes.c_uint]
libgl.glFrontFace.argtypes = [ctypes.c_uint]
libgl.glDepthFunc.argtypes = [ctypes.c_uint]
libgl.glDepthMask.argtypes = [ctypes.c_ubyte]
libgl.glBlendFunc.argtypes = [ctypes.c_uint, ctypes.c_uint]

VERTEX_SHADER_SRC = """#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUv;

uniform mat4 uWorld;
uniform mat4 uViewProj;
uniform float uShellCount;
uniform float uFurLength;
uniform float uTime;
uniform int uEnableGravity;
uniform int uEnableWind;

out vec3 vNormal;
out vec2 vUv;
out float vShell;
out vec3 vWorldPos;

void main() {
    float s = float(gl_InstanceID) / max(uShellCount - 1.0, 1.0); // 0 = root, 1 = tip
    vec3 p = aPos + aNormal * (uFurLength * s);
    vec4 w = uWorld * vec4(p, 1.0);

    if (uEnableGravity == 1) {
        w.y -= 0.10 * s * s; // physics droop on outer layers
    }
    if (uEnableWind == 1) {
        w.xyz += 0.022 * s * sin(uTime * 3.0 + aPos.yzx * 7.5); // wind flutter
    }

    gl_Position = uViewProj * w;
    vNormal = normalize(mat3(uWorld) * aNormal);
    vUv = aUv;
    vShell = s;
    vWorldPos = w.xyz;
}
"""

FRAGMENT_SHADER_SRC = """#version 330 core
in vec3 vNormal;
in vec2 vUv;
in float vShell;
in vec3 vWorldPos;

uniform int uIterations;
uniform float uFurDensityExp;
uniform int uColorTheme;
uniform float uTime;

out vec4 FragColor;

float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

void main() {
    // Dense procedural fur noise (900 x 380 grid produces 342,000 distinct hair cells)
    float h = hash(floor(vUv * vec2(900.0, 380.0)));

    // Heavy FMA ALU burn loop (stresses tensor and CUDA ALUs to pull max Watts)
    vec4 a = vec4(h, vUv, vShell);
    vec4 b = a.wzyx + 0.5;
    for (int k = 0; k < uIterations; k++) {
        a = a * 1.0001 + (b * 0.0003);
        b = b * 0.9997 + (a * 0.0002);
    }
    float acc = fract(dot(a, b));

    // Root (vShell == 0.0) is a 100% solid, impenetrable core body!
    // Shells > 0 taper down according to the fur density exponent:
    if (vShell > 0.0) {
        float threshold = pow(vShell, uFurDensityExp);
        if ((h + acc * 1e-6) < threshold) discard;
    }

    // Directional lighting + ambient light
    vec3 L = normalize(vec3(-0.4, 0.8, -0.5));
    float diff = max(dot(vNormal, L), 0.0);

    // Warm ambient ensures dark areas never become black voids
    float ambient = mix(0.42, 0.28, vShell);
    float light = diff * 0.65 + ambient;

    // Ambient occlusion: darkens near the roots, brighter at tips
    float ao = mix(0.48, 1.0, vShell);

    // Specular sheen on fur tips
    vec3 V = normalize(vec3(0.0, 1.2, 3.2) - vWorldPos);
    vec3 H = normalize(L + V);
    float spec = pow(max(dot(vNormal, H), 0.0), 20.0) * 0.35 * vShell;

    float lum = (light * ao + spec) * (0.94 + 0.06 * acc);

    // 5 Distinct Color Themes
    vec3 colRoot;
    vec3 colTip;

    if (uColorTheme == 0) {
        // FurMark Classic Golden Orange
        colRoot = vec3(0.55, 0.24, 0.05);
        colTip  = vec3(1.28, 0.76, 0.22);
    } else if (uColorTheme == 1) {
        // Fiery Lava / Magma
        colRoot = vec3(0.75, 0.08, 0.02);
        colTip  = vec3(1.30, 0.88, 0.12);
    } else if (uColorTheme == 2) {
        // CachyOS Emerald Neon
        colRoot = vec3(0.04, 0.32, 0.14);
        colTip  = vec3(0.22, 1.25, 0.68);
    } else if (uColorTheme == 3) {
        // Cyberpunk Violet / Cyan
        colRoot = vec3(0.48, 0.04, 0.60);
        colTip  = vec3(0.12, 0.98, 1.25);
    } else {
        // ResetExplode Monochrome Platinum
        colRoot = vec3(0.28, 0.28, 0.32);
        colTip  = vec3(1.05, 1.05, 1.12);
    }

    vec3 baseCol = mix(colRoot, colTip, vShell);
    vec3 fur = baseCol * lum;

    // Solid alpha: Hairs are physically solid strands, not transparent smoke!
    float alpha = (vShell == 0.0) ? 1.0 : mix(1.0, 0.92, vShell);

    FragColor = vec4(fur, alpha);
}
"""

def generate_torus_geometry(seg=160, sides=64, R=1.0, r=0.42):
    """Generates outward-facing CCW parametric Torus vertices and indices."""
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
            # CCW winding outward-facing
            indices.extend([a, a + 1, b, b, a + 1, b + 1])
    inds = np.array(indices, dtype=np.uint32)

    return verts, inds

class FurmarkWidget(QOpenGLWidget):
    stats_updated = pyqtSignal(float, float)

    def __init__(self, msaa=4, vsync=False, parent=None):
        super().__init__(parent)
        self.prog = None
        self.vao = 0
        self.num_indices = 0
        self.start_time = time.time()
        self.frame_count = 0
        self.last_time = time.time()
        self.running = True

        # Stress settings
        self.shell_count = 160
        self.iterations = 512
        self.fur_length = 0.16
        self.fur_density_exp = 1.6 # Solid core + thick fur carpet
        self.color_theme = 0       # 0 = Classic Gold, 1 = Lava, 2 = CachyOS, 3 = Cyberpunk, 4 = Platinum
        self.gravity = True
        self.wind = True
        self.rot_speed = 1.0

        # OpenGL Surface Format
        fmt = QSurfaceFormat()
        fmt.setSamples(msaa)
        fmt.setSwapInterval(1 if vsync else 0)
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

        libgl.glBindVertexArray(0)

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

        # Clear background to deep dark slate
        libgl.glClearColor(ctypes.c_float(0.015), ctypes.c_float(0.015), ctypes.c_float(0.02), ctypes.c_float(1.0))
        libgl.glClear(0x00004000 | 0x00000100) # GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT

        # Depth buffer: enabled and writing
        libgl.glEnable(0x0B71) # GL_DEPTH_TEST
        libgl.glDepthFunc(0x0203) # GL_LEQUAL
        libgl.glDepthMask(1) # GL_TRUE

        # Backface culling: crucial to prevent see-through internal geometry!
        libgl.glEnable(0x0B44) # GL_CULL_FACE
        libgl.glCullFace(0x0405) # GL_BACK
        libgl.glFrontFace(0x0901) # GL_CCW

        # Blending for semi-transparent fur tips
        libgl.glEnable(0x0BE2) # GL_BLEND
        libgl.glBlendFunc(0x0302, 0x0303) # GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA

        self.prog.bind()

        # Dynamic 3D rotation
        world = QMatrix4x4()
        rot_time = elapsed * self.rot_speed
        world.rotate(rot_time * 25.0, 1, 0, 0)
        world.rotate(rot_time * 35.0, 0, 1, 0)

        aspect = float(self.width()) / float(max(self.height(), 1))
        viewproj = QMatrix4x4()
        viewproj.perspective(45.0, aspect, 0.1, 100.0)
        viewproj.lookAt(QVector3D(0, 1.2, 3.2), QVector3D(0, 0, 0), QVector3D(0, 1, 0))

        self.prog.setUniformValue("uWorld", world)
        self.prog.setUniformValue("uViewProj", viewproj)
        self.prog.setUniformValue("uShellCount", float(self.shell_count))
        self.prog.setUniformValue("uFurLength", float(self.fur_length))
        self.prog.setUniformValue("uTime", float(elapsed))
        self.prog.setUniformValue("uEnableGravity", 1 if self.gravity else 0)
        self.prog.setUniformValue("uEnableWind", 1 if self.wind else 0)
        self.prog.setUniformValue("uIterations", int(self.iterations))
        self.prog.setUniformValue("uFurDensityExp", float(self.fur_density_exp))
        self.prog.setUniformValue("uColorTheme", int(self.color_theme))

        # Massive instanced draw call: renders millions of fur polygons
        libgl.glBindVertexArray(self.vao)
        libgl.glDrawElementsInstanced(0x0004, self.num_indices, 0x1405, None, int(self.shell_count))
        libgl.glBindVertexArray(0)

        self.prog.release()

        # Trigger immediate next frame for continuous burn
        self.update()

class GpuStressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CACHYPULSE — GPU STRESS BURNER (FURMARK)")
        self.resize(1200, 780)
        self.setMinimumSize(920, 600)
        self.setStyleSheet("background-color: #000000; color: #FFFFFF;")

        self.nvml = NvmlClient()
        self.max_temp_limit = 86
        self.current_msaa = 4
        self.current_vsync = False

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(10)

        # ---------------- 1. Primary Control Bar ----------------
        ctrl_bar = QFrame()
        ctrl_bar.setStyleSheet("background-color: #080808; border: 1px solid #1C1C1C; border-radius: 12px; padding: 8px 16px;")
        ctrl_l = QHBoxLayout(ctrl_bar)
        ctrl_l.setSpacing(12)

        lbl_logo = QLabel("GPU BURNER")
        lbl_logo.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: 1.5px;")
        ctrl_l.addWidget(lbl_logo)

        ctrl_l.addStretch()

        ctrl_l.addWidget(QLabel("Preset:"))
        self.combo_preset = QComboBox()
        self.combo_preset.addItems([
            "Normal (96 Camadas · 256 FMAs)",
            "Alta (160 Camadas · 512 FMAs)",
            "Extrema (256 Camadas · 1024 FMAs)",
            "Ultra Burn (320 Camadas · 2048 FMAs)"
        ])
        self.combo_preset.setCurrentIndex(1)
        self.combo_preset.currentIndexChanged.connect(self._change_preset)
        ctrl_l.addWidget(self.combo_preset)

        ctrl_l.addWidget(QLabel("Resolução:"))
        self.combo_res = QComboBox()
        self.combo_res.addItems(["1280x720 (HD)", "1600x900", "1920x1080 (FHD)", "2560x1440 (2K)"])
        self.combo_res.setCurrentIndex(0)
        self.combo_res.currentIndexChanged.connect(self._change_resolution)
        ctrl_l.addWidget(self.combo_res)

        self.btn_fullscreen = QPushButton("Tela Cheia (F11)")
        self.btn_fullscreen.setStyleSheet("background: #141414; border: 1px solid #282828; color: #FFFFFF; font-weight: 600; padding: 6px 14px; border-radius: 6px;")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        ctrl_l.addWidget(self.btn_fullscreen)

        ctrl_l.addWidget(QLabel("Anti-Aliasing:"))
        self.combo_msaa = QComboBox()
        self.combo_msaa.addItems(["Sem MSAA (1x)", "2x MSAA", "4x MSAA", "8x MSAA"])
        self.combo_msaa.setCurrentIndex(2) # Default 4x
        self.combo_msaa.currentIndexChanged.connect(self._change_msaa)
        ctrl_l.addWidget(self.combo_msaa)

        ctrl_l.addWidget(QLabel("Limite Térmico:"))
        self.spin_temp = QSpinBox()
        self.spin_temp.setRange(60, 95)
        self.spin_temp.setValue(86)
        self.spin_temp.setSuffix(" °C")
        self.spin_temp.valueChanged.connect(lambda v: setattr(self, "max_temp_limit", v))
        ctrl_l.addWidget(self.spin_temp)

        self.btn_stop = QPushButton("Encerrar")
        self.btn_stop.setStyleSheet("background-color: #FFFFFF; color: #000000; font-weight: 700; padding: 7px 20px; border-radius: 8px;")
        self.btn_stop.clicked.connect(self.close)
        ctrl_l.addWidget(self.btn_stop)

        self.layout.addWidget(ctrl_bar)

        # ---------------- 2. Advanced Graphics Tweaks Bar ----------------
        tweaks_bar = QFrame()
        tweaks_bar.setStyleSheet("background-color: #060606; border: 1px solid #161616; border-radius: 10px; padding: 6px 16px;")
        tb_l = QHBoxLayout(tweaks_bar)
        tb_l.setSpacing(14)

        tb_l.addWidget(QLabel("Tema Visual:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems([
            "Dourado Clássico (FurMark)",
            "Chamas & Magma (Fogo)",
            "CachyOS Verde Neon",
            "Cyberpunk Violeta",
            "Platina Monocromático"
        ])
        self.combo_theme.currentIndexChanged.connect(self._change_theme)
        tb_l.addWidget(self.combo_theme)

        tb_l.addWidget(QLabel("Densidade da Pelagem:"))
        self.combo_density = QComboBox()
        self.combo_density.addItems(["Normal (Clássica)", "Densa (Peluda)", "Super Densa (Espessa)", "Sólida / Tapete de Lã"])
        self.combo_density.setCurrentIndex(1) # Densa
        self.combo_density.currentIndexChanged.connect(self._change_density)
        tb_l.addWidget(self.combo_density)

        tb_l.addWidget(QLabel("Comprimento:"))
        self.combo_length = QComboBox()
        self.combo_length.addItems(["Curto (0.10)", "Médio (0.16)", "Longo (0.26)", "Extremo (0.36)"])
        self.combo_length.setCurrentIndex(1)
        self.combo_length.currentIndexChanged.connect(self._change_length)
        tb_l.addWidget(self.combo_length)

        tb_l.addWidget(QLabel("Rotação:"))
        self.combo_rot = QComboBox()
        self.combo_rot.addItems(["Normal (1x)", "Rápida (2x)", "Lenta (0.5x)", "Pausada"])
        self.combo_rot.currentIndexChanged.connect(self._change_rotation)
        tb_l.addWidget(self.combo_rot)

        self.chk_gravity = QCheckBox("Gravidade")
        self.chk_gravity.setChecked(True)
        self.chk_gravity.toggled.connect(self._toggle_gravity)
        tb_l.addWidget(self.chk_gravity)

        self.chk_wind = QCheckBox("Vento")
        self.chk_wind.setChecked(True)
        self.chk_wind.toggled.connect(self._toggle_wind)
        tb_l.addWidget(self.chk_wind)

        self.chk_vsync = QCheckBox("Trava 60 FPS")
        self.chk_vsync.setChecked(False)
        self.chk_vsync.toggled.connect(self._toggle_vsync)
        tb_l.addWidget(self.chk_vsync)

        tb_l.addStretch()
        self.layout.addWidget(tweaks_bar)

        # ---------------- 3. OpenGL 3D Viewport ----------------
        self.gl_widget = FurmarkWidget(msaa=self.current_msaa, vsync=self.current_vsync, parent=self)
        self.gl_widget.stats_updated.connect(self._on_stats_updated)
        self.layout.addWidget(self.gl_widget, stretch=1)

        # ---------------- 4. Real-time Telemetry HUD Footer ----------------
        hud_bar = QFrame()
        hud_bar.setStyleSheet("background-color: #080808; border: 1px solid #1C1C1C; border-radius: 12px; padding: 12px 22px;")
        hud_l = QHBoxLayout(hud_bar)

        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fps.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 24px; font-weight: 800; color: #FFFFFF;")
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

        self.lbl_vram = QLabel("VRAM: -- GB")
        self.lbl_vram.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: #A855F7;")
        hud_l.addWidget(self.lbl_vram)

        self.lbl_fan = QLabel("Fan: --%")
        self.lbl_fan.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: #737373;")
        hud_l.addWidget(self.lbl_fan)

        self.layout.addWidget(hud_bar)

        # Polling hardware telemetry
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_gpu)
        self.timer.start(1000)

        # Initial Preset config
        self._change_preset(1)

        # Fullscreen Shortcut (F11)
        self.shortcut_f11 = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        self.shortcut_f11.activated.connect(self._toggle_fullscreen)

    # ------------------ EVENT HANDLERS & GRAPHICS SWITCHING ------------------
    def _change_preset(self, idx):
        if idx == 0: # Normal
            self.gl_widget.shell_count = 96
            self.gl_widget.iterations = 256
        elif idx == 1: # Alta
            self.gl_widget.shell_count = 160
            self.gl_widget.iterations = 512
        elif idx == 2: # Extrema
            self.gl_widget.shell_count = 256
            self.gl_widget.iterations = 1024
        else: # Ultra Burn
            self.gl_widget.shell_count = 320
            self.gl_widget.iterations = 2048

    def _change_resolution(self, idx):
        if self.isFullScreen():
            self.showNormal()
        res_map = [(1280, 720), (1600, 900), (1920, 1080), (2560, 1440)]
        if 0 <= idx < len(res_map):
            w, h = res_map[idx]
            self.resize(w, h)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.btn_fullscreen.setText("Tela Cheia (F11)")
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("Janela Normal (ESC)")

    def _change_msaa(self, idx):
        msaa_levels = [1, 2, 4, 8]
        new_msaa = msaa_levels[idx]
        if new_msaa == self.current_msaa:
            return

        self.current_msaa = new_msaa
        # Recreate viewport with new multisample quality
        old_widget = self.gl_widget
        old_widget.running = False

        self.gl_widget = FurmarkWidget(msaa=self.current_msaa, vsync=self.current_vsync, parent=self)
        self.gl_widget.shell_count = old_widget.shell_count
        self.gl_widget.iterations = old_widget.iterations
        self.gl_widget.fur_length = old_widget.fur_length
        self.gl_widget.fur_density_exp = old_widget.fur_density_exp
        self.gl_widget.color_theme = old_widget.color_theme
        self.gl_widget.gravity = old_widget.gravity
        self.gl_widget.wind = old_widget.wind
        self.gl_widget.rot_speed = old_widget.rot_speed
        self.gl_widget.stats_updated.connect(self._on_stats_updated)

        self.layout.replaceWidget(old_widget, self.gl_widget)
        old_widget.deleteLater()

    def _change_theme(self, idx):
        self.gl_widget.color_theme = idx

    def _change_density(self, idx):
        # Higher exponent keeps more fur fibers intact near the body
        exp_map = [1.2, 1.5, 1.8, 2.2]
        self.gl_widget.fur_density_exp = exp_map[idx]

    def _change_length(self, idx):
        len_map = [0.10, 0.16, 0.26, 0.36]
        self.gl_widget.fur_length = len_map[idx]

    def _change_rotation(self, idx):
        speed_map = [1.0, 2.0, 0.5, 0.0]
        self.gl_widget.rot_speed = speed_map[idx]

    def _toggle_gravity(self, checked):
        self.gl_widget.gravity = checked

    def _toggle_wind(self, checked):
        self.gl_widget.wind = checked

    def _toggle_vsync(self, checked):
        self.current_vsync = checked
        fmt = self.gl_widget.format()
        fmt.setSwapInterval(1 if checked else 0)
        self.gl_widget.setFormat(fmt)

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

            vram_gb = telem["vram_used_mb"] / 1024.0
            total_gb = telem["vram_total_mb"] / 1024.0
            self.lbl_vram.setText(f"VRAM: {vram_gb:.1f} / {total_gb:.1f} GB")
            self.lbl_fan.setText(f"Fan: {telem['fan_pct']}%")

            # Thermal safety trigger
            if temp >= self.max_temp_limit:
                self.gl_widget.running = False
                self.lbl_fps.setText("PARADO: LIMITE TÉRMICO ATINGIDO!")
                self.lbl_fps.setStyleSheet("color: red; font-weight: bold; font-size: 18px;")
                QTimer.singleShot(2500, self.close)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self._toggle_fullscreen()
            else:
                self.close()
        elif event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.gl_widget.running = False
        self.timer.stop()
        self.nvml.close()
        super().closeEvent(event)

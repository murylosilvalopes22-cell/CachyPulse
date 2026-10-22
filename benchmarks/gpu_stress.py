"""
GPU Stress Test / Authentic 3D FurMark Torus with Instanced Shells & Deep Graphics Controls for CachyPulse.
Direct high-performance port and enhancement of ResetExplode's GpuBurn:
- Parametric 3D Torus mesh with multi-LOD support (80x32, 120x48, 160x64)
- Instanced Shell Rendering (24 to 192 layers)
- Solid, non-transparent core body (Shell 0) with rich ambient lighting
- Thick procedural hair follicle cutout with customizable density exponent
- Glossy specular sheen and ambient occlusion along hair strands
- Calibrated FMA ALU burn chains to hit high framerates (60 to 300+ FPS) or 100% GPU TDP
- Granular graphics controls: Resolution, Fullscreen, MSAA, V-Sync, Fur Density, Length,
  LOD Geometry, Color Themes, Gravity Droop, Wind Ripple, and 3D Rotation Speed.
"""

import time
import ctypes
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QFrame, QGridLayout, QWidget
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
uniform int uEnableSpecular;
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

    // Calibrated FMA ALU burn loop (stresses tensor and CUDA ALUs safely without collapsing FPS)
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
    float spec = 0.0;
    if (uEnableSpecular == 1) {
        vec3 V = normalize(vec3(0.0, 1.2, 3.2) - vWorldPos);
        vec3 H = normalize(L + V);
        spec = pow(max(dot(vNormal, H), 0.0), 20.0) * 0.35 * vShell;
    }

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
            indices.extend([a, a + 1, b, b, a + 1, b + 1])
    inds = np.array(indices, dtype=np.uint32)

    return verts, inds

class FurmarkWidget(QOpenGLWidget):
    stats_updated = pyqtSignal(float, float)

    def __init__(self, msaa=1, vsync=False, parent=None):
        super().__init__(parent)
        self.prog = None
        self.vao = 0
        self.vbo = 0
        self.ebo = 0
        self.num_indices = 0
        self.start_time = time.time()
        self.frame_count = 0
        self.last_time = time.time()
        self.running = True

        # Geometry LOD
        self.mesh_seg = 120
        self.mesh_sides = 48

        # Stress settings (calibrated for real GPU scalability)
        self.shell_count = 64
        self.iterations = 24
        self.fur_length = 0.16
        self.fur_density_exp = 1.5
        self.color_theme = 0
        self.specular = True
        self.gravity = True
        self.wind = True
        self.rot_speed = 1.0

        # Target frame limiter (0 = uncapped)
        self.target_fps = 0
        self.last_frame_stamp = time.time()

        # OpenGL Surface Format
        fmt = QSurfaceFormat()
        fmt.setSamples(msaa)
        fmt.setSwapInterval(1 if vsync else 0)
        self.setFormat(fmt)

    def set_geometry_lod(self, seg, sides):
        self.mesh_seg = seg
        self.mesh_sides = sides
        if self.isValid():
            self.makeCurrent()
            self._rebuild_buffers()
            self.doneCurrent()

    def _rebuild_buffers(self):
        verts, inds = generate_torus_geometry(self.mesh_seg, self.mesh_sides, 1.0, 0.42)
        self.num_indices = len(inds)

        if not self.vao:
            vao = (ctypes.c_uint * 1)()
            libgl.glGenVertexArrays(1, vao)
            self.vao = vao[0]

        libgl.glBindVertexArray(self.vao)

        if not self.vbo:
            vbo = (ctypes.c_uint * 1)()
            libgl.glGenBuffers(1, vbo)
            self.vbo = vbo[0]
        libgl.glBindBuffer(0x8892, self.vbo)
        libgl.glBufferData(0x8892, verts.nbytes, verts.ctypes.data, 0x88E4)

        libgl.glVertexAttribPointer(0, 3, 0x1406, 0, 32, None)
        libgl.glEnableVertexAttribArray(0)
        libgl.glVertexAttribPointer(1, 3, 0x1406, 0, 32, ctypes.c_void_p(12))
        libgl.glEnableVertexAttribArray(1)
        libgl.glVertexAttribPointer(2, 2, 0x1406, 0, 32, ctypes.c_void_p(24))
        libgl.glEnableVertexAttribArray(2)

        if not self.ebo:
            ebo = (ctypes.c_uint * 1)()
            libgl.glGenBuffers(1, ebo)
            self.ebo = ebo[0]
        libgl.glBindBuffer(0x8893, self.ebo)
        libgl.glBufferData(0x8893, inds.nbytes, inds.ctypes.data, 0x88E4)

        libgl.glBindVertexArray(0)

    def initializeGL(self):
        self.prog = QOpenGLShaderProgram(self)
        self.prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VERTEX_SHADER_SRC)
        self.prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FRAGMENT_SHADER_SRC)
        self.prog.link()

        self._rebuild_buffers()

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
        self.prog.setUniformValue("uEnableSpecular", 1 if self.specular else 0)

        # Massive instanced draw call: renders millions of fur polygons
        libgl.glBindVertexArray(self.vao)
        libgl.glDrawElementsInstanced(0x0004, self.num_indices, 0x1405, None, int(self.shell_count))
        libgl.glBindVertexArray(0)

        self.prog.release()

        # Framerate limiter if active (e.g. 60 FPS, 144 FPS)
        if self.target_fps > 0:
            target_dt = 1.0 / self.target_fps
            spent = time.time() - now
            rem = target_dt - spent
            if rem > 0.001:
                time.sleep(rem)

        # Trigger immediate next frame for continuous burn
        self.update()

class GpuStressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CACHYPULSE — GPU STRESS BURNER (FURMARK 3D)")
        self.resize(1240, 800)
        self.setMinimumSize(940, 620)
        self.setStyleSheet("background-color: #000000; color: #FFFFFF;")

        self.nvml = NvmlClient()
        self.max_temp_limit = 86
        self.current_msaa = 1  # 1x default ensures smooth 100+ FPS on any setting
        self.current_vsync = False
        self.adv_expanded = True

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(10)

        # ---------------- 1. Primary Control Bar ----------------
        ctrl_bar = QFrame()
        ctrl_bar.setStyleSheet("background-color: #080808; border: 1px solid #1C1C1C; border-radius: 12px; padding: 8px 16px;")
        ctrl_l = QHBoxLayout(ctrl_bar)
        ctrl_l.setSpacing(10)

        lbl_logo = QLabel("GPU BURNER")
        lbl_logo.setStyleSheet("font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', monospace; font-size: 15px; font-weight: 800; color: #FFFFFF; letter-spacing: 1.5px;")
        ctrl_l.addWidget(lbl_logo)

        ctrl_l.addStretch()

        ctrl_l.addWidget(QLabel("Preset:"))
        self.combo_preset = QComboBox()
        self.combo_preset.addItems([
            "Ultra Leve (144+ FPS · 32 Camadas)",
            "Leve (60-120 FPS · 48 Camadas)",
            "Equilibrado (64 Camadas · Padrão)",
            "Padrão FurMark (96 Camadas)",
            "Pesado (128 Camadas · Burn Alto)",
            "Extremo (160 Camadas · 100% TDP)",
            "Ultra Burn (192 Camadas · Carga Máxima)",
            "Personalizado (Ajuste Manual)"
        ])
        self.combo_preset.setCurrentIndex(2) # Default Equilibrado (~140 FPS)
        self.combo_preset.currentIndexChanged.connect(self._change_preset)
        ctrl_l.addWidget(self.combo_preset)

        ctrl_l.addWidget(QLabel("Resolução:"))
        self.combo_res = QComboBox()
        self.combo_res.addItems([
            "960x540 (qHD Econômico)",
            "1280x720 (720p HD)",
            "1600x900",
            "1920x1080 (1080p FHD)",
            "2560x1440 (2K QHD)"
        ])
        self.combo_res.setCurrentIndex(1)
        self.combo_res.currentIndexChanged.connect(self._change_resolution)
        ctrl_l.addWidget(self.combo_res)

        self.btn_fullscreen = QPushButton("Tela Cheia (F11)")
        self.btn_fullscreen.setStyleSheet("background: #141414; border: 1px solid #282828; color: #FFFFFF; font-weight: 600; padding: 6px 14px; border-radius: 6px;")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        ctrl_l.addWidget(self.btn_fullscreen)

        self.btn_toggle_adv = QPushButton("Ajustes Avançados")
        self.btn_toggle_adv.setStyleSheet("background: #101010; border: 1px solid #262626; color: #00D2FF; font-weight: 600; padding: 6px 14px; border-radius: 6px;")
        self.btn_toggle_adv.clicked.connect(self._toggle_adv_panel)
        ctrl_l.addWidget(self.btn_toggle_adv)

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

        # ---------------- 2. Advanced Graphics Tweaks Grid (Granular Controls) ----------------
        self.adv_card = QFrame()
        self.adv_card.setStyleSheet("background-color: #060606; border: 1px solid #161616; border-radius: 12px; padding: 12px 18px;")
        adv_grid = QGridLayout(self.adv_card)
        adv_grid.setHorizontalSpacing(16)
        adv_grid.setVerticalSpacing(8)

        # Section 1: Performance & Geometry
        adv_grid.addWidget(QLabel("Camadas (Shells):"), 0, 0)
        self.combo_shells = QComboBox()
        self.combo_shells.addItems(["24 Camadas", "32 Camadas", "48 Camadas", "64 Camadas", "96 Camadas", "128 Camadas", "160 Camadas", "192 Camadas"])
        self.combo_shells.setCurrentIndex(3) # 64
        self.combo_shells.currentIndexChanged.connect(self._on_manual_shell_change)
        adv_grid.addWidget(self.combo_shells, 0, 1)

        adv_grid.addWidget(QLabel("Carga ALU (FMAs):"), 0, 2)
        self.combo_fma = QComboBox()
        self.combo_fma.addItems(["0 (Geometria Pura · Ultra Rápido)", "8 FMAs (Mínimo)", "16 FMAs (Leve)", "24 FMAs (Equilibrado)", "32 FMAs (Padrão)", "48 FMAs (Alto)", "64 FMAs (Pesado)", "96 FMAs (Extremo)"])
        self.combo_fma.setCurrentIndex(3) # 24
        self.combo_fma.currentIndexChanged.connect(self._on_manual_fma_change)
        adv_grid.addWidget(self.combo_fma, 0, 3)

        adv_grid.addWidget(QLabel("Anti-Aliasing:"), 0, 4)
        self.combo_msaa = QComboBox()
        self.combo_msaa.addItems(["Desativado (1x · Máx. FPS)", "2x MSAA", "4x MSAA", "8x MSAA"])
        self.combo_msaa.setCurrentIndex(0) # 1x default
        self.combo_msaa.currentIndexChanged.connect(self._change_msaa)
        adv_grid.addWidget(self.combo_msaa, 0, 5)

        adv_grid.addWidget(QLabel("Malha do Toro (LOD):"), 0, 6)
        self.combo_lod = QComboBox()
        self.combo_lod.addItems(["Baixa (80x32 · 5k tris)", "Média (120x48 · 11k tris)", "Alta (160x64 · 20k tris)"])
        self.combo_lod.setCurrentIndex(1) # Medium default
        self.combo_lod.currentIndexChanged.connect(self._change_lod)
        adv_grid.addWidget(self.combo_lod, 0, 7)

        # Section 2: Visual Styling & Fur Characteristics
        adv_grid.addWidget(QLabel("Densidade do Pelo:"), 1, 0)
        self.combo_density = QComboBox()
        self.combo_density.addItems(["Fina / Esparsa", "Normal (Clássica)", "Densa (Peluda)", "Super Densa / Lã"])
        self.combo_density.setCurrentIndex(2) # Densa
        self.combo_density.currentIndexChanged.connect(self._change_density)
        adv_grid.addWidget(self.combo_density, 1, 1)

        adv_grid.addWidget(QLabel("Comprimento Fiapos:"), 1, 2)
        self.combo_length = QComboBox()
        self.combo_length.addItems(["Curto (0.08)", "Médio (0.16)", "Longo (0.24)", "Extremo (0.34)"])
        self.combo_length.setCurrentIndex(1) # 0.16
        self.combo_length.currentIndexChanged.connect(self._change_length)
        adv_grid.addWidget(self.combo_length, 1, 3)

        adv_grid.addWidget(QLabel("Tema de Cores:"), 1, 4)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Dourado (FurMark)", "Chamas / Magma", "CachyOS Verde", "Cyberpunk", "Platina Monocromático"])
        self.combo_theme.currentIndexChanged.connect(self._change_theme)
        adv_grid.addWidget(self.combo_theme, 1, 5)

        adv_grid.addWidget(QLabel("Taxa de Quadros:"), 1, 6)
        self.combo_fps_limit = QComboBox()
        self.combo_fps_limit.addItems(["Desbloqueado (Máx. Carga)", "Trava 60 FPS", "Trava 144 FPS", "V-Sync Ativado"])
        self.combo_fps_limit.currentIndexChanged.connect(self._change_fps_limit)
        adv_grid.addWidget(self.combo_fps_limit, 1, 7)

        # Section 3: Physical Dynamics & Toggles
        toggles_row = QHBoxLayout()
        toggles_row.setSpacing(16)

        self.chk_gravity = QCheckBox("Gravidade (Queda física)")
        self.chk_gravity.setChecked(True)
        self.chk_gravity.toggled.connect(self._toggle_gravity)
        toggles_row.addWidget(self.chk_gravity)

        self.chk_wind = QCheckBox("Vento (Ondulação dos fios)")
        self.chk_wind.setChecked(True)
        self.chk_wind.toggled.connect(self._toggle_wind)
        toggles_row.addWidget(self.chk_wind)

        self.chk_specular = QCheckBox("Brilho Especular (Glossy sheen)")
        self.chk_specular.setChecked(True)
        self.chk_specular.toggled.connect(self._toggle_specular)
        toggles_row.addWidget(self.chk_specular)

        toggles_row.addStretch()

        toggles_row.addWidget(QLabel("Rotação:"))
        self.combo_rot = QComboBox()
        self.combo_rot.addItems(["Normal (1x)", "Rápida (2x)", "Lenta (0.5x)", "Pausada"])
        self.combo_rot.currentIndexChanged.connect(self._change_rotation)
        toggles_row.addWidget(self.combo_rot)

        adv_grid.addLayout(toggles_row, 2, 0, 1, 8)
        self.layout.addWidget(self.adv_card)

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

        # Apply initial preset: Equilibrado (~140 FPS)
        self._change_preset(2)

        # Fullscreen Shortcut (F11)
        self.shortcut_f11 = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        self.shortcut_f11.activated.connect(self._toggle_fullscreen)

    # ------------------ EVENT HANDLERS & GRAPHICS SWITCHING ------------------
    def _toggle_adv_panel(self):
        self.adv_expanded = not self.adv_expanded
        self.adv_card.setVisible(self.adv_expanded)
        self.btn_toggle_adv.setText("Ajustes Avançados ▲" if self.adv_expanded else "Ajustes Avançados ▼")

    def _change_preset(self, idx):
        if idx == 7: # Personalizado
            return

        presets = [
            # shells, iters, lod_idx, msaa_idx
            (32, 8, 0, 0),   # 0: Ultra Leve (300+ FPS)
            (48, 16, 1, 0),  # 1: Leve (180+ FPS)
            (64, 24, 1, 0),  # 2: Equilibrado (~140 FPS)
            (96, 32, 2, 0),  # 3: Padrão FurMark (~100 FPS)
            (128, 48, 2, 1), # 4: Pesado (~60 FPS)
            (160, 64, 2, 2), # 5: Extremo (~45 FPS)
            (192, 96, 2, 2), # 6: Ultra Burn (~30 FPS)
        ]

        if idx < len(presets):
            shells, iters, lod, msaa = presets[idx]

            self.gl_widget.shell_count = shells
            self.gl_widget.iterations = iters

            # Sync UI controls
            shell_map = [24, 32, 48, 64, 96, 128, 160, 192]
            if shells in shell_map:
                self.combo_shells.blockSignals(True)
                self.combo_shells.setCurrentIndex(shell_map.index(shells))
                self.combo_shells.blockSignals(False)

            fma_map = [0, 8, 16, 24, 32, 48, 64, 96]
            if iters in fma_map:
                self.combo_fma.blockSignals(True)
                self.combo_fma.setCurrentIndex(fma_map.index(iters))
                self.combo_fma.blockSignals(False)

            self.combo_lod.blockSignals(True)
            self.combo_lod.setCurrentIndex(lod)
            self.combo_lod.blockSignals(False)
            self._change_lod(lod)

            if msaa != (self.current_msaa // 2 if self.current_msaa > 1 else 0):
                self.combo_msaa.blockSignals(True)
                self.combo_msaa.setCurrentIndex(msaa)
                self.combo_msaa.blockSignals(False)
                self._change_msaa(msaa)

    def _on_manual_shell_change(self, idx):
        shell_map = [24, 32, 48, 64, 96, 128, 160, 192]
        self.gl_widget.shell_count = shell_map[idx]
        self.combo_preset.setCurrentIndex(7) # Set to Personalizado

    def _on_manual_fma_change(self, idx):
        fma_map = [0, 8, 16, 24, 32, 48, 64, 96]
        self.gl_widget.iterations = fma_map[idx]
        self.combo_preset.setCurrentIndex(7)

    def _change_lod(self, idx):
        lod_table = [(80, 32), (120, 48), (160, 64)]
        seg, sides = lod_table[idx]
        self.gl_widget.set_geometry_lod(seg, sides)

    def _change_resolution(self, idx):
        if self.isFullScreen():
            self.showNormal()
        res_map = [(960, 540), (1280, 720), (1600, 900), (1920, 1080), (2560, 1440)]
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
        old_widget = self.gl_widget
        old_widget.running = False

        self.gl_widget = FurmarkWidget(msaa=self.current_msaa, vsync=self.current_vsync, parent=self)
        self.gl_widget.shell_count = old_widget.shell_count
        self.gl_widget.iterations = old_widget.iterations
        self.gl_widget.fur_length = old_widget.fur_length
        self.gl_widget.fur_density_exp = old_widget.fur_density_exp
        self.gl_widget.color_theme = old_widget.color_theme
        self.gl_widget.specular = old_widget.specular
        self.gl_widget.gravity = old_widget.gravity
        self.gl_widget.wind = old_widget.wind
        self.gl_widget.rot_speed = old_widget.rot_speed
        self.gl_widget.target_fps = old_widget.target_fps
        self.gl_widget.set_geometry_lod(old_widget.mesh_seg, old_widget.mesh_sides)
        self.gl_widget.stats_updated.connect(self._on_stats_updated)

        self.layout.replaceWidget(old_widget, self.gl_widget)
        old_widget.deleteLater()

    def _change_theme(self, idx):
        self.gl_widget.color_theme = idx

    def _change_density(self, idx):
        exp_map = [1.1, 1.4, 1.7, 2.1]
        self.gl_widget.fur_density_exp = exp_map[idx]

    def _change_length(self, idx):
        len_map = [0.08, 0.16, 0.24, 0.34]
        self.gl_widget.fur_length = len_map[idx]

    def _change_rotation(self, idx):
        speed_map = [1.0, 2.0, 0.5, 0.0]
        self.gl_widget.rot_speed = speed_map[idx]

    def _change_fps_limit(self, idx):
        if idx == 0: # Desbloqueado
            self.gl_widget.target_fps = 0
            self._set_vsync(False)
        elif idx == 1: # 60 FPS
            self.gl_widget.target_fps = 60
            self._set_vsync(False)
        elif idx == 2: # 144 FPS
            self.gl_widget.target_fps = 144
            self._set_vsync(False)
        elif idx == 3: # V-Sync
            self.gl_widget.target_fps = 0
            self._set_vsync(True)

    def _set_vsync(self, enabled):
        self.current_vsync = enabled
        fmt = self.gl_widget.format()
        fmt.setSwapInterval(1 if enabled else 0)
        self.gl_widget.setFormat(fmt)

    def _toggle_gravity(self, checked):
        self.gl_widget.gravity = checked

    def _toggle_wind(self, checked):
        self.gl_widget.wind = checked

    def _toggle_specular(self, checked):
        self.gl_widget.specular = checked

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

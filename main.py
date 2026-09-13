import sys
import os
import json
import wave
import copy
import time
import threading
import tempfile
import numpy as np
import keyboard
import pygame
import pygame.sndarray
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QComboBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QCheckBox, QSlider, QSystemTrayIcon, QMenu, QAction,
                             QToolBox, QMessageBox, QAbstractItemView, QDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QIcon, QFont
import ctypes
import ctypes.wintypes

# ===================== Win32 常量与结构 =====================
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008

SW_SHOWNOACTIVATE = 4
SWP_NOACTIVATE = 0x0010
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
HWND_TOPMOST = -1

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION),
    ]

VK_MAP = {
    'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'back': 0x08,
    'caps': 0x14, 'shift': 0x10, 'rshift': 0xA1, 'ctrl': 0x11,
    'rctrl': 0xA3, 'alt': 0x12, 'ralt': 0xA5,
    'win': 0x5B, 'rwin': 0x5C, 'menu': 0x5D,
    'esc': 0x1B, 'ins': 0x2D, 'del': 0x2E,
    'home': 0x24, 'end': 0x23, 'pageup': 0x21, 'pagedown': 0x22,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    '-': 0xBD, '=': 0xBB, '[': 0xDB, ']': 0xDD, '\\': 0xDC,
    ';': 0xBA, "'": 0xDE, ',': 0xBC, '.': 0xBE, '/': 0xBF, '`': 0xC0,
}

# 需要 EXTENDEDKEY 标志的键
EXTENDED_KEYS = {
    0xA1, 0xA3, 0xA5,  # rshift, rctrl, ralt
    0x5B, 0x5C, 0x5D,  # win, rwin, menu
    0x2D, 0x2E,  # ins, del
    0x24, 0x23, 0x21, 0x22,  # home, end, pageup, pagedown
    0x26, 0x28, 0x25, 0x27,  # arrows
}

# ★ 全局标志
_is_simulating = False


def _make_key_input(vk, flags=0):
    """构造一个键盘 INPUT 结构"""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = user32.MapVirtualKeyW(vk, 0)
    inp.union.ki.dwFlags = flags
    if vk in EXTENDED_KEYS:
        inp.union.ki.dwFlags |= KEYEVENTF_EXTENDEDKEY
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    return inp


def do_send_input(inputs):
    """发送一组 INPUT"""
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    user32.SendInput(n, arr, ctypes.sizeof(INPUT))


def simulate_keys(key, modifier_keys=None, target_hwnd=None):
    """
    在子线程中：恢复目标窗口焦点 → 发送按键 → 完成
    """
    global _is_simulating

    vk = VK_MAP.get(key)
    if vk is None:
        return

    mod_vks = []
    if modifier_keys:
        for mk in modifier_keys:
            mvk = VK_MAP.get(mk)
            if mvk:
                mod_vks.append(mvk)

    try:
        _is_simulating = True
        time.sleep(0.01)

        # ★ 恢复目标窗口到前台
        if target_hwnd and user32.IsWindow(target_hwnd):
            user32.SetForegroundWindow(target_hwnd)
            time.sleep(0.05)

        # 构建输入序列
        inputs = []
        # 按下修饰键
        for mvk in mod_vks:
            inputs.append(_make_key_input(mvk, 0))
        # 按下目标键
        inputs.append(_make_key_input(vk, 0))
        # 释放目标键
        inputs.append(_make_key_input(vk, KEYEVENTF_KEYUP))
        # 释放修饰键（逆序）
        for mvk in reversed(mod_vks):
            inputs.append(_make_key_input(mvk, KEYEVENTF_KEYUP))

        do_send_input(inputs)

    except Exception as e:
        print(f"模拟按键失败: {e}")
    finally:
        time.sleep(0.02)
        _is_simulating = False


# ===================== 键名规范化 =====================
KEY_NAME_MAP = {}
SCAN_CODE_MAP = {
    42: 'shift', 54: 'rshift', 29: 'ctrl', 285: 'rctrl',
    56: 'alt', 312: 'ralt', 91: 'win', 92: 'rwin',
    347: 'win', 348: 'rwin', 58: 'caps', 57: 'space',
    28: 'enter', 1: 'esc', 15: 'tab', 14: 'back',
    339: 'del', 83: 'del', 338: 'ins', 82: 'ins',
}

def _build_key_map():
    pairs = [
        (['spacebar', 'space'], 'space'),
        (['return', 'enter', '\r', '\n'], 'enter'),
        (['escape', 'esc'], 'esc'),
        (['left shift', 'lshift', 'shift'], 'shift'),
        (['right shift', 'rshift'], 'rshift'),
        (['left ctrl', 'lctrl', 'ctrl', 'left control', 'control'], 'ctrl'),
        (['right ctrl', 'rctrl', 'right control'], 'rctrl'),
        (['left alt', 'lalt', 'alt'], 'alt'),
        (['right alt', 'ralt', 'altgr'], 'ralt'),
        (['left windows', 'left win', 'lwin', 'windows', 'win', 'left meta', 'cmd'], 'win'),
        (['right windows', 'right win', 'rwin', 'right meta'], 'rwin'),
        (['caps lock', 'capital', 'caps', 'capslock'], 'caps'),
        (['backspace', 'back'], 'back'),
        (['delete', 'del'], 'del'),
        (['insert', 'ins'], 'ins'),
        (['tab'], 'tab'),
        (['menu', 'apps', 'context menu'], 'menu'),
    ]
    for names, canonical in pairs:
        for n in names:
            KEY_NAME_MAP[n] = canonical
    for k, v in {'!':'1','@':'2','#':'3','$':'4','%':'5','^':'6','&':'7',
                  '*':'8','(':'9',')':'0','_':'-','+':'=','{':'[','}':']',
                  '|':'\\',':':';','"':"'",'<':',','>':'.','?':'/','~':'`'}.items():
        KEY_NAME_MAP[k] = v

_build_key_map()

def normalize_key(name, scan_code=None):
    if scan_code and scan_code in SCAN_CODE_MAP:
        return SCAN_CODE_MAP[scan_code]
    if not name: return ""
    name = str(name).strip().lower()
    return KEY_NAME_MAP.get(name, name)


def get_resource_path(relative_path):
    """获取资源文件的绝对路径（兼容开发环境和PyInstaller打包后的环境）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)


# ===================== 用户配置持久化 =====================
def get_app_dir():
    """获取程序所在目录（兼容PyInstaller打包后与源码运行两种情况）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(sys.argv[0]))


CONFIG_FILE = os.path.join(get_app_dir(), "config.json")


def load_config():
    """读取 config.json；不存在或损坏时返回空字典（utf-8-sig 兼容带 BOM 的文件）"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f) or {}
    except Exception:
        return {}


def save_config(cfg):
    """写入 config.json（无 BOM 的 UTF-8，便于用记事本等直接编辑）"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"配置保存失败: {e}")


class KeySignal(QObject):
    pressed = pyqtSignal(str)
    released = pyqtSignal(str)


# ===================== 音频处理 =====================
def make_reversed_sound(filepath):
    try:
        snd = pygame.mixer.Sound(filepath)
        data = pygame.sndarray.array(snd)
        rev_data = data[::-1].copy()
        return pygame.sndarray.make_sound(rev_data)
    except: return None

def make_octave_down_sound(filepath):
    try:
        snd = pygame.mixer.Sound(filepath)
        data = pygame.sndarray.array(snd)
        framerate = 44100
        grain_size = int(framerate * 0.05)
        if grain_size < 2 or len(data) == 0:
            return snd
        
        n = data.shape[0]
        out = np.zeros_like(data)
        
        for i in range(0, n, grain_size):
            grain = data[i:i+grain_size]
            g_len = len(grain)
            if g_len < 2:
                out[i:i+g_len] = grain
                continue
            
            x = np.arange(g_len)
            xn = np.linspace(0, g_len-1, g_len * 2)
            if data.ndim == 1:
                stretched = np.interp(xn, x, grain).astype(data.dtype)
                out[i:i+g_len] = stretched[:g_len]
            else:
                stretched = np.zeros((g_len * 2, data.shape[1]), dtype=data.dtype)
                for c in range(data.shape[1]):
                    stretched[:, c] = np.interp(xn, x, grain[:, c]).astype(data.dtype)
                out[i:i+g_len] = stretched[:g_len]
                
        return pygame.sndarray.make_sound(out)
    except: return None


# ===================== 音频引擎 =====================
class AudioEngine:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(32)
        self.sounds_normal = {}
        self.sounds_reversed = {}
        self.sounds_octdown = {}
        self.sounds_rev_oct = {}
        self.rules = {}
        self.pack_dir = ""
        self.is_performance_mode = False
        self.performance_sounds = {}
        self.space_channel = None
        self.shift_reverse = False
        self.caps_octave_down = False
        self.space_playing = False
        self.space_start_time = 0.0
        self.current_space_snd = None
        
        # 尝试默认加载或创建 default_pack
        default_p = os.path.join(get_app_dir(), "default_pack")
        if not os.path.exists(default_p):
            os.makedirs(default_p, exist_ok=True)
        # ★ 优先加载上次使用的音效包；音效包被移动/删除时回退到 default_pack
        saved_pack = load_config().get("pack_dir", "")
        if not (saved_pack and os.path.isdir(saved_pack)):
            saved_pack = default_p
        self.load_pack(saved_pack)

    def load_pack(self, pack_dir, overwrite_rules=True):
        self.pack_dir = pack_dir
        rp = os.path.join(pack_dir, "rule.json")
        if overwrite_rules:
            if not os.path.exists(rp):
                self.rules = {"space": {"file": "", "enabled": True}}
                self.save_rules()
            else:
                try:
                    with open(rp, 'r', encoding='utf-8') as f:
                        self.rules = json.load(f)
                except: pass
        else:
            self.save_rules()
        # ★ 记住当前音效包，下次启动自动加载
        if self.pack_dir and os.path.isdir(self.pack_dir):
            cfg = load_config()
            cfg["pack_dir"] = self.pack_dir
            save_config(cfg)
        self.reload_sounds()

    def reload_sounds(self):
        self.sounds_normal.clear(); self.sounds_reversed.clear()
        self.sounds_octdown.clear(); self.sounds_rev_oct.clear()
        for key, cfg in self.rules.items():
            if cfg.get("enabled", True) and cfg.get("file"):
                fp = cfg["file"]
                if not os.path.isabs(fp) and self.pack_dir:
                    fp = os.path.join(self.pack_dir, fp)
                if not os.path.exists(fp): continue
                k = key.lower()
                try:
                    self.sounds_normal[k] = pygame.mixer.Sound(fp)
                    r = make_reversed_sound(fp)
                    if r: self.sounds_reversed[k] = r
                    o = make_octave_down_sound(fp)
                    if o: self.sounds_octdown[k] = o
                    
                    if o:
                        # 基于降调音频直接倒放
                        ro_arr = pygame.sndarray.array(o)[::-1].copy()
                        self.sounds_rev_oct[k] = pygame.sndarray.make_sound(ro_arr)
                        
                except Exception as e:
                    print(f"音效加载失败[{k}]: {e}")

    def save_rules(self):
        if not self.pack_dir:
            self.pack_dir = os.path.join(get_app_dir(), "default_pack")
        if not os.path.exists(self.pack_dir):
            os.makedirs(self.pack_dir, exist_ok=True)
        try:
            with open(os.path.join(self.pack_dir, "rule.json"), 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, indent=4, ensure_ascii=False)
        except Exception as e: 
            print(f"Error saving rules: {e}")

    def _get_sound(self, key):
        if self.shift_reverse and self.caps_octave_down:
            return self.sounds_rev_oct.get(key)
        elif self.shift_reverse:
            return self.sounds_reversed.get(key)
        elif self.caps_octave_down:
            return self.sounds_octdown.get(key)
        return self.sounds_normal.get(key)

    def toggle_caps(self): self.caps_octave_down = not self.caps_octave_down
    def toggle_shift(self): self.shift_reverse = not self.shift_reverse

    def _delayed_space_pause(self):
        if not self.space_playing and self.space_channel:
            self.space_channel.pause()

    def play_key(self, key):
        if key == 'caps': self.toggle_caps(); return
        if key in ('shift','rshift'): self.toggle_shift(); return
        if self.is_performance_mode:
            if key in self.performance_sounds: self.performance_sounds[key].play()
            return
        cfg = self.rules.get(key, {})
        if not cfg.get("enabled", True): return
        snd = self._get_sound(key)
        if not snd: return
        if key == 'space':
            self.space_playing = True
            self.space_start_time = time.time()
            if self.space_channel and self.current_space_snd == snd:
                self.space_channel.unpause()
                if not self.space_channel.get_busy():
                    self.space_channel.play(snd)
            else:
                self.space_channel = pygame.mixer.find_channel(True)
                if self.space_channel: self.space_channel.play(snd)
                self.current_space_snd = snd
        else:
            ch = pygame.mixer.find_channel(True)
            if ch: ch.play(snd)

    def release_key(self, key):
        if key == 'space' and self.space_playing:
            self.space_playing = False
            elapsed = time.time() - self.space_start_time
            if elapsed < 0.3:
                QTimer.singleShot(int((0.3 - elapsed) * 1000), self._delayed_space_pause)
            else:
                if self.space_channel:
                    self.space_channel.pause()

    def load_performance_key(self, filepath):
        try:
            snd = pygame.mixer.Sound(filepath)
            data = pygame.sndarray.array(snd)
            
            km = {'a':0,'s':2,'d':4,'f':5,'g':7,'h':9,'j':11,'k':12}
            self.performance_sounds.clear()
            n = data.shape[0]
            
            for k, semi in km.items():
                if semi == 0:
                    self.performance_sounds[k] = pygame.mixer.Sound(filepath)
                    continue
                    
                factor = 2**(semi/12.0)
                new_n = int(n / factor)
                x = np.arange(new_n) * factor
                
                if data.ndim == 1:
                    resampled = np.interp(x, np.arange(n), data).astype(data.dtype)
                else:
                    resampled = np.zeros((new_n, data.shape[1]), dtype=data.dtype)
                    for c in range(data.shape[1]):
                        resampled[:, c] = np.interp(x, np.arange(n), data[:, c]).astype(data.dtype)
                        
                self.performance_sounds[k] = pygame.sndarray.make_sound(resampled)
            self.is_performance_mode = True
        except Exception as e: print(f"演奏模式失败: {e}")


# ===================== 按键捕获对话框 =====================
class KeyCaptureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("捕获按键")
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(320, 150)
        self.captured_key = ""
        self._hook_id = None
        layout = QVBoxLayout(self)
        self.label = QLabel("请按下要绑定的按键...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        layout.addWidget(self.label)
        self.lbl_key = QLabel("")
        self.lbl_key.setAlignment(Qt.AlignCenter)
        self.lbl_key.setFont(QFont("Arial", 20, QFont.Bold))
        self.lbl_key.setStyleSheet("color: #FF8C00; padding: 10px;")
        layout.addWidget(self.lbl_key)
        bl = QHBoxLayout()
        self.btn_ok = QPushButton("确定"); self.btn_ok.setEnabled(False)
        self.btn_ok.setFocusPolicy(Qt.NoFocus)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFocusPolicy(Qt.NoFocus)
        self.btn_cancel.clicked.connect(self.reject)
        bl.addWidget(self.btn_ok); bl.addWidget(self.btn_cancel)
        layout.addLayout(bl)
        self.setStyleSheet("""
            QDialog{background-color:#1a1a1a;}QLabel{color:white;}
            QPushButton{background-color:#333;color:white;border:1px solid #666;border-radius:4px;padding:8px 20px;font-weight:bold;}
            QPushButton:hover{background-color:#555;}QPushButton:disabled{color:#666;}
        """)

    def keyPressEvent(self, e): pass
    def keyReleaseEvent(self, e): pass

    def showEvent(self, e):
        super().showEvent(e)
        self._hook_id = keyboard.on_press(self._on_key)

    def hideEvent(self, e):
        if self._hook_id:
            keyboard.unhook(self._hook_id); self._hook_id = None
        super().hideEvent(e)

    def _on_key(self, e):
        k = normalize_key(e.name, getattr(e, 'scan_code', None))
        if k:
            self.captured_key = k
            self.lbl_key.setText(k.upper())
            self.btn_ok.setEnabled(True)


class ReadOnlyItem(QTableWidgetItem):
    def __init__(self, text=""):
        super().__init__(text)
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)


# ===================== 设置面板 =====================
class CustomSettingsUI(QWidget):
    def __init__(self, parent_vkb):
        super().__init__()
        self.parent_vkb = parent_vkb
        self.audio = parent_vkb.audio
        self.setWindowTitle("设置")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(600, 720)
        self._drag_pos = None
        self.is_editing = False
        self._rules_snapshot = {}
        self.init_ui()
        self.update_theme(self.parent_vkb.theme_color)

    def init_ui(self):
        ml = QVBoxLayout(self); ml.setContentsMargins(15,15,15,15)
        self.container = QWidget(); self.container.setObjectName("SC")
        cl = QVBoxLayout(self.container); cl.setContentsMargins(20,20,20,20)

        hl = QHBoxLayout()
        self.lbl_title = QLabel("⚙️ 键盘设置")
        self.lbl_title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.btn_close = QPushButton("×"); self.btn_close.setFixedSize(30,30)
        self.btn_close.clicked.connect(self._on_close)
        hl.addWidget(self.lbl_title); hl.addStretch(); hl.addWidget(self.btn_close)
        cl.addLayout(hl)

        self.toolbox = QToolBox(); cl.addWidget(self.toolbox)

        # 1) 外观
        p2 = QWidget(); v2 = QVBoxLayout(p2)
        ht = QHBoxLayout(); ht.addWidget(QLabel("主题:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["橙色","绿色","蓝色"])
        self.combo_theme.currentIndexChanged.connect(self.parent_vkb.change_theme)
        ht.addWidget(self.combo_theme); v2.addLayout(ht)

        hs = QHBoxLayout(); hs.addWidget(QLabel("尺寸:"))
        self.sl_scale = QSlider(Qt.Horizontal); self.sl_scale.setRange(20,70); self.sl_scale.setValue(40)
        self.sl_scale.valueChanged.connect(self.parent_vkb.update_scale)
        self.lbl_s = QLabel("40"); self.lbl_s.setFixedWidth(30)
        self.sl_scale.valueChanged.connect(lambda v: self.lbl_s.setText(str(v)))
        hs.addWidget(self.sl_scale); hs.addWidget(self.lbl_s); v2.addLayout(hs)

        ho = QHBoxLayout(); ho.addWidget(QLabel("不透明度:"))
        self.sl_op = QSlider(Qt.Horizontal); self.sl_op.setRange(20,100); self.sl_op.setValue(100)
        self.sl_op.valueChanged.connect(self.parent_vkb.update_opacity)
        self.lbl_o = QLabel("100%"); self.lbl_o.setFixedWidth(40)
        self.sl_op.valueChanged.connect(lambda v: self.lbl_o.setText(f"{v}%"))
        ho.addWidget(self.sl_op); ho.addWidget(self.lbl_o); v2.addLayout(ho)

        info_v2 = QLabel("请先到【音效与模式】中导入现有音效包或在【音效自定义】中绑定按键\n按下Shift：倒放\n按下CapsLock：水牛音")
        info_v2.setStyleSheet("color:#999;font-size:11px;padding:8px;")
        v2.addWidget(info_v2); v2.addStretch()
        self.toolbox.addItem(p2, "🖥️ 外观")
        
        # 2) 音效
        p1 = QWidget(); v1 = QVBoxLayout(p1)
        self.btn_load = QPushButton("📂 导入音效包")
        self.btn_load.clicked.connect(self.do_load_pack)
        self.btn_perf = QPushButton("🎹 开启演奏模式")
        self.btn_perf.setCheckable(True)
        self.btn_perf.toggled.connect(self.toggle_perf)
        info_v1 = QLabel("使用此功能，确保在音效包文件夹中有key.mp3/ogg/wav/flac\n开启后按ASD...K键")
        info_v1.setStyleSheet("color:#999;font-size:11px;padding:8px;")
        v1.addWidget(self.btn_load); v1.addWidget(self.btn_perf); v1.addWidget(info_v1); v1.addStretch()
        self.toolbox.addItem(p1, "🎵 音效与模式")

        # 3) 规则
        p3 = QWidget(); v3 = QVBoxLayout(p3)
        tip = QLabel("保存以生效规则")
        tip.setStyleSheet("color:#888;font-size:10px;padding:4px;")
        v3.addWidget(tip)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["按键","音频文件","启用","操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_cell_dbl)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(38)
        v3.addWidget(self.table)

        hb = QHBoxLayout()
        self.btn_open_dir = QPushButton("📂 打开目录"); self.btn_open_dir.clicked.connect(self.open_rule_dir)
        self.btn_add = QPushButton("+ 添加"); self.btn_add.clicked.connect(self.add_row)
        self.btn_save = QPushButton("保存"); self.btn_save.clicked.connect(self.do_save)
        hb.addWidget(self.btn_open_dir); hb.addWidget(self.btn_add); hb.addWidget(self.btn_save)
        v3.addLayout(hb)
        self.toolbox.addItem(p3, "⌨️ 音效自定义")

        # 4) 关于
        p4 = QWidget(); v4 = QVBoxLayout(p4)
        al = QLabel('<div align="center" style="margin-top:20px;">'
            '<a href="https://space.bilibili.com/6297797" style="color:#00aaff;text-decoration:none;font-size:18px;font-weight:bold;">作者 @依然匹萨吧</a><br><br>'
            '<span style="color:#ff5555;font-size:13px;font-weight:bold;">本软件免费，禁止商用</span></div>')
        al.setOpenExternalLinks(True); v4.addWidget(al); v4.addStretch()
        self.toolbox.addItem(p4, "ℹ️ 关于")
        ml.addWidget(self.container)

    def update_theme(self, tc):
        self.btn_close.setStyleSheet(f"QPushButton{{background:transparent;color:{tc};font-size:20px;font-weight:bold;border:none;}}QPushButton:hover{{color:red;}}")
        self.setStyleSheet(f"""
            QWidget#SC{{background-color:rgba(15,15,15,240);border:2px solid {tc};border-radius:10px;}}
            QLabel{{color:#eee;font-size:13px;font-weight:bold;}}
            QPushButton{{background-color:rgba(30,30,30,200);color:{tc};border:1px solid {tc};border-radius:5px;padding:8px;font-weight:bold;}}
            QPushButton:hover{{background-color:{tc};color:black;}}
            QToolBox::tab{{background-color:rgba(30,30,30,200);color:{tc};border:1px solid {tc};border-radius:4px;font-weight:bold;font-size:14px;}}
            QToolBox::tab:selected{{background-color:{tc};color:black;}}
            QWidget{{background-color:transparent;}}
            QTableWidget{{background-color:rgba(10,10,10,200);color:{tc};gridline-color:{tc};border:1px solid {tc};font-size:12px;}}
            QTableWidget::item{{padding:4px;background-color:rgba(10,10,10,200);color:{tc};}}
            QTableWidget::item:selected{{background-color:rgba(60,60,60,200);color:white;}}
            QHeaderView::section{{background-color:rgba(30,30,30,255);color:white;border:none;padding:4px;border-bottom:1px solid {tc};}}
            QComboBox{{background-color:rgba(30,30,30,200);color:white;border:1px solid {tc};padding:3px;border-radius:3px;}}
            QComboBox QAbstractItemView{{background-color:rgba(30,30,30,245);color:white;border:1px solid {tc};selection-background-color:{tc};selection-color:black;outline:none;}}
            QComboBox::drop-down{{border:none;width:20px;}}
            QComboBox::down-arrow{{image:none;border-left:5px solid transparent;border-right:5px solid transparent;border-top:6px solid {tc};margin-right:5px;}}
            QSlider::groove:horizontal{{border:1px solid #999;height:8px;background:#333;border-radius:4px;}}
            QSlider::handle:horizontal{{background:{tc};width:18px;margin:-5px 0;border-radius:9px;}}
            QCheckBox{{color:{tc};}}QCheckBox::indicator{{width:16px;height:16px;border:1px solid {tc};border-radius:3px;background-color:rgba(30,30,30,200);}}
            QCheckBox::indicator:checked{{background-color:{tc};}}
        """)

    def mousePressEvent(self, e):
        if e.button()==Qt.LeftButton: self._drag_pos=e.globalPos()-self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons()==Qt.LeftButton and self._drag_pos: self.move(e.globalPos()-self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos=None

    def showEvent(self, e):
        super().showEvent(e); self.is_editing=True
        self._rules_snapshot=copy.deepcopy(self.audio.rules); self.refresh_table()
    def hideEvent(self, e):
        super().hideEvent(e); self.is_editing=False

    def _on_close(self):
        cur = self._collect()
        if cur != self._rules_snapshot:
            msg = QMessageBox(self); msg.setWindowTitle("未保存")
            msg.setText("规则已修改，是否保存？")
            msg.setStandardButtons(QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
            msg.setStyleSheet("QMessageBox{background-color:#1a1a1a;}QLabel{color:white;}QPushButton{background-color:#333;color:white;border:1px solid #666;border-radius:4px;padding:6px 16px;min-width:70px;}QPushButton:hover{background-color:#555;}")
            r = msg.exec_()
            if r==QMessageBox.Save: self.do_save(); self.hide()
            elif r==QMessageBox.Discard:
                self.audio.rules=copy.deepcopy(self._rules_snapshot); self.audio.reload_sounds(); self.hide()
            return
        self.hide()

    def _collect(self):
        rules={}
        for r in range(self.table.rowCount()):
            ki=self.table.item(r,0); fi=self.table.item(r,1); cw=self.table.cellWidget(r,2)
            if ki and fi and cw:
                ch = cw.findChild(QCheckBox) if isinstance(cw, QWidget) and not isinstance(cw, QCheckBox) else cw
                if ch:
                    k=ki.text().strip().lower()
                    if k and k!="(双击设置)":
                        rules[k]={"file":fi.text().strip(),"enabled":ch.isChecked()}
        return rules

    def do_load_pack(self):
        f=QFileDialog.getExistingDirectory(self,"选择音效包")
        if f:
            reply = QMessageBox.question(self, "导入音效包", "是否导入当前规则？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.audio.load_pack(f, overwrite_rules=True)
                self._rules_snapshot=copy.deepcopy(self.audio.rules)
                self.refresh_table()

    def toggle_perf(self, c):
        if c:
            fp = None
            if self.audio.pack_dir:
                for ext in ['wav', 'mp3', 'ogg', 'flac']:
                    temp = os.path.join(self.audio.pack_dir, f"key.{ext}")
                    if os.path.exists(temp):
                        fp = temp
                        break
            if fp:
                self.btn_perf.setText("🎹 退出演奏模式")
                self.audio.load_performance_key(fp)
            else:
                sd = self.audio.pack_dir if self.audio.pack_dir else ""
                f, _ = QFileDialog.getOpenFileName(self, "选择音频文件", sd, "Audio (*.wav *.mp3 *.ogg *.flac)")
                if f:
                    self.btn_perf.setText("🎹 退出演奏模式")
                    self.audio.load_performance_key(f)
                else:
                    self.btn_perf.setChecked(False)
        else:
            self.btn_perf.setText("🎹 开启演奏模式")
            self.audio.is_performance_mode = False

    def refresh_table(self):
        self.table.setRowCount(0)
        for k,c in self.audio.rules.items():
            self._ins(k, c.get("file",""), c.get("enabled",True))

    def _ins(self, key, file, enabled):
        r=self.table.rowCount(); self.table.insertRow(r)
        ki=ReadOnlyItem(key); ki.setToolTip("双击捕获按键"); self.table.setItem(r,0,ki)
        fi=ReadOnlyItem(file if file else "(双击浏览)"); fi.setToolTip("双击选择音频"); self.table.setItem(r,1,fi)
        chk=QCheckBox(); chk.setChecked(enabled)
        chk.clicked.connect(lambda: self.do_save())
        cwd1=QWidget(); l1=QHBoxLayout(cwd1); l1.setContentsMargins(0,0,0,0); l1.setAlignment(Qt.AlignCenter); l1.addWidget(chk)
        self.table.setCellWidget(r,2,cwd1)
        
        bd=QPushButton("❌️"); bd.setFixedSize(26,26)
        bd.setStyleSheet("padding: 0px; margin: 0px;")
        bd.clicked.connect(lambda: self._del(bd))
        cwd2=QWidget(); l2=QHBoxLayout(cwd2); l2.setContentsMargins(0,0,0,0); l2.setAlignment(Qt.AlignCenter); l2.addWidget(bd)
        self.table.setCellWidget(r,3,cwd2)

    def _del(self, w):
        for r in range(self.table.rowCount()):
            cw = self.table.cellWidget(r,3)
            # 兼容直接放置button或者用QWidget包裹的情况
            if cw is w or (cw and cw.isAncestorOf(w)):
                ki=self.table.item(r,0); n=ki.text() if ki else "?"
                msg=QMessageBox(self); msg.setWindowTitle("删除"); msg.setText(f'删除"{n}"？')
                msg.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
                msg.setStyleSheet("QMessageBox{background-color:#1a1a1a;}QLabel{color:white;}QPushButton{background-color:#333;color:white;border:1px solid #666;border-radius:4px;padding:6px 16px;min-width:70px;}QPushButton:hover{background-color:#555;}")
                if msg.exec_()==QMessageBox.Yes: 
                    self.table.removeRow(r)
                    self.do_save()
                return

    def _on_cell_dbl(self, row, col):
        if col==0:
            dlg=KeyCaptureDialog(self)
            if dlg.exec_()==QDialog.Accepted and dlg.captured_key:
                self.table.item(row,0).setText(dlg.captured_key)
                self.do_save()
        elif col==1:
            sd=self.audio.pack_dir if self.audio.pack_dir else ""
            fp,_=QFileDialog.getOpenFileName(self,"选择音频",sd,"音频(*.wav *.mp3 *.ogg *.flac);;所有(*)")
            if fp:
                if self.audio.pack_dir and fp.startswith(self.audio.pack_dir):
                    fp=os.path.relpath(fp,self.audio.pack_dir)
                self.table.item(row,1).setText(fp)
                self.do_save()

    def add_row(self):
        self._ins("(双击设置)","",True)
        self.table.scrollToBottom()
        self.table.selectRow(self.table.rowCount()-1)
        self.do_save()

    def open_rule_dir(self):
        d = self.audio.pack_dir
        if d and os.path.exists(d):
            os.startfile(d)
        else:
            QMessageBox.information(self, "提示", "尚未选择音效包，不存在规则集目录。")

    def do_save(self):
        self.audio.rules=self._collect(); self.audio.save_rules(); self.audio.reload_sounds()
        self._rules_snapshot=copy.deepcopy(self.audio.rules)
        self.btn_save.setText("✅ 已保存!"); self.btn_save.setEnabled(False)
        QTimer.singleShot(1500,lambda:(self.btn_save.setText("保存"),self.btn_save.setEnabled(True)))


# ===================== 主界面 =====================
class VirtualKeyboardApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音效键盘")
        self.icon_path = get_resource_path("sound_keyboard.ico")
        self.setWindowIcon(QIcon(self.icon_path))
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.audio = AudioEngine()
        self.theme_color = "#FF8C00"
        self.base_size = 40
        self.buttons = {}
        self.pressed_keys = set()
        self._last_fg_hwnd = 0
        self.locked_modifiers = set()

        self.key_sig = KeySignal()
        self.key_sig.pressed.connect(self.on_key_pressed)
        self.key_sig.released.connect(self.on_key_released)
        self._drag_pos = None

        self._cleanup_timer = QTimer(self)
        self._cleanup_timer.timeout.connect(self._cleanup_stuck)
        self._cleanup_timer.start(1500)

        self._fg_timer = QTimer(self)
        self._fg_timer.timeout.connect(self._track_fg)
        self._fg_timer.start(100)

        self.init_ui()
        self.init_tray()
        self.settings_dialog = CustomSettingsUI(self)
        self.start_keyboard_hook()

    def _track_fg(self):
        """★ 记住最后一个非自身的前台窗口"""
        try:
            hwnd = user32.GetForegroundWindow()
            my = int(self.winId())
            sd = 0
            if hasattr(self,'settings_dialog') and self.settings_dialog.isVisible():
                sd = int(self.settings_dialog.winId())
            if hwnd and hwnd != my and hwnd != sd:
                self._last_fg_hwnd = hwnd
        except: pass

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(QIcon(self.icon_path), self)
        self.tray_icon.setToolTip("音效键盘")
        tm = QMenu()
        tm.setStyleSheet("QMenu{background-color:#222;color:#fff;border:1px solid #555;}QMenu::item:selected{background-color:#555;}")
        a1=QAction("显示/隐藏",self); a1.triggered.connect(self.toggle_vis)
        a2=QAction("⚙️ 设置",self); a2.triggered.connect(self.open_settings)
        a3=QAction("❌ 退出",self); a3.triggered.connect(self.quit_app)
        tm.addAction(a1); tm.addAction(a2); tm.addSeparator(); tm.addAction(a3)
        self.tray_icon.setContextMenu(tm)
        self.tray_icon.activated.connect(lambda r: self.toggle_vis() if r==QSystemTrayIcon.DoubleClick else None)
        self.tray_icon.show()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15,15,15,15)
        self.main_layout.setSpacing(5)

        top = QHBoxLayout(); top.addStretch()

        self.lbl_rev = QLabel("REV"); self.lbl_rev.setFixedSize(35,18)
        self.lbl_rev.setAlignment(Qt.AlignCenter); self.lbl_rev.setFont(QFont("Arial",7,QFont.Bold))
        top.addWidget(self.lbl_rev)

        self.lbl_oct = QLabel("OCT↓"); self.lbl_oct.setFixedSize(40,18)
        self.lbl_oct.setAlignment(Qt.AlignCenter); self.lbl_oct.setFont(QFont("Arial",7,QFont.Bold))
        top.addWidget(self.lbl_oct)

        # ★ 组合键锁按钮
        self.mod_btns = {}
        for mn, ml in [('ctrl','Ctrl'),('shift','Shift'),('alt','Alt')]:
            b = QPushButton(ml); b.setFixedSize(42,18)
            b.setFont(QFont("Arial",7,QFont.Bold))
            b.setCheckable(True); b.setFocusPolicy(Qt.NoFocus)
            b.toggled.connect(lambda c, m=mn: self._toggle_mod(m, c))
            self.mod_btns[mn] = b; top.addWidget(b)

        self.btn_gear = QPushButton("⚙️"); self.btn_gear.setFixedSize(30,22)
        self.btn_gear.setFocusPolicy(Qt.NoFocus)
        self.btn_gear.clicked.connect(self.open_settings)
        top.addWidget(self.btn_gear)
        self.main_layout.addLayout(top)

        self.kb_container = QWidget(); self.kb_container.setObjectName("KBC")
        self.kb_layout = QVBoxLayout(self.kb_container)
        self.kb_layout.setContentsMargins(10,10,10,10)

        self.rows_def = [
            [('esc','ESC',1),('f1','F1',1),('f2','F2',1),('f3','F3',1),('f4','F4',1),
             ('f5','F5',1),('f6','F6',1),('f7','F7',1),('f8','F8',1),('f9','F9',1),
             ('f10','F10',1),('f11','F11',1),('f12','F12',1),('ins','INS',1),('del','DEL',1)],
            [('`','~',1),('1','1',1),('2','2',1),('3','3',1),('4','4',1),('5','5',1),
             ('6','6',1),('7','7',1),('8','8',1),('9','9',1),('0','0',1),('-','-',1),
             ('=','=',1),('back','⌫',2)],
            [('tab','TAB',1.5),('q','Q',1),('w','W',1),('e','E',1),('r','R',1),
             ('t','T',1),('y','Y',1),('u','U',1),('i','I',1),('o','O',1),
             ('p','P',1),('[','[',1),(']',']',1),('\\','\\',1.5)],
            [('caps','CAPS',1.75),('a','A',1),('s','S',1),('d','D',1),('f','F',1),
             ('g','G',1),('h','H',1),('j','J',1),('k','K',1),('l','L',1),
             (';',';',1),("'","'",1),('enter','⏎',2.25)],
            [('shift','⇧SHIFT',2.25),('z','Z',1),('x','X',1),('c','C',1),('v','V',1),
             ('b','B',1),('n','N',1),('m','M',1),(',',',',1),('.','.', 1),
             ('/','/',1),('rshift','SHIFT⇧',2.75)],
            [('ctrl','CTRL',1.25),('win','WIN',1.25),('alt','ALT',1.25),
             ('space','',6.25),('left','◀',1.25),('up','▲',1.25),
             ('down','▼',1.25),('right','▶',1.25)]
        ]

        self.row_layouts = []
        for row in self.rows_def:
            hl = QHBoxLayout(); hl.setSpacing(0)
            for rk, dt, wm in row:
                btn = QPushButton(dt)
                btn.setProperty("width_mult", wm)
                btn.setProperty("is_pressed", False)
                btn.setFocusPolicy(Qt.NoFocus)
                self.buttons[rk] = btn
                hl.addWidget(btn)
                # ★ 用 pressed/released 实现完整按下-释放体验
                btn.pressed.connect(lambda k=rk: self._vk_press(k))
                btn.released.connect(lambda k=rk: self._vk_release(k))
            self.kb_layout.addLayout(hl)
            self.row_layouts.append(hl)

        self.main_layout.addWidget(self.kb_container)
        self.update_scale(self.base_size)

    def _toggle_mod(self, mod, checked):
        if checked: self.locked_modifiers.add(mod)
        else: self.locked_modifiers.discard(mod)
        self._update_mod_styles()

    def _update_mod_styles(self):
        for m, b in self.mod_btns.items():
            if b.isChecked():
                b.setStyleSheet(f"background-color:{self.theme_color};color:black;border:1px solid {self.theme_color};border-radius:3px;font-weight:bold;")
            else:
                b.setStyleSheet("background-color:rgba(30,30,30,200);color:#888;border:1px solid #555;border-radius:3px;")

    def _vk_press(self, key):
        """鼠标按下虚拟按键"""
        if key in self.buttons:
            self.buttons[key].setProperty("is_pressed", True)
            self._style_btn(self.buttons[key], True)
        # 播放音效
        self.audio.play_key(key)
        self._update_indicators()

    def _vk_release(self, key):
        """鼠标释放虚拟按键"""
        if key in self.buttons:
            self.buttons[key].setProperty("is_pressed", False)
            self._style_btn(self.buttons[key], False)
        self.audio.release_key(key)

        # ★ 模拟输入：先恢复前台窗口焦点再 SendInput
        mods = list(self.locked_modifiers)
        target = self._last_fg_hwnd

        if target:
            threading.Thread(
                target=simulate_keys,
                args=(key, mods, target),
                daemon=True
            ).start()

        # 非修饰键时清除组合键锁
        if key not in ('ctrl','rctrl','shift','rshift','alt','ralt','caps') and self.locked_modifiers:
            self.locked_modifiers.clear()
            for b in self.mod_btns.values(): b.setChecked(False)
            self._update_mod_styles()

    def _style_btn(self, btn, active):
        if active:
            btn.setStyleSheet(f"background-color:{self.theme_color};color:#000;border:2px solid {self.theme_color};border-radius:5px;font-weight:bold;")
        else:
            btn.setStyleSheet(f"background-color:rgba(10,10,10,150);color:{self.theme_color};border:1px solid {self.theme_color};border-radius:5px;font-weight:bold;")

    def _update_indicators(self):
        if self.audio.shift_reverse:
            self.lbl_rev.setStyleSheet(f"background-color:{self.theme_color};color:black;border-radius:3px;font-weight:bold;")
        else:
            self.lbl_rev.setStyleSheet("background-color:rgba(30,30,30,200);color:#555;border:1px solid #555;border-radius:3px;")
        if self.audio.caps_octave_down:
            self.lbl_oct.setStyleSheet(f"background-color:{self.theme_color};color:black;border-radius:3px;font-weight:bold;")
        else:
            self.lbl_oct.setStyleSheet("background-color:rgba(30,30,30,200);color:#555;border:1px solid #555;border-radius:3px;")

    def apply_styles(self):
        self.kb_container.setStyleSheet(f"QWidget#KBC{{background-color:rgba(15,15,15,240);border:2px solid {self.theme_color};border-radius:10px;}}")
        self.btn_gear.setStyleSheet(f"background-color:rgba(30,30,30,200);color:{self.theme_color};border:1px solid {self.theme_color};border-radius:5px;font-weight:bold;")
        for btn in self.buttons.values():
            self._style_btn(btn, btn.property("is_pressed"))
        self._update_indicators()
        self._update_mod_styles()

    def update_scale(self, sz):
        self.base_size = sz
        sp = max(2, int(sz*0.12))
        self.kb_layout.setSpacing(sp)
        font = QFont("Arial", max(6, int(sz*0.28)), QFont.Bold)
        for ri, row in enumerate(self.rows_def):
            n=len(row); self.row_layouts[ri].setSpacing(sp)
            ts=sp*(n-1); aw=int(15.0*sz)-ts
            tm=sum(m for _,_,m in row)
            rw=[(m/tm)*aw for _,_,m in row]
            iw=[int(w) for w in rw]
            pe=aw-sum(iw)
            rem=sorted(range(n),key=lambda i:rw[i]-iw[i],reverse=True)
            for i in range(abs(pe)): iw[rem[i%n]]+=1 if pe>0 else -1
            for i,(rk,_,_) in enumerate(row):
                self.buttons[rk].setFixedSize(iw[i],sz)
                self.buttons[rk].setFont(font)
        self.apply_styles(); self.adjustSize()

    def update_opacity(self, v): self.setWindowOpacity(v/100.0)

    def change_theme(self, idx):
        cs=["#FF8C00","#00FF00","#00FFFF","#AA00FF","#FF3333"]
        if 0<=idx<len(cs):
            self.theme_color=cs[idx]; self.apply_styles()
            if hasattr(self,'settings_dialog'): self.settings_dialog.update_theme(self.theme_color)

    def open_settings(self): self.settings_dialog.show(); self.settings_dialog.raise_()
    def toggle_vis(self): self.hide() if self.isVisible() else self.show()
    def quit_app(self): keyboard.unhook_all(); QApplication.quit()

    def mousePressEvent(self, e):
        if e.button()==Qt.LeftButton: self._drag_pos=e.globalPos()-self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons()==Qt.LeftButton and self._drag_pos: self.move(e.globalPos()-self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos=None

    def start_keyboard_hook(self):
        def on_hook(e):
            global _is_simulating
            if _is_simulating: return
            if hasattr(self,'settings_dialog') and self.settings_dialog.is_editing:
                if self.settings_dialog.isActiveWindow(): return
            k=normalize_key(e.name, getattr(e,'scan_code',None))
            if not k: return
            if e.event_type==keyboard.KEY_DOWN:
                if k not in self.pressed_keys:
                    self.pressed_keys.add(k); self.key_sig.pressed.emit(k)
            elif e.event_type==keyboard.KEY_UP:
                self.pressed_keys.discard(k); self.key_sig.released.emit(k)
        keyboard.hook(on_hook)

    def _cleanup_stuck(self):
        for k,b in self.buttons.items():
            if b.property("is_pressed") and k not in self.pressed_keys:
                b.setProperty("is_pressed",False); self._style_btn(b,False)

    def on_key_pressed(self, key):
        if key in self.buttons:
            self.buttons[key].setProperty("is_pressed",True)
            self._style_btn(self.buttons[key],True)
        self.audio.play_key(key)
        self._update_indicators()

    def on_key_released(self, key):
        if key in self.buttons:
            self.buttons[key].setProperty("is_pressed",False)
            self._style_btn(self.buttons[key],False)
        self.audio.release_key(key)
        self.pressed_keys.discard(key)


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)
    window = VirtualKeyboardApp()
    window.show()
    sys.exit(app.exec_())
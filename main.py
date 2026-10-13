import sys
import os
import json
import wave
import copy
import time
import threading
import tempfile
import numpy as np
import pygame
import pygame.sndarray
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QComboBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QCheckBox, QSlider, QSystemTrayIcon, QMenu, QAction,
                             QToolBox, QMessageBox, QAbstractItemView, QDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QIcon, QFont, QFontMetrics
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
    'prtsc': 0x2C, 'scrlock': 0x91, 'pause': 0x13,
    'pgup': 0x21, 'pgdn': 0x22,
    'numlock': 0x90,
    'n0': 0x60, 'n1': 0x61, 'n2': 0x62, 'n3': 0x63, 'n4': 0x64,
    'n5': 0x65, 'n6': 0x66, 'n7': 0x67, 'n8': 0x68, 'n9': 0x69,
    'n*': 0x6A, 'n+': 0x6B, 'n-': 0x6D, 'n.': 0x6E, 'n/': 0x6F,
    'nenter': 0x0D,
    'mute': 0xAD, 'vol-': 0xAE, 'vol+': 0xAF, 'calc': 0xB7,
    'f13': 0x7C, 'f14': 0x7D, 'f15': 0x7E, 'f16': 0x7F,
    'f17': 0x80, 'f18': 0x81, 'f19': 0x82, 'f20': 0x83,
    'f21': 0x84, 'f22': 0x85, 'f23': 0x86, 'f24': 0x87,
}

# 需要 EXTENDEDKEY 标志的键
EXTENDED_KEYS = {
    0xA1, 0xA3, 0xA5,  # rshift, rctrl, ralt
    0x5B, 0x5C, 0x5D,  # win, rwin, menu
    0x2D, 0x2E,  # ins, del
    0x24, 0x23, 0x21, 0x22,  # home, end, pageup, pagedown
    0x26, 0x28, 0x25, 0x27,  # arrows
    0x2C,  # prtsc
    0x6F,  # 小键盘 /（扩展键）
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


# ===================== 键名解析（原生 VK 表） =====================
# keyboard 库对媒体键会给出不可靠的名字（如音量键被命名成 'D'/'C'），
# 因此改用原生钩子直接读 VK + 扩展位，键名与界面/规则使用的完全一致
VK_TO_KEY = {
    0x08: 'back', 0x09: 'tab', 0x0D: 'enter', 0x13: 'pause', 0x14: 'caps',
    0x1B: 'esc', 0x20: 'space',
    0x21: 'pgup', 0x22: 'pgdn', 0x23: 'end', 0x24: 'home',
    0x25: 'left', 0x26: 'up', 0x27: 'right', 0x28: 'down',
    0x2D: 'ins', 0x2E: 'del',
    0x5B: 'win', 0x5C: 'rwin', 0x5D: 'menu',
    0x90: 'numlock', 0x91: 'scrlock',
    0xA0: 'shift', 0xA1: 'rshift', 0xA2: 'ctrl', 0xA3: 'rctrl',
    0xA4: 'alt', 0xA5: 'ralt',
    0xAD: 'mute', 0xAE: 'vol-', 0xAF: 'vol+',
    0xB0: 'next', 0xB1: 'prev', 0xB2: 'stop', 0xB3: 'play', 0xB5: 'media',
    0xB7: 'calc',
    0xBA: ';', 0xBB: '=', 0xBC: ',', 0xBD: '-', 0xBE: '.', 0xBF: '/',
    0xC0: '`', 0xDB: '[', 0xDC: '\\', 0xDD: ']', 0xDE: "'",
}
for _i in range(10): VK_TO_KEY[0x30 + _i] = str(_i)        # 主键区数字
for _i in range(26): VK_TO_KEY[0x41 + _i] = chr(97 + _i)   # 字母
for _i in range(10): VK_TO_KEY[0x60 + _i] = 'n%d' % _i     # 小键盘数字
VK_TO_KEY.update({0x6A: 'n*', 0x6B: 'n+', 0x6D: 'n-', 0x6E: 'n.', 0x6F: 'n/'})
for _i in range(12): VK_TO_KEY[0x70 + _i] = 'f%d' % (_i + 1)
for _i in range(12): VK_TO_KEY[0x7C + _i] = 'f%d' % (_i + 13)
# 键名 → VK 码（调试行展示用；优先原生钩子的 VK 表，缺失时回落到 VK_MAP）
_NAME_TO_VK = {name: vk for vk, name in VK_TO_KEY.items()}

def vk_to_key(vk, extended, scan=0):
    """虚拟键码(+扩展位+扫描码) → 规范键名"""
    if vk in (0x10, 0x11, 0x12):  # Shift/Ctrl/Alt 通用码，靠扩展位分左右
        base = {0x10: 'shift', 0x11: 'ctrl', 0x12: 'alt'}[vk]
        return ('r' + base) if extended else base
    if vk == 0x0D and extended: return 'nenter'  # 小键盘回车
    if vk == 0x2C: return 'prtsc'
    # NumLock 关闭的小键盘：vk 被系统译成导航键，但扫描码仍是小键盘区且无扩展位
    # （真实导航键带扩展位，据此区分；使小键盘在任何 NumLock 状态下都按小键盘响应）
    if not extended and scan in _NUMLOCK_OFF_NUMPAD:
        return _NUMLOCK_OFF_NUMPAD[scan]
    return VK_TO_KEY.get(vk)

# NumLock 关闭时小键盘的扫描码 → 键名
_NUMLOCK_OFF_NUMPAD = {
    71: 'n7', 72: 'n8', 73: 'n9', 75: 'n4', 76: 'n5', 77: 'n6',
    79: 'n1', 80: 'n2', 81: 'n3', 82: 'n0', 83: 'n.',
}

# 旧版/常见键名别名 → 规范键名（加载 rule.json 时自动转换，保证旧音效包可用）
RULE_KEY_ALIAS = {
    'spacebar': 'space', 'return': 'enter',
    'escape': 'esc',
    'left shift': 'shift', 'lshift': 'shift', 'l_shift': 'shift', 'left_shift': 'shift',
    'right shift': 'rshift', 'r_shift': 'rshift', 'right_shift': 'rshift',
    'left ctrl': 'ctrl', 'lctrl': 'ctrl', 'left control': 'ctrl', 'control': 'ctrl', 'l_ctrl': 'ctrl', 'left_ctrl': 'ctrl',
    'right ctrl': 'rctrl', 'right control': 'rctrl', 'r_ctrl': 'rctrl', 'right_ctrl': 'rctrl',
    'left alt': 'alt', 'lalt': 'alt', 'l_alt': 'alt', 'left_alt': 'alt',
    'right alt': 'ralt', 'altgr': 'ralt', 'r_alt': 'ralt', 'right_alt': 'ralt',
    'left windows': 'win', 'left win': 'win', 'lwin': 'win', 'windows': 'win',
    'left meta': 'win', 'cmd': 'win', 'l_win': 'win', 'left_win': 'win',
    'right windows': 'rwin', 'right win': 'rwin', 'right meta': 'rwin', 'r_win': 'rwin', 'right_win': 'rwin',
    'caps lock': 'caps', 'capital': 'caps', 'capslock': 'caps', 'caps_lock': 'caps',
    'backspace': 'back', 'back_space': 'back',
    'delete': 'del', 'insert': 'ins',
    'print screen': 'prtsc', 'printscreen': 'prtsc', 'sys req': 'prtsc', 'print_screen': 'prtsc',
    'scroll lock': 'scrlock', 'scrolllock': 'scrlock', 'scroll_lock': 'scrlock',
    'page up': 'pgup', 'pageup': 'pgup', 'page_up': 'pgup',
    'page down': 'pgdn', 'pagedown': 'pgdn', 'page_down': 'pgdn',
    'num lock': 'numlock', 'number lock': 'numlock', 'num_lock': 'numlock',
    'volume mute': 'mute', 'volume down': 'vol-', 'volume up': 'vol+',
    'calculator': 'calc',
    'menu key': 'menu', 'apps': 'menu', 'context menu': 'menu', 'application': 'menu',
    'keypad enter': 'nenter', 'num enter': 'nenter', 'numpad enter': 'nenter',
    'keypad /': 'n/', 'num /': 'n/', 'numpad /': 'n/', 'numpad divide': 'n/',
    'keypad *': 'n*', 'num *': 'n*', 'numpad *': 'n*', 'numpad multiply': 'n*',
    'keypad +': 'n+', 'num +': 'n+', 'numpad +': 'n+', 'numpad add': 'n+',
    'keypad -': 'n-', 'num -': 'n-', 'numpad -': 'n-', 'numpad subtract': 'n-',
    'keypad .': 'n.', 'num .': 'n.', 'numpad .': 'n.', 'numpad decimal': 'n.',
    # 原版把 Shift+数字的符号名映射到数字键
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7',
    '*': '8', '(': '9', ')': '0', '_': '-', '+': '=', '{': '[', '}': ']',
    '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/', '~': '`',
}
for _d in range(10):
    for _p in ('keypad %d', 'num %d', 'numpad %d', 'numpad%d', 'num%d',
               'keypad_%d', 'num_%d', 'numpad_%d', 'kp_%d', 'kp %d'):
        RULE_KEY_ALIAS[_p % _d] = 'n%d' % _d
# 小键盘运算符的各种写法（空格/下划线/英文全称）
for _p in ('keypad enter', 'num enter', 'numpad enter', 'keypad_enter',
           'num_enter', 'numpad_enter', 'kp_enter'):
    RULE_KEY_ALIAS[_p] = 'nenter'
for _p in ('keypad /', 'num /', 'numpad /', 'keypad_/', 'num_/', 'numpad_/',
           'kp_/', 'numpad divide', 'num_divide', 'numpad_divide'):
    RULE_KEY_ALIAS[_p] = 'n/'
for _p in ('keypad *', 'num *', 'numpad *', 'keypad_*', 'num_*', 'numpad_*',
           'kp_*', 'numpad multiply', 'num_multiply', 'numpad_multiply'):
    RULE_KEY_ALIAS[_p] = 'n*'
for _p in ('keypad +', 'num +', 'numpad +', 'keypad_+', 'num_+', 'numpad_+',
           'kp_+', 'numpad add', 'num_add', 'numpad_add'):
    RULE_KEY_ALIAS[_p] = 'n+'
for _p in ('keypad -', 'num -', 'numpad -', 'keypad_-', 'num_-', 'numpad_-',
           'kp_-', 'numpad subtract', 'num_subtract', 'numpad_subtract'):
    RULE_KEY_ALIAS[_p] = 'n-'
for _p in ('keypad .', 'num .', 'numpad .', 'keypad_.', 'num_.', 'numpad_.',
           'kp_.', 'numpad decimal', 'num_decimal', 'numpad_decimal', 'decimal', 'point'):
    RULE_KEY_ALIAS[_p] = 'n.'
# 小键盘 r_ 前缀写法（用户的音效包风格）
RULE_KEY_ALIAS.update({
    'r_/': 'n/', 'r_*': 'n*', 'r_-': 'n-', 'r_+': 'n+', 'r_.': 'n.',
    'r_enter': 'nenter',
    'r0': 'n0', 'r1': 'n1', 'r2': 'n2', 'r3': 'n3', 'r4': 'n4',
    'r5': 'n5', 'r6': 'n6', 'r7': 'n7', 'r8': 'n8', 'r9': 'n9',
    'r_0': 'n0', 'r_1': 'n1', 'r_2': 'n2', 'r_3': 'n3', 'r_4': 'n4',
    'r_5': 'n5', 'r_6': 'n6', 'r_7': 'n7', 'r_8': 'n8', 'r_9': 'n9',
    'fn': 'menu',  # FN 槽位（规范名 menu）
})

# 未识别按键调试日志：记录 vk/扫描码/扩展位，用于识别 FN 等特殊键
_unknown_logged = set()
def _log_unknown_key(vk, scan, extended):
    if vk in _unknown_logged: return
    _unknown_logged.add(vk)
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "key_debug.log")
        with open(p, 'a', encoding='utf-8') as f:
            f.write(f"未识别按键: vk=0x{vk:02X} scan=0x{scan:02X} extended={extended}\n")
    except: pass

# ===================== 原生底层键盘钩子 =====================
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
WH_KEYBOARD_LL, LLKHF_EXTENDED, WM_QUIT = 13, 0x01, 0x0012

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", ctypes.wintypes.DWORD), ("scanCode", ctypes.wintypes.DWORD),
                ("flags", ctypes.wintypes.DWORD), ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

LRESULT = ctypes.wintypes.LPARAM
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int,
                              ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                  ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM]

class RawKeyHook:
    """WH_KEYBOARD_LL 钩子：监听器收到 (规范键名, 是否按下)"""
    def __init__(self):
        self.listeners = []
        self._proc = HOOKPROC(self._cb)  # 持有引用防止回调被 GC
        self._thread = None
        self._tid = 0

    def add_listener(self, fn):
        if fn not in self.listeners: self.listeners.append(fn)

    def remove_listener(self, fn):
        if fn in self.listeners: self.listeners.remove(fn)

    def _cb(self, nCode, wParam, lParam):
        if nCode == 0 and not _is_simulating:
            try:
                k = KBDLLHOOKSTRUCT.from_address(lParam)
                down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                key = vk_to_key(k.vkCode, k.flags & LLKHF_EXTENDED, k.scanCode)
                if key:
                    for fn in list(self.listeners):
                        try: fn(key, down)
                        except: pass
                elif down:
                    _log_unknown_key(k.vkCode, k.scanCode, bool(k.flags & LLKHF_EXTENDED))
            except: pass
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC,
                                             ctypes.wintypes.HINSTANCE, ctypes.wintypes.DWORD]
        hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        if not hook: return
        self._tid = kernel32.GetCurrentThreadId()
        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        user32.UnhookWindowsHookEx(hook)

    def stop(self):
        if self._tid: user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)


def get_resource_path(relative_path):
    """获取资源文件的绝对路径（兼容开发环境和PyInstaller打包后的环境）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

# ===================== 配置持久化 =====================
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

def load_app_settings():
    """读取上次的配置（音效包/主题/尺寸/不透明度/窗口位置）"""
    try:
        with open(os.path.join(BASE_DIR, 'settings.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return {}

def save_app_settings(d):
    try:
        with open(os.path.join(BASE_DIR, 'settings.json'), 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    except: pass

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
        self.performance_file = ''
        self.space_channel = None
        self.shift_reverse = False
        self.caps_octave_down = False
        # 趣味变调模式开关（默认关闭；开启后 Shift=倒放、CapsLock=低八度）
        self.reverse_enabled = False
        self.octave_enabled = False
        self.space_playing = False
        self.space_start_time = 0.0
        self.current_space_snd = None
        
        # 尝试默认加载或创建 default_pack
        default_p = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "default_pack")
        if not os.path.exists(default_p):
            os.makedirs(default_p, exist_ok=True)
        self.load_pack(default_p)

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
                        loaded = json.load(f)
                    # 旧版键名（left shift / volume mute / num 7 等）自动转换为规范键名，
                    # 键名统一小写；规范名条目优先，别名不覆盖已有的规范条目
                    self.rules = {}
                    aliased = {}
                    for k, v in loaded.items():
                        kk = str(k).strip().lower()
                        ck = RULE_KEY_ALIAS.get(kk, kk)
                        if ck == k:
                            self.rules[ck] = v
                        else:
                            aliased.setdefault(ck, v)
                    for ck, v in aliased.items():
                        self.rules.setdefault(ck, v)
                except: pass
        else:
            self.save_rules()
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
            self.pack_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "default_pack")
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

    # 小键盘键无专属音效时回落到主键区同名键（原版行为：小键盘数字与主键区共用音效）
    # 注：小键盘 / 和 . 不回落，保持静音（按用户要求）
    NUMPAD_FALLBACK = {f'n{d}': str(d) for d in range(10)}
    NUMPAD_FALLBACK.update({'n+': '+', 'n-': '-', 'nenter': 'enter'})

    def _delayed_space_pause(self):
        if not self.space_playing and self.space_channel:
            self.space_channel.pause()

    def play_key(self, key):
        """播放按键音效；返回 (是否播放, 音效名, 说明) 供主界面调试行展示"""
        # 仅在设置里开启趣味模式时，Shift/CapsLock 才切换变调；默认只播音效
        if key == 'caps' and self.octave_enabled: self.toggle_caps()
        if key in ('shift','rshift') and self.reverse_enabled: self.toggle_shift()
        if self.is_performance_mode and key not in ('caps','shift','rshift'):
            if key in self.performance_sounds:
                self.performance_sounds[key].play()
                return True, self.performance_file, '演奏模式'
            return False, '', '演奏模式未覆盖该键'
        cfg = self.rules.get(key, {})
        snd_name = os.path.basename(cfg.get('file') or '')
        if key in self.rules and not cfg.get("enabled", True):
            return False, snd_name, '音效已停用'
        snd = self._get_sound(key)
        fb_used = ''
        if snd is None and key in self.NUMPAD_FALLBACK:
            fb = self.NUMPAD_FALLBACK[key]
            if self.rules.get(fb, {}).get("enabled", True):
                snd = self._get_sound(fb)
                if snd is not None:
                    fb_used = fb
                    snd_name = os.path.basename(self.rules.get(fb, {}).get('file') or '') or fb
        if not snd:
            detail = '音频文件加载失败' if (key in self.rules and cfg.get('file')) else '未绑定音效'
            return False, snd_name, detail
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
        if fb_used:
            return True, snd_name, f'正常播放（回落 {fb_used} 音效）'
        variant = ''
        if self.shift_reverse and self.caps_octave_down: variant = '（倒放+低八度）'
        elif self.shift_reverse: variant = '（倒放）'
        elif self.caps_octave_down: variant = '（低八度）'
        return True, snd_name, '正常播放' + variant

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
            self.performance_file = os.path.basename(filepath)
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

    def _vkb(self):
        p = self.parent()
        return getattr(p, 'parent_vkb', None) if p else None

    def showEvent(self, e):
        vkb = self._vkb()
        if vkb is not None and hasattr(vkb, 'raw_hook'):
            vkb.raw_hook.add_listener(self._on_key)

    def hideEvent(self, e):
        vkb = self._vkb()
        if vkb is not None and hasattr(vkb, 'raw_hook'):
            vkb.raw_hook.remove_listener(self._on_key)
        super().hideEvent(e)

    def _on_key(self, key, down):
        if not down or not key: return
        self.captured_key = key
        self.lbl_key.setText(key.upper())
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

        info_v2 = QLabel("请先到【音效与模式】中导入现有音效包或在【音效自定义】中绑定按键\n倒放/水牛音等趣味模式可在【音效与模式】页开启（默认关闭）")
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
        self.chk_rev = QCheckBox("⇧ Shift 切换倒放模式（默认关闭）")
        self.chk_oct = QCheckBox("Caps Lock 切换低八度水牛音（默认关闭）")
        self.chk_rev.toggled.connect(lambda c: setattr(self.audio, 'reverse_enabled', c))
        self.chk_oct.toggled.connect(lambda c: setattr(self.audio, 'octave_enabled', c))
        info_v1 = QLabel("使用此功能，确保在音效包文件夹中有key.mp3/ogg/wav/flac\n开启后按ASD...K键")
        info_v1.setStyleSheet("color:#999;font-size:11px;padding:8px;")
        v1.addWidget(self.btn_load); v1.addWidget(self.btn_perf)
        v1.addWidget(self.chk_rev); v1.addWidget(self.chk_oct)
        v1.addWidget(info_v1); v1.addStretch()
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
                self.parent_vkb._save_settings()

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

        # ★ 恢复上次配置：音效包 + 界面尺寸（在构建界面前应用）
        self._saved = load_app_settings()
        _pd = self._saved.get('pack_dir', '')
        if _pd and os.path.exists(os.path.join(_pd, 'rule.json')):
            try: self.audio.load_pack(_pd)
            except: pass
        if 'scale' in self._saved:
            try: self.base_size = max(20, min(70, int(self._saved['scale'])))
            except: pass
        self.pressed_keys = set()
        self.mouse_pressed_keys = set()  # 鼠标按住中的虚拟键（豁免卡键清理定时器）
        self._press_ts = {}  # 每个键最近一次点亮时间（保证按下效果最少可见时长）
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
        self._apply_saved_settings()

    def _apply_saved_settings(self):
        """恢复主题/不透明度/窗口位置/趣味模式（需在设置面板创建后调用）"""
        st = self._saved
        try:
            if 'theme_idx' in st:
                self.settings_dialog.combo_theme.setCurrentIndex(int(st['theme_idx']))
            if 'scale' in st:
                self.settings_dialog.sl_scale.setValue(self.base_size)
            if 'opacity' in st:
                self.settings_dialog.sl_op.setValue(max(20, min(100, int(st['opacity']))))
            self.settings_dialog.chk_rev.setChecked(bool(st.get('reverse_mode', False)))
            self.settings_dialog.chk_oct.setChecked(bool(st.get('octave_mode', False)))
            if st.get('classic_layout', False):
                self.toggle_layout()
            pos = st.get('pos')
            if pos and len(pos) == 2:
                g = QApplication.desktop().availableGeometry()
                self.move(min(max(int(pos[0]), g.left()), g.right()-200),
                          min(max(int(pos[1]), g.top()), g.bottom()-100))
        except: pass

    def _save_settings(self):
        """保存当前配置，下次启动自动恢复"""
        sd = self.settings_dialog if hasattr(self, 'settings_dialog') else None
        save_app_settings({
            'pack_dir': getattr(self.audio, 'pack_dir', '') or '',
            'theme_idx': sd.combo_theme.currentIndex() if sd else 0,
            'scale': self.base_size,
            'opacity': round(self.windowOpacity()*100),
            'pos': [self.x(), self.y()],
            'reverse_mode': bool(getattr(self.audio, 'reverse_enabled', False)),
            'octave_mode': bool(getattr(self.audio, 'octave_enabled', False)),
            'classic_layout': bool(getattr(self, 'use_classic_layout', False)),
        })

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
        self.lbl_rev.setToolTip("倒放模式指示：设置中开启后，按 Shift 键切换")
        top.addWidget(self.lbl_rev)

        self.lbl_oct = QLabel("OCT↓"); self.lbl_oct.setFixedSize(40,18)
        self.lbl_oct.setAlignment(Qt.AlignCenter); self.lbl_oct.setFont(QFont("Arial",7,QFont.Bold))
        self.lbl_oct.setToolTip("低八度模式指示：设置中开启后，按 CapsLock 键切换")
        top.addWidget(self.lbl_oct)

        # ★ 组合键锁按钮
        self.mod_btns = {}
        for mn, ml in [('ctrl','Ctrl'),('shift','Shift'),('alt','Alt')]:
            b = QPushButton(ml); b.setFixedSize(42,18)
            b.setFont(QFont("Arial",7,QFont.Bold))
            b.setToolTip(f"组合键锁：点击锁定 {ml}，再点虚拟按键可发送组合键")
            b.setCheckable(True); b.setFocusPolicy(Qt.NoFocus)
            b.toggled.connect(lambda c, m=mn: self._toggle_mod(m, c))
            self.mod_btns[mn] = b; top.addWidget(b)

        # ★ 布局切换按钮（经典 6 行 / 108 键）
        self.btn_layout = QPushButton("经典"); self.btn_layout.setFixedSize(42,18)
        self.btn_layout.setFont(QFont("Microsoft YaHei", 7, QFont.Bold))
        self.btn_layout.setFocusPolicy(Qt.NoFocus)
        self.btn_layout.setToolTip("当前：108 键布局，点击切换为经典 6 行布局")
        self.btn_layout.clicked.connect(self.toggle_layout)
        top.addWidget(self.btn_layout)

        self.btn_gear = QPushButton("⚙️"); self.btn_gear.setFixedSize(30,22)
        self.btn_gear.setFocusPolicy(Qt.NoFocus)
        self.btn_gear.setToolTip("打开设置")
        self.btn_gear.clicked.connect(self.open_settings)
        top.addWidget(self.btn_gear)

        # ★ 隐藏窗口按钮（与托盘右键“显示/隐藏”一致，托盘可恢复）
        self.btn_hide = QPushButton("—"); self.btn_hide.setFixedSize(30,22)
        self.btn_hide.setFocusPolicy(Qt.NoFocus)
        self.btn_hide.setToolTip("隐藏键盘（托盘双击或右键恢复）")
        self.btn_hide.clicked.connect(self.hide)
        top.addWidget(self.btn_hide)
        self.main_layout.addLayout(top)

        self.kb_container = QWidget(); self.kb_container.setObjectName("KBC")

        # ★ 两套布局：108 键变体（默认）/ 原版经典 6 行，右上角按钮随时切换
        # 108 键布局：MUTE/VOL-/VOL+/F13 占功能行的小键盘位置，小键盘整体下移一行
        # 每行总宽均为 22.5u（去掉旧扩展列的空隙后收紧，按键等比加宽填满窗口）
        _G = 0.25  # 功能区之间的间隔
        self.LAYOUT_108 = [
            # 第1行：ESC + F区 + PrtSc/ScrLk/Pause + 媒体键横排（小键盘上方）
            [('esc','ESC',1),(None,'',2/3),
             ('f1','F1',1),('f2','F2',1),('f3','F3',1),('f4','F4',1),(None,'',2/3),
             ('f5','F5',1),('f6','F6',1),('f7','F7',1),('f8','F8',1),(None,'',2/3),
             ('f9','F9',1),('f10','F10',1),('f11','F11',1),('f12','F12',1),
             (None,'',_G),
             ('prtsc','PrtSc',1),('scrlock','ScrLk',1),('pause','Pause',1),
             (None,'',_G),
             ('mute','MUTE',1),('vol-','VOL-',1),('vol+','VOL+',1),('f13','F13',1)],
            # 第2行：数字行 + Ins/Home/PgUp + 小键盘 NumLk / * -
            [('`','~',1),('1','1',1),('2','2',1),('3','3',1),('4','4',1),('5','5',1),
             ('6','6',1),('7','7',1),('8','8',1),('9','9',1),('0','0',1),('-','-',1),
             ('=','=',1),('back','⌫',2),
             (None,'',_G),
             ('ins','INS',1),('home','HOME',1),('pgup','PGUP',1),
             (None,'',_G),
             ('numlock','NumLk',1),('n/','/',1),('n*','*',1),('n-','-',1)],
            # 第3行：Tab行 + Del/End/PgDn + 小键盘 789+（+ 跨两行）
            [('tab','TAB',1.5),('q','Q',1),('w','W',1),('e','E',1),('r','R',1),
             ('t','T',1),('y','Y',1),('u','U',1),('i','I',1),('o','O',1),
             ('p','P',1),('[','[',1),(']',']',1),('\\','\\',1.5),
             (None,'',_G),
             ('del','DEL',1),('end','END',1),('pgdn','PGDN',1),
             (None,'',_G),
             ('n7','7',1),('n8','8',1),('n9','9',1),('n+','+',1)],
            # 第4行：Caps行 + 空位 + 小键盘 456
            [('caps','CAPS',1.75),('a','A',1),('s','S',1),('d','D',1),('f','F',1),
             ('g','G',1),('h','H',1),('j','J',1),('k','K',1),('l','L',1),
             (';',';',1),("'","'",1),('enter','⏎',2.25),
             (None,'',3.5),
             ('n4','4',1),('n5','5',1),('n6','6',1),(None,'',1)],
            # 第5行：Shift行 + ↑ + 小键盘 123 Enter（Enter 跨两行）
            [('shift','⇧SHIFT',2.25),('z','Z',1),('x','X',1),('c','C',1),('v','V',1),
             ('b','B',1),('n','N',1),('m','M',1),(',',',',1),('.','.', 1),
             ('/','/',1),('rshift','SHIFT⇧',2.75),
             (None,'',_G),
             (None,'',1),('up','▲',1),(None,'',1),
             (None,'',_G),
             ('n1','1',1),('n2','2',1),('n3','3',1),('nenter','⏎',1)],
            # 第6行：底行（含右修饰键）+ 方向键 + 小键盘 0.
            [('ctrl','CTRL',1.25),('win','WIN',1.25),('alt','ALT',1.25),
             ('space','',6.25),('ralt','ALT',1.25),('rwin','WIN',1.25),
             ('menu','FN',1.25),('rctrl','CTRL',1.25),
             (None,'',_G),('left','◀',1),('down','▼',1),('right','▶',1),
             (None,'',_G),
             ('n0','0',2),('n.','.',1),(None,'',1)]
        ]
        # 经典布局：原版 6 行（无小键盘/导航区/媒体键/右修饰键），每行 15u
        self.LAYOUT_CLASSIC = [
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
             ('space','',6.25),('left','◀',1.25),
             ('up','▲',1.25),('down','▼',1.25),('right','▶',1.25)]
        ]
        self.use_classic_layout = False

        # 绝对定位：按每行起始宽度单位直接摆放，保证小键盘/导航区跨行严格对齐
        # (None, '', w) 为占位间隔，不生成控件
        self._key_geom = {}  # rk -> (行号, 起始单位, 宽度单位)
        self._build_keyboard()

        self.main_layout.addWidget(self.kb_container)

        # ★ 调试信息行：显示最近按下按键的 键码/关联音效/播放结果，5 秒无操作自动还原
        self.lbl_debug = QLabel()
        self.lbl_debug.setObjectName("DBG")
        self.lbl_debug.setAlignment(Qt.AlignCenter)
        _fd = QFont("Microsoft YaHei"); _fd.setPixelSize(12); _fd.setBold(True)
        self.lbl_debug.setFont(_fd)
        self._debug_full = ''
        self._debug_color = '#8a8a8a'
        self._debug_timer = QTimer(self)
        self._debug_timer.setSingleShot(True)
        self._debug_timer.timeout.connect(self._debug_idle)
        self._debug_idle()
        self.main_layout.addWidget(self.lbl_debug)

        self.update_scale(self.base_size)

    def _build_keyboard(self):
        """按当前布局重建键盘按钮（108 键变体 / 原版经典 6 行）"""
        for btn in self.buttons.values():
            btn.setParent(None); btn.deleteLater()
        self.buttons.clear(); self._key_geom.clear(); self._press_ts.clear()
        rows = self.LAYOUT_CLASSIC if self.use_classic_layout else self.LAYOUT_108
        for ri, row in enumerate(rows):
            pos = 0.0
            for rk, dt, wm in row:
                if rk is not None:
                    btn = QPushButton(dt, self.kb_container)
                    btn.show()  # 切换布局时父容器已可见，新控件必须显式 show 才会显示
                    btn.setProperty("width_mult", wm)
                    btn.setProperty("is_pressed", False)
                    btn.setFocusPolicy(Qt.NoFocus)
                    self.buttons[rk] = btn
                    self._key_geom[rk] = (ri, pos, wm)
                    # ★ 用 pressed/released 实现完整按下-释放体验
                    btn.pressed.connect(lambda k=rk: self._vk_press(k))
                    btn.released.connect(lambda k=rk: self._vk_release(k))
                pos += wm
        self._total_units = pos  # 各行单位总数一致
        self._n_rows = len(rows)
        # 跨行键：108 布局中小键盘 + / Enter 占两行高度（真实键盘造型）
        self._row_span = {} if self.use_classic_layout else {'n+': 2, 'nenter': 2}

    def toggle_layout(self):
        """经典 6 行 / 108 键布局切换"""
        self.use_classic_layout = not self.use_classic_layout
        self._build_keyboard()
        self.update_scale(self.base_size)
        self._update_layout_btn()

    def _update_layout_btn(self):
        if self.use_classic_layout:
            self.btn_layout.setText("108")
            self.btn_layout.setToolTip("当前：经典 6 行布局，点击切换为 108 键布局")
        else:
            self.btn_layout.setText("经典")
            self.btn_layout.setToolTip("当前：108 键布局，点击切换为经典 6 行布局")

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
        self.mouse_pressed_keys.add(key)  # 长按（如 VOL+）期间不被卡键清理熄灭
        self._set_key_light(key, True)
        # 播放音效（返回值用于下方调试行）
        self._show_key_debug(key, self.audio.play_key(key))
        self._update_indicators()

    def _vk_release(self, key):
        """鼠标释放虚拟按键"""
        self.mouse_pressed_keys.discard(key)
        self._set_key_light(key, False)
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

    def _set_key_light(self, key, on):
        """点亮/熄灭按键；熄灭时保证最少亮 200ms。
        媒体键（如音量键）常为脉冲式 down+up，几乎同时到达，不保底可见时长则按下效果肉眼不可见"""
        btn = self.buttons.get(key)
        if not btn: return
        if on:
            self._press_ts[key] = time.time()
            btn.setProperty("is_pressed", True)
            self._style_btn(btn, True)
            return
        ts = self._press_ts.get(key)
        remain = 0.2 - (time.time() - ts) if ts else 0.0
        if remain > 0:
            QTimer.singleShot(int(remain * 1000), lambda: self._light_off(key, ts))
        else:
            self._light_off(key, ts)

    def _light_off(self, key, ts):
        if ts is not None and self._press_ts.get(key) != ts:
            return  # 延迟期间又被按下，交给新一次释放处理
        self._press_ts.pop(key, None)
        btn = self.buttons.get(key)
        if btn:
            btn.setProperty("is_pressed", False)
            self._style_btn(btn, False)

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
        self.btn_hide.setStyleSheet(f"background-color:rgba(30,30,30,200);color:{self.theme_color};border:1px solid {self.theme_color};border-radius:5px;font-weight:bold;")
        self.btn_layout.setStyleSheet(f"background-color:rgba(30,30,30,200);color:{self.theme_color};border:1px solid {self.theme_color};border-radius:3px;")
        for btn in self.buttons.values():
            self._style_btn(btn, btn.property("is_pressed"))
        self._update_indicators()
        self._update_mod_styles()

    def update_scale(self, sz):
        self.base_size = sz
        gap = max(2, int(sz*0.10))    # 键间隙
        vs = max(2, int(sz*0.12))     # 行距
        unit = int(18.0*sz) / self._total_units  # 18.0 = 键盘总宽系数（宽度较初版 +20%）
        if self.use_classic_layout:
            unit = sz  # 经典布局按标准键帽尺寸排布（1u = 键帽尺寸），还原原版比例
        M = 10  # 容器内边距
        for rk, (ri, su, wm) in self._key_geom.items():
            btn = self.buttons[rk]
            x0 = M + round(unit*su); x1 = M + round(unit*(su+wm))
            y = M + ri*(sz+vs)
            span = self._row_span.get(rk, 1)
            h = span*sz + (span-1)*vs
            btn.setGeometry(x0 + gap//2, y, max(1, (x1-x0) - gap), h)
            # 字号随标签长度自动收缩，避免小键帽文字被裁切
            f = QFont("Arial"); f.setBold(True); f.setPixelSize(max(6, int(unit*0.34)))
            while f.pixelSize() > 6 and QFontMetrics(f).horizontalAdvance(btn.text()) > (x1-x0) - gap - 4:
                f.setPixelSize(f.pixelSize()-1)
            btn.setFont(f)
        self.kb_container.setFixedSize(
            M*2 + round(unit*self._total_units),
            M*2 + self._n_rows*sz + (self._n_rows-1)*vs)
        self.apply_styles(); self.adjustSize()
        self._save_settings()

    def update_opacity(self, v): self.setWindowOpacity(v/100.0); self._save_settings()

    def change_theme(self, idx):
        cs=["#FF8C00","#00FF00","#00FFFF","#AA00FF","#FF3333"]
        if 0<=idx<len(cs):
            self.theme_color=cs[idx]; self.apply_styles()
            if hasattr(self,'settings_dialog'): self.settings_dialog.update_theme(self.theme_color)
            self._save_settings()

    def open_settings(self): self.settings_dialog.show(); self.settings_dialog.raise_()
    def toggle_vis(self): self.hide() if self.isVisible() else self.show()
    def quit_app(self): self._save_settings(); self.raw_hook.stop(); QApplication.quit()

    def mousePressEvent(self, e):
        if e.button()==Qt.LeftButton: self._drag_pos=e.globalPos()-self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons()==Qt.LeftButton and self._drag_pos: self.move(e.globalPos()-self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos=None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # 窗口宽度变化（如调整尺寸滑块）后，按新宽度重新截断调试行文本
        if hasattr(self, 'lbl_debug'):
            self._set_debug_text(self._debug_full, self._debug_color)

    def start_keyboard_hook(self):
        self.raw_hook = RawKeyHook()
        def on_raw(key, down):
            if hasattr(self, 'settings_dialog') and self.settings_dialog.is_editing:
                return  # 按键捕获期间由捕获对话框自行监听
            if down:
                if key not in self.pressed_keys:
                    self.pressed_keys.add(key); self.key_sig.pressed.emit(key)
            else:
                self.pressed_keys.discard(key); self.key_sig.released.emit(key)
        self.raw_hook.add_listener(on_raw)
        self.raw_hook.start()

    def _cleanup_stuck(self):
        for k,b in self.buttons.items():
            if b.property("is_pressed") and k not in self.pressed_keys and k not in self.mouse_pressed_keys:
                b.setProperty("is_pressed",False); self._style_btn(b,False); self._press_ts.pop(k, None)

    def on_key_pressed(self, key):
        self._set_key_light(key, True)
        self._show_key_debug(key, self.audio.play_key(key))
        self._update_indicators()

    def on_key_released(self, key):
        self._set_key_light(key, False)
        self.audio.release_key(key)
        self.pressed_keys.discard(key)

    # ===================== 按键调试行 =====================
    def _debug_idle(self):
        """无按键时的占位提示（保持行高稳定）"""
        self._set_debug_text("调试 · 按下任意键显示：键码 / 音效 / 播放状态", "#8a8a8a")

    def _set_debug_text(self, text, color):
        """更新调试行；过长的音效名按当前宽度截断，避免撑破窗口"""
        self._debug_full, self._debug_color = text, color
        if not hasattr(self, 'lbl_debug'):
            return
        shown = text
        w = self.lbl_debug.contentsRect().width() - 16
        if text and w > 40:
            fm = QFontMetrics(self.lbl_debug.font())
            shown = fm.elidedText(text, Qt.ElideRight, w)
        self.lbl_debug.setText(shown)
        self.lbl_debug.setStyleSheet(
            f"QLabel#DBG{{background-color:rgba(10,10,10,200);color:{color};"
            f"border:1px solid #444;border-radius:4px;padding:2px 8px;}}")

    def _show_key_debug(self, key, result):
        """按键按下后刷新调试行：键码 | 关联音效 | 是否正常播放，最多显示 5 秒"""
        ok, snd, detail = result
        vk = _NAME_TO_VK.get(key) or VK_MAP.get(key)
        code = f"{key}(VK 0x{vk:02X})" if vk else key
        self._set_debug_text(
            f"键码 {code} ｜ 音效 {snd or '—'} ｜ {'✔' if ok else '✘'} {detail}",
            "#8dff8d" if ok else "#ff7d7d")
        self._debug_timer.start(5000)


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)
    window = VirtualKeyboardApp()
    window.show()
    sys.exit(app.exec_())
# 音效键盘 (SoundKeyboard)

## 作者：[@依然匹萨吧](https://space.bilibili.com/6297797)

## 功能介绍

**[介绍视频](https://www.bilibili.com/video/BV1ArQZBwE27)**

**音效键盘** 是一款基于 PyQt5 开发的桌面按键音效反馈工具。它可以为你在敲击键盘时播放自定义的音频，支持丰富的按键映射规则，并自带多种趣味音效变调功能，让你的每一次打字都充满乐趣。

### 1. 基础功能
- **自定义按键音效**：支持为每一个按键独立绑定音频文件，按下按键时自动播放对应音效，兼容 mp3、ogg、wav、flac 等常见格式。
- **预设包支持**：支持一键导入和自定义音效包(包含音频文件和规则集文件的文件夹)，快速应用成套的音效配置。

### 2. 特色音效模式
- **水牛音（低八度）**：按下 `CapsLock`（大小写锁定键），可开启音频的低八度变调效果。
- **倒放音效**：按下 `Shift` 键，可开启按键音效的倒放效果。
- **演奏模式**：开启该模式后，通过按下特定的按键（如 A, S, D, F 等），可像弹钢琴一样触发不同音高的音效（需当前音效包内提供对应的 `key.mp3/wav/ogg/flac` 音频文件）。

### 3. 可视化界面与自定义
- **界面外观设置**：支持自由修改主题色（橙色、绿色、蓝色）、界面尺寸缩放（20%~70%）以及窗口不透明度。
- **可视化规则编辑**：内置按键捕获机制，双击即可轻松绑定按键与音频文件，无需手动编写配置文件。
- **系统托盘驻留**：支持最小化至系统托盘，不占用任务栏空间，随时可以唤出设置或进行隐藏。

## 文件说明

```text
├── main.py                       # 主程序入口
├── build.spec                    # PyInstaller 打包配置（Windows）
├── requirements.txt              # Python 依赖列表
├── rule.example.json             # 示例规则映射配置文件
├── run.bat                       # Windows 快速启动脚本
├── run.command                   # macOS 快速启动脚本
├── README.md                     # README 文件
└── LICENSE                       # 许可证文件
```

> **注意**：程序首次运行或保存配置时，会自动在同目录下生成默认音效包文件夹以保存你的自定义设置。

## 环境要求

- **操作系统**: Windows 7/10/11（推荐 Windows 10/11）、macOS 12 或更高版本
- **Python**: 3.10 或更高版本 (若使用源码运行)
- **底层依赖**:
  - Windows: 使用 Win32 API 和 `keyboard` 进行前台窗口恢复、全局按键监听与按键模拟。
  - macOS: 使用 Quartz Event Tap 进行全局按键监听，使用 `pynput` 模拟按键，并通过 PyObjC/AppKit 尝试恢复前台应用。

## 快速开始

### 运行发布版本（EXE）
下载最新版本的 `.exe` 和音效包压缩包，解压音效包后把文件夹和 `.exe` 放到同目录下双击运行主程序即可。

> `.exe` 发布版本仅适用于 Windows。macOS 请使用源码运行，或自行用 PyInstaller 打包 `.app`。

### 从源码运行

#### Windows

**方法一：**
在 Windows 环境下，直接双击运行项目目录中的 [`run.bat`](run.bat)。

**方法二：手动命令行运行**

1. **克隆或下载项目**
   
   ```bash
   git clone https://github.com/PizzaDark/SoundKeyboard.git
   cd SoundKeyboard
   ```
   
2. **安装依赖**

   ```bash
   # 推荐使用 Python 3.10+
   python -m venv .venv
   .venv\Scripts\activate # Windows
   
   pip install -r requirements.txt
   ```

3. **运行程序**

   ```bash
   python main.py
   ```

#### macOS

**方法一：**
在 macOS 环境下，直接双击运行项目目录中的 [`run.command`](run.command)。

如果系统提示无法打开，先在终端中执行一次：

   ```bash
   chmod +x run.command
   ```

**方法二：手动命令行运行**

1. **克隆或下载项目**

   ```bash
   git clone https://github.com/PizzaDark/SoundKeyboard.git
   cd SoundKeyboard
   ```

2. **安装依赖**

   ```bash
   # 推荐使用 Python 3.10+
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **授予系统权限**

   首次运行前，打开 macOS 的 **系统设置 > 隐私与安全性**，给当前启动程序的应用授予权限。

   - 双击 `run.command` 启动时，通常需要给 **Terminal** 授权。
   - 从 iTerm2、Trae、Cursor、VS Code 等工具里启动时，需要给对应工具授权。
   - 这不是每次都要重新授权；macOS 会按“实际启动程序”分别记录权限。换一种启动方式时，需要给新的启动程序授权一次。

   需要开启的权限：

   - **辅助功能**
   - **输入监控**

   程序启动时也会主动检测权限并弹出提示。开启权限后，请完全退出程序和启动它的终端/编辑器，再重新打开。

4. **运行程序**

   ```bash
   python main.py
   ```

##### macOS 已知差异

- macOS 的系统安全策略会限制全局键盘监听和模拟输入，必须授予“辅助功能”和“输入监控”权限。
- macOS 版本中，虚拟键盘上的 `CAPS` 按钮只切换软件内的 OCT 音效模式，不额外切换系统 Caps Lock 状态。
- 点击虚拟键盘时，程序会尝试把输入发送回之前的前台 App；如果目标 App 或系统权限拦截，可能只播放音效而不输入字符。
- 菜单栏托盘行为由 Qt 和 macOS 系统共同控制，和 Windows 系统托盘表现可能略有不同。

## 音效包与规则配置指南

本软件使用“音效包”文件夹的形式来管理音效。一个标准的音效包文件夹内包含你所需要的音频文件，并在根目录包含一个 `rule.json` 文件：

- 程序启动时会优先自动查找并加载 `sound` 目录中的音效包，支持以下目录结构：

  ```text
  SoundKeyboard/
  ├── main.py
  └── sound/
      ├── default/
      │   ├── rule.json
      │   ├── key.mp3
      │   └── ...
      └── another-pack/
          └── rule.json
  ```

- `sound` 目录既可以放在项目内部，也可以放在项目同级目录。程序会扫描其中包含 `rule.json` 的子目录。
- 如果发现多个音效包，首次启动按目录名称排序选择一个；之后会记住你在“当前音效包”里选择的音效包，不会在下次启动时自动覆盖。
- 你可以在设置面板的 **音效与模式** 中通过“当前音效包”下拉框切换音效包。
- 你可以在软件的“音效自定义”界面中点击 **+添加**，双击捕获按键并选择本地音频文件。
- 点击 **保存** 后，程序会自动生成或更新当前挂载的音效包的 `rule.json`。
- 点击设置面板的 **导入音效包** 可以选择“音效包文件夹”，也可以直接选择 `rule.json`。macOS 的文件夹选择弹窗不会让你选中 JSON 文件，如果要导入 JSON，请使用菜单里的“选择 rule.json”。

## 构建可执行文件

本项目支持使用 PyInstaller 打包为独立的 Windows 桌面程序：

```bash
pyinstaller build.spec
```

打包完成后，独立的 `.exe` 程序及相关依赖将生成在 `dist/` 目录下。

macOS 如需打包，可先确认源码运行正常，再参考 PyInstaller 的 macOS 打包方式创建 `.app`；当前仓库内的 `build.spec` 主要面向 Windows。

## 依赖库

| 依赖包 | 用途 |
|--------|------|
| PyQt5 | GUI 桌面界面与设置面板的构建交互 |
| pygame | 高性能的音频混音器与按键音效播放引擎 |
| numpy | 用于底层音频数据的矩阵处理、变调计算及倒放生成 |
| keyboard | Windows/Linux 全局键盘事件的底层捕获与注入回调 |
| pynput | macOS 按键模拟 |
| pyobjc-framework-Cocoa | macOS Quartz 键盘监听、权限检测与前台应用恢复 |

## 声明与开源许可证

**声明：本软件免费且非官方，禁止商用贩卖，使用代表同意自行承担所有后果。**

本项目采用 **[知识共享 署名 - 非商业性使用 - 相同方式共享 4.0 国际许可证 (CC BY-NC-SA 4.0)](LICENSE)** 授权。

### 核心条款说明

1. **允许的行为**：你可以自由复制、修改、分发本项目的代码 / 程序，前提是满足以下条件；
2. **禁止的行为**：严禁将本项目（包括修改后的衍生版本）用于任何商业目的（如出售、付费分发、商业运营等）；
3. **必须遵守**：
   - **署名**：必须保留原作者信息（[@依然匹萨吧](https://space.bilibili.com/6297797)）；
   - **相同方式共享**：若你修改 / 衍生本项目，必须采用与本协议相同的许可证发布。

请查看官方协议全文：https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh-hans

本项目仅供学习交流使用，禁止商用或贩卖。

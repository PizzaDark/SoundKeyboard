#!/bin/bash

set -e

PROJECT_NAME="SoundKeyboard"
GITHUB_USER="PizzaDark"
GITHUB_REPO="$PROJECT_NAME"
REPO_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO.git"
REPO_ZIP_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO/archive/refs/heads/main.zip"
REPO_DIR="$PROJECT_NAME"

cd "$(dirname "$0")"

clear
echo "========================================"
echo "  自动安装脚本"
echo "========================================"
echo

echo "[1/5] 正在检查 Python 环境..."
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        version="$($candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
        major="${version%%.*}"
        minor="${version#*.}"
        if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; }; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[错误] 未检测到 Python 3.10 或更高版本！"
    echo
    echo "请从以下链接下载并安装 Python 3.10 或更高版本："
    echo "https://www.python.org/downloads/"
    echo
    read -n 1 -s -r -p "按任意键退出..."
    echo
    exit 1
fi

echo "检测到 Python: $($PYTHON_BIN --version)"
echo "[✓] Python 版本符合要求 (需要 3.10+)"
echo

echo "[2/5] 正在检查 Git 环境..."
if ! command -v git >/dev/null 2>&1; then
    echo "[提示] 未检测到 Git 环境"
    echo
    echo "您可以手动从 GitHub 下载 ZIP 压缩包并解压："
    echo "$REPO_ZIP_URL"
    echo
    echo "如果您已经手动下载并解压了源代码，请继续。"
else
    echo "[✓] Git 环境正常"
fi

current_dir="$(basename "$PWD")"
if [ "$current_dir" = "$PROJECT_NAME" ] || [ -f "main.py" ]; then
    echo "[提示] 当前已在项目目录中，跳过克隆步骤"
elif [ -d "$REPO_DIR" ] && [ -f "$REPO_DIR/main.py" ]; then
    cd "$REPO_DIR"
    echo "[✓] 已进入项目目录: $REPO_DIR"
elif command -v git >/dev/null 2>&1; then
    retries=3
    count=1
    while [ "$count" -le "$retries" ]; do
        echo "正在尝试克隆仓库 (尝试 $count/$retries)..."
        if git clone "$REPO_URL"; then
            echo "[✓] 克隆成功"
            cd "$REPO_DIR"
            break
        fi
        if [ "$count" -lt "$retries" ]; then
            echo "等待 2 秒后重试..."
            sleep 2
        fi
        count=$((count + 1))
    done

    if [ "$count" -gt "$retries" ]; then
        echo "[错误] Git 克隆失败，请手动下载："
        echo "$REPO_ZIP_URL"
        read -n 1 -s -r -p "按任意键退出..."
        echo
        exit 1
    fi
else
    echo "[错误] 未找到 main.py，也无法自动克隆项目。"
    read -n 1 -s -r -p "按任意键退出..."
    echo
    exit 1
fi
echo

echo "[3/5] 正在检查/创建虚拟环境..."
if [ -d ".venv" ]; then
    echo "[提示] 检测到现有虚拟环境"
else
    echo "正在创建虚拟环境..."
    "$PYTHON_BIN" -m venv .venv
    echo "[✓] 虚拟环境创建成功"
fi
echo

echo "[4/5] 正在激活虚拟环境..."
source .venv/bin/activate
echo "[✓] 虚拟环境已激活"
echo "当前 Python: $(command -v python)"
echo

echo "[5/5] 正在安装/更新依赖包..."
if [ ! -f "requirements.txt" ]; then
    echo "[警告] 未找到 requirements.txt 文件！"
    echo "将尝试直接运行程序..."
else
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo "[✓] 依赖安装完成"
fi
echo

echo "========================================"
echo "  macOS 权限提示"
echo "========================================"
echo "如需全局键盘监听和模拟输入，请在："
echo "系统设置 > 隐私与安全性"
echo "为本次启动它的应用开启「辅助功能」和「输入监控」。"
echo
echo "如果双击 run.command 启动，通常需要授权 Terminal。"
echo "如果从 Trae / VS Code / Cursor / iTerm2 启动，需要授权对应应用。"
echo
python - <<'PY'
try:
    import ApplicationServices
    ax = ApplicationServices.AXIsProcessTrusted()
    listen = ApplicationServices.CGPreflightListenEventAccess()
    print(f"当前权限状态: 辅助功能={ax}, 输入监控={listen}")
except Exception as e:
    print(f"当前权限状态检查失败: {e}")
PY
echo

echo "========================================"
echo "  环境准备完成，正在启动程序..."
echo "========================================"
echo

if [ ! -f "main.py" ]; then
    echo "[错误] 未找到 main.py 文件！"
    echo "请确保您在正确的项目目录中运行此脚本。"
    read -n 1 -s -r -p "按任意键退出..."
    echo
    exit 1
fi

python main.py

echo
echo "========================================"
echo "  程序已退出"
echo "========================================"
read -n 1 -s -r -p "按任意键关闭窗口..."
echo

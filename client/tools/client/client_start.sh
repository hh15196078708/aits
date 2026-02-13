#!/bin/bash
# =============================================================================
# 跨平台Python客户端 - Linux/macOS启动脚本
# =============================================================================
# 
# 功能:
#   1. 检查Python环境
#   2. 自动安装依赖
#   3. 设置UTF-8编码
#   4. 启动客户端程序
#
# 兼容系统:
#   - Linux: Ubuntu, CentOS, Debian, Fedora, openSUSE
#   - 国产Linux: 统信UOS, 银河麒麟, 中标麒麟, 深度Linux
#   - macOS: 10.14+ (Intel/Apple Silicon)
#
# 使用方法:
#   chmod +x client_start.sh
#   ./client_start.sh
# =============================================================================

# 设置UTF-8编码
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

# 切换到脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示启动信息
echo "============================================================================="
echo "               跨平台Python客户端 - Linux/macOS"
echo "============================================================================="
echo ""

# -----------------------------------------------------------------------------
# 步骤1: 检测操作系统
# -----------------------------------------------------------------------------
print_info "检测操作系统..."

OS_TYPE="unknown"
OS_NAME="Unknown"

if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
    OS_NAME="macOS $(sw_vers -productVersion 2>/dev/null || echo 'Unknown')"
    
    # 检测架构（Intel/Apple Silicon）
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        OS_NAME="$OS_NAME (Apple Silicon)"
    else
        OS_NAME="$OS_NAME (Intel)"
    fi
elif [[ "$OSTYPE" == "linux"* ]]; then
    OS_TYPE="linux"
    
    # 检测Linux发行版
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME="$NAME $VERSION"
        
        # 检测国产Linux
        if [[ "$ID" == "uos" ]] || [[ "$NAME" == *"UOS"* ]] || [[ "$NAME" == *"Uniontech"* ]]; then
            print_info "检测到国产Linux: 统信UOS"
        elif [[ "$ID" == "kylin" ]] || [[ "$NAME" == *"Kylin"* ]]; then
            print_info "检测到国产Linux: 银河麒麟"
        elif [[ "$ID" == "neokylin" ]]; then
            print_info "检测到国产Linux: 中标麒麟"
        elif [[ "$ID" == "deepin" ]]; then
            print_info "检测到国产Linux: 深度Linux"
        fi
    else
        OS_NAME="Linux $(uname -r)"
    fi
fi

print_info "操作系统: $OS_NAME"
echo ""

# -----------------------------------------------------------------------------
# 步骤2: 检查Python环境
# -----------------------------------------------------------------------------
print_info "[1/4] 检查Python环境..."

PYTHON_CMD=""

# 检测Python命令
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        # 检查版本是否>=3.6
        version=$($cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        major=$(echo $version | cut -d. -f1)
        minor=$(echo $version | cut -d. -f2)
        
        if [[ "$major" -ge 3 ]] && [[ "$minor" -ge 6 ]]; then
            PYTHON_CMD=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    print_error "未找到Python 3.6或更高版本"
    echo ""
    echo "请安装Python 3.6+:"
    if [[ "$OS_TYPE" == "macos" ]]; then
        echo "  brew install python3"
        echo "  或从 https://www.python.org/downloads/ 下载"
    else
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
        echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
        echo "  国产Linux:    sudo apt install python3 python3-pip"
    fi
    exit 1
fi

print_info "       找到Python: $PYTHON_CMD"
print_info "       版本: $($PYTHON_CMD --version 2>&1)"
echo ""

# -----------------------------------------------------------------------------
# 步骤3: 检查并安装依赖
# -----------------------------------------------------------------------------
print_info "[2/4] 检查并安装依赖..."

# 检查pip
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    print_warn "pip未安装，尝试安装..."
    if [[ "$OS_TYPE" == "macos" ]]; then
        $PYTHON_CMD -m ensurepip --default-pip 2>/dev/null || true
    else
        # Linux
        if command -v apt &> /dev/null; then
            sudo apt install -y python3-pip 2>/dev/null || true
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-pip 2>/dev/null || true
        fi
    fi
fi

# 升级pip（静默）
$PYTHON_CMD -m pip install --upgrade pip -q 2>/dev/null || true

# 安装依赖
print_info "       安装Python依赖..."
$PYTHON_CMD -m pip install -r requirements.txt -q 2>/dev/null

if [ $? -ne 0 ]; then
    print_warn "部分依赖安装失败，尝试单独安装..."
    $PYTHON_CMD -m pip install psutil -q 2>/dev/null || true
    $PYTHON_CMD -m pip install pycryptodome -q 2>/dev/null || true
    $PYTHON_CMD -m pip install requests -q 2>/dev/null || true
fi

print_info "       依赖安装完成"
echo ""

# -----------------------------------------------------------------------------
# 步骤4: 国产Linux专属检查
# -----------------------------------------------------------------------------
if [[ "$OS_TYPE" == "linux" ]]; then
    print_info "[3/4] 检查系统工具..."
    
    # 检查dmidecode（用于获取机器码）
    if ! command -v dmidecode &> /dev/null; then
        print_warn "dmidecode未安装，部分硬件信息可能无法获取"
        echo ""
        echo "建议安装dmidecode以获取完整的机器码:"
        if command -v apt &> /dev/null; then
            echo "  sudo apt install dmidecode"
        elif command -v yum &> /dev/null; then
            echo "  sudo yum install dmidecode"
        fi
        echo ""
    else
        print_info "       dmidecode已安装"
    fi
else
    print_info "[3/4] macOS无需额外系统工具"
fi
echo ""

# -----------------------------------------------------------------------------
# 步骤5: 启动客户端
# -----------------------------------------------------------------------------
print_info "[4/4] 启动客户端..."
echo "============================================================================="
echo ""

# 启动主程序
$PYTHON_CMD main.py

# 显示退出信息
echo ""
echo "============================================================================="
echo "客户端已退出"
echo "============================================================================="

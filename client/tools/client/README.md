# 跨平台Python客户端

跨平台机器注册、心跳检测、授权管理客户端，支持Windows/Linux/macOS及国产操作系统。

## 兼容系统清单

### Windows
- Windows 7/8/10/11（32位/64位）
- Windows Server 2016/2019/2022

### Linux
- **通用发行版**: Ubuntu 18.04+、CentOS 7+、Debian 10+、Fedora 34+、openSUSE 15+
- **国产发行版**: 统信UOS、银河麒麟V10、中标麒麟、深度Linux

### macOS
- macOS 10.14+ (Mojave及以上)
- 支持Intel和Apple Silicon (M1/M2/M3)

## 目录结构

```
client/
├── adapters/                    # 系统适配器（硬件采集）
│   ├── __init__.py
│   ├── win_collector.py         # Windows硬件采集
│   ├── linux_collector.py       # Linux硬件采集（含国产Linux）
│   └── mac_collector.py         # macOS硬件采集
├── config_manager.py            # 配置文件管理
├── hardware_collector.py        # 硬件采集统一入口
├── network_client.py            # 网络通信客户端
├── auth_manager.py              # 授权管理
├── logger.py                    # 日志管理
├── system_adapter.py            # 系统类型检测与适配
├── crypto_utils.py              # AES加密工具
├── resource_monitor.py          # 资源监控
├── main.py                      # 程序入口
├── utils.py                     # 通用工具函数
├── constants.py                 # 常量定义
├── requirements.txt             # 依赖清单
├── client_start.bat             # Windows启动脚本
├── client_start.sh              # Linux/macOS启动脚本
└── README.md                    # 本文档
```

## 快速开始

### Windows

1. **安装Python**: 下载并安装 [Python 3.6+](https://www.python.org/downloads/)
2. **双击运行**: `client_start.bat`

或手动安装依赖并启动:
```batch
pip install -r requirements.txt
pip install pywin32 wmi
python main.py
```

### Linux/macOS

1. **添加执行权限**:
```bash
chmod +x client_start.sh
```

2. **运行启动脚本**:
```bash
./client_start.sh
```

或手动安装依赖并启动:
```bash
pip3 install -r requirements.txt
python3 main.py
```

### 国产Linux

与标准Linux相同，额外建议安装dmidecode以获取完整机器码:
```bash
# 统信UOS/银河麒麟/深度Linux
sudo apt install dmidecode

# 中标麒麟
sudo yum install dmidecode
```

## 配置项修改

编辑 `constants.py` 修改以下配置:

```python
# 服务端地址
SERVER_URL = "http://127.0.0.1:8080/api"

# 心跳间隔（秒）
HEARTBEAT_INTERVAL = 15

# 请求超时（秒）
REQUEST_TIMEOUT = 3

# 离线宽限期（秒）
OFFLINE_GRACE_PERIOD = 600
```

## 配置文件位置

| 系统 | 配置目录 | 日志目录 |
|------|----------|----------|
| Windows | `%APPDATA%\client_config\` | `%TEMP%\client_logs\` |
| Linux | `~/.client_config/` | `/var/log/client/` 或 `~/.client_logs/` |
| macOS | `~/.client_config/` | `~/Library/Logs/client/` |

## 资源占用

| 资源类型 | 峰值限制 | 平均限制 |
|----------|----------|----------|
| CPU | ≤8% | ≤5% |
| 内存 | ≤300MB | ≤100MB |
| 磁盘IO | ≤10MB/s | ≤1MB/s |

程序内置资源监控，超限时自动节流。

## 授权到期测试

1. **模拟服务端返回expired状态**: 修改服务端心跳响应中的 `auth_status` 为 `expired`
2. **观察客户端行为**: 客户端收到expired后会优雅退出
3. **重启验证**: 重启客户端后会提示"授权已到期"并退出

## 常见问题排查

### 1. Windows: pywin32安装失败

```batch
pip install pywin32 --no-cache-dir
python Scripts\pywin32_postinstall.py -install
```

### 2. Linux: 权限不足无法获取机器码

确保安装dmidecode并有权限运行:
```bash
sudo dmidecode -s baseboard-serial-number
```

或程序会自动使用 `/etc/machine-id` 作为兜底。

### 3. macOS: 无法获取序列号

确保终端有权限访问硬件信息:
```bash
ioreg -l | grep IOPlatformSerialNumber
```

### 4. 心跳失败/网络超时

1. 检查服务端地址是否正确
2. 检查网络连通性
3. 检查防火墙设置
4. 离线状态下程序会在10分钟内正常运行

### 5. 中文乱码

Windows用户确保:
- 控制台使用UTF-8编码
- 启动脚本会自动执行 `chcp 65001`

### 6. 国产Linux兼容性问题

- 统信UOS/银河麒麟: 已测试兼容
- 中标麒麟: 建议安装dmidecode
- 其他国产发行版: 核心功能可用，部分硬件信息可能无法采集

## 依赖说明

### 必需依赖
- `psutil>=5.9.0`: 跨平台硬件信息采集
- `pycryptodome>=3.18.0`: AES加密

### 可选依赖
- `requests>=2.28.0`: HTTP客户端（无则使用urllib兜底）

### Windows专属依赖
- `pywin32>=306`: Windows API访问
- `wmi>=1.5.1`: WMI查询

## 开发说明

### 模块依赖关系

```
main.py
  ├── system_adapter.py      # 系统检测（无依赖）
  ├── logger.py              # 日志（依赖system_adapter, constants）
  ├── config_manager.py      # 配置（依赖system_adapter, utils）
  ├── hardware_collector.py  # 硬件采集（依赖adapters/*）
  ├── crypto_utils.py        # 加密（依赖constants）
  ├── network_client.py      # 网络（依赖crypto_utils, constants）
  ├── auth_manager.py        # 授权（依赖config_manager, utils）
  └── resource_monitor.py    # 资源监控（依赖utils, constants）
```

### 添加新平台支持

1. 在 `system_adapter.py` 添加新的 `OSType` 枚举
2. 在 `adapters/` 目录下创建新的采集器
3. 在 `hardware_collector.py` 添加采集器路由
4. 更新启动脚本

## 许可证

MIT License

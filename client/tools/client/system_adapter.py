# -*- coding: utf-8 -*-
"""
模块名称: system_adapter.py
模块功能: 系统类型检测、跨平台路径适配、系统专属配置封装
依赖模块: 标准库 (os, sys, platform, subprocess)
系统适配: 
    - Windows 7/8/10/11, Windows Server 2016/2019/2022
    - Linux (Ubuntu, CentOS, Debian, Fedora, openSUSE)
    - 国产Linux (统信UOS, 银河麒麟, 中标麒麟, 深度Linux)
    - macOS 10.14+

说明:
    本模块负责：
    1. 检测当前操作系统类型和版本
    2. 提供跨平台的配置文件路径和日志路径
    3. 设置UTF-8编码（Windows强制）
    4. 检测系统是否在支持列表中
    5. 封装系统专属操作，屏蔽主逻辑对系统差异的感知
"""

import os  # 操作系统接口
import sys  # 系统相关功能
import platform  # 平台信息
import subprocess  # 子进程调用
from typing import Dict, Optional, Tuple  # 类型提示
from enum import Enum  # 枚举类型


class OSType(Enum):
    """
    操作系统类型枚举
    
    功能: 定义支持的操作系统类型常量
    """
    WINDOWS = "Windows"  # Windows系列操作系统
    LINUX = "Linux"  # Linux系列（含国产Linux）
    MACOS = "macOS"  # macOS操作系统
    UNKNOWN = "Unknown"  # 未知操作系统


class LinuxDistro(Enum):
    """
    Linux发行版枚举
    
    功能: 定义支持的Linux发行版常量
    """
    UBUNTU = "Ubuntu"  # Ubuntu
    CENTOS = "CentOS"  # CentOS
    DEBIAN = "Debian"  # Debian
    FEDORA = "Fedora"  # Fedora
    OPENSUSE = "openSUSE"  # openSUSE
    UOS = "UOS"  # 统信UOS
    KYLIN = "Kylin"  # 银河麒麟
    NEOKYLIN = "NeoKylin"  # 中标麒麟
    DEEPIN = "Deepin"  # 深度Linux
    UNKNOWN = "Unknown"  # 未知发行版


class SystemAdapter:
    """
    系统适配器类
    
    功能: 提供跨平台的系统信息获取和路径适配
    系统适配: 所有平台通用，内部根据系统类型分别处理
    """
    
    _instance = None  # 单例实例
    _initialized = False  # 初始化标志
    
    def __new__(cls):
        """
        实现单例模式
        
        功能: 确保全局只有一个SystemAdapter实例
        参数: 无
        返回值: SystemAdapter实例
        """
        if cls._instance is None:  # 如果实例不存在
            cls._instance = super().__new__(cls)  # 创建新实例
        return cls._instance  # 返回单例实例
    
    def __init__(self):
        """
        初始化系统适配器
        
        功能: 检测系统类型并初始化相关配置
        参数: 无
        返回值: 无
        异常情况: 系统不支持时不会抛出异常，但会记录状态
        """
        if SystemAdapter._initialized:  # 如果已初始化则跳过
            return
        
        self._os_type: OSType = self._detect_os_type()  # 检测操作系统类型
        self._os_version: str = self._detect_os_version()  # 检测系统版本
        self._os_arch: str = self._detect_os_arch()  # 检测系统架构
        self._kernel_version: str = self._detect_kernel_version()  # 检测内核版本
        self._linux_distro: Optional[LinuxDistro] = None  # Linux发行版
        
        if self._os_type == OSType.LINUX:  # 如果是Linux系统
            self._linux_distro = self._detect_linux_distro()  # 检测Linux发行版
        
        self._setup_encoding()  # 设置UTF-8编码
        SystemAdapter._initialized = True  # 标记已初始化
    
    def _detect_os_type(self) -> OSType:
        """
        检测操作系统类型
        
        功能: 判断当前运行的操作系统类型
        参数: 无
        返回值: OSType枚举值
        异常情况: 无
        系统适配: 使用platform.system()进行检测
        """
        system = platform.system()  # 获取系统名称（Windows/Linux/Darwin）
        if system == "Windows":  # Windows系统
            return OSType.WINDOWS
        elif system == "Linux":  # Linux系统（含国产Linux）
            return OSType.LINUX
        elif system == "Darwin":  # macOS系统
            return OSType.MACOS
        else:  # 其他未知系统
            return OSType.UNKNOWN
    
    def _detect_os_version(self) -> str:
        """
        检测操作系统版本
        
        功能: 获取操作系统的详细版本号
        参数: 无
        返回值: 版本号字符串
        异常情况: 获取失败时返回"Unknown"
        系统适配:
            - Windows: 使用platform.version()
            - Linux: 读取/etc/os-release或lsb_release
            - macOS: 使用platform.mac_ver()
        """
        try:
            if self._os_type == OSType.WINDOWS:  # Windows系统
                # 返回Windows版本号，如"10.0.19041"
                return platform.version()
            elif self._os_type == OSType.MACOS:  # macOS系统
                # 返回macOS版本号，如"10.15.7"
                mac_ver = platform.mac_ver()[0]  # 获取版本元组的第一个元素
                return mac_ver if mac_ver else "Unknown"
            elif self._os_type == OSType.LINUX:  # Linux系统
                # 尝试从/etc/os-release读取版本信息
                return self._get_linux_version()
            else:
                return "Unknown"  # 未知系统返回Unknown
        except Exception:  # 捕获所有异常
            return "Unknown"  # 异常时返回Unknown
    
    def _get_linux_version(self) -> str:
        """
        获取Linux系统版本
        
        功能: 从/etc/os-release或其他来源读取Linux版本
        参数: 无
        返回值: 版本字符串
        异常情况: 读取失败时返回platform.release()
        系统适配: Linux专用
        """
        try:
            # 尝试读取/etc/os-release文件（大多数现代Linux发行版）
            if os.path.exists("/etc/os-release"):  # 检查文件是否存在
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    content = f.read()  # 读取文件内容
                # 解析VERSION_ID或VERSION字段
                for line in content.split("\n"):  # 逐行解析
                    if line.startswith("VERSION="):  # 找到VERSION行
                        # 去除引号和前缀
                        return line.split("=", 1)[1].strip().strip('"')
                    elif line.startswith("VERSION_ID="):  # 找到VERSION_ID行
                        return line.split("=", 1)[1].strip().strip('"')
            # 兜底：返回内核版本
            return platform.release()
        except Exception:
            return platform.release()  # 异常时返回内核版本
    
    def _detect_os_arch(self) -> str:
        """
        检测操作系统架构
        
        功能: 获取系统架构（32位/64位）
        参数: 无
        返回值: "64bit"或"32bit"
        异常情况: 无
        系统适配: 所有平台通用
        """
        # 使用platform.machine()获取架构信息
        machine = platform.machine().lower()  # 获取机器类型并转小写
        # 判断是否为64位架构
        if machine in ("x86_64", "amd64", "arm64", "aarch64"):
            return "64bit"  # 64位架构
        else:
            return "32bit"  # 32位架构
    
    def _detect_kernel_version(self) -> str:
        """
        检测内核版本
        
        功能: 获取操作系统内核版本
        参数: 无
        返回值: 内核版本字符串
        异常情况: 获取失败时返回空字符串
        系统适配:
            - Windows: 返回构建版本号
            - Linux/macOS: 返回内核版本号
        """
        try:
            if self._os_type == OSType.WINDOWS:  # Windows系统
                # Windows返回构建版本号
                return platform.version()
            else:  # Linux/macOS
                # 返回内核版本
                return platform.release()
        except Exception:
            return ""  # 异常时返回空字符串
    
    def _detect_linux_distro(self) -> LinuxDistro:
        """
        检测Linux发行版
        
        功能: 识别具体的Linux发行版名称
        参数: 无
        返回值: LinuxDistro枚举值
        异常情况: 无法识别时返回UNKNOWN
        系统适配: Linux专用，支持国产Linux识别
        """
        try:
            # 读取/etc/os-release文件获取发行版信息
            distro_id = ""  # 发行版ID
            distro_name = ""  # 发行版名称
            
            if os.path.exists("/etc/os-release"):  # 检查文件是否存在
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:  # 逐行读取
                        if line.startswith("ID="):  # 发行版ID
                            distro_id = line.split("=", 1)[1].strip().strip('"').lower()
                        elif line.startswith("NAME="):  # 发行版名称
                            distro_name = line.split("=", 1)[1].strip().strip('"').lower()
            
            # 根据ID或名称匹配发行版
            if "ubuntu" in distro_id or "ubuntu" in distro_name:
                return LinuxDistro.UBUNTU
            elif "centos" in distro_id or "centos" in distro_name:
                return LinuxDistro.CENTOS
            elif "debian" in distro_id or "debian" in distro_name:
                return LinuxDistro.DEBIAN
            elif "fedora" in distro_id or "fedora" in distro_name:
                return LinuxDistro.FEDORA
            elif "opensuse" in distro_id or "suse" in distro_name:
                return LinuxDistro.OPENSUSE
            elif "uos" in distro_id or "uniontech" in distro_name:
                return LinuxDistro.UOS  # 统信UOS
            elif "kylin" in distro_id or "kylin" in distro_name:
                return LinuxDistro.KYLIN  # 银河麒麟
            elif "neokylin" in distro_id:
                return LinuxDistro.NEOKYLIN  # 中标麒麟
            elif "deepin" in distro_id or "deepin" in distro_name:
                return LinuxDistro.DEEPIN  # 深度Linux
            else:
                return LinuxDistro.UNKNOWN  # 未知发行版
        except Exception:
            return LinuxDistro.UNKNOWN  # 异常时返回未知
    
    def _setup_encoding(self) -> None:
        """
        设置UTF-8编码
        
        功能: 确保程序使用UTF-8编码，避免中文乱码
        参数: 无
        返回值: 无
        异常情况: 无
        系统适配: Windows强制设置，其他系统通常已是UTF-8
        """
        if self._os_type == OSType.WINDOWS:  # Windows系统需要强制设置
            try:
                # 设置标准输出和标准错误的编码为UTF-8
                if hasattr(sys.stdout, 'reconfigure'):  # Python 3.7+
                    sys.stdout.reconfigure(encoding='utf-8')  # 重新配置stdout编码
                    sys.stderr.reconfigure(encoding='utf-8')  # 重新配置stderr编码
                # 设置环境变量强制UTF-8
                os.environ['PYTHONIOENCODING'] = 'utf-8'  # 设置Python IO编码
            except Exception:
                pass  # 设置失败时忽略，不影响程序运行
    
    def get_config_dir(self) -> str:
        """
        获取配置文件目录路径
        
        功能: 返回当前系统对应的配置文件目录
        参数: 无
        返回值: 配置目录绝对路径
        异常情况: 目录不存在时会尝试创建
        系统适配:
            - Windows: %APPDATA%/client_config
            - Linux: ~/.client_config
            - macOS: ~/.client_config
        """
        if self._os_type == OSType.WINDOWS:  # Windows系统
            # 使用APPDATA环境变量，通常为 C:\Users\{用户名}\AppData\Roaming
            appdata = os.environ.get("APPDATA", "")  # 获取APPDATA路径
            if appdata:
                config_dir = os.path.join(appdata, "client_config")  # 拼接配置目录
            else:
                # 兜底：使用用户目录
                config_dir = os.path.join(os.path.expanduser("~"), "client_config")
        else:  # Linux/macOS
            # 使用用户主目录下的隐藏文件夹
            config_dir = os.path.join(os.path.expanduser("~"), ".client_config")
        
        return config_dir  # 返回配置目录路径
    
    def get_log_dir(self) -> str:
        """
        获取日志文件目录路径
        
        功能: 返回当前系统对应的日志目录，带权限检测和降级
        参数: 无
        返回值: 日志目录绝对路径
        异常情况: 主目录无权限时降级到用户目录
        系统适配:
            - Windows: %TEMP%/client_logs
            - Linux: /var/log/client/ (无权限时 ~/.client_logs)
            - macOS: ~/Library/Logs/client/
        """
        if self._os_type == OSType.WINDOWS:  # Windows系统
            # 使用TEMP目录
            temp_dir = os.environ.get("TEMP", "")  # 获取TEMP路径
            if temp_dir:
                log_dir = os.path.join(temp_dir, "client_logs")  # 拼接日志目录
            else:
                # 兜底：使用用户目录
                log_dir = os.path.join(os.path.expanduser("~"), "client_logs")
        elif self._os_type == OSType.MACOS:  # macOS系统
            # 使用标准日志目录
            log_dir = os.path.join(os.path.expanduser("~"), "Library", "Logs", "client")
        else:  # Linux系统（含国产Linux）
            # 优先使用/var/log/client
            primary_log_dir = "/var/log/client"
            if self._check_dir_writable(primary_log_dir):  # 检查是否有写入权限
                log_dir = primary_log_dir
            else:
                # 降级到用户目录
                log_dir = os.path.join(os.path.expanduser("~"), ".client_logs")
        
        return log_dir  # 返回日志目录路径
    
    def _check_dir_writable(self, dir_path: str) -> bool:
        """
        检查目录是否可写
        
        功能: 验证指定目录是否有写入权限
        参数:
            dir_path: 要检查的目录路径
        返回值: True表示可写，False表示不可写或不存在
        异常情况: 目录不存在时尝试创建并检查
        系统适配: 所有平台通用
        """
        try:
            # 如果目录不存在，尝试创建
            if not os.path.exists(dir_path):
                # 尝试创建目录
                os.makedirs(dir_path, exist_ok=True)
                return True  # 创建成功表示有权限
            # 目录存在，检查写入权限
            return os.access(dir_path, os.W_OK)  # 检查写入权限
        except (OSError, PermissionError):
            return False  # 无权限或创建失败
    
    def ensure_dir_exists(self, dir_path: str) -> Tuple[bool, str]:
        """
        确保目录存在并可写
        
        功能: 创建目录并验证写入权限
        参数:
            dir_path: 目录路径
        返回值: (成功标志, 错误信息)
        异常情况: 权限不足时返回False和错误信息
        系统适配: 所有平台通用
        """
        try:
            if not os.path.exists(dir_path):  # 目录不存在
                os.makedirs(dir_path, exist_ok=True)  # 递归创建目录
            
            if not os.access(dir_path, os.W_OK):  # 检查写入权限
                return False, f"目录无写入权限: {dir_path}"
            
            return True, ""  # 成功
        except PermissionError:
            return False, f"权限不足，无法创建目录: {dir_path}"
        except OSError as e:
            return False, f"创建目录失败: {dir_path}, 错误: {str(e)}"
    
    def get_hostname(self) -> str:
        """
        获取机器主机名
        
        功能: 获取系统原生主机名，不做篡改
        参数: 无
        返回值: 主机名字符串
        异常情况: 获取失败时返回"Unknown"
        系统适配:
            - Windows: hostname命令
            - Linux: hostname命令
            - macOS: scutil --get ComputerName
        """
        try:
            if self._os_type == OSType.MACOS:  # macOS使用scutil
                # 使用scutil获取ComputerName
                result = subprocess.run(
                    ["scutil", "--get", "ComputerName"],
                    capture_output=True,  # 捕获输出
                    text=True,  # 文本模式
                    timeout=5  # 超时5秒
                )
                if result.returncode == 0:  # 命令执行成功
                    hostname = result.stdout.strip()  # 获取输出并去除空白
                    if hostname:
                        return hostname
                # 兜底使用platform.node()
                return platform.node() or "Unknown"
            else:  # Windows和Linux
                # 使用hostname命令
                result = subprocess.run(
                    ["hostname"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=(self._os_type == OSType.WINDOWS)  # Windows需要shell=True
                )
                if result.returncode == 0:
                    hostname = result.stdout.strip()
                    if hostname:
                        return hostname
                # 兜底使用platform.node()
                return platform.node() or "Unknown"
        except Exception:
            # 最终兜底
            return platform.node() or "Unknown"
    
    def is_domestic_linux(self) -> bool:
        """
        检查是否为国产Linux
        
        功能: 判断当前系统是否为国产Linux发行版
        参数: 无
        返回值: True表示是国产Linux，False表示不是
        异常情况: 无
        系统适配: Linux专用
        """
        if self._os_type != OSType.LINUX:  # 非Linux系统
            return False
        # 国产Linux发行版列表
        domestic_distros = {LinuxDistro.UOS, LinuxDistro.KYLIN, 
                          LinuxDistro.NEOKYLIN, LinuxDistro.DEEPIN}
        return self._linux_distro in domestic_distros  # 检查是否在国产列表中
    
    def is_supported(self) -> Tuple[bool, str]:
        """
        检查系统是否受支持
        
        功能: 验证当前系统是否在支持列表中
        参数: 无
        返回值: (是否支持, 提示信息)
        异常情况: 无
        系统适配: 所有平台
        """
        if self._os_type == OSType.UNKNOWN:  # 未知系统
            return False, "不支持的操作系统，核心功能可能无法正常工作"
        
        if self._os_type == OSType.WINDOWS:
            # Windows版本检查（需要至少Windows 7）
            try:
                ver = platform.version()  # 获取版本号
                major = int(ver.split(".")[0])  # 提取主版本号
                if major < 6:  # Windows Vista以下
                    return False, "不支持Windows XP及更早版本"
            except Exception:
                pass  # 版本解析失败时不阻止运行
        
        return True, "系统兼容性检查通过"
    
    def get_os_info(self) -> Dict:
        """
        获取完整的操作系统信息
        
        功能: 返回包含系统所有信息的字典
        参数: 无
        返回值: 操作系统信息字典
        异常情况: 无
        系统适配: 所有平台
        """
        info = {
            "type": self._os_type.value,  # 系统类型
            "version": self._os_version,  # 系统版本
            "arch": self._os_arch,  # 系统架构
            "kernel": self._kernel_version,  # 内核版本
            "hostname": self.get_hostname(),  # 主机名
        }
        
        if self._os_type == OSType.LINUX and self._linux_distro:
            info["distro"] = self._linux_distro.value  # 添加Linux发行版信息
            info["is_domestic"] = self.is_domestic_linux()  # 是否国产Linux
        
        return info
    
    @property
    def os_type(self) -> OSType:
        """获取操作系统类型"""
        return self._os_type
    
    @property
    def os_version(self) -> str:
        """获取操作系统版本"""
        return self._os_version
    
    @property
    def os_arch(self) -> str:
        """获取操作系统架构"""
        return self._os_arch
    
    @property
    def kernel_version(self) -> str:
        """获取内核版本"""
        return self._kernel_version
    
    @property
    def linux_distro(self) -> Optional[LinuxDistro]:
        """获取Linux发行版"""
        return self._linux_distro
    
    @property
    def is_windows(self) -> bool:
        """是否为Windows系统"""
        return self._os_type == OSType.WINDOWS
    
    @property
    def is_linux(self) -> bool:
        """是否为Linux系统"""
        return self._os_type == OSType.LINUX
    
    @property
    def is_macos(self) -> bool:
        """是否为macOS系统"""
        return self._os_type == OSType.MACOS


# 创建全局单例实例，供其他模块使用
system_adapter = SystemAdapter()

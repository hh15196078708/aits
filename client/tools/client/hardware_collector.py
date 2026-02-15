# -*- coding: utf-8 -*-
"""
模块名称: hardware_collector.py
模块功能: 硬件采集统一入口，根据系统类型调用对应适配器
依赖模块: 
    - 本地模块: system_adapter, utils, constants
    - adapters: win_collector, linux_collector, mac_collector
系统适配: 所有平台通用，内部自动路由到对应采集器

说明:
    本模块是硬件采集的统一入口：
    1. 自动检测系统类型并选择对应采集器
    2. 统一异常处理和兜底逻辑
    3. 机器码采集失败时生成UUID并持久化
    4. 对外提供统一的API接口
"""

import os  # 操作系统接口
import platform
from typing import Dict, Optional  # 类型提示

import psutil

# 导入本地模块
from system_adapter import system_adapter, OSType  # 系统适配器
from utils import (
    generate_uuid,  # UUID生成
    safe_file_read,  # 安全文件读取
    safe_file_write  # 安全文件写入
)
from constants import (
    MACHINE_ID_FILE,  # 机器ID文件名
    CPU_USAGE_SAMPLE_INTERVAL  # CPU采样间隔
)


class HardwareCollector:
    """
    硬件采集统一入口类
    
    功能: 根据系统类型自动选择采集器，提供统一的硬件信息采集接口
    系统适配: 所有平台通用
    
    使用方式:
        collector = HardwareCollector()
        cpu_info = collector.get_cpu_info()
        machine_code = collector.get_machine_code()
    """
    
    _instance = None  # 单例实例
    _initialized = False  # 初始化标志
    
    def __new__(cls):
        """
        实现单例模式
        
        功能: 确保全局只有一个采集器实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化硬件采集器
        
        功能: 根据系统类型创建对应的平台采集器
        参数: 无
        返回值: 无
        异常情况: 不支持的系统会使用默认采集器
        """
        if HardwareCollector._initialized:  # 避免重复初始化
            return
        
        self._collector = None  # 平台采集器实例
        self._os_type = system_adapter.os_type  # 当前系统类型
        self._machine_id_path = ""  # 机器ID持久化路径
        
        self._init_collector()  # 初始化平台采集器
        self._init_machine_id_path()  # 初始化机器ID路径
        HardwareCollector._initialized = True
    
    def _init_collector(self) -> None:
        """
        初始化平台采集器
        
        功能: 根据系统类型导入并创建对应的采集器
        参数: 无
        返回值: 无
        异常情况: 导入失败时使用通用采集逻辑
        
        延迟导入: 仅导入当前平台需要的采集器，减少启动时间
        """
        try:
            if self._os_type == OSType.WINDOWS:
                # 导入Windows采集器
                from adapters.win_collector import WindowsCollector
                self._collector = WindowsCollector()
            elif self._os_type == OSType.LINUX:
                # 导入Linux采集器
                from adapters.linux_collector import LinuxCollector
                self._collector = LinuxCollector()
            elif self._os_type == OSType.MACOS:
                # 导入macOS采集器
                from adapters.mac_collector import MacCollector
                self._collector = MacCollector()
            else:
                # 未知系统，尝试使用Linux采集器作为兜底
                try:
                    from adapters.linux_collector import LinuxCollector
                    self._collector = LinuxCollector()
                except ImportError:
                    self._collector = None
        except ImportError as e:
            # 采集器导入失败
            print(f"[警告] 无法导入平台采集器: {e}")
            self._collector = None
    
    def _init_machine_id_path(self) -> None:
        """
        初始化机器ID持久化路径
        
        功能: 设置机器ID文件的存储路径
        参数: 无
        返回值: 无
        异常情况: 无
        """
        # 机器ID存储在配置目录下
        config_dir = system_adapter.get_config_dir()
        self._machine_id_path = os.path.join(config_dir, MACHINE_ID_FILE)
    
    def get_cpu_info(self, sample_interval: float = CPU_USAGE_SAMPLE_INTERVAL) -> Dict:
        """
        获取CPU信息
        
        功能: 采集CPU型号、核心数、使用率
        参数:
            sample_interval: CPU使用率采样间隔（秒）
        返回值: CPU信息字典
        异常情况: 采集失败返回默认值
        """
        default_result = {
            "model": "Unknown",
            "physical_cores": 0,
            "logical_cores": 0,
            "usage_percent": 0.0
        }
        
        if self._collector:
            try:
                return self._collector.get_cpu_info(sample_interval)
            except Exception:
                pass
        
        return default_result
    
    def get_memory_info(self) -> Dict:
        """
        获取内存信息
        
        功能: 采集内存总容量、可用容量、使用率
        参数: 无
        返回值: 内存信息字典
        异常情况: 采集失败返回默认值
        """
        default_result = {
            "total_gb": 0.0,
            "available_gb": 0.0,
            "usage_percent": 0.0
        }
        
        if self._collector:
            try:
                return self._collector.get_memory_info()
            except Exception:
                pass
        
        return default_result
    
    def get_disk_info(self) -> Dict:
        """
        获取硬盘信息
        
        功能: 采集主磁盘的容量信息
        参数: 无
        返回值: 硬盘信息字典
        异常情况: 采集失败返回默认值
        """
        default_result = {
            "path": "/" if self._os_type != OSType.WINDOWS else "C:/",
            "total_gb": 0.0,
            "available_gb": 0.0
        }
        
        if self._collector:
            try:
                return self._collector.get_disk_info()
            except Exception:
                pass
        
        return default_result
    
    def get_ip_info(self) -> Dict:
        """
        获取IP地址信息
        
        功能: 采集内网IP地址
        参数: 无
        返回值: IP信息字典
        异常情况: 采集失败返回Unknown
        """
        default_result = {
            "internal_ip": "Unknown",
            "external_ip": None,
            "source": "unknown"
        }
        
        if self._collector:
            try:
                return self._collector.get_ip_info()
            except Exception:
                pass
        
        return default_result
    
    def get_machine_code(self) -> str:
        """
        获取机器唯一标识（机器码）
        
        功能: 获取或生成机器唯一标识
        参数: 无
        返回值: 机器码字符串
        异常情况: 无，始终返回有效机器码
        
        逻辑说明:
            1. 首先尝试从硬件获取（主板序列号等）
            2. 如果硬件获取失败，检查是否有持久化的UUID
            3. 如果都没有，生成新的UUID并持久化
        """
        machine_code = ""
        
        # 步骤1：尝试从硬件获取
        if self._collector:
            try:
                machine_code = self._collector.get_machine_code()
            except Exception:
                pass
        
        # 步骤2：如果硬件获取失败，尝试读取持久化的UUID
        if not machine_code:
            machine_code = self._load_persisted_machine_id()
        
        # 步骤3：如果仍然没有，生成新UUID并持久化
        if not machine_code:
            machine_code = generate_uuid()
            self._persist_machine_id(machine_code)
        
        return machine_code
    
    def _load_persisted_machine_id(self) -> str:
        """
        加载持久化的机器ID
        
        功能: 从文件读取之前生成的UUID
        参数: 无
        返回值: 机器ID字符串，不存在返回空字符串
        异常情况: 读取失败返回空字符串
        """
        try:
            content = safe_file_read(self._machine_id_path)
            if content:
                return content.strip()
        except Exception:
            pass
        return ""
    
    def _persist_machine_id(self, machine_id: str) -> bool:
        """
        持久化机器ID
        
        功能: 将生成的UUID保存到文件
        参数:
            machine_id: 要保存的机器ID
        返回值: True表示成功，False表示失败
        异常情况: 写入失败返回False
        """
        try:
            # 确保目录存在
            dir_path = os.path.dirname(self._machine_id_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            return safe_file_write(self._machine_id_path, machine_id)
        except Exception:
            return False
    
    def get_os_info(self) -> Dict:
        """
        获取操作系统信息
        
        功能: 返回完整的操作系统信息
        参数: 无
        返回值: 系统信息字典
        异常情况: 无
        """
        return system_adapter.get_os_info()
    
    def get_hostname(self) -> str:
        """
        获取机器主机名
        
        功能: 返回系统原生主机名
        参数: 无
        返回值: 主机名字符串
        异常情况: 获取失败返回"Unknown"
        """
        return system_adapter.get_hostname()
    
    def get_all_info(self, cpu_sample_interval: float = CPU_USAGE_SAMPLE_INTERVAL) -> Dict:
        """
        获取所有硬件信息
        
        功能: 一次性采集所有硬件信息
        参数:
            cpu_sample_interval: CPU采样间隔（秒）
        返回值: 包含所有硬件信息的字典
        异常情况: 部分采集失败不影响其他项
        """
        result = {
            "cpu": self.get_cpu_info(cpu_sample_interval),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "ip_info": self.get_ip_info(),
            "os_info": self.get_os_info(),
            "machine_name": self.get_hostname(),
            "machine_code": self.get_machine_code()
        }
        return result
    
    def get_heartbeat_data(self, cpu_sample_interval: float = CPU_USAGE_SAMPLE_INTERVAL) -> Dict:
        """
        获取心跳数据
        
        功能: 采集心跳请求需要的数据
        参数:
            cpu_sample_interval: CPU采样间隔（秒）
        返回值: 心跳数据字典
        异常情况: 部分采集失败不影响其他项
        
        说明: 心跳数据包含CPU、内存、硬盘、系统信息
        """
        return {
            "cpu": self.get_cpu_info(cpu_sample_interval),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "os_info": self.get_os_info()
        }
    
    def get_registration_data(self) -> Dict:
        """
        获取注册数据
        
        功能: 采集首次注册需要的数据
        参数: 无
        返回值: 注册数据字典
        异常情况: 部分采集失败不影响其他项
        
        说明: 注册数据包含机器码、主机名、IP信息、系统信息
        """
        return {
            "machine_code": self.get_machine_code(),
            "machine_name": self.get_hostname(),
            "ip_info": self.get_ip_info(),
            "os_info": self.get_os_info()
        }
    
    def is_collector_available(self) -> bool:
        """
        检查采集器是否可用
        
        功能: 验证平台采集器是否成功初始化
        参数: 无
        返回值: True表示可用，False表示不可用
        异常情况: 无
        """
        return self._collector is not None

    def collect_all(self) -> Dict:
        """
        采集特定的7个硬件指标：
        1. 操作系统信息 (os_info)
        2. CPU配置 (cpu_config)
        3. CPU占有率 (cpu_usage)
        4. 内存大小 (memory_size)
        5. 内存占有率 (memory_usage)
        6. 硬盘大小 (disk_size)
        7. 硬盘使用率 (disk_usage)
        """
        try:
            # ---------------- 1. 操作系统信息 ----------------
            os_info = platform.platform()

            # ---------------- 2. CPU配置 ----------------
            processor_name = platform.processor()
            if not processor_name:
                processor_name = platform.machine()  # 如果获取不到详细名称，使用机器类型作为备选

            physical_cores = psutil.cpu_count(logical=False)  # 物理核心
            logical_cores = psutil.cpu_count(logical=True)  # 逻辑核心

            # 格式化输出，例如: Intel64 Family 6 Model 158 [4 Cores / 8 Threads]
            cpu_config = f"{processor_name} [{physical_cores} Cores / {logical_cores} Threads]"

            # ---------------- 3. CPU占有率 ----------------
            # interval=1 会阻塞1秒钟以计算准确的CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)

            # ---------------- 4. 内存大小 & 5. 内存占有率 ----------------
            mem = psutil.virtual_memory()
            # 将字节转换为GB，保留2位小数
            memory_total_gb = round(mem.total / (1024 ** 3), 2)
            memory_size = f"{memory_total_gb} GB"
            memory_usage = mem.percent

            # ---------------- 6. 硬盘大小 & 7. 硬盘使用率 ----------------
            # 自动判断操作系统来选择监控的根路径
            if platform.system() == 'Windows':
                disk_path = 'C:\\'
            else:
                disk_path = '/'

            disk_info = psutil.disk_usage(disk_path)

            disk_total_gb = round(disk_info.total / (1024 ** 3), 2)
            disk_size = f"{disk_total_gb} GB"
            disk_usage = disk_info.percent

            # 组装结果字典
            result = {
                "os_info": os_info,  # 操作系统信息
                "cpu_config": cpu_config,  # CPU配置
                "cpu_usage": cpu_usage,  # CPU占有率 (%)
                "memory_size": memory_size,  # 内存大小 (GB)
                "memory_usage": memory_usage,  # 内存占有率 (%)
                "disk_size": disk_size,  # 硬盘大小 (GB)
                "disk_usage": disk_usage  # 硬盘使用率 (%)
            }
            return result

        except Exception as e:
            # 发生错误时返回带默认值的字典，防止程序崩溃
            return {
                "os_info": "Unknown",
                "cpu_config": "Unknown",
                "cpu_usage": 0,
                "memory_size": "0 GB",
                "memory_usage": 0,
                "disk_size": "0 GB",
                "disk_usage": 0
            }


# 创建全局硬件采集器实例
hardware_collector = HardwareCollector()

# -*- coding: utf-8 -*-
"""
模块名称: adapters/win_collector.py
模块功能: Windows系统硬件信息采集
依赖模块: 
    - 标准库: os, subprocess, socket
    - 第三方库: psutil>=5.9.0, wmi>=1.5.1, pywin32>=306（可选）
系统适配: Windows 7/8/10/11, Windows Server 2016/2019/2022

说明:
    本模块负责Windows平台的硬件信息采集：
    1. CPU信息：使用wmi模块获取，psutil兜底
    2. 内存信息：使用psutil
    3. 硬盘信息：使用psutil，win32api兜底
    4. 机器码：优先使用主板序列号，UUID兜底
    5. IP地址：支持多网卡，区分内网/公网
"""

import os  # 操作系统接口
import subprocess  # 子进程调用
import socket  # 网络套接字
from typing import Dict, Optional, List  # 类型提示

# 尝试导入psutil
try:
    import psutil  # 跨平台硬件信息采集库
    PSUTIL_AVAILABLE = True  # psutil可用标志
except ImportError:
    PSUTIL_AVAILABLE = False  # psutil不可用

# 尝试导入wmi（Windows专用）
try:
    import wmi  # Windows Management Instrumentation
    WMI_AVAILABLE = True  # wmi可用标志
except ImportError:
    WMI_AVAILABLE = False  # wmi不可用

# 尝试导入win32api（Windows专用）
try:
    import win32api  # Windows API访问
    WIN32API_AVAILABLE = True  # win32api可用标志
except ImportError:
    WIN32API_AVAILABLE = False  # win32api不可用


class WindowsCollector:
    """
    Windows硬件采集器
    
    功能: 采集Windows系统的CPU、内存、硬盘、IP、机器码等信息
    系统适配: Windows 7/8/10/11, Windows Server 2016/2019/2022
    
    资源优化:
        - CPU使用率采样间隔0.5秒，降低CPU占用
        - 优先使用缓存的WMI连接
        - 避免高频调用
    """
    
    def __init__(self):
        """
        初始化Windows采集器
        
        功能: 创建WMI连接（如果可用）
        参数: 无
        返回值: 无
        异常情况: WMI不可用时降级处理
        """
        self._wmi_conn = None  # WMI连接对象
        if WMI_AVAILABLE:  # 如果wmi模块可用
            try:
                self._wmi_conn = wmi.WMI()  # 创建WMI连接
            except Exception:
                self._wmi_conn = None  # 连接失败时设为None
    
    def get_cpu_info(self, sample_interval: float = 0.5) -> Dict:
        """
        获取CPU信息
        
        功能: 采集CPU型号、核心数、使用率
        参数:
            sample_interval: CPU使用率采样间隔（秒），默认0.5秒
        返回值: CPU信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 优先使用WMI，psutil兜底
        
        资源优化: 采样间隔控制在0.5秒以内，降低CPU占用
        """
        result = {
            "model": "Unknown",  # CPU型号
            "physical_cores": 0,  # 物理核心数
            "logical_cores": 0,  # 逻辑核心数
            "usage_percent": 0.0  # 使用率
        }
        
        try:
            # 尝试使用WMI获取CPU型号
            if self._wmi_conn:
                for cpu in self._wmi_conn.Win32_Processor():  # 遍历CPU
                    result["model"] = cpu.Name.strip()  # 获取CPU名称
                    break  # 只取第一个CPU
            
            # 使用psutil获取核心数和使用率
            if PSUTIL_AVAILABLE:
                result["physical_cores"] = psutil.cpu_count(logical=False) or 0
                result["logical_cores"] = psutil.cpu_count(logical=True) or 0
                # 采样获取CPU使用率，interval控制采样时间
                result["usage_percent"] = round(
                    psutil.cpu_percent(interval=sample_interval), 2)
            else:
                # psutil不可用时使用WMI
                if self._wmi_conn:
                    for cpu in self._wmi_conn.Win32_Processor():
                        result["physical_cores"] = cpu.NumberOfCores or 0
                        result["logical_cores"] = cpu.NumberOfLogicalProcessors or 0
                        result["usage_percent"] = float(cpu.LoadPercentage or 0)
                        break
        except Exception:
            pass  # 采集失败时保持默认值
        
        return result
    
    def get_memory_info(self) -> Dict:
        """
        获取内存信息
        
        功能: 采集内存总容量、可用容量、使用率
        参数: 无
        返回值: 内存信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 使用psutil，WMI兜底
        """
        result = {
            "total_gb": 0.0,  # 总容量（GB）
            "available_gb": 0.0,  # 可用容量（GB）
            "usage_percent": 0.0  # 使用率
        }
        
        try:
            if PSUTIL_AVAILABLE:
                mem = psutil.virtual_memory()  # 获取内存信息
                result["total_gb"] = round(mem.total / (1024 ** 3), 2)
                result["available_gb"] = round(mem.available / (1024 ** 3), 2)
                result["usage_percent"] = round(mem.percent, 2)
            elif self._wmi_conn:
                # WMI兜底
                for mem in self._wmi_conn.Win32_ComputerSystem():
                    total_bytes = int(mem.TotalPhysicalMemory or 0)
                    result["total_gb"] = round(total_bytes / (1024 ** 3), 2)
                    break
                # 获取可用内存
                for os_info in self._wmi_conn.Win32_OperatingSystem():
                    free_bytes = int(os_info.FreePhysicalMemory or 0) * 1024
                    result["available_gb"] = round(free_bytes / (1024 ** 3), 2)
                    break
                # 计算使用率
                if result["total_gb"] > 0:
                    used = result["total_gb"] - result["available_gb"]
                    result["usage_percent"] = round(
                        (used / result["total_gb"]) * 100, 2)
        except Exception:
            pass  # 采集失败时保持默认值
        
        return result
    
    def get_disk_info(self) -> Dict:
        """
        获取硬盘信息
        
        功能: 采集系统盘（C盘）的容量信息
        参数: 无
        返回值: 硬盘信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 优先使用psutil，win32api兜底
        
        资源优化: 仅采集C盘，避免遍历所有分区导致IO过高
        """
        result = {
            "path": "C:/",  # 磁盘路径
            "total_gb": 0.0,  # 总容量（GB）
            "available_gb": 0.0  # 可用容量（GB）
        }
        
        try:
            if PSUTIL_AVAILABLE:
                # 获取C盘信息
                disk = psutil.disk_usage("C:/")  # 获取磁盘使用情况
                result["total_gb"] = round(disk.total / (1024 ** 3), 2)
                result["available_gb"] = round(disk.free / (1024 ** 3), 2)
            elif WIN32API_AVAILABLE:
                # win32api兜底
                free_bytes, total_bytes, _ = win32api.GetDiskFreeSpaceEx("C:/")
                result["total_gb"] = round(total_bytes / (1024 ** 3), 2)
                result["available_gb"] = round(free_bytes / (1024 ** 3), 2)
            else:
                # 使用命令行兜底
                output = subprocess.check_output(
                    ["wmic", "logicaldisk", "where", "DeviceID='C:'", "get", 
                     "Size,FreeSpace", "/format:csv"],
                    text=True, timeout=5
                )
                lines = output.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[-1].split(",")
                    if len(parts) >= 3:
                        result["available_gb"] = round(
                            int(parts[1]) / (1024 ** 3), 2)
                        result["total_gb"] = round(
                            int(parts[2]) / (1024 ** 3), 2)
        except Exception:
            pass  # 采集失败时保持默认值
        
        return result
    
    def get_machine_code(self) -> str:
        """
        获取机器唯一标识（机器码）
        
        功能: 获取主板序列号作为机器码，失败时返回空字符串
        参数: 无
        返回值: 机器码字符串，获取失败返回空字符串
        异常情况: 所有方法都失败时返回空字符串
        系统适配: 优先使用WMI获取主板序列号
        
        说明: 不在此处生成UUID兜底，由上层统一处理
        """
        machine_code = ""
        
        try:
            # 方法1：使用WMI获取主板序列号
            if self._wmi_conn:
                for board in self._wmi_conn.Win32_BaseBoard():
                    serial = board.SerialNumber
                    if serial and serial.strip() and serial.strip().lower() not in [
                        "none", "default string", "to be filled by o.e.m.", 
                        "not available", "n/a"]:
                        machine_code = serial.strip()
                        break
            
            # 方法2：如果主板序列号无效，尝试获取BIOS序列号
            if not machine_code and self._wmi_conn:
                for bios in self._wmi_conn.Win32_BIOS():
                    serial = bios.SerialNumber
                    if serial and serial.strip() and serial.strip().lower() not in [
                        "none", "default string", "to be filled by o.e.m.", 
                        "not available", "n/a"]:
                        machine_code = serial.strip()
                        break
            
            # 方法3：使用wmic命令行
            if not machine_code:
                try:
                    output = subprocess.check_output(
                        ["wmic", "baseboard", "get", "serialnumber"],
                        text=True, timeout=5, stderr=subprocess.DEVNULL
                    )
                    lines = output.strip().split("\n")
                    if len(lines) >= 2:
                        serial = lines[1].strip()
                        if serial and serial.lower() not in [
                            "none", "default string", "to be filled by o.e.m.", 
                            "not available", "n/a"]:
                            machine_code = serial
                except Exception:
                    pass
        except Exception:
            pass
        
        return machine_code
    
    def get_ip_info(self) -> Dict:
        """
        获取IP地址信息
        
        功能: 采集内网IP和公网IP，支持多网卡
        参数: 无
        返回值: IP信息字典
        异常情况: 采集失败时返回Unknown
        系统适配: 使用psutil获取网卡信息
        
        说明: 
            - 内网IP：优先取第一个非回环地址
            - 公网IP：需要访问外部服务获取，此处不实现
        """
        result = {
            "internal_ip": "Unknown",  # 内网IP
            "external_ip": None,  # 公网IP（由上层获取）
            "source": "psutil"  # 采集来源
        }
        
        try:
            if PSUTIL_AVAILABLE:
                # 获取所有网卡地址
                addrs = psutil.net_if_addrs()  # 获取网卡地址信息
                for iface, addr_list in addrs.items():
                    for addr in addr_list:
                        # 只取IPv4地址
                        if addr.family == socket.AF_INET:
                            ip = addr.address
                            # 排除回环地址和链路本地地址
                            if not ip.startswith("127.") and not ip.startswith("169.254."):
                                result["internal_ip"] = ip
                                return result  # 找到第一个有效IP即返回
            else:
                # 兜底方法：使用socket
                result["source"] = "socket"
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    # 连接到一个不存在的地址，不会真正发送数据
                    s.connect(("8.8.8.8", 80))
                    result["internal_ip"] = s.getsockname()[0]
                finally:
                    s.close()
        except Exception:
            pass
        
        return result
    
    def get_all_info(self, cpu_sample_interval: float = 0.5) -> Dict:
        """
        获取所有硬件信息
        
        功能: 一次性采集所有硬件信息
        参数:
            cpu_sample_interval: CPU采样间隔（秒）
        返回值: 包含所有硬件信息的字典
        异常情况: 部分采集失败不影响其他项
        """
        return {
            "cpu": self.get_cpu_info(cpu_sample_interval),
            "memory": self.get_memory_info(),
            "disk": self.get_disk_info(),
            "ip_info": self.get_ip_info()
        }

# -*- coding: utf-8 -*-
"""
模块名称: adapters/mac_collector.py
模块功能: macOS系统硬件信息采集
依赖模块: 
    - 标准库: os, subprocess, socket
    - 第三方库: psutil>=5.9.0（可选，支持Apple Silicon）
系统适配: macOS 10.14+ (Mojave及以上)，支持Intel和Apple Silicon

说明:
    本模块负责macOS平台的硬件信息采集：
    1. CPU信息：使用sysctl命令+psutil
    2. 内存信息：使用vm_stat解析+psutil
    3. 硬盘信息：使用diskutil+psutil
    4. 机器码：使用ioreg获取主板序列号
    5. IP地址：支持多网卡，区分内网/公网
"""

import os  # 操作系统接口
import subprocess  # 子进程调用
import socket  # 网络套接字
import re  # 正则表达式
from typing import Dict, Optional  # 类型提示

# 尝试导入psutil
try:
    import psutil  # 跨平台硬件信息采集库
    PSUTIL_AVAILABLE = True  # psutil可用标志
except ImportError:
    PSUTIL_AVAILABLE = False  # psutil不可用


class MacCollector:
    """
    macOS硬件采集器
    
    功能: 采集macOS系统的CPU、内存、硬盘、IP、机器码等信息
    系统适配: macOS 10.14+ (Mojave及以上)，Intel和Apple Silicon
    
    资源优化:
        - CPU使用率使用sysctl低耗采样
        - 内存使用vm_stat避免频繁系统调用
        - 仅采集主磁盘，避免遍历外置设备
    """
    
    def __init__(self):
        """
        初始化macOS采集器
        
        功能: 检测系统架构（Intel/Apple Silicon）
        参数: 无
        返回值: 无
        异常情况: 无
        """
        self._is_apple_silicon = self._check_apple_silicon()
    
    def _check_apple_silicon(self) -> bool:
        """
        检查是否为Apple Silicon架构
        
        功能: 判断当前Mac使用的CPU架构
        参数: 无
        返回值: True表示Apple Silicon，False表示Intel
        异常情况: 检测失败时默认返回False
        """
        try:
            import platform
            machine = platform.machine()
            return machine == "arm64"  # Apple Silicon返回arm64
        except Exception:
            return False
    
    def _run_sysctl(self, key: str) -> Optional[str]:
        """
        执行sysctl命令获取系统信息
        
        功能: 使用sysctl获取指定键的值
        参数:
            key: sysctl键名
        返回值: 值字符串，失败返回None
        异常情况: 执行失败返回None
        """
        try:
            output = subprocess.check_output(
                ["sysctl", "-n", key],
                text=True, timeout=5, stderr=subprocess.DEVNULL
            )
            return output.strip()
        except Exception:
            return None
    
    def get_cpu_info(self, sample_interval: float = 0.5) -> Dict:
        """
        获取CPU信息
        
        功能: 采集CPU型号、核心数、使用率
        参数:
            sample_interval: CPU使用率采样间隔（秒），默认0.5秒
        返回值: CPU信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 使用sysctl获取CPU信息，psutil获取使用率
        
        Apple Silicon适配: 使用machdep.cpu.brand_string可能为空，
                          改用hw.model和sysctl获取
        """
        result = {
            "model": "Unknown",  # CPU型号
            "physical_cores": 0,  # 物理核心数
            "logical_cores": 0,  # 逻辑核心数
            "usage_percent": 0.0  # 使用率
        }
        
        try:
            # 获取CPU型号
            brand = self._run_sysctl("machdep.cpu.brand_string")
            if brand:
                result["model"] = brand
            else:
                # Apple Silicon兜底
                model = self._run_sysctl("hw.model")
                if model:
                    result["model"] = f"Apple {model}"
            
            # 获取核心数
            if PSUTIL_AVAILABLE:
                result["physical_cores"] = psutil.cpu_count(logical=False) or 0
                result["logical_cores"] = psutil.cpu_count(logical=True) or 0
                result["usage_percent"] = round(
                    psutil.cpu_percent(interval=sample_interval), 2)
            else:
                # sysctl兜底
                physical = self._run_sysctl("hw.physicalcpu")
                logical = self._run_sysctl("hw.logicalcpu")
                if physical:
                    result["physical_cores"] = int(physical)
                if logical:
                    result["logical_cores"] = int(logical)
                # CPU使用率需要psutil，无法通过sysctl直接获取
        except Exception:
            pass
        
        return result
    
    def get_memory_info(self) -> Dict:
        """
        获取内存信息
        
        功能: 采集内存总容量、可用容量、使用率
        参数: 无
        返回值: 内存信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 使用psutil优先，vm_stat解析兜底
        """
        result = {
            "total_gb": 0.0,  # 总容量（GB）
            "available_gb": 0.0,  # 可用容量（GB）
            "usage_percent": 0.0  # 使用率
        }
        
        try:
            if PSUTIL_AVAILABLE:
                mem = psutil.virtual_memory()
                result["total_gb"] = round(mem.total / (1024 ** 3), 2)
                result["available_gb"] = round(mem.available / (1024 ** 3), 2)
                result["usage_percent"] = round(mem.percent, 2)
            else:
                # 使用vm_stat解析
                result = self._get_memory_from_vm_stat()
        except Exception:
            pass
        
        return result
    
    def _get_memory_from_vm_stat(self) -> Dict:
        """
        从vm_stat命令解析内存信息
        
        功能: 不依赖psutil获取内存信息
        参数: 无
        返回值: 内存信息字典
        异常情况: 解析失败返回默认值
        
        说明: vm_stat输出格式:
            Pages free:                              123456.
            Pages active:                            789012.
            ...
        """
        result = {
            "total_gb": 0.0,
            "available_gb": 0.0,
            "usage_percent": 0.0
        }
        
        try:
            # 获取总内存
            total_str = self._run_sysctl("hw.memsize")
            if total_str:
                result["total_gb"] = round(int(total_str) / (1024 ** 3), 2)
            
            # 解析vm_stat
            output = subprocess.check_output(
                ["vm_stat"],
                text=True, timeout=5
            )
            
            # 页面大小（通常是4096或16384）
            page_size = 4096
            page_size_match = re.search(r"page size of (\d+) bytes", output)
            if page_size_match:
                page_size = int(page_size_match.group(1))
            
            # 解析各类页面数
            pages_free = 0
            pages_inactive = 0
            pages_speculative = 0
            
            for line in output.split("\n"):
                if "Pages free:" in line:
                    pages_free = int(re.search(r"(\d+)", line).group(1))
                elif "Pages inactive:" in line:
                    pages_inactive = int(re.search(r"(\d+)", line).group(1))
                elif "Pages speculative:" in line:
                    pages_speculative = int(re.search(r"(\d+)", line).group(1))
            
            # 计算可用内存（free + inactive + speculative）
            available_bytes = (pages_free + pages_inactive + pages_speculative) * page_size
            result["available_gb"] = round(available_bytes / (1024 ** 3), 2)
            
            # 计算使用率
            if result["total_gb"] > 0:
                result["usage_percent"] = round(
                    (result["total_gb"] - result["available_gb"]) / result["total_gb"] * 100, 2)
        except Exception:
            pass
        
        return result
    
    def get_disk_info(self) -> Dict:
        """
        获取硬盘信息
        
        功能: 采集主磁盘（/）的容量信息
        参数: 无
        返回值: 硬盘信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 使用psutil优先，diskutil兜底
        
        资源优化: 仅采集根分区，不遍历外置设备
        """
        result = {
            "path": "/",  # 磁盘路径
            "total_gb": 0.0,  # 总容量（GB）
            "available_gb": 0.0  # 可用容量（GB）
        }
        
        try:
            if PSUTIL_AVAILABLE:
                disk = psutil.disk_usage("/")
                result["total_gb"] = round(disk.total / (1024 ** 3), 2)
                result["available_gb"] = round(disk.free / (1024 ** 3), 2)
            else:
                # 使用df命令
                output = subprocess.check_output(
                    ["df", "-k", "/"],
                    text=True, timeout=5
                )
                lines = output.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        # df -k输出单位是KB
                        result["total_gb"] = round(
                            int(parts[1]) / (1024 ** 2), 2)
                        result["available_gb"] = round(
                            int(parts[3]) / (1024 ** 2), 2)
        except Exception:
            pass
        
        return result
    
    def get_machine_code(self) -> str:
        """
        获取机器唯一标识（机器码）
        
        功能: 使用ioreg获取主板序列号
        参数: 无
        返回值: 机器码字符串，获取失败返回空字符串
        异常情况: 所有方法都失败时返回空字符串
        系统适配: 使用ioreg命令获取硬件序列号
        """
        machine_code = ""
        
        try:
            # 方法1：使用ioreg获取序列号
            output = subprocess.check_output(
                ["ioreg", "-l"],
                text=True, timeout=10, stderr=subprocess.DEVNULL
            )
            
            # 查找IOPlatformSerialNumber
            for line in output.split("\n"):
                if "IOPlatformSerialNumber" in line:
                    # 格式: "IOPlatformSerialNumber" = "ABC123..."
                    match = re.search(r'"IOPlatformSerialNumber"\s*=\s*"([^"]+)"', line)
                    if match:
                        machine_code = match.group(1)
                        break
            
            # 方法2：使用system_profiler（更可靠但较慢）
            if not machine_code:
                try:
                    output = subprocess.check_output(
                        ["system_profiler", "SPHardwareDataType"],
                        text=True, timeout=10, stderr=subprocess.DEVNULL
                    )
                    for line in output.split("\n"):
                        if "Serial Number" in line:
                            machine_code = line.split(":")[1].strip()
                            break
                except Exception:
                    pass
        except Exception:
            pass
        
        return machine_code
    
    def get_ip_info(self) -> Dict:
        """
        获取IP地址信息
        
        功能: 采集内网IP，支持多网卡
        参数: 无
        返回值: IP信息字典
        异常情况: 采集失败时返回Unknown
        系统适配: 使用psutil获取网卡信息
        """
        result = {
            "internal_ip": "Unknown",  # 内网IP
            "external_ip": None,  # 公网IP（由上层获取）
            "source": "psutil"  # 采集来源
        }
        
        try:
            if PSUTIL_AVAILABLE:
                addrs = psutil.net_if_addrs()
                # macOS网卡命名：en0通常是WiFi/以太网
                preferred_interfaces = ["en0", "en1", "en2", "en3", "en4"]
                
                # 优先检查常用接口
                for iface in preferred_interfaces:
                    if iface in addrs:
                        for addr in addrs[iface]:
                            if addr.family == socket.AF_INET:
                                ip = addr.address
                                if not ip.startswith("127.") and not ip.startswith("169.254."):
                                    result["internal_ip"] = ip
                                    return result
                
                # 遍历所有接口
                for iface, addr_list in addrs.items():
                    if iface.startswith("lo"):  # 跳过回环
                        continue
                    for addr in addr_list:
                        if addr.family == socket.AF_INET:
                            ip = addr.address
                            if not ip.startswith("127.") and not ip.startswith("169.254."):
                                result["internal_ip"] = ip
                                return result
            else:
                # socket兜底
                result["source"] = "socket"
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
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

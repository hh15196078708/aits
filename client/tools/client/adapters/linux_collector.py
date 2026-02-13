# -*- coding: utf-8 -*-
"""
模块名称: adapters/linux_collector.py
模块功能: Linux系统硬件信息采集（含国产Linux）
依赖模块: 
    - 标准库: os, subprocess, socket
    - 第三方库: psutil>=5.9.0（可选）
系统适配: 
    - 通用Linux: Ubuntu, CentOS, Debian, Fedora, openSUSE
    - 国产Linux: 统信UOS, 银河麒麟, 中标麒麟, 深度Linux

说明:
    本模块负责Linux平台的硬件信息采集：
    1. CPU信息：使用psutil优先，/proc/cpuinfo兜底
    2. 内存信息：使用psutil优先，/proc/meminfo兜底
    3. 硬盘信息：使用psutil优先，df命令/os.statvfs兜底
    4. 机器码：dmidecode获取主板序列号，/etc/machine-id或UUID兜底
    5. IP地址：支持多网卡，区分内网/公网
"""

import os  # 操作系统接口
import subprocess  # 子进程调用
import socket  # 网络套接字
from typing import Dict, Optional  # 类型提示

# 尝试导入psutil
try:
    import psutil  # 跨平台硬件信息采集库
    PSUTIL_AVAILABLE = True  # psutil可用标志
except ImportError:
    PSUTIL_AVAILABLE = False  # psutil不可用


class LinuxCollector:
    """
    Linux硬件采集器
    
    功能: 采集Linux系统的CPU、内存、硬盘、IP、机器码等信息
    系统适配: Ubuntu, CentOS, Debian, Fedora, openSUSE, 
              统信UOS, 银河麒麟, 中标麒麟, 深度Linux
    
    资源优化:
        - CPU使用率采样间隔0.5秒，降低CPU占用
        - 优先使用/proc文件系统，避免启动外部进程
        - 仅采集根分区，避免遍历所有分区
    """
    
    def __init__(self):
        """
        初始化Linux采集器
        
        功能: 检测可用的采集方法
        参数: 无
        返回值: 无
        异常情况: 无
        """
        self._has_dmidecode = self._check_dmidecode()  # 检查dmidecode是否可用
    
    def _check_dmidecode(self) -> bool:
        """
        检查dmidecode工具是否可用
        
        功能: 验证系统是否安装了dmidecode
        参数: 无
        返回值: True表示可用，False表示不可用
        异常情况: 无
        系统适配: 国产Linux可能需要单独安装dmidecode
        """
        try:
            result = subprocess.run(
                ["which", "dmidecode"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0  # 返回码0表示找到
        except Exception:
            return False
    
    def get_cpu_info(self, sample_interval: float = 0.5) -> Dict:
        """
        获取CPU信息
        
        功能: 采集CPU型号、核心数、使用率
        参数:
            sample_interval: CPU使用率采样间隔（秒），默认0.5秒
        返回值: CPU信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 优先使用psutil，/proc/cpuinfo兜底
        
        资源优化: 采样间隔控制在0.5秒以内
        """
        result = {
            "model": "Unknown",  # CPU型号
            "physical_cores": 0,  # 物理核心数
            "logical_cores": 0,  # 逻辑核心数
            "usage_percent": 0.0  # 使用率
        }
        
        try:
            # 使用psutil获取核心数和使用率
            if PSUTIL_AVAILABLE:
                result["physical_cores"] = psutil.cpu_count(logical=False) or 0
                result["logical_cores"] = psutil.cpu_count(logical=True) or 0
                result["usage_percent"] = round(
                    psutil.cpu_percent(interval=sample_interval), 2)
            
            # 从/proc/cpuinfo获取CPU型号
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("model name"):
                            # 格式: model name : Intel(R) Core(TM) i7-10700 CPU @ 2.90GHz
                            result["model"] = line.split(":", 1)[1].strip()
                            break
                
                # 如果psutil不可用，从文件计算核心数
                if not PSUTIL_AVAILABLE:
                    with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                        content = f.read()
                    # 统计processor出现次数（逻辑核心数）
                    result["logical_cores"] = content.count("processor")
                    # 统计不重复的physical id（物理核心数）
                    physical_ids = set()
                    core_ids = set()
                    for line in content.split("\n"):
                        if line.startswith("physical id"):
                            physical_ids.add(line.split(":")[1].strip())
                        elif line.startswith("core id"):
                            core_ids.add(line.split(":")[1].strip())
                    result["physical_cores"] = len(physical_ids) * len(core_ids) if physical_ids and core_ids else result["logical_cores"]
        except Exception:
            pass  # 采集失败时保持默认值
        
        # 如果psutil不可用，从/proc/stat计算CPU使用率
        if not PSUTIL_AVAILABLE and result["usage_percent"] == 0.0:
            result["usage_percent"] = self._get_cpu_usage_from_proc()
        
        return result
    
    def _get_cpu_usage_from_proc(self) -> float:
        """
        从/proc/stat计算CPU使用率
        
        功能: 不依赖psutil计算CPU使用率
        参数: 无
        返回值: CPU使用率（百分比）
        异常情况: 计算失败返回0.0
        """
        try:
            # 读取两次/proc/stat计算差值
            import time
            
            def read_cpu_times():
                with open("/proc/stat", "r") as f:
                    line = f.readline()
                # cpu  user nice system idle iowait irq softirq
                parts = line.split()
                return [int(p) for p in parts[1:8]]
            
            times1 = read_cpu_times()
            time.sleep(0.5)  # 等待0.5秒
            times2 = read_cpu_times()
            
            # 计算差值
            deltas = [t2 - t1 for t1, t2 in zip(times1, times2)]
            total = sum(deltas)
            idle = deltas[3]  # idle是第4个值
            
            if total > 0:
                return round((1 - idle / total) * 100, 2)
        except Exception:
            pass
        return 0.0
    
    def get_memory_info(self) -> Dict:
        """
        获取内存信息
        
        功能: 采集内存总容量、可用容量、使用率
        参数: 无
        返回值: 内存信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 优先使用psutil，/proc/meminfo兜底
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
                # 从/proc/meminfo读取
                if os.path.exists("/proc/meminfo"):
                    with open("/proc/meminfo", "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    mem_total = 0
                    mem_available = 0
                    
                    for line in content.split("\n"):
                        if line.startswith("MemTotal:"):
                            # 格式: MemTotal: 16384000 kB
                            mem_total = int(line.split()[1]) * 1024
                        elif line.startswith("MemAvailable:"):
                            mem_available = int(line.split()[1]) * 1024
                    
                    result["total_gb"] = round(mem_total / (1024 ** 3), 2)
                    result["available_gb"] = round(mem_available / (1024 ** 3), 2)
                    if mem_total > 0:
                        result["usage_percent"] = round(
                            (mem_total - mem_available) / mem_total * 100, 2)
        except Exception:
            pass
        
        return result
    
    def get_disk_info(self) -> Dict:
        """
        获取硬盘信息
        
        功能: 采集根分区（/）的容量信息
        参数: 无
        返回值: 硬盘信息字典
        异常情况: 采集失败时返回默认值
        系统适配: 优先使用psutil，os.statvfs或df命令兜底
        
        资源优化: 仅采集根分区，避免IO过高
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
                # 使用os.statvfs
                st = os.statvfs("/")
                result["total_gb"] = round(
                    st.f_blocks * st.f_frsize / (1024 ** 3), 2)
                result["available_gb"] = round(
                    st.f_bavail * st.f_frsize / (1024 ** 3), 2)
        except Exception:
            # 使用df命令兜底
            try:
                output = subprocess.check_output(
                    ["df", "-B1", "/"],
                    text=True, timeout=5
                )
                lines = output.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        result["total_gb"] = round(int(parts[1]) / (1024 ** 3), 2)
                        result["available_gb"] = round(int(parts[3]) / (1024 ** 3), 2)
            except Exception:
                pass
        
        return result
    
    def get_machine_code(self) -> str:
        """
        获取机器唯一标识（机器码）
        
        功能: 获取主板序列号作为机器码
        参数: 无
        返回值: 机器码字符串，获取失败返回空字符串
        异常情况: 所有方法都失败时返回空字符串
        系统适配: 
            - 优先使用dmidecode获取主板序列号
            - 兜底使用/etc/machine-id
        
        国产Linux适配: 提示用户安装dmidecode
        """
        machine_code = ""
        
        try:
            # 方法1：使用dmidecode获取主板序列号（需要root权限）
            if self._has_dmidecode:
                try:
                    output = subprocess.check_output(
                        ["sudo", "dmidecode", "-s", "baseboard-serial-number"],
                        text=True, timeout=5, stderr=subprocess.DEVNULL
                    )
                    serial = output.strip()
                    if serial and serial.lower() not in [
                        "none", "default string", "to be filled by o.e.m.", 
                        "not available", "n/a", "not specified"]:
                        machine_code = serial
                except subprocess.CalledProcessError:
                    # 没有sudo权限，尝试不使用sudo
                    try:
                        output = subprocess.check_output(
                            ["dmidecode", "-s", "baseboard-serial-number"],
                            text=True, timeout=5, stderr=subprocess.DEVNULL
                        )
                        serial = output.strip()
                        if serial and serial.lower() not in [
                            "none", "default string", "to be filled by o.e.m.", 
                            "not available", "n/a", "not specified"]:
                            machine_code = serial
                    except Exception:
                        pass
                except Exception:
                    pass
            
            # 方法2：读取/etc/machine-id（大多数Linux发行版都有）
            if not machine_code and os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r", encoding="utf-8") as f:
                    machine_id = f.read().strip()
                if machine_id:
                    machine_code = machine_id
            
            # 方法3：读取/var/lib/dbus/machine-id（备用位置）
            if not machine_code and os.path.exists("/var/lib/dbus/machine-id"):
                with open("/var/lib/dbus/machine-id", "r", encoding="utf-8") as f:
                    machine_id = f.read().strip()
                if machine_id:
                    machine_code = machine_id
            
            # 方法4：读取DMI信息文件（某些系统）
            if not machine_code:
                dmi_paths = [
                    "/sys/class/dmi/id/board_serial",
                    "/sys/class/dmi/id/product_serial"
                ]
                for path in dmi_paths:
                    if os.path.exists(path):
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                serial = f.read().strip()
                            if serial and serial.lower() not in [
                                "none", "default string", "to be filled by o.e.m.", 
                                "not available", "n/a"]:
                                machine_code = serial
                                break
                        except PermissionError:
                            continue  # 没有权限，尝试下一个
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
        系统适配: 使用psutil获取网卡信息，socket兜底
        """
        result = {
            "internal_ip": "Unknown",  # 内网IP
            "external_ip": None,  # 公网IP（由上层获取）
            "source": "psutil"  # 采集来源
        }
        
        try:
            if PSUTIL_AVAILABLE:
                addrs = psutil.net_if_addrs()
                for iface, addr_list in addrs.items():
                    # 跳过回环接口和docker接口
                    if iface.startswith("lo") or iface.startswith("docker"):
                        continue
                    for addr in addr_list:
                        if addr.family == socket.AF_INET:
                            ip = addr.address
                            if not ip.startswith("127.") and not ip.startswith("169.254."):
                                result["internal_ip"] = ip
                                return result
            else:
                # 使用socket兜底
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

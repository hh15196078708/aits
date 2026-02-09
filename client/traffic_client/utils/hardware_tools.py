# -*- coding: utf-8 -*-
"""
@模块名称: 硬件特征采集工具 (utils/hardware_tools.py)
@功能描述: 跨平台(Windows/Linux)采集CPU、主板、网卡、硬盘物理特征。
         包含虚拟化设备过滤逻辑。
@依赖库: wmi (Windows, 可选), subprocess (通用)
"""

import os
import platform
import subprocess
import re
import sys
from typing import Dict, Optional

# 尝试导入 SystemUtils，如果找不到则定义一个简易版（便于单文件调试）
try:
    from utils.system_tools import SystemUtils
except ImportError:
    class SystemUtils:
        @staticmethod
        def is_windows():
            return platform.system().lower() == 'windows'

        @staticmethod
        def execute_cmd(cmd):
            try:
                res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8',
                                     errors='ignore')
                return res.returncode == 0, res.stdout.strip()
            except Exception:
                return False, ""

# 尝试导入WMI，仅在Windows下有效
try:
    import wmi
    import pythoncom

    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


class HardwareCollector:
    # 虚拟化关键词黑名单 (忽略大小写)
    VIRTUAL_KEYWORDS = [
        "virtual", "vmware", "virtualbox", "kvm", "hyper-v", "qemu",
        "parallels", "xen", "vbox", "adapter", "pseudo", "loopback"
    ]

    @staticmethod
    def _is_virtual_device(name: str) -> bool:
        """判断设备名称是否包含虚拟化关键词"""
        if not name:
            return False
        name_lower = name.lower()
        for keyword in HardwareCollector.VIRTUAL_KEYWORDS:
            if keyword in name_lower:
                return True
        return False

    @staticmethod
    def _run_wmic(command: str) -> str:
        """
        [Windows Fallback] 使用 wmic 命令行获取信息
        当 wmi 库不可用时作为后备方案
        """
        try:
            # wmic cpu get ProcessorId
            # Output format:
            # ProcessorId
            # XXXXXXXX
            cmd = f"wmic {command}"
            success, output = SystemUtils.execute_cmd(cmd)
            if success and output:
                lines = [line.strip() for line in output.split('\n') if line.strip()]
                if len(lines) >= 2:
                    # 取第二行作为值
                    return lines[1]
        except Exception as e:
            print(f"[Debug] WMIC fallback error: {e}")
        return ""

    @staticmethod
    def get_cpu_serial() -> str:
        """获取CPU序列号"""
        serial = ""
        try:
            if SystemUtils.is_windows():
                # 优先尝试 WMI 库
                if WMI_AVAILABLE:
                    try:
                        pythoncom.CoInitialize()
                        c = wmi.WMI()
                        for cpu in c.Win32_Processor():
                            if cpu.ProcessorId:
                                serial = cpu.ProcessorId.strip()
                                break
                    except Exception as e:
                        print(f"[Debug] WMI CPU error: {e}")

                # 回退到 WMIC 命令
                if not serial:
                    serial = HardwareCollector._run_wmic("cpu get ProcessorId")
            else:
                # Linux: dmidecode (root) or /proc/cpuinfo
                success, output = SystemUtils.execute_cmd("dmidecode -t processor")
                if success:
                    for line in output.split('\n'):
                        if "ID:" in line:
                            parts = line.split("ID:")
                            if len(parts) > 1:
                                serial = parts[1].strip().replace(" ", "")
                                break

                # Linux Fallback: 读取 /proc/cpuinfo (部分ARM架构或特殊环境)
                if not serial:
                    success, output = SystemUtils.execute_cmd("cat /proc/cpuinfo")
                    if success:
                        for line in output.split('\n'):
                            if "Serial" in line:
                                parts = line.split(":")
                                if len(parts) > 1:
                                    serial = parts[1].strip()
                                    break
        except Exception as e:
            print(f"[Debug] Get CPU Serial error: {e}")
        return serial if serial else "UNKNOWN_CPU"

    @staticmethod
    def get_board_sn() -> str:
        """获取主板序列号"""
        sn = ""
        try:
            if SystemUtils.is_windows():
                if WMI_AVAILABLE:
                    try:
                        pythoncom.CoInitialize()
                        c = wmi.WMI()
                        for board in c.Win32_BaseBoard():
                            if board.SerialNumber:
                                sn = board.SerialNumber.strip()
                                break
                    except Exception as e:
                        print(f"[Debug] WMI Board error: {e}")

                if not sn:
                    sn = HardwareCollector._run_wmic("baseboard get SerialNumber")
            else:
                # Linux Priority 1: sysfs (root not always required)
                success, output = SystemUtils.execute_cmd("cat /sys/class/dmi/id/board_serial")
                if success and output:
                    sn = output.strip()

                # Linux Priority 2: dmidecode
                if not sn:
                    success, output = SystemUtils.execute_cmd("dmidecode -t baseboard")
                    if success:
                        for line in output.split('\n'):
                            if "Serial Number:" in line:
                                parts = line.split(":")
                                if len(parts) > 1:
                                    sn = parts[1].strip()
                                    break
        except Exception as e:
            print(f"[Debug] Get Board SN error: {e}")
        return sn if sn else "UNKNOWN_BOARD"

    @staticmethod
    def get_disk_id() -> str:
        """获取系统盘唯一ID"""
        disk_id = ""
        try:
            if SystemUtils.is_windows():
                if WMI_AVAILABLE:
                    try:
                        pythoncom.CoInitialize()
                        c = wmi.WMI()
                        for disk in c.Win32_DiskDrive():
                            # 简单的物理盘过滤
                            media_type = str(disk.MediaType).lower() if disk.MediaType else ""
                            if disk.SerialNumber and ("fixed" in media_type or "external" in media_type):
                                disk_id = disk.SerialNumber.strip()
                                break
                    except Exception as e:
                        print(f"[Debug] WMI Disk error: {e}")

                if not disk_id:
                    disk_id = HardwareCollector._run_wmic("diskdrive get SerialNumber")
            else:
                # Linux
                # 尝试常见的磁盘标识
                for cmd in ["lsblk --nodeps -no serial /dev/sda",
                            "lsblk --nodeps -no serial /dev/vda",
                            "lsblk --nodeps -no serial /dev/nvme0n1"]:
                    success, output = SystemUtils.execute_cmd(cmd)
                    if success and output:
                        disk_id = output.strip()
                        break
        except Exception as e:
            print(f"[Debug] Get Disk ID error: {e}")
        return disk_id if disk_id else "UNKNOWN_DISK"

    @staticmethod
    def get_mac_address() -> str:
        """获取物理网卡MAC地址"""
        mac_list = []
        try:
            if SystemUtils.is_windows():
                # Method 1: WMI
                if WMI_AVAILABLE:
                    try:
                        pythoncom.CoInitialize()
                        c = wmi.WMI()
                        for interface in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                            desc = interface.Description
                            if desc and not HardwareCollector._is_virtual_device(desc):
                                if interface.MACAddress:
                                    mac_list.append(interface.MACAddress.replace(":", ""))
                    except Exception as e:
                        print(f"[Debug] WMI MAC error: {e}")

                # Method 2: getmac command (Backup)
                if not mac_list:
                    success, output = SystemUtils.execute_cmd("getmac /FO CSV /NH")
                    if success:
                        # Output: "MAC", "Transport Name"
                        import csv
                        import io
                        reader = csv.reader(io.StringIO(output))
                        for row in reader:
                            if row and len(row) > 0:
                                mac = row[0].replace("-", "")
                                if len(mac) == 12:  # Valid MAC length
                                    mac_list.append(mac)

            else:
                # Linux
                import glob
                interfaces = glob.glob("/sys/class/net/*")
                for iface_path in interfaces:
                    iface_name = os.path.basename(iface_path)
                    if iface_name == "lo" or HardwareCollector._is_virtual_device(iface_name):
                        continue
                    if not os.path.exists(os.path.join(iface_path, "device")):
                        continue  # Skip virtual interfaces
                    try:
                        with open(os.path.join(iface_path, "address"), 'r') as f:
                            mac = f.read().strip().replace(":", "").upper()
                            if mac:
                                mac_list.append(mac)
                    except:
                        continue
        except Exception as e:
            print(f"[Debug] Get MAC error: {e}")

        mac_list.sort()

        # 最后的兜底：如果完全获取不到，使用 UUID (仅用于开发环境防止流程阻塞)
        if not mac_list:
            import uuid
            node = uuid.getnode()
            mac = ':'.join(['{:02x}'.format((node >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1]).replace(":",
                                                                                                                "").upper()
            return mac

        return mac_list[0] if mac_list else "UNKNOWN_MAC"

    @staticmethod
    def collect_all_features() -> Dict[str, str]:
        """采集所有硬件特征"""
        # 打印调试信息，确认运行环境
        if WMI_AVAILABLE:
            print("[Info] WMI library is available.")
        else:
            print("[Info] WMI library NOT found. Using command fallback.")

        return {
            "cpu_serial": HardwareCollector.get_cpu_serial(),
            "board_sn": HardwareCollector.get_board_sn(),
            "disk_id": HardwareCollector.get_disk_id(),
            "mac_addr": HardwareCollector.get_mac_address()
        }


if __name__ == "__main__":
    print(HardwareCollector.collect_all_features())
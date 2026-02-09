# -*- coding: utf-8 -*-
"""
@模块名称: 系统底层工具类 (utils/system_tools.py)
@功能描述: 封装跨平台(Windows/Linux)系统调用差异，提供统一接口。
         包含：系统信息获取、命令执行、路径标准化。
@前置约束:
    1. 禁止使用第三方重依赖库，优先使用标准库。
    2. Windows端通过pywin32/wmi兼容，Linux端通过Shell兼容。
"""

import sys
import os
import platform
import subprocess
import shutil
import socket
from pathlib import Path
from typing import Dict, Tuple, Optional


class SystemUtils:

    @staticmethod
    def get_os_type() -> str:
        """
        获取当前操作系统类型 (小写)
        :return: 'windows' | 'linux' | 'unknown'
        """
        system = platform.system().lower()
        if 'windows' in system:
            return 'windows'
        elif 'linux' in system:
            return 'linux'
        return 'unknown'

    @staticmethod
    def is_windows() -> bool:
        return SystemUtils.get_os_type() == 'windows'

    @staticmethod
    def get_root_path() -> Path:
        """
        获取工程根目录绝对路径（兼容pyinstaller打包后的路径）
        """
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe
            return Path(sys.executable).parent.resolve()
        else:
            # 如果是脚本运行，定位到utils的上级目录
            return Path(__file__).parent.parent.resolve()

    @staticmethod
    def resolve_path(relative_path: str) -> str:
        """
        跨平台路径拼接与标准化
        :param relative_path: 相对路径，如 "data/logs"
        :return: 绝对路径字符串
        """
        root = SystemUtils.get_root_path()
        # Path join 会自动处理 Windows(\) 和 Linux(/) 的分隔符
        full_path = root.joinpath(relative_path)
        return str(full_path)

    @staticmethod
    def ensure_dir(dir_path: str) -> None:
        """确保目录存在，不存在则创建"""
        path_obj = Path(dir_path)
        if not path_obj.exists():
            path_obj.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def execute_cmd(cmd: str, timeout: int = 10) -> Tuple[bool, str]:
        """
        跨平台执行系统命令
        :param cmd: 命令字符串
        :param timeout: 超时时间（秒）
        :return: (是否成功, 输出结果或错误信息)
        """
        try:
            # Windows下处理编码问题，通常是gbk；Linux通常是utf-8
            encoding = 'gbk' if SystemUtils.is_windows() else 'utf-8'

            # shell=True 允许执行shell内置命令，但需注意注入风险（内部使用可控）
            process = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                encoding=encoding,
                errors='ignore'  # 忽略解码错误，防止崩溃
            )

            if process.returncode == 0:
                return True, process.stdout.strip()
            else:
                return False, process.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, f"Error: Command execution timed out ({timeout}s)"
        except Exception as e:
            return False, f"Error: {str(e)}"

    @staticmethod
    def get_system_basic_info() -> Dict:
        """
        获取基础系统信息（用于日志和初步环境判断）
        """
        info = {
            "os_type": SystemUtils.get_os_type(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "python_version": platform.python_version()
        }
        return info

    @staticmethod
    def get_pid_file_path() -> str:
        """获取PID文件路径"""
        if SystemUtils.is_windows():
            return SystemUtils.resolve_path("data/client.pid")
        else:
            return "/var/run/traffic_client.pid"


# 简单自测
if __name__ == "__main__":
    print(f"OS: {SystemUtils.get_os_type()}")
    print(f"Root: {SystemUtils.get_root_path()}")
    success, output = SystemUtils.execute_cmd("echo Hello System")
    print(f"Cmd Test: {output}")
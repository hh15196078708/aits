# -*- coding: utf-8 -*-
"""
模块名称: config_manager.py
模块功能: 读写 client_config.json 中的运行时状态，跨平台路径适配，线程安全持久化
依赖模块: 标准库 (os, re, json, threading)
系统适配: 所有平台通用

说明:
    本模块负责管理客户端的运行时状态持久化：
    1. 配置文件为项目目录下的 client_config.json（由服务端统一生成下发）
    2. 支持 JSONC 格式（// 行注释），加载时自动剥离注释
    3. 保存时写入标准 JSON（注释不会还原，但不影响功能）
    4. 运行时状态字段（client_id、machine_code 等）与 settings 节共存于同一文件
    5. 线程安全的读写操作
"""

import os
import re
import json
import threading
from typing import Any, Dict, List, Optional

from constants import CONFIG_FILE_NAME
from utils import (
    safe_file_read,
    safe_file_write,
    safe_json_loads,
    get_timestamp
)


# =============================================================================
# JSONC 注释剥离（与 constants.py 中保持相同实现）
# =============================================================================

def _strip_comments(text: str) -> str:
    """
    从 JSONC 文本中移除 // 行注释，保留字符串内的 //（如 URL http://...）。
    """
    _pattern = re.compile(
        r'"(?:[^"\\]|\\.)*"'  # JSON 字符串（原样保留）
        r'|'
        r'//[^\n]*'           # // 行注释（移除）
    )
    return _pattern.sub(
        lambda m: m.group(0) if m.group(0).startswith('"') else '',
        text
    )


class ConfigManager:
    """
    配置管理器（单例）

    功能: 管理 client_config.json 中运行时状态字段的读写
    配置文件位置: 与源码同目录（项目根目录），由服务端统一下发

    支持 JSONC（// 注释）格式加载，保存时写回标准 JSON。
    settings 节由 constants.py 负责读取，本类不修改该节内容，
    但在保存时会将其原样写回，确保文件完整性。

    运行时状态字段:
        client_id           — 服务端分配的客户端 ID
        machine_code        — 机器唯一码
        auth_key            — 授权密钥
        expire_time         — 授权到期时间
        machine_name        — 机器名称
        ip_info             — IP 信息 {internal_ip, external_ip, source}
        os_info             — 系统信息 {type, version, arch, kernel}
        auth_cache          — 授权状态缓存 {status, update_time}
        first_run_time      — 首次运行时间戳
        last_heartbeat_time — 最后心跳时间戳
        web_log_offsets     — Web 日志文件读取偏移量
        web_log_sources     — Web 日志源配置列表
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ConfigManager._initialized:
            return

        self._config: Dict[str, Any] = {}
        self._config_dir: str = ""
        self._config_file: str = ""
        self._lock = threading.Lock()

        self._init_config_path()
        self._load_config()
        ConfigManager._initialized = True

    # -------------------------------------------------------------------------
    # 内部：路径初始化与文件读写
    # -------------------------------------------------------------------------

    def _init_config_path(self) -> None:
        """
        初始化配置文件路径。
        配置文件（client_config.json）与本模块同目录，由服务端下发到此路径。
        """
        self._config_dir = os.path.dirname(os.path.abspath(__file__))
        self._config_file = os.path.join(self._config_dir, CONFIG_FILE_NAME)

    def _load_config(self) -> None:
        """
        从 client_config.json 加载全部内容（含 settings 节和运行时状态）。
        加载时自动剥离 // 行注释，支持 JSONC 格式。
        """
        with self._lock:
            content = safe_file_read(self._config_file)
            if content:
                cleaned = _strip_comments(content)
                parsed = safe_json_loads(cleaned, default={})
                self._config = parsed if isinstance(parsed, dict) else {}
            else:
                self._config = {}

    def _save_config(self) -> bool:
        """
        将全部配置（含 settings 节和运行时状态）序列化为标准 JSON 并写入文件。
        注意：保存时注释不会还原（标准 JSON 不支持注释），但内容完整无损。
        """
        try:
            content = json.dumps(
                self._config,
                ensure_ascii=False,
                indent=2,
                sort_keys=True
            )
            return safe_file_write(self._config_file, content)
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # 首次运行检测
    # -------------------------------------------------------------------------

    def is_first_run(self) -> bool:
        """返回 True 表示首次运行（配置中尚无 machine_code）"""
        with self._lock:
            return not self._config.get("machine_code")

    # -------------------------------------------------------------------------
    # 机器码
    # -------------------------------------------------------------------------

    def get_machine_code(self) -> Optional[str]:
        """获取机器唯一码"""
        with self._lock:
            return self._config.get("machine_code")

    def set_machine_code(self, machine_code: str) -> bool:
        """设置并持久化机器唯一码"""
        with self._lock:
            self._config["machine_code"] = machine_code
            return self._save_config()

    # -------------------------------------------------------------------------
    # 客户端 ID
    # -------------------------------------------------------------------------

    def get_client_id(self) -> Optional[str]:
        """获取服务端分配的客户端 ID"""
        with self._lock:
            return self._config.get("client_id")

    def set_client_id(self, client_id: str) -> bool:
        """设置并持久化客户端 ID"""
        with self._lock:
            self._config["client_id"] = client_id
            return self._save_config()

    # -------------------------------------------------------------------------
    # 授权密钥
    # -------------------------------------------------------------------------

    def get_auth_key(self) -> Optional[str]:
        """获取授权密钥"""
        with self._lock:
            return self._config.get("auth_key")

    def set_auth_key(self, auth_key: str) -> bool:
        """设置并持久化授权密钥"""
        with self._lock:
            self._config["auth_key"] = auth_key
            return self._save_config()

    # -------------------------------------------------------------------------
    # 授权到期时间
    # -------------------------------------------------------------------------

    def get_expire_time(self) -> Optional[str]:
        """获取授权到期时间字符串"""
        with self._lock:
            return self._config.get("expire_time")

    def set_expire_time(self, expire_time: str) -> bool:
        """设置并持久化授权到期时间"""
        with self._lock:
            self._config["expire_time"] = expire_time
            return self._save_config()

    # -------------------------------------------------------------------------
    # 机器名称
    # -------------------------------------------------------------------------

    def get_machine_name(self) -> Optional[str]:
        """获取机器名称（主机名）"""
        with self._lock:
            return self._config.get("machine_name")

    def set_machine_name(self, machine_name: str) -> bool:
        """设置并持久化机器名称"""
        with self._lock:
            self._config["machine_name"] = machine_name
            return self._save_config()

    # -------------------------------------------------------------------------
    # IP 信息
    # -------------------------------------------------------------------------

    def get_ip_info(self) -> Optional[Dict]:
        """获取 IP 信息（含 internal_ip / external_ip / source）"""
        with self._lock:
            return self._config.get("ip_info")

    def set_ip_info(self, ip_info: Dict) -> bool:
        """设置并持久化 IP 信息"""
        with self._lock:
            self._config["ip_info"] = ip_info
            return self._save_config()

    # -------------------------------------------------------------------------
    # 操作系统信息
    # -------------------------------------------------------------------------

    def get_os_info(self) -> Optional[Dict]:
        """获取操作系统信息（含 type / version / arch / kernel）"""
        with self._lock:
            return self._config.get("os_info")

    def set_os_info(self, os_info: Dict) -> bool:
        """设置并持久化操作系统信息"""
        with self._lock:
            self._config["os_info"] = os_info
            return self._save_config()

    # -------------------------------------------------------------------------
    # 授权状态缓存
    # -------------------------------------------------------------------------

    def get_auth_cache(self) -> Optional[Dict]:
        """获取授权状态缓存（含 status 和 update_time）"""
        with self._lock:
            return self._config.get("auth_cache")

    def set_auth_cache(self, status: str) -> bool:
        """更新授权状态缓存，并记录当前时间戳"""
        with self._lock:
            self._config["auth_cache"] = {
                "status": status,
                "update_time": get_timestamp()
            }
            return self._save_config()

    # -------------------------------------------------------------------------
    # 首次运行时间戳
    # -------------------------------------------------------------------------

    def get_first_run_time(self) -> Optional[int]:
        """获取首次运行时间戳（Unix 秒）"""
        with self._lock:
            return self._config.get("first_run_time")

    def set_first_run_time(self) -> bool:
        """记录首次运行时间戳（仅首次写入，已有则跳过）"""
        with self._lock:
            if "first_run_time" not in self._config:
                self._config["first_run_time"] = get_timestamp()
                return self._save_config()
            return True

    # -------------------------------------------------------------------------
    # 最后心跳时间戳
    # -------------------------------------------------------------------------

    def get_last_heartbeat_time(self) -> Optional[int]:
        """获取最后一次心跳时间戳（Unix 秒）"""
        with self._lock:
            return self._config.get("last_heartbeat_time")

    def set_last_heartbeat_time(self) -> bool:
        """更新最后心跳时间戳为当前时间"""
        with self._lock:
            self._config["last_heartbeat_time"] = get_timestamp()
            return self._save_config()

    # -------------------------------------------------------------------------
    # 批量更新（减少 IO 次数）
    # -------------------------------------------------------------------------

    def update_registration_info(self, machine_code: str, auth_key: str,
                                  expire_time: str, machine_name: str,
                                  ip_info: Dict, os_info: Dict) -> bool:
        """
        批量更新注册相关字段（一次 IO 完成所有写入）。
        在首次注册或重新注册时调用。
        """
        with self._lock:
            self._config["machine_code"] = machine_code
            self._config["auth_key"]     = auth_key
            self._config["expire_time"]  = expire_time
            self._config["machine_name"] = machine_name
            self._config["ip_info"]      = ip_info
            self._config["os_info"]      = os_info
            self._config["first_run_time"] = self._config.get(
                "first_run_time", get_timestamp()
            )
            return self._save_config()

    def update_heartbeat_info(self, ip_info: Dict, os_info: Dict) -> bool:
        """
        批量更新心跳相关字段（IP 信息、系统信息、最后心跳时间）。
        在非首次运行的每次心跳后调用。
        """
        with self._lock:
            self._config["ip_info"]             = ip_info
            self._config["os_info"]             = os_info
            self._config["last_heartbeat_time"] = get_timestamp()
            return self._save_config()

    # -------------------------------------------------------------------------
    # Web 日志偏移量
    # -------------------------------------------------------------------------

    def get_web_log_offsets(self) -> Dict[str, Dict]:
        """
        获取 Web 日志文件读取偏移量映射。
        格式: {"/path/to/access.log": {"offset": 102400, "size": 102400, "mtime": ..., "inode": ...}}
        """
        with self._lock:
            offsets = self._config.get("web_log_offsets", {})
            return dict(offsets) if isinstance(offsets, dict) else {}

    def set_web_log_offsets(self, offsets: Dict[str, Dict]) -> bool:
        """持久化保存 Web 日志文件读取偏移量"""
        with self._lock:
            self._config["web_log_offsets"] = offsets
            return self._save_config()

    # -------------------------------------------------------------------------
    # Web 日志源配置
    # -------------------------------------------------------------------------

    def get_web_log_sources(self) -> List[Dict]:
        """
        获取 Web 日志源配置列表。
        每项格式: {"path": "/var/log/nginx/access.log", "type": "nginx", "enabled": true}
        """
        with self._lock:
            sources = self._config.get("web_log_sources", [])
            return list(sources) if isinstance(sources, list) else []

    def set_web_log_sources(self, sources: List[Dict]) -> bool:
        """持久化保存 Web 日志源配置列表"""
        with self._lock:
            self._config["web_log_sources"] = sources
            return self._save_config()

    # -------------------------------------------------------------------------
    # IP 白名单
    # -------------------------------------------------------------------------

    def get_ip_whitelist(self) -> List[str]:
        """获取服务端下发的IP白名单列表"""
        with self._lock:
            wl = self._config.get("ip_whitelist", [])
            return list(wl) if isinstance(wl, list) else []

    def set_ip_whitelist(self, whitelist: List[str]) -> bool:
        """持久化保存IP白名单列表"""
        with self._lock:
            self._config["ip_whitelist"] = whitelist
            return self._save_config()

    # -------------------------------------------------------------------------
    # 已封禁 IP 列表
    # -------------------------------------------------------------------------

    def get_blocked_ips(self) -> List[str]:
        """获取已封禁的IP列表"""
        with self._lock:
            blocked = self._config.get("blocked_ips", [])
            return list(blocked) if isinstance(blocked, list) else []

    def set_blocked_ips(self, blocked_ips: List[str]) -> bool:
        """持久化保存已封禁的IP列表"""
        with self._lock:
            self._config["blocked_ips"] = blocked_ips
            return self._save_config()

    # -------------------------------------------------------------------------
    # 工具方法
    # -------------------------------------------------------------------------

    def get_all_config(self) -> Dict:
        """返回完整配置字典的副本（含 settings 节和运行时状态）"""
        with self._lock:
            return self._config.copy()

    def clear_config(self) -> bool:
        """
        清空所有配置数据并持久化。
        警告：此操作不可逆，清空后程序下次启动将视为首次运行。
        """
        with self._lock:
            self._config = {}
            return self._save_config()

    @property
    def config_dir(self) -> str:
        """配置文件所在目录路径（即项目目录）"""
        return self._config_dir

    @property
    def config_file(self) -> str:
        """配置文件完整路径"""
        return self._config_file


# 全局单例
config_manager = ConfigManager()

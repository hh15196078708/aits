# -*- coding: utf-8 -*-
"""
模块名称: config_manager.py
模块功能: 配置文件读写、跨平台路径适配、持久化存储
依赖模块: 标准库 (os, json, threading)
系统适配: 所有平台通用

说明:
    本模块负责管理客户端配置：
    1. 跨平台配置目录自动适配
    2. JSON格式配置文件读写
    3. 权限检测与创建
    4. 存储机器码、授权密钥、基础信息、授权状态缓存
    5. 线程安全的读写操作
"""

import os  # 操作系统接口
import json  # JSON序列化
import threading  # 线程模块
from typing import Any, Dict, Optional  # 类型提示

# 导入本地模块
from constants import CONFIG_FILE_NAME  # 配置文件名
from system_adapter import system_adapter  # 系统适配器
from utils import (
    safe_file_read,  # 安全文件读取
    safe_file_write,  # 安全文件写入
    safe_json_loads,  # 安全JSON解析
    get_timestamp  # 获取时间戳
)


class ConfigManager:
    """
    配置管理器类
    
    功能: 管理客户端所有配置数据的持久化存储
    系统适配: 所有平台通用，路径自动适配
    
    配置数据结构:
    {
        "client_id": "服务端返回的客户端ID",
        "machine_code": "机器唯一标识",
        "auth_key": "授权密钥",
        "expire_time": "授权到期时间",
        "machine_name": "机器名称",
        "ip_info": {
            "internal_ip": "内网IP",
            "external_ip": "公网IP",
            "source": "采集来源"
        },
        "os_info": {
            "type": "系统类型",
            "version": "系统版本",
            "arch": "架构",
            "kernel": "内核版本"
        },
        "auth_cache": {
            "status": "授权状态",
            "update_time": "更新时间戳"
        },
        "first_run_time": "首次运行时间戳",
        "last_heartbeat_time": "最后心跳时间戳"
    }
    """
    
    _instance = None  # 单例实例
    _initialized = False  # 初始化标志
    
    def __new__(cls):
        """
        实现单例模式
        
        功能: 确保全局只有一个配置管理器实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化配置管理器
        
        功能: 加载现有配置或创建新配置
        参数: 无
        返回值: 无
        异常情况: 配置目录创建失败时会抛出异常
        """
        if ConfigManager._initialized:  # 避免重复初始化
            return
        
        self._config: Dict[str, Any] = {}  # 配置数据字典
        self._config_dir: str = ""  # 配置目录路径
        self._config_file: str = ""  # 配置文件路径
        self._lock = threading.Lock()  # 线程锁，保证读写安全
        
        self._init_config_path()  # 初始化配置路径
        self._load_config()  # 加载配置
        ConfigManager._initialized = True
    
    def _init_config_path(self) -> None:
        """
        初始化配置文件路径
        
        功能: 根据系统类型确定配置目录，并确保目录存在
        参数: 无
        返回值: 无
        异常情况: 目录创建失败时抛出异常
        """
        # 获取系统适配的配置目录
        self._config_dir = system_adapter.get_config_dir()
        
        # 确保目录存在并可写
        success, error_msg = system_adapter.ensure_dir_exists(self._config_dir)
        if not success:
            # 目录创建失败，抛出异常
            raise PermissionError(f"无法创建配置目录: {error_msg}")
        
        # 构建配置文件完整路径
        self._config_file = os.path.join(self._config_dir, CONFIG_FILE_NAME)
    
    def _load_config(self) -> None:
        """
        从文件加载配置
        
        功能: 读取配置文件并解析为字典
        参数: 无
        返回值: 无
        异常情况: 文件不存在或解析失败时使用空配置
        """
        with self._lock:  # 获取锁
            # 读取配置文件内容
            content = safe_file_read(self._config_file)
            
            if content:  # 文件存在且有内容
                # 解析JSON
                parsed = safe_json_loads(content, default={})
                if isinstance(parsed, dict):  # 确保是字典类型
                    self._config = parsed
                else:
                    self._config = {}  # 解析结果不是字典，使用空配置
            else:
                self._config = {}  # 文件不存在或为空
    
    def _save_config(self) -> bool:
        """
        保存配置到文件
        
        功能: 将配置字典序列化为JSON并写入文件
        参数: 无
        返回值: True表示成功，False表示失败
        异常情况: 写入失败时返回False
        """
        try:
            # 序列化为格式化的JSON（便于人工查看）
            content = json.dumps(
                self._config,
                ensure_ascii=False,  # 允许中文
                indent=2,  # 缩进2空格
                sort_keys=True  # 键排序
            )
            # 写入文件
            return safe_file_write(self._config_file, content)
        except Exception:
            return False
    
    def is_first_run(self) -> bool:
        """
        检查是否为首次运行
        
        功能: 判断是否为首次运行（配置文件不存在或无机器码）
        参数: 无
        返回值: True表示首次运行，False表示非首次
        异常情况: 无
        
        判断逻辑:
            1. 配置文件不存在 -> 首次运行
            2. 配置中没有machine_code -> 首次运行
            3. 其他情况 -> 非首次运行
        """
        with self._lock:
            # 检查配置中是否有机器码
            return not self._config.get("machine_code")
    
    def get_machine_code(self) -> Optional[str]:
        """
        获取机器码
        
        功能: 返回存储的机器唯一标识
        参数: 无
        返回值: 机器码字符串，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("machine_code")
    
    def set_machine_code(self, machine_code: str) -> bool:
        """
        设置机器码
        
        功能: 存储机器唯一标识并持久化
        参数:
            machine_code: 机器码字符串
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["machine_code"] = machine_code
            return self._save_config()
    
    def get_client_id(self) -> Optional[str]:
        """
        获取客户端ID
        
        功能: 返回服务端分配的客户端ID
        参数: 无
        返回值: 客户端ID字符串，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("client_id")
    
    def set_client_id(self, client_id: str) -> bool:
        """
        设置客户端ID
        
        功能: 存储服务端返回的客户端ID并持久化
        参数:
            client_id: 客户端ID字符串
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["client_id"] = client_id
            return self._save_config()
    
    def get_auth_key(self) -> Optional[str]:
        """
        获取授权密钥
        
        功能: 返回存储的授权密钥
        参数: 无
        返回值: 授权密钥字符串，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("auth_key")
    
    def set_auth_key(self, auth_key: str) -> bool:
        """
        设置授权密钥
        
        功能: 存储授权密钥并持久化
        参数:
            auth_key: 授权密钥字符串
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["auth_key"] = auth_key
            return self._save_config()
    
    def get_expire_time(self) -> Optional[str]:
        """
        获取授权到期时间
        
        功能: 返回授权到期时间字符串
        参数: 无
        返回值: 到期时间字符串，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("expire_time")
    
    def set_expire_time(self, expire_time: str) -> bool:
        """
        设置授权到期时间
        
        功能: 存储授权到期时间并持久化
        参数:
            expire_time: 到期时间字符串
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["expire_time"] = expire_time
            return self._save_config()
    
    def get_machine_name(self) -> Optional[str]:
        """
        获取机器名称
        
        功能: 返回存储的机器名称
        参数: 无
        返回值: 机器名称字符串，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("machine_name")
    
    def set_machine_name(self, machine_name: str) -> bool:
        """
        设置机器名称
        
        功能: 存储机器名称并持久化
        参数:
            machine_name: 机器名称字符串
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["machine_name"] = machine_name
            return self._save_config()
    
    def get_ip_info(self) -> Optional[Dict]:
        """
        获取IP信息
        
        功能: 返回存储的IP信息字典
        参数: 无
        返回值: IP信息字典，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("ip_info")
    
    def set_ip_info(self, ip_info: Dict) -> bool:
        """
        设置IP信息
        
        功能: 存储IP信息并持久化
        参数:
            ip_info: IP信息字典，包含internal_ip、external_ip、source
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["ip_info"] = ip_info
            return self._save_config()
    
    def get_os_info(self) -> Optional[Dict]:
        """
        获取操作系统信息
        
        功能: 返回存储的操作系统信息字典
        参数: 无
        返回值: 系统信息字典，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("os_info")
    
    def set_os_info(self, os_info: Dict) -> bool:
        """
        设置操作系统信息
        
        功能: 存储操作系统信息并持久化
        参数:
            os_info: 系统信息字典，包含type、version、arch、kernel
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["os_info"] = os_info
            return self._save_config()
    
    def get_auth_cache(self) -> Optional[Dict]:
        """
        获取授权缓存
        
        功能: 返回授权状态缓存信息
        参数: 无
        返回值: 缓存字典，包含status和update_time
        异常情况: 无
        """
        with self._lock:
            return self._config.get("auth_cache")
    
    def set_auth_cache(self, status: str) -> bool:
        """
        设置授权缓存
        
        功能: 更新授权状态缓存并记录时间
        参数:
            status: 授权状态（normal/expired）
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["auth_cache"] = {
                "status": status,
                "update_time": get_timestamp()
            }
            return self._save_config()
    
    def get_first_run_time(self) -> Optional[int]:
        """
        获取首次运行时间
        
        功能: 返回首次运行的时间戳
        参数: 无
        返回值: Unix时间戳，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("first_run_time")
    
    def set_first_run_time(self) -> bool:
        """
        设置首次运行时间
        
        功能: 记录首次运行时间戳
        参数: 无
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            if "first_run_time" not in self._config:  # 仅首次设置
                self._config["first_run_time"] = get_timestamp()
                return self._save_config()
            return True
    
    def get_last_heartbeat_time(self) -> Optional[int]:
        """
        获取最后心跳时间
        
        功能: 返回最后一次心跳的时间戳
        参数: 无
        返回值: Unix时间戳，不存在时返回None
        异常情况: 无
        """
        with self._lock:
            return self._config.get("last_heartbeat_time")
    
    def set_last_heartbeat_time(self) -> bool:
        """
        更新最后心跳时间
        
        功能: 记录当前心跳时间戳
        参数: 无
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["last_heartbeat_time"] = get_timestamp()
            return self._save_config()
    
    def update_registration_info(self, machine_code: str, auth_key: str, 
                                 expire_time: str, machine_name: str,
                                 ip_info: Dict, os_info: Dict) -> bool:
        """
        更新注册信息
        
        功能: 批量更新所有注册相关信息
        参数:
            machine_code: 机器码
            auth_key: 授权密钥
            expire_time: 到期时间
            machine_name: 机器名称
            ip_info: IP信息字典
            os_info: 系统信息字典
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        
        说明: 批量更新减少IO操作次数
        """
        with self._lock:
            self._config["machine_code"] = machine_code
            self._config["auth_key"] = auth_key
            self._config["expire_time"] = expire_time
            self._config["machine_name"] = machine_name
            self._config["ip_info"] = ip_info
            self._config["os_info"] = os_info
            self._config["first_run_time"] = self._config.get(
                "first_run_time", get_timestamp())
            return self._save_config()
    
    def update_heartbeat_info(self, ip_info: Dict, os_info: Dict) -> bool:
        """
        更新心跳相关信息
        
        功能: 更新IP和系统信息（非首次运行时调用）
        参数:
            ip_info: IP信息字典
            os_info: 系统信息字典
        返回值: True表示保存成功，False表示失败
        异常情况: 写入失败时返回False
        """
        with self._lock:
            self._config["ip_info"] = ip_info
            self._config["os_info"] = os_info
            self._config["last_heartbeat_time"] = get_timestamp()
            return self._save_config()
    
    def get_all_config(self) -> Dict:
        """
        获取所有配置
        
        功能: 返回完整的配置字典副本
        参数: 无
        返回值: 配置字典的副本
        异常情况: 无
        """
        with self._lock:
            return self._config.copy()
    
    def clear_config(self) -> bool:
        """
        清空配置
        
        功能: 删除所有配置数据
        参数: 无
        返回值: True表示成功，False表示失败
        异常情况: 无
        
        警告: 此操作不可逆，慎用
        """
        with self._lock:
            self._config = {}
            return self._save_config()
    
    @property
    def config_dir(self) -> str:
        """获取配置目录路径"""
        return self._config_dir
    
    @property
    def config_file(self) -> str:
        """获取配置文件路径"""
        return self._config_file


# 创建全局配置管理器实例
config_manager = ConfigManager()

# -*- coding: utf-8 -*-
"""
模块名称: auth_manager.py
模块功能: 授权密钥管理、授权状态校验、到期处理
依赖模块: 
    - 本地模块: config_manager, utils, constants
系统适配: 所有平台通用

说明:
    本模块负责授权管理：
    1. 授权密钥存储与读取
    2. 授权状态校验（缓存有效期5分钟）
    3. 启动时校验
    4. 到期处理（优雅退出）
    5. 离线兜底（10分钟宽限期）
"""

import time  # 时间相关
import threading  # 线程模块
from typing import Tuple, Optional  # 类型提示
from enum import Enum  # 枚举类型

# 导入本地模块
from config_manager import config_manager  # 配置管理器
from utils import get_timestamp, CachedValue  # 工具函数
from constants import (
    AUTH_CACHE_TTL,  # 授权缓存有效期
    OFFLINE_GRACE_PERIOD,  # 离线宽限期
    AUTH_STATUS_NORMAL,  # 授权正常状态
    AUTH_STATUS_EXPIRED  # 授权到期状态
)


class AuthState(Enum):
    """
    授权状态枚举
    
    功能: 定义所有可能的授权状态
    """
    VALID = "valid"  # 授权有效
    EXPIRED = "expired"  # 授权已到期
    UNKNOWN = "unknown"  # 未知状态（需要验证）
    OFFLINE_GRACE = "offline_grace"  # 离线宽限期内


class AuthManager:
    """
    授权管理器
    
    功能: 管理客户端授权状态
    系统适配: 所有平台通用
    
    核心功能:
        - 授权状态缓存（5分钟有效期）
        - 启动时校验
        - 运行中检测
        - 离线兜底（10分钟）
        - 优雅退出
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化授权管理器
        
        功能: 加载授权信息并初始化状态
        参数: 无
        返回值: 无
        异常情况: 无
        """
        if AuthManager._initialized:
            return
        
        self._auth_key: Optional[str] = None  # 授权密钥
        self._expire_time: Optional[str] = None  # 到期时间字符串
        self._auth_cache = CachedValue(ttl=AUTH_CACHE_TTL)  # 状态缓存
        self._offline_start_time: Optional[int] = None  # 离线开始时间
        self._shutdown_event = threading.Event()  # 关闭事件
        self._lock = threading.Lock()  # 线程锁
        
        self._load_auth_info()  # 加载授权信息
        AuthManager._initialized = True
    
    def _load_auth_info(self) -> None:
        """
        从配置加载授权信息
        
        功能: 读取持久化的授权密钥和到期时间
        参数: 无
        返回值: 无
        异常情况: 配置读取失败时保持默认值
        """
        self._auth_key = config_manager.get_auth_key()
        self._expire_time = config_manager.get_expire_time()
        
        # 加载授权缓存
        cache = config_manager.get_auth_cache()
        if cache:
            status = cache.get("status")
            update_time = cache.get("update_time", 0)
            # 检查缓存是否在有效期内
            if get_timestamp() - update_time < AUTH_CACHE_TTL:
                self._auth_cache.set(status)
    
    def get_auth_key(self) -> Optional[str]:
        """
        获取授权密钥
        
        功能: 返回当前授权密钥
        参数: 无
        返回值: 授权密钥字符串，未设置返回None
        异常情况: 无
        """
        return self._auth_key
    
    def set_auth_key(self, auth_key: str, expire_time: str) -> bool:
        """
        设置授权密钥
        
        功能: 保存授权密钥和到期时间
        参数:
            auth_key: 授权密钥
            expire_time: 到期时间字符串
        返回值: True表示保存成功
        异常情况: 保存失败返回False
        """
        with self._lock:
            self._auth_key = auth_key
            self._expire_time = expire_time
            
            # 持久化到配置文件
            success1 = config_manager.set_auth_key(auth_key)
            success2 = config_manager.set_expire_time(expire_time)
            
            # 设置授权状态为有效
            self._auth_cache.set(AUTH_STATUS_NORMAL)
            config_manager.set_auth_cache(AUTH_STATUS_NORMAL)
            
            return success1 and success2
    
    def update_auth_status(self, status: str) -> None:
        """
        更新授权状态
        
        功能: 根据心跳响应更新授权状态
        参数:
            status: 授权状态（normal/expired）
        返回值: 无
        异常情况: 无
        """
        with self._lock:
            self._auth_cache.set(status)
            config_manager.set_auth_cache(status)
            
            # 如果授权正常，重置离线计时器
            if status == AUTH_STATUS_NORMAL:
                self._offline_start_time = None
    
    def get_auth_state(self) -> AuthState:
        """
        获取当前授权状态
        
        功能: 返回授权状态枚举值
        参数: 无
        返回值: AuthState枚举
        异常情况: 无
        
        逻辑说明:
            1. 首先检查缓存
            2. 缓存无效时检查本地配置
            3. 均无有效数据时返回UNKNOWN
        """
        # 检查缓存
        cached_status = self._auth_cache.get()
        if cached_status:
            if cached_status == AUTH_STATUS_EXPIRED:
                return AuthState.EXPIRED
            elif cached_status == AUTH_STATUS_NORMAL:
                return AuthState.VALID
        
        # 缓存无效，检查配置
        cache = config_manager.get_auth_cache()
        if cache:
            status = cache.get("status")
            if status == AUTH_STATUS_EXPIRED:
                return AuthState.EXPIRED
        
        return AuthState.UNKNOWN
    
    def check_startup_auth(self) -> Tuple[bool, str]:
        """
        启动时授权校验
        
        功能: 程序启动时检查授权状态
        参数: 无
        返回值: (是否允许运行, 提示信息)
        异常情况: 无
        
        逻辑说明:
            1. 如果本地缓存显示已到期，直接拒绝
            2. 如果缓存有效且状态正常，允许运行
            3. 其他情况需要联网验证
        """
        state = self.get_auth_state()
        
        if state == AuthState.EXPIRED:
            return False, "授权已到期，不能使用任何功能"
        elif state == AuthState.VALID:
            return True, "授权校验通过"
        else:
            # 状态未知，需要联网验证
            return True, "需要联网验证授权状态"
    
    def check_runtime_auth(self) -> Tuple[bool, str]:
        """
        运行时授权校验
        
        功能: 根据心跳响应检查授权状态
        参数: 无
        返回值: (是否允许继续运行, 提示信息)
        异常情况: 无
        """
        state = self.get_auth_state()
        
        if state == AuthState.EXPIRED:
            return False, "授权已到期，程序即将退出"
        elif state == AuthState.VALID:
            return True, ""
        elif state == AuthState.OFFLINE_GRACE:
            return True, "离线模式，宽限期内"
        else:
            return True, "授权状态未知"
    
    def start_offline_timer(self) -> None:
        """
        启动离线计时器
        
        功能: 记录离线开始时间
        参数: 无
        返回值: 无
        异常情况: 无
        """
        with self._lock:
            if self._offline_start_time is None:
                self._offline_start_time = get_timestamp()
    
    def check_offline_grace(self) -> Tuple[bool, int]:
        """
        检查离线宽限期
        
        功能: 验证是否在离线宽限期内
        参数: 无
        返回值: (是否在宽限期内, 剩余秒数)
        异常情况: 无
        
        逻辑说明:
            - 离线状态下，如果本地记录授权未到期
            - 允许临时运行最长10分钟
        """
        with self._lock:
            # 如果没有开始离线计时，不在宽限期
            if self._offline_start_time is None:
                return True, OFFLINE_GRACE_PERIOD
            
            # 检查本地授权状态
            state = self.get_auth_state()
            if state == AuthState.EXPIRED:
                return False, 0
            
            # 计算已离线时间
            offline_duration = get_timestamp() - self._offline_start_time
            remaining = OFFLINE_GRACE_PERIOD - offline_duration
            
            if remaining > 0:
                return True, remaining
            else:
                return False, 0
    
    def reset_offline_timer(self) -> None:
        """
        重置离线计时器
        
        功能: 网络恢复后重置计时器
        参数: 无
        返回值: 无
        异常情况: 无
        """
        with self._lock:
            self._offline_start_time = None
    
    def is_auth_expired(self) -> bool:
        """
        检查授权是否到期
        
        功能: 快速判断授权是否已到期
        参数: 无
        返回值: True表示已到期
        异常情况: 无
        """
        return self.get_auth_state() == AuthState.EXPIRED
    
    def request_shutdown(self) -> None:
        """
        请求程序关闭
        
        功能: 设置关闭事件，通知主程序退出
        参数: 无
        返回值: 无
        异常情况: 无
        """
        self._shutdown_event.set()
    
    def is_shutdown_requested(self) -> bool:
        """
        检查是否请求关闭
        
        功能: 判断是否收到关闭请求
        参数: 无
        返回值: True表示已请求关闭
        异常情况: 无
        """
        return self._shutdown_event.is_set()
    
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        等待关闭事件
        
        功能: 阻塞等待关闭请求
        参数:
            timeout: 超时时间（秒），None表示无限等待
        返回值: True表示收到关闭请求
        异常情况: 无
        """
        return self._shutdown_event.wait(timeout)
    
    def handle_auth_expired(self) -> None:
        """
        处理授权到期
        
        功能: 授权到期时的处理逻辑
        参数: 无
        返回值: 无
        异常情况: 无
        
        说明: 设置状态并请求程序关闭
        """
        with self._lock:
            self._auth_cache.set(AUTH_STATUS_EXPIRED)
            config_manager.set_auth_cache(AUTH_STATUS_EXPIRED)
        
        self.request_shutdown()
    
    def has_valid_auth_key(self) -> bool:
        """
        检查是否有有效的授权密钥
        
        功能: 判断是否已设置授权密钥
        参数: 无
        返回值: True表示有授权密钥
        异常情况: 无
        """
        return bool(self._auth_key)


# 创建全局授权管理器实例
auth_manager = AuthManager()

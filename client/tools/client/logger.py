# -*- coding: utf-8 -*-
"""
模块名称: logger.py
模块功能: 日志管理，包括跨平台路径适配、大小切割、缓冲写入、速率限制
依赖模块: 标准库 (logging, os, time, threading)
系统适配: 所有平台通用

说明:
    本模块提供统一的日志管理功能：
    1. 跨平台日志目录自动适配
    2. 按文件大小自动切割（10MB）
    3. 缓冲写入减少IO
    4. 速率限制防止IO过高
    5. 同时输出到文件和控制台
"""

import os  # 操作系统接口
import time  # 时间相关功能
import logging  # Python标准日志模块
import threading  # 线程模块
from logging.handlers import RotatingFileHandler  # 按大小切割的日志处理器
from typing import Optional  # 类型提示

# 导入本地模块
from constants import (
    LOG_MAX_SIZE,  # 日志文件最大大小
    LOG_BACKUP_COUNT,  # 日志备份数量
    LOG_LEVEL,  # 日志级别
    LOG_FILE_PREFIX,  # 日志文件前缀
    DISK_IO_THROTTLE_THRESHOLD,  # IO节流阈值
    DISK_IO_THROTTLE_SLEEP  # IO节流休眠时间
)
from system_adapter import system_adapter  # 系统适配器


class IOThrottler:
    """
    IO速率限制器
    
    功能: 监控和限制日志写入速率，防止磁盘IO过高
    系统适配: 所有平台通用
    
    设计思路:
        使用滑动窗口算法统计每秒写入字节数，
        超过阈值时暂停写入一段时间。
    """
    
    def __init__(self, threshold_mb_per_sec: float = 9.0, sleep_time: float = 0.5):
        """
        初始化IO限制器
        
        功能: 设置IO限制参数
        参数:
            threshold_mb_per_sec: IO速率阈值（MB/秒），默认9MB/s
            sleep_time: 超限时休眠时间（秒），默认0.5秒
        返回值: 无
        异常情况: 无
        """
        self._threshold = threshold_mb_per_sec * 1024 * 1024  # 转换为字节/秒
        self._sleep_time = sleep_time  # 休眠时间
        self._bytes_written = 0  # 当前窗口已写入字节数
        self._window_start = time.time()  # 窗口开始时间
        self._lock = threading.Lock()  # 线程锁
    
    def check_and_throttle(self, bytes_to_write: int) -> None:
        """
        检查并执行速率限制
        
        功能: 检查当前IO速率，超限时暂停
        参数:
            bytes_to_write: 即将写入的字节数
        返回值: 无
        异常情况: 无
        系统适配: 所有平台通用
        
        资源优化:
            - 每秒重置计数窗口
            - 超限时仅休眠，不丢弃日志
        """
        with self._lock:  # 获取锁保证线程安全
            current_time = time.time()  # 获取当前时间
            
            # 检查是否需要重置窗口（超过1秒）
            if current_time - self._window_start >= 1.0:
                self._bytes_written = 0  # 重置计数
                self._window_start = current_time  # 更新窗口起始时间
            
            # 累加即将写入的字节数
            self._bytes_written += bytes_to_write
            
            # 检查是否超过阈值
            if self._bytes_written > self._threshold:
                # 超过阈值，休眠一段时间
                time.sleep(self._sleep_time)
                # 休眠后重置窗口
                self._bytes_written = 0
                self._window_start = time.time()


class ThrottledRotatingFileHandler(RotatingFileHandler):
    """
    带速率限制的轮转文件处理器
    
    功能: 继承RotatingFileHandler，添加IO速率限制
    系统适配: 所有平台通用
    
    设计思路:
        在写入日志前检查IO速率，超限时暂停写入，
        确保磁盘IO不超过阈值。
    """
    
    def __init__(self, filename, maxBytes=0, backupCount=0, 
                 encoding=None, throttler: Optional[IOThrottler] = None):
        """
        初始化处理器
        
        功能: 创建带速率限制的文件处理器
        参数:
            filename: 日志文件路径
            maxBytes: 单文件最大字节数
            backupCount: 备份文件数量
            encoding: 文件编码
            throttler: IO限制器实例
        返回值: 无
        异常情况: 无
        """
        super().__init__(filename, maxBytes=maxBytes, 
                        backupCount=backupCount, encoding=encoding)
        self._throttler = throttler  # 保存限制器引用
    
    def emit(self, record):
        """
        写入日志记录
        
        功能: 在写入前执行速率检查
        参数:
            record: 日志记录对象
        返回值: 无
        异常情况: 写入失败时不抛出异常
        """
        try:
            # 格式化日志消息
            msg = self.format(record)
            # 计算消息字节数（UTF-8编码）
            msg_bytes = len(msg.encode('utf-8', errors='replace'))
            
            # 执行速率限制检查
            if self._throttler:
                self._throttler.check_and_throttle(msg_bytes)
            
            # 调用父类方法写入日志
            super().emit(record)
        except Exception:
            # 忽略写入异常，防止日志系统崩溃
            self.handleError(record)


class ClientLogger:
    """
    客户端日志管理器
    
    功能: 提供统一的日志记录接口
    系统适配: 所有平台通用
    
    说明:
        - 同时输出到文件和控制台
        - 文件按大小自动切割
        - 带IO速率限制
        - 支持日志级别配置
    """
    
    _instance = None  # 单例实例
    _initialized = False  # 初始化标志
    
    def __new__(cls):
        """
        实现单例模式
        
        功能: 确保全局只有一个日志管理器实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化日志管理器
        
        功能: 配置日志处理器和格式
        参数: 无
        返回值: 无
        异常情况: 日志目录创建失败时会打印错误
        """
        if ClientLogger._initialized:  # 避免重复初始化
            return
        
        self._logger: Optional[logging.Logger] = None  # 日志器实例
        self._throttler: Optional[IOThrottler] = None  # IO限制器
        self._setup_logger()  # 设置日志器
        ClientLogger._initialized = True
    
    def _setup_logger(self) -> None:
        """
        配置日志器
        
        功能: 创建并配置日志处理器
        参数: 无
        返回值: 无
        异常情况: 目录创建失败时仅使用控制台输出
        """
        # 创建日志器
        self._logger = logging.getLogger("client")  # 获取名为client的日志器
        self._logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))  # 设置日志级别
        
        # 清除已有的处理器（防止重复添加）
        self._logger.handlers.clear()
        
        # 创建日志格式器
        # 格式: 时间 - 级别 - 模块名:行号 - 消息
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler()  # 创建控制台处理器
        console_handler.setLevel(logging.DEBUG)  # 控制台显示所有级别
        console_handler.setFormatter(formatter)  # 设置格式
        self._logger.addHandler(console_handler)  # 添加到日志器
        
        # 添加文件处理器
        self._setup_file_handler(formatter)
    
    def _setup_file_handler(self, formatter: logging.Formatter) -> None:
        """
        配置文件处理器
        
        功能: 创建带速率限制的文件处理器
        参数:
            formatter: 日志格式器
        返回值: 无
        异常情况: 目录创建失败时不添加文件处理器
        """
        # 获取日志目录
        log_dir = system_adapter.get_log_dir()
        
        # 确保目录存在
        success, error_msg = system_adapter.ensure_dir_exists(log_dir)
        if not success:
            # 目录创建失败，打印警告并仅使用控制台输出
            print(f"[警告] 无法创建日志目录: {error_msg}")
            return
        
        # 构建日志文件路径
        log_file = os.path.join(log_dir, f"{LOG_FILE_PREFIX}.log")
        
        # 创建IO限制器
        self._throttler = IOThrottler(
            threshold_mb_per_sec=DISK_IO_THROTTLE_THRESHOLD,
            sleep_time=DISK_IO_THROTTLE_SLEEP
        )
        
        try:
            # 创建带速率限制的文件处理器
            file_handler = ThrottledRotatingFileHandler(
                filename=log_file,
                maxBytes=LOG_MAX_SIZE,  # 单文件最大10MB
                backupCount=LOG_BACKUP_COUNT,  # 保留5个备份
                encoding="utf-8",  # 使用UTF-8编码
                throttler=self._throttler
            )
            file_handler.setLevel(logging.DEBUG)  # 文件记录所有级别
            file_handler.setFormatter(formatter)  # 设置格式
            self._logger.addHandler(file_handler)  # 添加到日志器
        except Exception as e:
            # 文件处理器创建失败
            print(f"[警告] 无法创建日志文件处理器: {e}")
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """
        记录DEBUG级别日志
        
        功能: 记录调试信息
        参数:
            msg: 日志消息
            *args, **kwargs: 格式化参数
        """
        if self._logger:
            self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """
        记录INFO级别日志
        
        功能: 记录一般信息
        参数:
            msg: 日志消息
            *args, **kwargs: 格式化参数
        """
        if self._logger:
            self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """
        记录WARNING级别日志
        
        功能: 记录警告信息
        参数:
            msg: 日志消息
            *args, **kwargs: 格式化参数
        """
        if self._logger:
            self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """
        记录ERROR级别日志
        
        功能: 记录错误信息
        参数:
            msg: 日志消息
            *args, **kwargs: 格式化参数
        """
        if self._logger:
            self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """
        记录CRITICAL级别日志
        
        功能: 记录严重错误信息
        参数:
            msg: 日志消息
            *args, **kwargs: 格式化参数
        """
        if self._logger:
            self._logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        """
        记录异常信息（含堆栈）
        
        功能: 记录异常信息，自动附加堆栈跟踪
        参数:
            msg: 日志消息
            *args, **kwargs: 格式化参数
        """
        if self._logger:
            self._logger.exception(msg, *args, **kwargs)


# 创建全局日志器实例
logger = ClientLogger()

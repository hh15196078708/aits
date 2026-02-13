# -*- coding: utf-8 -*-
"""
模块名称: resource_monitor.py
模块功能: 资源监控（CPU/内存/IO），包含节流和内存清理
依赖模块: 
    - 标准库: threading, time, gc
    - 第三方库: psutil>=5.9.0（可选）
系统适配: 所有平台通用

说明:
    本模块负责监控和控制资源占用：
    1. CPU监控：每5秒采样，超7%休眠0.1秒
    2. 内存监控：超280MB释放缓存
    3. 资源节流：防止程序占用过多系统资源
"""

import gc  # 垃圾回收
import time  # 时间相关
import threading  # 线程模块
from typing import Optional, Callable  # 类型提示

# 导入本地模块
from constants import (
    CPU_THROTTLE_THRESHOLD,  # CPU节流阈值
    CPU_THROTTLE_SLEEP,  # CPU节流休眠时间
    CPU_SAMPLE_INTERVAL,  # CPU采样间隔
    MEMORY_WARNING_THRESHOLD,  # 内存警告阈值
    MEMORY_PEAK_LIMIT  # 内存峰值上限
)
from utils import bytes_to_mb, force_gc  # 工具函数

# 尝试导入psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ResourceMonitor:
    """
    资源监控器
    
    功能: 监控CPU和内存使用情况，必要时进行节流
    系统适配: 所有平台通用
    
    资源限制:
        - CPU峰值: ≤8%
        - CPU平均: ≤5%
        - 内存峰值: ≤300MB
        - 内存常驻: ≤100MB
    
    节流策略:
        - CPU超7%时休眠0.1秒
        - 内存超280MB时执行GC
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
        初始化资源监控器
        
        功能: 创建监控线程和相关变量
        参数: 无
        返回值: 无
        异常情况: psutil不可用时降级处理
        """
        if ResourceMonitor._initialized:
            return
        
        self._running = False  # 运行标志
        self._monitor_thread: Optional[threading.Thread] = None  # 监控线程
        self._stop_event = threading.Event()  # 停止事件
        self._lock = threading.Lock()  # 线程锁
        
        # 资源使用统计
        self._cpu_samples = []  # CPU采样历史
        self._max_samples = 12  # 保留最近1分钟的采样（每5秒一次）
        
        # 回调函数
        self._on_cpu_high: Optional[Callable] = None  # CPU过高回调
        self._on_memory_high: Optional[Callable] = None  # 内存过高回调
        
        ResourceMonitor._initialized = True
    
    def start(self) -> None:
        """
        启动资源监控
        
        功能: 创建并启动后台监控线程
        参数: 无
        返回值: 无
        异常情况: 已运行时忽略
        """
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._stop_event.clear()
            
            # 创建守护线程
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="ResourceMonitor",
                daemon=True  # 守护线程，主程序退出时自动结束
            )
            self._monitor_thread.start()
    
    def stop(self) -> None:
        """
        停止资源监控
        
        功能: 停止后台监控线程
        参数: 无
        返回值: 无
        异常情况: 无
        """
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            self._stop_event.set()
            
            if self._monitor_thread:
                self._monitor_thread.join(timeout=2)
                self._monitor_thread = None
    
    def _monitor_loop(self) -> None:
        """
        监控循环
        
        功能: 后台线程的主循环
        参数: 无
        返回值: 无
        异常情况: 异常不中断循环
        
        监控频率: 每5秒执行一次
        """
        while not self._stop_event.is_set():
            try:
                # 检查CPU使用率
                self._check_cpu()
                
                # 检查内存使用
                self._check_memory()
            except Exception:
                pass  # 忽略异常，继续监控
            
            # 等待下一次采样
            self._stop_event.wait(CPU_SAMPLE_INTERVAL)
    
    def _check_cpu(self) -> None:
        """
        检查CPU使用率
        
        功能: 获取CPU使用率并执行节流
        参数: 无
        返回值: 无
        异常情况: psutil不可用时跳过
        
        节流策略: CPU超过7%时休眠0.1秒
        """
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            # 获取当前进程的CPU使用率
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)
            
            # 记录采样
            self._cpu_samples.append(cpu_percent)
            if len(self._cpu_samples) > self._max_samples:
                self._cpu_samples.pop(0)
            
            # 检查是否需要节流
            if cpu_percent > CPU_THROTTLE_THRESHOLD:
                time.sleep(CPU_THROTTLE_SLEEP)
                
                # 触发回调
                if self._on_cpu_high:
                    self._on_cpu_high(cpu_percent)
        except Exception:
            pass
    
    def _check_memory(self) -> None:
        """
        检查内存使用
        
        功能: 获取内存使用量并执行清理
        参数: 无
        返回值: 无
        异常情况: psutil不可用时跳过
        
        清理策略: 内存超过280MB时执行GC
        """
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            # 获取当前进程的内存使用
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = bytes_to_mb(memory_info.rss)
            
            # 检查是否需要清理
            if memory_mb > MEMORY_WARNING_THRESHOLD:
                # 执行垃圾回收
                force_gc()
                
                # 触发回调
                if self._on_memory_high:
                    self._on_memory_high(memory_mb)
        except Exception:
            pass
    
    def get_cpu_usage(self) -> float:
        """
        获取当前CPU使用率
        
        功能: 返回当前进程的CPU使用率
        参数: 无
        返回值: CPU使用率百分比
        异常情况: psutil不可用时返回0
        """
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            process = psutil.Process()
            return process.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    def get_memory_usage(self) -> float:
        """
        获取当前内存使用量
        
        功能: 返回当前进程的内存使用量（MB）
        参数: 无
        返回值: 内存使用量（MB）
        异常情况: psutil不可用时返回0
        """
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return bytes_to_mb(memory_info.rss)
        except Exception:
            return 0.0
    
    def get_avg_cpu_usage(self) -> float:
        """
        获取平均CPU使用率
        
        功能: 返回最近采样的平均CPU使用率
        参数: 无
        返回值: 平均CPU使用率百分比
        异常情况: 无采样数据时返回0
        """
        if not self._cpu_samples:
            return 0.0
        return round(sum(self._cpu_samples) / len(self._cpu_samples), 2)
    
    def throttle_if_needed(self) -> bool:
        """
        按需节流
        
        功能: 检查CPU使用率，必要时执行节流
        参数: 无
        返回值: True表示执行了节流
        异常情况: 无
        
        使用场景: 在高频操作前调用
        """
        cpu_usage = self.get_cpu_usage()
        if cpu_usage > CPU_THROTTLE_THRESHOLD:
            time.sleep(CPU_THROTTLE_SLEEP)
            return True
        return False
    
    def gc_if_needed(self) -> bool:
        """
        按需执行GC
        
        功能: 检查内存使用，必要时执行垃圾回收
        参数: 无
        返回值: True表示执行了GC
        异常情况: 无
        """
        memory_mb = self.get_memory_usage()
        if memory_mb > MEMORY_WARNING_THRESHOLD:
            force_gc()
            return True
        return False
    
    def set_cpu_callback(self, callback: Callable[[float], None]) -> None:
        """
        设置CPU过高回调
        
        功能: 设置CPU使用率过高时的回调函数
        参数:
            callback: 回调函数，参数为CPU使用率
        返回值: 无
        异常情况: 无
        """
        self._on_cpu_high = callback
    
    def set_memory_callback(self, callback: Callable[[float], None]) -> None:
        """
        设置内存过高回调
        
        功能: 设置内存使用过高时的回调函数
        参数:
            callback: 回调函数，参数为内存使用量（MB）
        返回值: 无
        异常情况: 无
        """
        self._on_memory_high = callback
    
    def is_resource_ok(self) -> bool:
        """
        检查资源是否正常
        
        功能: 验证CPU和内存是否在限制范围内
        参数: 无
        返回值: True表示资源正常
        异常情况: psutil不可用时默认返回True
        """
        if not PSUTIL_AVAILABLE:
            return True
        
        try:
            cpu_ok = self.get_cpu_usage() <= CPU_THROTTLE_THRESHOLD
            memory_ok = self.get_memory_usage() <= MEMORY_PEAK_LIMIT
            return cpu_ok and memory_ok
        except Exception:
            return True


# 创建全局资源监控器实例
resource_monitor = ResourceMonitor()

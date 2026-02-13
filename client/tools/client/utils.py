# -*- coding: utf-8 -*-
"""
模块名称: utils.py
模块功能: 通用工具函数，包括数据格式化、异常处理、资源监控辅助等
依赖模块: 标准库 (os, sys, time, json, uuid, hashlib, gc)
系统适配: 所有平台通用

说明:
    本模块提供各模块共用的工具函数，包括：
    1. 数据格式化（字节转GB、时间格式化等）
    2. UUID生成与持久化
    3. JSON安全读写
    4. 异常处理装饰器
    5. 内存清理辅助函数
"""

import os  # 操作系统接口，用于文件路径操作
import sys  # 系统相关功能，用于获取Python版本等
import time  # 时间相关功能，用于时间戳和延时
import json  # JSON序列化/反序列化
import uuid  # UUID生成，用于机器码兜底
import hashlib  # 哈希算法，用于生成唯一标识
import gc  # 垃圾回收，用于内存清理
import threading  # 线程模块，用于线程安全操作
from functools import wraps  # 装饰器辅助函数
from typing import Any, Dict, Optional, Callable, Tuple  # 类型提示


def bytes_to_gb(bytes_value: int, decimal_places: int = 2) -> float:
    """
    将字节数转换为GB单位
    
    功能: 将字节数转换为GB，保留指定小数位
    参数:
        bytes_value: 字节数，整数类型
        decimal_places: 小数位数，默认2位
    返回值: 转换后的GB值，浮点数
    异常情况: 输入非数字时返回0.0
    系统适配: 所有平台通用
    """
    try:
        # 1GB = 1024^3 字节 = 1073741824 字节
        gb_value = bytes_value / (1024 ** 3)  # 将字节转换为GB
        return round(gb_value, decimal_places)  # 四舍五入到指定小数位
    except (TypeError, ValueError):  # 处理非数字输入
        return 0.0  # 异常时返回0.0作为兜底值


def bytes_to_mb(bytes_value: int, decimal_places: int = 2) -> float:
    """
    将字节数转换为MB单位
    
    功能: 将字节数转换为MB，保留指定小数位
    参数:
        bytes_value: 字节数，整数类型
        decimal_places: 小数位数，默认2位
    返回值: 转换后的MB值，浮点数
    异常情况: 输入非数字时返回0.0
    系统适配: 所有平台通用
    """
    try:
        # 1MB = 1024^2 字节 = 1048576 字节
        mb_value = bytes_value / (1024 ** 2)  # 将字节转换为MB
        return round(mb_value, decimal_places)  # 四舍五入到指定小数位
    except (TypeError, ValueError):  # 处理非数字输入
        return 0.0  # 异常时返回0.0作为兜底值


def get_timestamp() -> int:
    """
    获取当前Unix时间戳（秒级）
    
    功能: 返回当前时间的Unix时间戳
    参数: 无
    返回值: 整数时间戳
    异常情况: 无
    系统适配: 所有平台通用
    """
    return int(time.time())  # 获取当前时间戳并转为整数


def get_timestamp_ms() -> int:
    """
    获取当前Unix时间戳（毫秒级）
    
    功能: 返回当前时间的Unix时间戳（毫秒）
    参数: 无
    返回值: 整数时间戳（毫秒）
    异常情况: 无
    系统适配: 所有平台通用
    """
    return int(time.time() * 1000)  # 获取当前时间戳乘以1000得到毫秒


def format_datetime(timestamp: Optional[int] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳为可读字符串
    
    功能: 将Unix时间戳转换为格式化的日期时间字符串
    参数:
        timestamp: Unix时间戳，默认为当前时间
        fmt: 日期时间格式字符串，默认为 YYYY-MM-DD HH:MM:SS
    返回值: 格式化后的日期时间字符串
    异常情况: 时间戳无效时返回空字符串
    系统适配: 所有平台通用
    """
    try:
        if timestamp is None:  # 如果未提供时间戳
            timestamp = get_timestamp()  # 使用当前时间戳
        # 将时间戳转换为本地时间结构，再格式化为字符串
        return time.strftime(fmt, time.localtime(timestamp))
    except (OSError, ValueError, OverflowError):  # 处理无效时间戳
        return ""  # 异常时返回空字符串


def generate_uuid() -> str:
    """
    生成唯一的UUID字符串
    
    功能: 生成一个随机的UUID4字符串，用于机器码兜底
    参数: 无
    返回值: 32位UUID字符串（不含连字符）
    异常情况: 无
    系统适配: 所有平台通用
    """
    # 使用uuid4生成随机UUID，移除连字符并转为大写
    return str(uuid.uuid4()).replace("-", "").upper()


def generate_machine_uuid(seed: str = "") -> str:
    """
    基于种子生成确定性的机器UUID
    
    功能: 根据种子字符串生成确定性的UUID，相同种子生成相同UUID
    参数:
        seed: 种子字符串，为空时使用随机UUID
    返回值: 32位UUID字符串
    异常情况: 种子为空时生成随机UUID
    系统适配: 所有平台通用
    """
    if not seed:  # 如果没有提供种子
        return generate_uuid()  # 生成随机UUID
    # 使用SHA256对种子进行哈希，取前32位作为机器ID
    hash_obj = hashlib.sha256(seed.encode("utf-8"))  # 创建SHA256哈希对象
    return hash_obj.hexdigest()[:32].upper()  # 取前32位并转大写


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    安全地解析JSON字符串
    
    功能: 解析JSON字符串，失败时返回默认值
    参数:
        json_str: JSON格式字符串
        default: 解析失败时的默认返回值
    返回值: 解析后的Python对象，失败时返回default
    异常情况: JSON格式错误时返回default
    系统适配: 所有平台通用
    """
    try:
        return json.loads(json_str)  # 尝试解析JSON字符串
    except (json.JSONDecodeError, TypeError, ValueError):  # 处理解析错误
        return default  # 返回默认值


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    安全地序列化对象为JSON字符串
    
    功能: 将Python对象序列化为JSON字符串，失败时返回默认值
    参数:
        obj: 要序列化的Python对象
        default: 序列化失败时的默认返回值
    返回值: JSON格式字符串
    异常情况: 序列化失败时返回default
    系统适配: 所有平台通用
    """
    try:
        # 序列化为JSON，确保中文正常显示，使用紧凑格式
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError):  # 处理序列化错误
        return default  # 返回默认值


def safe_file_read(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """
    安全地读取文件内容
    
    功能: 读取文件全部内容，失败时返回None
    参数:
        file_path: 文件路径
        encoding: 文件编码，默认UTF-8
    返回值: 文件内容字符串，失败时返回None
    异常情况: 文件不存在或读取失败时返回None
    系统适配: 所有平台通用
    """
    try:
        with open(file_path, "r", encoding=encoding) as f:  # 以只读模式打开文件
            return f.read()  # 读取并返回全部内容
    except (IOError, OSError, UnicodeDecodeError):  # 处理文件读取错误
        return None  # 返回None表示读取失败


def safe_file_write(file_path: str, content: str, encoding: str = "utf-8") -> bool:
    """
    安全地写入文件内容
    
    功能: 将内容写入文件，自动创建目录
    参数:
        file_path: 文件路径
        content: 要写入的内容
        encoding: 文件编码，默认UTF-8
    返回值: True表示成功，False表示失败
    异常情况: 权限不足或磁盘满时返回False
    系统适配: 所有平台通用
    """
    try:
        # 获取文件所在目录
        dir_path = os.path.dirname(file_path)  # 提取目录路径
        if dir_path and not os.path.exists(dir_path):  # 如果目录不存在
            os.makedirs(dir_path, exist_ok=True)  # 递归创建目录
        with open(file_path, "w", encoding=encoding) as f:  # 以写模式打开文件
            f.write(content)  # 写入内容
        return True  # 返回成功
    except (IOError, OSError, PermissionError):  # 处理写入错误
        return False  # 返回失败


def force_gc() -> None:
    """
    强制执行垃圾回收
    
    功能: 手动触发Python垃圾回收，释放未使用的内存
    参数: 无
    返回值: 无
    异常情况: 无
    系统适配: 所有平台通用
    """
    gc.collect()  # 执行垃圾回收


def get_python_version() -> Tuple[int, int, int]:
    """
    获取当前Python版本
    
    功能: 返回Python版本号元组
    参数: 无
    返回值: (主版本号, 次版本号, 修订号) 元组
    异常情况: 无
    系统适配: 所有平台通用
    """
    return sys.version_info[:3]  # 返回版本号的前三位


def check_python_version(min_version: Tuple[int, int] = (3, 6)) -> bool:
    """
    检查Python版本是否满足最低要求
    
    功能: 验证当前Python版本是否高于指定最低版本
    参数:
        min_version: 最低版本要求，默认(3, 6)
    返回值: True表示版本满足要求，False表示不满足
    异常情况: 无
    系统适配: 所有平台通用
    """
    current = sys.version_info[:2]  # 获取当前版本的主版本号和次版本号
    return current >= min_version  # 比较版本号


def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                       exceptions: Tuple = (Exception,)) -> Callable:
    """
    异常重试装饰器
    
    功能: 装饰函数，在发生指定异常时自动重试
    参数:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
        exceptions: 需要捕获的异常类型元组
    返回值: 装饰器函数
    异常情况: 重试次数用尽后抛出最后一次异常
    系统适配: 所有平台通用
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)  # 保留原函数的元信息
        def wrapper(*args, **kwargs):
            last_exception = None  # 记录最后一次异常
            for attempt in range(max_retries):  # 循环尝试
                try:
                    return func(*args, **kwargs)  # 尝试执行函数
                except exceptions as e:  # 捕获指定异常
                    last_exception = e  # 记录异常
                    if attempt < max_retries - 1:  # 如果还有重试机会
                        time.sleep(delay)  # 等待指定时间后重试
            raise last_exception  # 重试用尽，抛出最后一次异常
        return wrapper
    return decorator


class ThreadSafeDict:
    """
    线程安全的字典类
    
    功能: 提供线程安全的字典操作
    系统适配: 所有平台通用
    """
    
    def __init__(self):
        """
        初始化线程安全字典
        
        功能: 创建内部字典和锁
        参数: 无
        返回值: 无
        异常情况: 无
        """
        self._dict: Dict = {}  # 内部字典存储数据
        self._lock = threading.Lock()  # 创建线程锁保证安全
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取键对应的值
        
        功能: 线程安全地获取字典值
        参数:
            key: 键名
            default: 键不存在时的默认值
        返回值: 键对应的值或默认值
        异常情况: 无
        """
        with self._lock:  # 获取锁
            return self._dict.get(key, default)  # 获取值
    
    def set(self, key: str, value: Any) -> None:
        """
        设置键值对
        
        功能: 线程安全地设置字典值
        参数:
            key: 键名
            value: 值
        返回值: 无
        异常情况: 无
        """
        with self._lock:  # 获取锁
            self._dict[key] = value  # 设置值
    
    def delete(self, key: str) -> bool:
        """
        删除指定键
        
        功能: 线程安全地删除字典键
        参数:
            key: 要删除的键名
        返回值: True表示删除成功，False表示键不存在
        异常情况: 无
        """
        with self._lock:  # 获取锁
            if key in self._dict:  # 检查键是否存在
                del self._dict[key]  # 删除键
                return True  # 返回成功
            return False  # 键不存在
    
    def clear(self) -> None:
        """
        清空字典
        
        功能: 线程安全地清空所有键值对
        参数: 无
        返回值: 无
        异常情况: 无
        """
        with self._lock:  # 获取锁
            self._dict.clear()  # 清空字典
    
    def to_dict(self) -> Dict:
        """
        返回字典的副本
        
        功能: 返回内部字典的浅拷贝
        参数: 无
        返回值: 字典副本
        异常情况: 无
        """
        with self._lock:  # 获取锁
            return self._dict.copy()  # 返回副本


class CachedValue:
    """
    带过期时间的缓存值类
    
    功能: 存储带TTL（生存时间）的缓存值
    系统适配: 所有平台通用
    """
    
    def __init__(self, ttl: int = 300):
        """
        初始化缓存值
        
        功能: 创建带TTL的缓存容器
        参数:
            ttl: 缓存有效期（秒），默认300秒（5分钟）
        返回值: 无
        异常情况: 无
        """
        self._value: Any = None  # 缓存的值
        self._expire_time: int = 0  # 过期时间戳
        self._ttl: int = ttl  # 缓存有效期
        self._lock = threading.Lock()  # 线程锁
    
    def get(self) -> Optional[Any]:
        """
        获取缓存值
        
        功能: 如果缓存未过期则返回值，否则返回None
        参数: 无
        返回值: 缓存值或None（已过期）
        异常情况: 无
        """
        with self._lock:  # 获取锁
            if get_timestamp() < self._expire_time:  # 检查是否过期
                return self._value  # 未过期，返回值
            return None  # 已过期，返回None
    
    def set(self, value: Any) -> None:
        """
        设置缓存值
        
        功能: 设置缓存值并更新过期时间
        参数:
            value: 要缓存的值
        返回值: 无
        异常情况: 无
        """
        with self._lock:  # 获取锁
            self._value = value  # 设置值
            self._expire_time = get_timestamp() + self._ttl  # 计算过期时间
    
    def invalidate(self) -> None:
        """
        使缓存失效
        
        功能: 立即使当前缓存过期
        参数: 无
        返回值: 无
        异常情况: 无
        """
        with self._lock:  # 获取锁
            self._expire_time = 0  # 设置过期时间为0，立即失效
    
    def is_valid(self) -> bool:
        """
        检查缓存是否有效
        
        功能: 判断缓存是否在有效期内
        参数: 无
        返回值: True表示有效，False表示已过期
        异常情况: 无
        """
        with self._lock:  # 获取锁
            return get_timestamp() < self._expire_time  # 比较当前时间和过期时间

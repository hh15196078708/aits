# -*- coding: utf-8 -*-
"""
模块名称: main.py
模块功能: 程序入口，包括初始化、注册、心跳定时器、信号处理
依赖模块: 所有本地模块
系统适配: 所有平台通用

说明:
    本模块是客户端程序的入口点：
    1. 系统兼容性检查
    2. 初始化所有模块
    3. 首次运行注册/非首次更新
    4. 启动心跳定时器（非阻塞）
    5. 信号处理（优雅退出）
    6. 守护进程模式
"""

import sys  # 系统相关
import signal  # 信号处理
import threading  # 线程模块
import time  # 时间相关
from typing import Optional  # 类型提示

# 导入本地模块
from constants import (
    HEARTBEAT_INTERVAL,  # 心跳间隔
    AUTH_STATUS_EXPIRED,  # 授权到期状态
    AUTH_STATUS_NORMAL,  # 授权正常状态
    MIN_PYTHON_VERSION,  # 最低Python版本
    PROJECT_ID
)
from utils import check_python_version, format_datetime, get_timestamp  # 工具函数
from system_adapter import system_adapter  # 系统适配器
from logger import logger  # 日志管理器
from config_manager import config_manager  # 配置管理器
from hardware_collector import hardware_collector  # 硬件采集器
from network_client import network_client  # 网络客户端
from auth_manager import auth_manager  # 授权管理器
from resource_monitor import resource_monitor  # 资源监控器


class ClientApplication:
    """
    客户端应用程序主类
    
    功能: 管理客户端程序的生命周期
    系统适配: 所有平台通用
    
    生命周期:
        1. 初始化 -> 2. 注册/更新 -> 3. 心跳循环 -> 4. 优雅退出
    """
    
    def __init__(self):
        """
        初始化客户端应用
        
        功能: 设置初始状态
        参数: 无
        返回值: 无
        异常情况: 无
        """
        self._running = False  # 运行标志
        self._heartbeat_thread: Optional[threading.Thread] = None  # 心跳线程
        self._stop_event = threading.Event()  # 停止事件
        self._client_id: str = ""  # 客户端ID（服务端分配）
        self._machine_code: str = ""  # 机器码
        self._auth_key: str = ""  # 授权密钥
    
    def run(self) -> int:
        """
        运行客户端程序
        
        功能: 程序主入口
        参数: 无
        返回值: 退出码（0成功，1失败）
        异常情况: 捕获所有异常并优雅退出
        """
        try:
            # 步骤1：系统兼容性检查
            if not self._check_compatibility():
                return 1
            
            # 步骤2：初始化各模块
            if not self._initialize():
                return 1
            
            # 步骤3：启动时授权校验
            if not self._check_startup_auth():
                return 1
            
            # 步骤4：注册或更新信息
            if not self._register_or_update():
                return 1
            
            # 步骤5：设置信号处理
            self._setup_signal_handlers()
            
            # 步骤6：启动资源监控
            resource_monitor.start()
            
            # 步骤7：启动心跳
            self._start_heartbeat()
            
            # 步骤8：主循环等待
            self._main_loop()
            
            return 0
        except KeyboardInterrupt:
            logger.info("收到中断信号，程序退出")
            return 0
        except Exception as e:
            logger.exception(f"程序运行异常: {e}")
            return 1
        finally:
            self._shutdown()
    
    def _check_compatibility(self) -> bool:
        """
        检查系统兼容性
        
        功能: 验证Python版本和操作系统是否支持
        参数: 无
        返回值: True表示兼容
        异常情况: 不兼容时打印错误信息
        """
        # 检查Python版本
        if not check_python_version(MIN_PYTHON_VERSION):
            print(f"错误: 需要Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}或更高版本")
            return False
        
        # 检查操作系统
        supported, message = system_adapter.is_supported()
        if not supported:
            print(f"警告: {message}")
            # 不强制退出，允许在非标准系统上尝试运行
        
        # 输出系统信息
        os_info = system_adapter.get_os_info()
        logger.info(f"系统类型: {os_info.get('type')}")
        logger.info(f"系统版本: {os_info.get('version')}")
        logger.info(f"系统架构: {os_info.get('arch')}")
        logger.info(f"主机名: {os_info.get('hostname')}")
        
        if os_info.get('distro'):
            logger.info(f"Linux发行版: {os_info.get('distro')}")
        
        return True
    
    def _initialize(self) -> bool:
        """
        初始化各模块
        
        功能: 初始化日志、配置、硬件采集等模块
        参数: 无
        返回值: True表示成功
        异常情况: 初始化失败时返回False
        """
        try:
            logger.info("开始初始化客户端...")
            
            # 检查配置目录
            config_dir = config_manager.config_dir
            logger.info(f"配置目录: {config_dir}")
            
            # 检查日志目录
            log_dir = system_adapter.get_log_dir()
            logger.info(f"日志目录: {log_dir}")
            
            # 检查硬件采集器
            if not hardware_collector.is_collector_available():
                logger.warning("硬件采集器初始化不完整，部分功能可能受限")
            
            logger.info("客户端初始化完成")
            return True
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def _check_startup_auth(self) -> bool:
        """
        启动时授权校验
        
        功能: 检查本地授权状态
        参数: 无
        返回值: True表示允许运行
        异常情况: 授权已到期时返回False
        """
        allowed, message = auth_manager.check_startup_auth()
        
        if not allowed:
            print(f"错误: {message}")
            logger.error(message)
            return False
        
        logger.info(message)
        return True
    
    def _register_or_update(self) -> bool:
        """
        注册或更新机器信息
        
        功能: 首次运行时注册，非首次时更新信息
        参数: 无
        返回值: True表示成功
        异常情况: 网络错误时允许离线运行
        """
        # 获取机器信息
        reg_data = hardware_collector.get_registration_data()
        self._machine_code = reg_data["machine_code"]
        machine_name = reg_data["machine_name"]
        ip_info = reg_data["ip_info"]
        os_info = reg_data["os_info"]
        
        logger.info(f"机器码: {self._machine_code}")
        logger.info(f"机器名: {machine_name}")
        logger.info(f"内网IP: {ip_info.get('internal_ip')}")
        
        # 判断是否首次运行
        is_first_run = config_manager.is_first_run()
        
        if is_first_run:
            logger.info("首次运行，开始注册...")
            return self._do_register(reg_data)
        else:
            logger.info("非首次运行，更新信息...")
            return self._do_update(reg_data)
    
    def _do_register(self, reg_data: dict) -> bool:
        """
        执行注册
        
        功能: 向服务端发送注册请求
        参数:
            reg_data: 注册数据
        返回值: True表示成功
        异常情况: 网络错误时返回False
        """
        success, client_id, auth_key, expire_time, error = network_client.register(
            machine_code=reg_data["machine_code"],
            machine_name=reg_data["machine_name"],
            ip_info=reg_data["ip_info"],
            os_info=reg_data["os_info"]
        )
        
        if success:
            # 保存客户端ID（服务端分配）
            self._client_id = client_id or ""
            if client_id:
                config_manager.set_client_id(client_id)
                logger.info(f"客户端ID: {client_id}")
            
            # 保存授权密钥
            self._auth_key = auth_key or ""
            if auth_key:
                auth_manager.set_auth_key(auth_key, expire_time or "")
            
            config_manager.update_registration_info(
                machine_code=reg_data["machine_code"],
                auth_key=auth_key or "",
                expire_time=expire_time or "",
                machine_name=reg_data["machine_name"],
                ip_info=reg_data["ip_info"],
                os_info=reg_data["os_info"]
            )
            
            logger.info("注册成功")
            if expire_time:
                logger.info(f"授权到期时间: {expire_time}")
            return True
        else:
            logger.error(f"注册失败: {error}")
            print(f"注册失败: {error}")
            return False
    
    def _do_update(self, reg_data: dict) -> bool:
        """
        执行信息更新
        
        功能: 向服务端更新机器信息
        参数:
            reg_data: 注册数据
        返回值: True表示成功（网络失败时允许离线运行）
        异常情况: 无
        """
        # 从配置加载客户端ID和授权密钥
        self._client_id = config_manager.get_client_id() or ""
        self._auth_key = config_manager.get_auth_key() or ""
        
        logger.info(f"客户端ID: {self._client_id}")
        
        # 设置网络客户端的授权密钥
        if self._auth_key:
            network_client.set_auth_key(self._auth_key)
        
        success, error = network_client.update_info(
            machine_code=reg_data["machine_code"],
            machine_name=reg_data["machine_name"],
            ip_info=reg_data["ip_info"],
            os_info=reg_data["os_info"]
        )
        
        if success:
            # 更新本地配置
            config_manager.update_heartbeat_info(
                ip_info=reg_data["ip_info"],
                os_info=reg_data["os_info"]
            )
            logger.info("信息更新成功")
        else:
            logger.warning(f"信息更新失败: {error}，将使用离线模式")
            auth_manager.start_offline_timer()
        
        # 更新失败不阻止程序运行
        return True
    
    def _setup_signal_handlers(self) -> None:
        """
        设置信号处理器
        
        功能: 注册SIGINT和SIGTERM信号处理
        参数: 无
        返回值: 无
        异常情况: Windows部分信号不支持
        """
        def signal_handler(signum, frame):
            """信号处理函数"""
            logger.info(f"收到信号 {signum}，准备退出...")
            self._stop_event.set()
            auth_manager.request_shutdown()
        
        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
        
        # Windows不支持SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def _start_heartbeat(self) -> None:
        """
        启动心跳线程
        
        功能: 创建并启动心跳发送线程
        参数: 无
        返回值: 无
        异常情况: 无
        """
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="HeartbeatThread",
            daemon=True
        )
        self._heartbeat_thread.start()
        logger.info(f"心跳线程已启动，间隔{HEARTBEAT_INTERVAL}秒")
    
    def _heartbeat_loop(self) -> None:
        """
        心跳循环
        
        功能: 定时发送心跳请求
        参数: 无
        返回值: 无
        异常情况: 异常不中断循环
        
        资源优化:
            - 使用Event.wait()非阻塞等待
            - 节流防止CPU过高
        """
        while not self._stop_event.is_set():
            try:
                # 发送心跳
                self._send_heartbeat()
                
                # 检查授权状态
                if auth_manager.is_auth_expired():
                    logger.warning("授权已到期，程序将退出")
                    auth_manager.handle_auth_expired()
                    break
                
                # 检查离线宽限期
                in_grace, remaining = auth_manager.check_offline_grace()
                if not in_grace:
                    logger.warning("离线宽限期已过，程序将退出")
                    auth_manager.request_shutdown()
                    break
                
                # 资源节流
                resource_monitor.throttle_if_needed()
                resource_monitor.gc_if_needed()
            except Exception as e:
                print(e)
                logger.error(f"心跳异常: {e}")
            
            # 等待下一次心跳（非阻塞）
            self._stop_event.wait(HEARTBEAT_INTERVAL)
    
    def _send_heartbeat(self) -> None:
        """
        发送心跳
        
        功能: 采集硬件数据并发送心跳请求
        参数: 无
        返回值: 无
        异常情况: 网络失败时启动离线计时器
        """
        # 采集心跳数据
        heartbeat_data = hardware_collector.collect_all()
        print(heartbeat_data)
        print("==============")
        # 发送心跳
        success, auth_status, error = network_client.heartbeat(
            client_id=self._client_id,
            machine_code=self._machine_code,
            auth_key=self._auth_key,
            heartbeat_data=heartbeat_data
        )
        
        if success:
            # 更新授权状态
            auth_manager.update_auth_status(auth_status)
            auth_manager.reset_offline_timer()
            
            # 更新心跳时间
            config_manager.set_last_heartbeat_time()
            
            if auth_status == AUTH_STATUS_EXPIRED:
                logger.warning("服务端返回授权已到期")
                auth_manager.handle_auth_expired()
            else:
                logger.info(f"心跳成功 [{format_datetime()}]")
        else:
            logger.warning(f"心跳失败: {error}")
            auth_manager.start_offline_timer()
    
    def _main_loop(self) -> None:
        """
        主循环
        
        功能: 等待程序退出
        参数: 无
        返回值: 无
        异常情况: 无
        """
        logger.info("客户端运行中，按Ctrl+C退出...")
        
        # 等待关闭信号
        while not auth_manager.is_shutdown_requested():
            if self._stop_event.wait(1):
                break
    
    def _shutdown(self) -> None:
        """
        优雅退出
        
        功能: 关闭所有资源和线程
        参数: 无
        返回值: 无
        异常情况: 无
        """
        logger.info("正在关闭客户端...")
        
        # 设置停止标志
        self._running = False
        self._stop_event.set()
        
        # 停止资源监控
        try:
            resource_monitor.stop()
        except Exception:
            pass
        
        # 等待心跳线程结束
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2)
        
        # 关闭网络客户端
        try:
            network_client.close()
        except Exception:
            pass
        
        logger.info("客户端已关闭")


def main():
    """
    程序入口函数
    
    功能: 创建并运行客户端应用
    参数: 无
    返回值: 退出码
    """
    app = ClientApplication()
    return app.run()


if __name__ == "__main__":
    # 程序入口点
    sys.exit(main())

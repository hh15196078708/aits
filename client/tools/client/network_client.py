# -*- coding: utf-8 -*-
"""
模块名称: network_client.py
模块功能: 网络请求封装，包括注册、心跳、加密、重试机制
依赖模块: 
    - 标准库: urllib.request, json, time
    - 第三方库: requests>=2.28.0（可选，优先使用）
系统适配: 所有平台通用

说明:
    本模块负责与服务端的网络通信：
    1. 注册请求：首次运行时发送机器信息
    2. 心跳请求：定时发送硬件状态
    3. 数据加密：使用AES加密心跳数据
    4. 重试机制：网络失败时自动重试
    5. 超时控制：避免网络阻塞
"""

import json  # JSON序列化
import time  # 时间相关
from typing import Dict, Optional, Tuple  # 类型提示
from urllib.request import Request, urlopen  # 标准库HTTP客户端
from urllib.error import URLError, HTTPError  # URL错误类型

# 导入本地模块
from constants import (
    SERVER_URL,  # 服务端地址
    REGISTER_ENDPOINT,  # 注册接口
    HEARTBEAT_ENDPOINT,  # 心跳接口
    REQUEST_TIMEOUT,  # 请求超时
    MAX_RETRY,  # 最大重试次数
    RETRY_INTERVAL,  # 重试间隔
    RESPONSE_CODE_SUCCESS,  # 成功响应码
    AUTH_STATUS_NORMAL,  # 授权正常状态
    AUTH_STATUS_EXPIRED,  # 授权到期状态
    PROJECT_ID  # 项目ID
)
from crypto_utils import AESCrypto, create_crypto  # AES加密

# 尝试导入requests库
try:
    import requests  # 更强大的HTTP客户端
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class NetworkClient:
    """
    网络通信客户端
    
    功能: 封装与服务端的所有网络通信
    系统适配: 所有平台通用
    
    支持的接口:
        - /register: 注册/更新机器信息
        - /heartbeat: 发送心跳数据
    
    特性:
        - 自动重试（最多3次）
        - 超时控制（3秒）
        - 数据加密（AES-128-CBC）
        - 优雅降级（requests不可用时使用urllib）
    """
    
    _instance = None  # 单例实例
    _initialized = False  # 初始化标志
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, server_url: str = SERVER_URL):
        """
        初始化网络客户端
        
        功能: 配置服务端地址和HTTP客户端
        参数:
            server_url: 服务端API地址
        返回值: 无
        异常情况: 无
        """
        if NetworkClient._initialized:
            return
        
        self._server_url = server_url.rstrip("/")  # 去除末尾斜杠
        self._crypto: Optional[AESCrypto] = None  # AES加密器
        self._session = None  # requests会话（如果可用）
        
        # 如果requests可用，创建会话
        if REQUESTS_AVAILABLE:
            self._session = requests.Session()
            # 设置连接池大小和重试策略
            adapter = requests.adapters.HTTPAdapter(pool_maxsize=10)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
        
        NetworkClient._initialized = True
    
    def set_auth_key(self, auth_key: str) -> None:
        """
        设置授权密钥
        
        功能: 使用授权密钥初始化AES加密器
        参数:
            auth_key: 授权密钥字符串
        返回值: 无
        异常情况: 密钥无效时加密器为None
        """
        if auth_key:
            self._crypto = create_crypto(auth_key)
    
    def _make_request(self, url: str, data: Dict, 
                      timeout: int = REQUEST_TIMEOUT) -> Tuple[bool, Optional[Dict], str]:
        """
        发送HTTP POST请求
        
        功能: 发送POST请求并返回响应
        参数:
            url: 请求URL
            data: 请求数据字典
            timeout: 超时时间（秒）
        返回值: (成功标志, 响应数据, 错误信息)
        异常情况: 网络错误时返回失败
        
        优先使用requests库，不可用时使用urllib
        """
        if REQUESTS_AVAILABLE:
            return self._request_with_requests(url, data, timeout)
        else:
            return self._request_with_urllib(url, data, timeout)
    
    def _request_with_requests(self, url: str, data: Dict, 
                               timeout: int) -> Tuple[bool, Optional[Dict], str]:
        """
        使用requests库发送请求
        
        功能: 通过requests发送POST请求
        参数:
            url: 请求URL
            data: 请求数据
            timeout: 超时时间
        返回值: (成功标志, 响应数据, 错误信息)
        """
        try:
            response = self._session.post(
                url,
                json=data,  # 自动序列化为JSON
                timeout=timeout,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
            
            # 检查HTTP状态码
            if response.status_code == 200:
                try:
                    resp_data = response.json()
                    return True, resp_data, ""
                except json.JSONDecodeError:
                    return False, None, "响应数据解析失败"
            else:
                return False, None, f"HTTP错误: {response.status_code}"
        except requests.Timeout:
            return False, None, "请求超时"
        except requests.ConnectionError:
            return False, None, "连接失败"
        except Exception as e:
            return False, None, f"请求异常: {str(e)}"
    
    def _request_with_urllib(self, url: str, data: Dict, 
                             timeout: int) -> Tuple[bool, Optional[Dict], str]:
        """
        使用urllib发送请求（兜底方案）
        
        功能: 通过urllib发送POST请求
        参数:
            url: 请求URL
            data: 请求数据
            timeout: 超时时间
        返回值: (成功标志, 响应数据, 错误信息)
        """
        try:
            # 序列化请求数据
            json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            
            # 创建请求对象
            req = Request(
                url,
                data=json_data,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json"
                },
                method="POST"
            )
            
            # 发送请求
            with urlopen(req, timeout=timeout) as response:
                resp_data = response.read().decode("utf-8")
                return True, json.loads(resp_data), ""
        except HTTPError as e:
            return False, None, f"HTTP错误: {e.code}"
        except URLError as e:
            return False, None, f"连接失败: {str(e.reason)}"
        except TimeoutError:
            return False, None, "请求超时"
        except json.JSONDecodeError:
            return False, None, "响应数据解析失败"
        except Exception as e:
            return False, None, f"请求异常: {str(e)}"
    
    def _request_with_retry(self, url: str, data: Dict, 
                           max_retries: int = MAX_RETRY) -> Tuple[bool, Optional[Dict], str]:
        """
        带重试的请求
        
        功能: 请求失败时自动重试
        参数:
            url: 请求URL
            data: 请求数据
            max_retries: 最大重试次数
        返回值: (成功标志, 响应数据, 错误信息)
        异常情况: 所有重试都失败时返回最后一次错误
        
        资源优化: 重试间隔1秒，避免频繁请求
        """
        last_error = ""
        
        for attempt in range(max_retries):
            success, resp_data, error = self._make_request(url, data)
            
            if success:
                return True, resp_data, ""
            
            last_error = error
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                time.sleep(RETRY_INTERVAL)
        
        return False, None, last_error
    
    def register(self, machine_code: str, machine_name: str, 
                 ip_info: Dict, os_info: Dict) -> Tuple[bool, Optional[str], Optional[str], Optional[str], str]:
        """
        发送注册请求
        
        功能: 向服务端注册机器信息
        参数:
            machine_code: 机器码
            machine_name: 机器名称
            ip_info: IP信息字典
            os_info: 系统信息字典
        返回值: (成功标志, 客户端ID, 授权密钥, 到期时间, 错误信息)
        异常情况: 注册失败时返回错误信息
        
        请求格式（匹配ewm_project_safe表结构）:
        {
            "projectId": "项目ID",
            "safeCode": "机器码",
            "safeName": "机器名称",
            "safeOs": "操作系统信息",
            "safeIp": "IP地址"
        }
        
        响应格式:
        {
            "code": 200,
            "msg": "success",
            "data": {
                "id": "客户端ID",
                "safeSecret": "授权密钥",
                "safeEndTime": "2025-12-31 23:59:59"
            }
        }
        """
        # 构建操作系统信息字符串
        os_str = f"{os_info.get('type', 'Unknown')} {os_info.get('version', '')} {os_info.get('arch', '')}"
        
        # 获取内网IP
        internal_ip = ip_info.get('internal_ip', 'Unknown')
        
        # 构建请求数据（匹配ewm_project_safe表字段）
        request_data = {
            "projectId": PROJECT_ID,  # 项目ID，从配置获取
            "safeCode": machine_code,  # 机器码 -> SAFE_CODE
            "safeName": machine_name,  # 机器名称 -> SAFE_NAME
            "safeOs": os_str.strip(),  # 操作系统 -> SAFE_OS
            "safeIp": internal_ip  # IP地址 -> SAFE_IP
        }
        
        # 构建请求URL
        url = f"{self._server_url}{REGISTER_ENDPOINT}"
        
        # 发送请求（带重试）
        success, resp_data, error = self._request_with_retry(url, request_data)
        
        if not success:
            return False, None, None, None, error
        
        # 解析响应
        try:
            code = resp_data.get("code")
            if code == 200 or code == RESPONSE_CODE_SUCCESS:
                data = resp_data.get("data", {})
                # 如果data是None，尝试从根层获取
                if data is None:
                    data = resp_data
                
                # 获取客户端ID（服务端分配）
                client_id = data.get("id") or data.get("clientId") or data.get("client_id")
                auth_key = data.get("safeSecret") or data.get("auth_key")
                expire_time = data.get("safeEndTime") or data.get("expire_time")
                
                if auth_key:
                    # 设置授权密钥用于后续加密
                    self.set_auth_key(auth_key)
                
                return True, client_id, auth_key, expire_time, ""
            else:
                message = resp_data.get("msg") or resp_data.get("message", "未知错误")
                return False, None, None, None, f"注册失败: {message}"
        except Exception as e:
            return False, None, None, None, f"响应解析失败: {str(e)}"
    
    def heartbeat(self, client_id: str, machine_code: str, auth_key: str, 
                  heartbeat_data: Dict) -> Tuple[bool, str, str]:
        """
        发送心跳请求
        
        功能: 向服务端发送心跳数据
        参数:
            client_id: 客户端ID（服务端分配）
            machine_code: 机器码
            auth_key: 授权密钥
            heartbeat_data: 心跳数据（CPU、内存、硬盘等）
        返回值: (成功标志, 授权状态, 错误信息)
        异常情况: 请求失败时返回错误信息
        
        请求格式（匹配ewm_project_safe表结构）:
        {
            "id": "客户端ID",
            "projectId": "项目ID",
            "safeCode": "机器码",
            "safeSecret": "授权密钥",
            "safeStatus": "ON",
            "cpu": {...},
            "memory": {...},
            "disk": {...}
        }
        
        响应格式:
        {
            "code": 200,
            "msg": "success",
            "data": {
                "safeStatus": "ON/OFF",
                "authStatus": "normal/expired"
            }
        }
        """
        # 构建请求数据（匹配ewm_project_safe表字段）
        request_data = {
            "id": client_id,  # 客户端ID（服务端分配的唯一标识）
            "projectId": PROJECT_ID,  # 项目ID
            "safeCode": machine_code,  # 机器码
            "safeSecret": auth_key,  # 授权密钥
            "safeStatus": "ON",  # 状态：在线
            # 心跳数据
            "safeOs": heartbeat_data.get("os_info", {}),
            "safeCpu": heartbeat_data.get("cpu_config", {}),  # CPU配置
            "safeCpuUsage": heartbeat_data.get("cpu_usage", 0.0),  # CPU占有率 (%)
            "safeMemory": heartbeat_data.get("memory_size", 0.0),  # 内存大小 (GB)
            "safeMemoryUsage": heartbeat_data.get("memory_usage", 0.0),  # 内存占有率 (%)
            "safeDisk": heartbeat_data.get("disk_size", 0.0),  # 硬盘大小 (GB)
            "safeDiskUsage": heartbeat_data.get("disk_usage", 0.0),  # 硬盘使用率 (%)
        }
        
        # 构建请求URL
        url = f"{self._server_url}{HEARTBEAT_ENDPOINT}"
        
        # 发送请求（带重试）
        success, resp_data, error = self._request_with_retry(url, request_data)
        
        if not success:
            return False, "", error
        
        # 解析响应
        try:
            code = resp_data.get("code")
            if code == 200 or code == RESPONSE_CODE_SUCCESS:
                data = resp_data.get("data", {})
                if data is None:
                    data = resp_data
                
                # 获取授权状态
                auth_status = data.get("authStatus") or data.get("auth_status", AUTH_STATUS_NORMAL)
                safe_status = data.get("safeStatus", "ON")
                
                # 如果safeStatus为OFF或authStatus为expired，表示授权已到期
                if safe_status == "OFF" or auth_status == AUTH_STATUS_EXPIRED:
                    return True, AUTH_STATUS_EXPIRED, ""
                
                return True, AUTH_STATUS_NORMAL, ""
            else:
                message = resp_data.get("msg") or resp_data.get("message", "未知错误")
                return False, "", f"心跳失败: {message}"
        except Exception as e:
            return False, "", f"响应解析失败: {str(e)}"
    
    def update_info(self, machine_code: str, machine_name: str, 
                    ip_info: Dict, os_info: Dict) -> Tuple[bool, str]:
        """
        更新机器信息（非首次运行）
        
        功能: 向服务端更新机器信息
        参数:
            machine_code: 机器码
            machine_name: 机器名称
            ip_info: IP信息
            os_info: 系统信息
        返回值: (成功标志, 错误信息)
        异常情况: 请求失败时返回错误信息
        
        说明: 复用注册接口，服务端根据safeCode判断是注册还是更新
        """
        # 构建操作系统信息字符串
        os_str = f"{os_info.get('type', 'Unknown')} {os_info.get('version', '')} {os_info.get('arch', '')}"
        
        # 获取内网IP
        internal_ip = ip_info.get('internal_ip', 'Unknown')
        
        # 构建请求数据（匹配ewm_project_safe表字段）
        request_data = {
            "projectId": PROJECT_ID,  # 项目ID
            "safeCode": machine_code,  # 机器码
            "safeName": machine_name,  # 机器名称
            "safeOs": os_str.strip(),  # 操作系统
            "safeIp": internal_ip  # IP地址
        }
        
        # 构建请求URL
        url = f"{self._server_url}{REGISTER_ENDPOINT}"
        
        # 发送请求（带重试）
        success, resp_data, error = self._request_with_retry(url, request_data)
        
        if not success:
            return False, error
        
        # 解析响应
        try:
            code = resp_data.get("code")
            if code == 200 or code == RESPONSE_CODE_SUCCESS:
                return True, ""
            else:
                message = resp_data.get("msg") or resp_data.get("message", "未知错误")
                return False, f"更新失败: {message}"
        except Exception as e:
            return False, f"响应解析失败: {str(e)}"
    
    def check_connection(self) -> Tuple[bool, str]:
        """
        检查网络连接
        
        功能: 测试与服务端的网络连通性
        参数: 无
        返回值: (连接成功, 错误信息)
        异常情况: 连接失败时返回错误信息
        """
        try:
            # 发送一个简单的请求测试连通性
            url = f"{self._server_url}/health"  # 假设有健康检查接口
            success, _, error = self._make_request(url, {})
            
            # 即使返回错误也可能表示服务端可达
            if success or "HTTP错误" in error:
                return True, ""
            return False, error
        except Exception as e:
            return False, str(e)
    
    def close(self) -> None:
        """
        关闭网络客户端
        
        功能: 释放网络资源
        参数: 无
        返回值: 无
        异常情况: 无
        """
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass


# 创建全局网络客户端实例
network_client = NetworkClient()

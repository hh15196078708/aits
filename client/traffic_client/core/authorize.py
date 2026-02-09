# -*- coding: utf-8 -*-
"""
@模块名称: 授权管理核心 (core/authorize.py)
@功能描述: 
    1. 生成/校验设备特征码。
    2. 处理首次授权、心跳保活、定时重校验。
    3. 管理授权状态生命周期。
@调用方式: 单例模式调用 AuthManager().start()
"""

import os
import time
import json
import schedule
import threading
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from utils.crypto_tools import CryptoManager
from utils.hardware_tools import HardwareCollector
from utils.http_client import SecureHttpClient
from utils.system_tools import SystemUtils

# 授权状态枚举
class AuthStatus(Enum):
    UNAUTHORIZED = "unauthorized"   # 未授权
    AUTHORIZED = "authorized"       # 已授权
    EXPIRED = "expired"             # 授权过期
    REVOKED = "revoked"             # 授权吊销
    EXCEPTION = "exception"         # 设备异常(特征不匹配)

class AuthManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AuthManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, server_url: str = "https://127.0.0.1:8080"):
        if hasattr(self, 'initialized'):
            return
        
        self.server_url = server_url
        self.http_client = SecureHttpClient(server_url)
        self.status = AuthStatus.UNAUTHORIZED
        self.client_id = None
        self.auth_token = None # 可能是签名或Token
        
        # 数据存储路径
        self.data_dir = SystemUtils.resolve_path("data")
        self.device_code_path = os.path.join(self.data_dir, "device_code.dat")
        self.auth_info_path = os.path.join(self.data_dir, "auth.dat")
        
        SystemUtils.ensure_dir(self.data_dir)
        
        self.initialized = True

    def _generate_device_code(self) -> str:
        """采集硬件特征并生成MD5特征码"""
        features = HardwareCollector.collect_all_features()
        # 拼接顺序: CPU -> Board -> MAC -> Disk
        raw_str = f"{features['cpu_serial']}|{features['board_sn']}|{features['mac_addr']}|{features['disk_id']}"
        return CryptoManager.generate_md5(raw_str)

    def _save_device_code(self, code: str):
        """AES加密保存设备码"""
        encrypted = CryptoManager.encrypt_aes256(code)
        with open(self.device_code_path, 'w') as f:
            f.write(encrypted)

    def _load_device_code(self) -> str:
        """加载解密设备码"""
        if not os.path.exists(self.device_code_path):
            return ""
        with open(self.device_code_path, 'r') as f:
            content = f.read().strip()
        return CryptoManager.decrypt_aes256(content)

    def _save_auth_info(self, info: Dict):
        """保存授权信息"""
        content = json.dumps(info)
        encrypted = CryptoManager.encrypt_aes256(content)
        with open(self.auth_info_path, 'w') as f:
            f.write(encrypted)
    
    def _load_auth_info(self) -> Optional[Dict]:
        """加载授权信息"""
        if not os.path.exists(self.auth_info_path):
            return None
        try:
            with open(self.auth_info_path, 'r') as f:
                content = f.read().strip()
            decrypted = CryptoManager.decrypt_aes256(content)
            return json.loads(decrypted) if decrypted else None
        except Exception:
            return None

    def login(self, auth_code: str) -> bool:
        """
        [入口] 首次授权校验流程
        """
        print("[Auth] Starting authorization login...")
        device_code = self._generate_device_code()
        self._save_device_code(device_code) # 保存当前特征码
        
        sys_info = SystemUtils.get_system_basic_info()
        payload = {
            "device_code": device_code,
            "auth_code": auth_code,
            "os_info": f"{sys_info['os_type']} {sys_info['os_release']}",
            "version": "1.0.0"
        }

        # 调用接口: /api/client/authorize
        resp = self.http_client.post("/api/client/authorize", payload, timeout=5)
        
        if resp and resp.get("code") == 200:
            data = resp.get("data", {})
            self.client_id = data.get("client_id")
            
            # 保存授权信息
            save_data = {
                "client_id": self.client_id,
                "expiry": data.get("expiry"),
                "signature": data.get("signature"),
                "bind_device_code": device_code # 本地记录绑定时的特征码
            }
            self._save_auth_info(save_data)
            self.status = AuthStatus.AUTHORIZED
            print(f"[Auth] Authorization successful. Client ID: {self.client_id}")
            return True
        else:
            msg = resp.get("msg") if resp else "Connection failed"
            print(f"[Auth] Authorization failed: {msg}")
            self.status = AuthStatus.UNAUTHORIZED
            return False

    def check_hardware_integrity(self):
        """
        [定时任务] 硬件特征重校验 (每30分钟)
        """
        if self.status != AuthStatus.AUTHORIZED:
            return

        current_code = self._generate_device_code()
        saved_code = self._load_device_code()
        
        # 1. 校验当前采集 vs 本地存储
        if current_code != saved_code:
            print(f"[Auth Alert] Hardware changed! (Local mismatch)")
            self._handle_exception("hardware_mismatch_local")
            return
            
        # 2. 校验当前采集 vs 授权信息中的绑定码
        auth_info = self._load_auth_info()
        if auth_info and auth_info.get("bind_device_code") != current_code:
            print(f"[Auth Alert] Hardware changed! (Auth info mismatch)")
            self._handle_exception("hardware_mismatch_auth")
            return
            
        print("[Auth] Hardware integrity check passed.")

    def _handle_exception(self, reason: str):
        """处理异常状态"""
        self.status = AuthStatus.EXCEPTION
        # 上报异常
        payload = {
            "client_id": self.client_id,
            "reason": reason,
            "device_code": self._generate_device_code()
        }
        self.http_client.post("/api/client/authorize/exception", payload)
        # 这里应触发停止核心采集功能的逻辑（通过状态检查拦截）

    def send_heartbeat(self):
        """
        [定时任务] 授权心跳 (每60秒)
        """
        if self.client_id is None:
            # 尝试从本地加载
            auth_info = self._load_auth_info()
            if auth_info:
                self.client_id = auth_info.get("client_id")
                self.status = AuthStatus.AUTHORIZED
            else:
                return # 未登录不发心跳

        payload = {
            "client_id": self.client_id,
            "status": self.status.value
        }
        
        resp = self.http_client.post("/api/client/authorize/heartbeat", payload, timeout=5)
        
        if resp and resp.get("code") == 200:
            # 解析服务端指令 (吊销/续期)
            server_status = resp.get("data", {}).get("status")
            if server_status == "revoked":
                self.status = AuthStatus.REVOKED
                print("[Auth] License revoked by server.")
            elif server_status == "expired":
                self.status = AuthStatus.EXPIRED
                print("[Auth] License expired.")
        else:
            print("[Auth] Heartbeat failed (Network issue).")

    def start_scheduler(self):
        """启动后台定时任务"""
        schedule.every(30).minutes.do(self.check_hardware_integrity)
        schedule.every(60).seconds.do(self.send_heartbeat)
        
        # 授权失效后的自动重试逻辑 (每5分钟)
        schedule.every(5).minutes.do(self._retry_auth_if_needed)

        def run_loop():
            while True:
                schedule.run_pending()
                time.sleep(1)
        
        t = threading.Thread(target=run_loop, daemon=True)
        t.start()

    def _retry_auth_if_needed(self):
        """当授权异常时尝试恢复"""
        if self.status in [AuthStatus.EXPIRED, AuthStatus.REVOKED, AuthStatus.EXCEPTION]:
            print(f"[Auth] Retrying authorization from status: {self.status.value}")
            # 这里需要一种机制获取原始授权码，或者仅重试心跳看状态是否变更
            # 简化逻辑：如果是过期或吊销，通常需要人工介入或新授权码
            # 如果是网络原因导致的异常，心跳会恢复
            pass

    def is_authorized(self) -> bool:
        """核心功能拦截器调用"""
        return self.status == AuthStatus.AUTHORIZED

# 模拟客户端入口调用
if __name__ == "__main__":
    # 初始化
    manager = AuthManager(server_url="http://127.0.0.1:81/safe/auth")
    
    # 模拟登录
    # manager.login("AUTH-CODE-123456")
    
    # 打印当前特征
    print(f"Device Code: {manager._generate_device_code()}")
    
    # 启动调度
    # manager.start_scheduler()
    
    # 阻塞主线程
    # while True: time.sleep(10)
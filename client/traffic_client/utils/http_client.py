# -*- coding: utf-8 -*-
"""
@模块名称: HTTP通信客户端 (utils/http_client.py)
@功能描述: 封装HTTPS请求，强制TLS 1.3，处理JSON响应。
@特性: 自动重试、超时控制、证书忽略(内网自签可能需要, 生产建议配置CA)。
"""

import requests
import ssl
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional


# 定义 TLS 1.3 适配器
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        """强制使用 TLS Client 协议，并配置上下文"""
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        # 尝试强制 TLS 1.3 (需 OpenSSL 1.1.1+)
        if hasattr(ssl, 'PROTOCOL_TLS_CLIENT'):
            ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2
        else:
            # 降级兼容: 至少 TLS 1.2
            ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

        ctx.check_hostname = False  # 内网环境可能IP访问，关闭Hostname校验
        ctx.verify_mode = ssl.CERT_NONE  # 内网自签证书，暂关闭验证

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )


class SecureHttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

        # 配置重试策略: 总共3次，间隔因子0.5 (0.5s, 1s, 2s...)
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])

        # 1. 挂载 HTTPS 适配器 (自定义 TLS 设置，生产环境用)
        tls_adapter = TLSAdapter(max_retries=retries)
        self.session.mount("https://", tls_adapter)

        # 2. 挂载 HTTP 适配器 (用于本地调试，确保 HTTP 请求也有重试策略)
        http_adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", http_adapter)

        # 统一请求头
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "TrafficAnalysisClient/1.0"
        })

    def post(self, endpoint: str, data: Dict, timeout: int = 5) -> Optional[Dict]:
        """
        发送POST请求
        :param endpoint: 接口路径 e.g. /api/auth
        :param data: 字典数据
        :param timeout: 超时时间(秒)
        :return: 响应JSON字典 或 None
        """
        url = f"{self.base_url}{endpoint}"
        try:
            # verify=False 在 HTTP 请求中会被自动忽略，所以无需特殊处理
            response = self.session.post(url, json=data, timeout=timeout, verify=False)
            response.raise_for_status()  # 检查HTTP状态码
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[HTTP Error] Request to {endpoint} failed: {e}")
            return None
        except json.JSONDecodeError:
            print(f"[HTTP Error] Invalid JSON response from {endpoint}")
            return None


# 测试用例
if __name__ == "__main__":
    # 支持 HTTP 本地调试
    client = SecureHttpClient("http://127.0.0.1:82")
    res = client.post("/safe/test/1", {"hello": "world"})
    print(res)
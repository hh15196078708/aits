import requests
import json
from .logger import Logger

# 初始化日志
logger = Logger().get_logger()


class HttpClient:
    """HTTP请求客户端封装"""

    @staticmethod
    def post(url, data=None, json_data=None, headers=None, timeout=10):
        """
        发送POST请求
        :param url: 请求地址
        :param data: 表单数据
        :param json_data: JSON数据
        :param headers: 请求头
        :param timeout: 超时时间
        :return: 响应数据的JSON对象 或 None
        """
        try:
            if headers is None:
                headers = {'Content-Type': 'application/json'}

            # 这里是实际的请求逻辑，测试时会被mock掉
            response = requests.post(url, data=data, json=json_data, headers=headers, timeout=timeout)
            response.raise_for_status()

            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text

        except Exception as e:
            logger.error(f"HTTP POST Request failed: {url}, error: {e}")
            return None
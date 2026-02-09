import requests
import json
import logging
from config.settings import client_settings

logger = logging.getLogger(__name__)


def _get_full_url(path):
    """拼接完整URL"""
    base_url = client_settings.server_url
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    if not path.startswith('/'):
        path = '/' + path
    return f"{base_url}{path}"


def post(path, data=None, json=None, **kwargs):
    """
    发送POST请求
    :param path: 接口路径，如 /api/login
    :param data: 表单数据
    :param json: JSON数据
    :return: 响应数据的字典或None
    """
    url = _get_full_url(path)
    try:
        # 设置默认超时时间
        kwargs.setdefault('timeout', 10)

        response = requests.post(url, data=data, json=json, **kwargs)

        # 尝试解析响应
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"请求失败 [{response.status_code}]: {url} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"发送POST请求异常: {url} - {e}")
        return None


def get(path, params=None, **kwargs):
    """
    发送GET请求
    """
    url = _get_full_url(path)
    try:
        kwargs.setdefault('timeout', 10)
        response = requests.get(url, params=params, **kwargs)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"请求失败 [{response.status_code}]: {url}")
            return None
    except Exception as e:
        logger.error(f"发送GET请求异常: {url} - {e}")
        return None
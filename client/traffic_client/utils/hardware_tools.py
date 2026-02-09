import uuid
import socket
import platform
import logging

logger = logging.getLogger(__name__)

def get_machine_code():
    """
    获取机器唯一标识（机器码）
    这里简单使用MAC地址作为示例，生产环境建议结合CPU/主板序列号
    """
    try:
        mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
        return mac.upper()
    except Exception as e:
        logger.error(f"获取机器码失败: {e}")
        return "UNKNOWN_MACHINE_CODE"

def get_hostname():
    """获取主机名"""
    return socket.gethostname()

def get_ip_address():
    """获取本机IP地址"""
    try:
        # 这是一个常用的技巧，连接外部地址来确定本机出口IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_os_info():
    """获取操作系统信息"""
    return f"{platform.system()} {platform.release()}"
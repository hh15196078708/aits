import subprocess
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


def get_mac_address():
    """获取本机MAC地址"""
    try:
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        return ":".join([mac[e:e + 2] for e in range(0, 11, 2)])
    except Exception:
        return "00:00:00:00:00:00"


def get_disk_serial():
    """
    获取硬盘序列号
    支持 Windows (wmic) 和 Linux (lsblk)
    """
    serial_number = "UNKNOWN_DISK"
    system_type = platform.system()

    try:
        if system_type == "Windows":
            # Windows下使用wmic命令
            command = "wmic diskdrive get serialnumber"
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            if stdout:
                # 解码，通常格式为：
                # SerialNumber
                # XXXXXXXX
                raw_output = stdout.decode(errors='ignore').strip()
                lines = [line.strip() for line in raw_output.split('\n') if line.strip()]
                if len(lines) > 1:
                    # 取标题后的第一行作为序列号
                    serial_number = lines[1]

        elif system_type == "Linux":
            # Linux下尝试使用lsblk
            # -d: device (not partitions), -n: no headings, -o SERIAL: output column
            command = "lsblk -d -n -o SERIAL"
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            if stdout:
                # 可能有多个磁盘，取第一个非空的
                lines = stdout.decode(errors='ignore').strip().split('\n')
                for line in lines:
                    if line.strip():
                        serial_number = line.strip()
                        break

    except Exception:
        pass

    return serial_number
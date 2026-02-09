import logging
import sys
import os

# 确保能找到同级或上级包
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from client.traffic_client.utils import hardware_tools, http_client
    # --- 修改处：导入 client_settings ---
    from client.traffic_client.config.settings import client_settings
except ImportError:
    try:
        from utils import hardware_tools, http_client
        from config.settings import client_settings
    except ImportError as e:
        logging.error(f"模块导入失败: {e}")
        raise e

logger = logging.getLogger(__name__)


class AuthorizeManager:
    """授权管理类"""

    def register_client(self):
        """注册客户端"""
        # 使用 client_settings
        project_id = client_settings.project_id
        if not project_id:
            logger.error("注册失败：config.json 未配置 project_id")
            return False

        logger.info(f"开始注册，项目ID: {project_id}...")

        try:
            machine_code = hardware_tools.get_machine_code()
            hostname = hardware_tools.get_hostname()
            ip_addr = hardware_tools.get_ip_address()
            os_info = hardware_tools.get_os_info()
        except Exception as e:
            logger.error(f"获取硬件信息失败: {e}")
            return False

        payload = {
            "safeCode": machine_code,
            "safeName": hostname,
            "safeIp": ip_addr,
            "safeOs": os_info,
            "projectId": project_id,
        }

        try:
            response = http_client.post("/safe/init/add", json=payload)

            if response and response.get('code') == 200:
                data = response.get('data', {})
                new_client_id = data.get('id') or data.get('clientId')
                new_client_secret = data.get('safeSecret') or data.get('clientSecret')

                if new_client_id and new_client_secret:
                    # 使用 client_settings 保存
                    client_settings.client_id = new_client_id
                    client_settings.client_secret = new_client_secret
                    logger.info(f"注册成功 ID: {new_client_id}")
                    return True
                return False
            else:
                msg = response.get('msg') if response else "未知错误"
                logger.error(f"注册失败: {msg}")
                return False
        except Exception as e:
            logger.error(f"注册异常: {e}")
            return False

    def check_auth(self):
        """检查授权"""
        # 使用 client_settings
        if not client_settings.client_id or not client_settings.client_secret:
            logger.warning("无凭证，准备注册...")
            return self.register_client()

        logger.info(f"检查授权 (ID: {client_settings.client_id})...")

        payload = {
            "id": client_settings.client_id,
            "safeSecret": client_settings.client_secret,
            "safeCode": hardware_tools.get_machine_code(),
            "projectId": client_settings.project_id
        }

        try:
            response = http_client.post("/safe/init/check", json=payload)

            if response and response.get('code') == 200:
                logger.info("授权有效")
                return True
            else:
                msg = response.get('msg') if response else "未知错误"
                logger.warning(f"授权失效: {msg}，重新注册...")
                return self.register_client()
        except Exception as e:
            logger.error(f"鉴权异常: {e}")
            return False
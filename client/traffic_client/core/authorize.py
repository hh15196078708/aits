import logging
import sys
import os

# Ensure peer or parent packages can be found
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from client.traffic_client.utils import hardware_tools, http_client
    # 引入 LicenseManager 用于校验秘钥合规性
    from client.traffic_client.utils.crypto_tools import LicenseManager
    from client.traffic_client.config.settings import client_settings
except ImportError:
    try:
        from utils import hardware_tools, http_client
        from utils.crypto_tools import LicenseManager
        from config.settings import client_settings
    except ImportError as e:
        logging.error(f"Module import failed: {e}")
        raise e

logger = logging.getLogger(__name__)


class AuthorizeManager:
    """Authorization Management Class"""

    def authenticate(self):
        """Register the client with the server"""
        project_id = client_settings.project_id
        if not project_id:
            logger.error("Registration failed: project_id not configured in config.json")
            return False

        logger.info(f"Starting registration, Project ID: {project_id}...")

        try:
            # 1. Collect real machine information
            machine_code = hardware_tools.get_machine_code()
            hostname = hardware_tools.get_hostname()
            ip_addr = hardware_tools.get_ip_address()
            os_info = hardware_tools.get_os_info()

            logger.debug(f"Collected Info - Code: {machine_code}, IP: {ip_addr}")
        except Exception as e:
            logger.error(f"Failed to collect hardware info: {e}")
            return False

        payload = {
            "safeCode": machine_code,
            "safeName": hostname,
            "safeIp": ip_addr,
            "safeOs": os_info,
            "projectId": project_id,
            # 将本地现有的 Secret 发给服务端（如果是更新注册），供服务端校验
            "safeSecret": client_settings.client_secret
        }

        try:
            # Fix: Build full URL using server_url from settings
            base_url = client_settings.server_url.rstrip('/')
            url = f"{base_url}/safe/init/add"

            # Use HttpClient class static method
            response = http_client.HttpClient.post(url, json_data=payload)

            if response and isinstance(response, dict) and response.get('code') == 200:
                data = response.get('data', {})
                # Support different field names that might return from server
                new_client_id = data.get('id') or data.get('clientId')
                new_client_secret = data.get('safeSecret') or data.get('clientSecret')

                if new_client_id and new_client_secret:
                    # --- 新增：本地合规性校验 ---
                    # 收到秘钥后，先验证这个秘钥是否是用我的机器码生成的
                    if not LicenseManager.verify_license(new_client_secret, machine_code):
                        logger.error(f"安全警告：服务端返回的秘钥与本机硬件指纹不匹配！(Received: {new_client_secret})")
                        return False

                    # --- 保存配置 ---
                    # 赋值操作会自动触发 settings.py 中的 save_config()，写入 config.json
                    client_settings.client_id = new_client_id
                    client_settings.client_secret = new_client_secret

                    logger.info(f"注册成功，秘钥校验通过。New ID: {new_client_id}")
                    return True

                logger.warning("Registration successful but returned data is incomplete")
                return False
            else:
                msg = response.get('msg') if isinstance(response, dict) else "Unknown Error"
                logger.error(f"Registration refused by server: {msg}")
                return False
        except Exception as e:
            logger.error(f"Registration exception: {e}")
            return False

    def check_auth(self):
        """Check if current authorization is valid"""
        if not client_settings.client_id or not client_settings.client_secret:
            logger.warning("No credentials found, attempting to register...")
            return self.authenticate()

        logger.info(f"Checking authorization (ID: {client_settings.client_id})...")

        payload = {
            "id": client_settings.client_id,
            # 心跳检测必须携带 safeSecret，服务端会校验它是否合法
            "safeSecret": client_settings.client_secret,
            "safeCode": hardware_tools.get_machine_code(),
            "projectId": client_settings.project_id
        }

        try:
            # Fix: Build full URL using server_url from settings
            base_url = client_settings.server_url.rstrip('/')
            url = f"{base_url}/safe/init/check"

            # Use HttpClient class static method
            response = http_client.HttpClient.post(url, json_data=payload)

            if response and isinstance(response, dict) and response.get('code') == 200:
                logger.info("Authorization is valid")
                return True
            else:
                msg = response.get('msg') if isinstance(response, dict) else "Unknown Error"
                logger.warning(f"Authorization invalid: {msg}, re-registering...")
                # 授权失效，尝试重新注册
                return self.authenticate()
        except Exception as e:
            logger.error(f"Auth check exception: {e}")
            return False
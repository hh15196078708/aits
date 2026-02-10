import logging
import sys
import os

# Ensure peer or parent packages can be found
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from client.traffic_client.utils import hardware_tools, http_client
    from client.traffic_client.config.settings import client_settings
except ImportError:
    try:
        from utils import hardware_tools, http_client
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
                    # Update settings
                    client_settings.client_id = new_client_id
                    client_settings.client_secret = new_client_secret
                    logger.info(f"Registration successful. New ID: {new_client_id}")
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
                return self.authenticate()
        except Exception as e:
            logger.error(f"Auth check exception: {e}")
            return False
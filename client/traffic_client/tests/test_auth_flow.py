import unittest
import sys
import os
import json
import traceback
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.authorize import AuthorizeManager
from config.settings import client_settings
from utils import hardware_tools


class TestAuthFlow(unittest.TestCase):
    """
    Integration Test for Authorization Flow (Real Network)

    This test uses REAL hardware tools to gather system info,
    and sends REAL network requests to a local server.
    """

    def setUp(self):
        print("\n" + "=" * 60)
        print(f"Executing: {self._testMethodName}")
        print("-" * 60)

        # Backup original settings
        self.original_client_id = client_settings.client_id
        self.original_client_secret = client_settings.client_secret
        self.original_server_url = getattr(client_settings, 'server_url', "http://localhost:82")

        # Reset settings for clean test & Set Local Server URL
        # 注意：这里模拟了配置文件被重置，同时指定了测试用的服务端地址
        client_settings._config['client_id'] = ""
        client_settings._config['client_secret'] = ""
        client_settings._config['server_url'] = "http://127.0.0.1:82"

    def tearDown(self):
        # Restore settings
        client_settings._config['client_id'] = self.original_client_id
        client_settings._config['client_secret'] = self.original_client_secret
        if 'server_url' in client_settings._config:
            client_settings._config['server_url'] = self.original_server_url
        print("=" * 60)

    def test_01_hardware_info(self):
        """Test Step 1: Verify local hardware info collection"""
        print("[1. Info Collection] Reading local system info...")

        machine_code = hardware_tools.get_machine_code()
        ip = hardware_tools.get_ip_address()
        hostname = hardware_tools.get_hostname()
        os_info = hardware_tools.get_os_info()

        print(f"   -> Machine Code: {machine_code}")
        print(f"   -> IP Address  : {ip}")
        print(f"   -> Hostname    : {hostname}")
        print(f"   -> OS Info     : {os_info}")

        self.assertIsNotNone(machine_code)
        self.assertNotEqual(machine_code, "UNKNOWN_MACHINE_CODE")
        self.assertTrue(len(ip) > 0)

    @patch('config.settings.Settings.save_config')  # Prevent writing to disk during test
    def test_02_register_and_auth_flow(self, mock_save):
        """
        Test Step 2: Real Network Registration and Validation Flow
        Target: http://127.0.0.1:82
        """
        print(f"[Config] Target Server: {client_settings.server_url}")

        auth_manager = AuthorizeManager()

        # --- Scenario A: Real Registration Request ---
        print("\n[2. Registration] Sending registration request to server...")

        try:
            # 执行真实的注册逻辑
            result = auth_manager.authenticate()

            if not result:
                print("   [Failed] Registration returned False.")
                print("   Possible causes: Server down, invalid response format, or logic error.")
                # 这里不强制 fail，允许查看日志输出
            else:
                print("   [Success] Registration successful!")

            # Verification
            self.assertTrue(result, "Registration failed (Check server logs or connection)")

            # Check if settings were updated in memory
            print(f"   -> Settings Updated: ClientID={client_settings.client_id}")
            print(f"   -> Settings Updated: Secret={client_settings.client_secret}")

            self.assertTrue(len(client_settings.client_id) > 0, "Client ID should be set after registration")
            self.assertTrue(len(client_settings.client_secret) > 0, "Client Secret should be set after registration")

        except Exception as e:
            print(f"   [Exception] Network/Logic error during registration: {e}")
            traceback.print_exc()
            self.fail(f"Registration process crashed: {e}")

        # --- Scenario B: Real Auth Check Request ---
        print("\n[3. Validation] Sending auth check request...")

        try:
            # 执行真实的鉴权逻辑
            check_result = auth_manager.check_auth()

            if check_result:
                print("   [Success] Auth check passed!")
            else:
                print("   [Failed] Auth check returned False.")

            # Verification
            self.assertTrue(check_result, "Auth check failed")

        except Exception as e:
            print(f"   [Exception] Network/Logic error during auth check: {e}")
            traceback.print_exc()
            self.fail(f"Auth check process crashed: {e}")


if __name__ == '__main__':
    unittest.main()
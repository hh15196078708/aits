import unittest
import sys
import os
import traceback
from unittest.mock import patch

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.authorize import AuthorizeManager
from config.settings import client_settings
from utils import hardware_tools
from utils.crypto_tools import LicenseManager


class TestAuthFlow(unittest.TestCase):
    """
    集成测试：授权与心跳流程 (真实网络环境)
    目标服务端: http://127.0.0.1:82
    """

    def setUp(self):
        print("\n" + "=" * 60)
        print(f"Executing: {self._testMethodName}")
        print("-" * 60)

        # 1. 备份原始配置
        self.original_client_id = client_settings.client_id
        self.original_client_secret = client_settings.client_secret
        self.original_server_url = getattr(client_settings, 'server_url', "http://localhost:82")

        # 2. 重置配置 & 设置测试目标地址
        # 注意：清空 ID/Secret 以模拟"全新安装"状态
        client_settings._config['client_id'] = ""
        client_settings._config['client_secret'] = ""
        client_settings._config['server_url'] = "http://127.0.0.1:82"

    def tearDown(self):
        # 还原配置
        client_settings._config['client_id'] = self.original_client_id
        client_settings._config['client_secret'] = self.original_client_secret
        if 'server_url' in client_settings._config:
            client_settings._config['server_url'] = self.original_server_url
        print("=" * 60)

    def test_01_hardware_info(self):
        """步骤1: 验证本机硬件信息采集"""
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

    @patch('config.settings.Settings.save_config')  # 禁止测试写入磁盘
    def test_02_register_and_auth_flow(self, mock_save):
        """
        步骤2: 真实注册与鉴权流程测试
        流程: 注册 -> 获取秘钥 -> 校验秘钥 -> 发起心跳
        """
        print(f"[Config] Target Server: {client_settings.server_url}")

        auth_manager = AuthorizeManager()
        machine_code = hardware_tools.get_machine_code()

        # --- 阶段 A: 注册 (Authenticate) ---
        print("\n[2. Registration] Sending registration request...")

        try:
            # 执行注册
            is_registered = auth_manager.authenticate()

            if not is_registered:
                print("   [Failed] Registration returned False.")
                print("   Possible causes: Server down, invalid URL, or server logic error.")
                print("\n" + "!" * 70)
                print("【故障排查提示】")
                print("如果日志显示 '服务端返回的秘钥与本机硬件指纹不匹配'，且 Receive 是一串乱码/随机字符：")
                print("1. 说明服务端加密过程崩溃，触发了 catch 块返回了随机字符串(RandomUtil.randomString)。")
                print("2. 请检查 Java 服务端日志，确认是否为 'InvalidKeyException'。")
                print("3. 务必确保 Java 端 SECRET_KEY 长度严格为 16字节 (例如 'TrafficClientKey')。")
                print("4. 修改 Java 代码后，请【重启 Java 服务】生效。")
                print("!" * 70 + "\n")
            else:
                print("   [Success] Registration successful!")

            # 断言注册成功
            self.assertTrue(is_registered, "Registration failed (See troubleshooting hints above)")

            # 验证内存中的配置是否更新
            new_id = client_settings.client_id
            new_secret = client_settings.client_secret

            print(f"   -> Received ClientID: {new_id}")
            print(f"   -> Received Secret  : {new_secret}")

            self.assertTrue(len(new_id) > 0, "Client ID should be set after registration")
            self.assertTrue(len(new_secret) > 0, "Client Secret should be set after registration")

            # --- 关键验证: 测试端独立校验秘钥合规性 ---
            print("\n[2.1 License Verification] Verifying secret locally...")
            is_valid_license = LicenseManager.verify_license(new_secret, machine_code)
            if is_valid_license:
                print("   [Pass] Secret matches Machine Code (AES-128 check passed).")
            else:
                print(f"   [Fail] Secret mismatch! Code={machine_code}, Secret={new_secret}")

            self.assertTrue(is_valid_license, "Server returned an invalid license key for this machine")

        except Exception as e:
            print(f"   [Exception] Registration crashed: {e}")
            traceback.print_exc()
            self.fail(f"Registration process crashed: {e}")

        # --- 阶段 B: 心跳检测 (Check Auth) ---
        print("\n[3. Heartbeat] Sending auth check with secret...")

        try:
            # 此时 settings 中已有 Secret，check_auth 会将其放入 Payload 发送给服务端
            check_result = auth_manager.check_auth()

            if check_result:
                print("   [Success] Heartbeat/Auth check passed!")
            else:
                print("   [Failed] Heartbeat check returned False.")

            self.assertTrue(check_result, "Heartbeat check failed")

        except Exception as e:
            print(f"   [Exception] Heartbeat crashed: {e}")
            traceback.print_exc()
            self.fail(f"Auth check process crashed: {e}")


if __name__ == '__main__':
    unittest.main()
import unittest
from unittest.mock import patch
import sys
import os
import logging

# 1. 设置项目根目录路径，确保能导入 client 包
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. 导入核心类和配置实例 (使用新的名字 client_settings)
from core.authorize import AuthorizeManager
from config.settings import client_settings


class TestAuthorizeManager(unittest.TestCase):

    def setUp(self):
        """每个测试前重置配置"""
        self.auth_manager = AuthorizeManager()

        # 3. 操作 client_settings 实例
        # 此时 client_settings 是一个 Settings 对象，肯定有 _config 属性
        self.original_project_id = client_settings._config.get("project_id")
        self.original_client_id = client_settings._config.get("client_id")
        self.original_client_secret = client_settings._config.get("client_secret")

        # 模拟配置
        client_settings._config["project_id"] = "TEST_PROJECT_001"
        client_settings._config["client_id"] = ""
        client_settings._config["client_secret"] = ""

    def tearDown(self):
        """恢复配置"""
        if hasattr(self, 'original_project_id'):
            client_settings._config["project_id"] = self.original_project_id
        if hasattr(self, 'original_client_id'):
            client_settings._config["client_id"] = self.original_client_id
        if hasattr(self, 'original_client_secret'):
            client_settings._config["client_secret"] = self.original_client_secret

    @patch('utils.http_client.post')
    @patch('utils.hardware_tools')
    def test_register_success(self, mock_hw, mock_post):
        """测试注册成功流程"""
        mock_hw.get_machine_code.return_value = "UUID-1234"
        mock_hw.get_hostname.return_value = "Test-PC"
        mock_hw.get_ip_address.return_value = "127.0.0.1"
        mock_hw.get_os_info.return_value = "Win10"

        mock_post.return_value = {
            "code": 200,
            "msg": "OK",
            "data": {"id": "CLIENT_001", "safeSecret": "SECRET_XYZ"}
        }

        result = self.auth_manager.register_client()

        self.assertTrue(result)
        self.assertEqual(client_settings.client_id, "CLIENT_001")
        self.assertEqual(client_settings.client_secret, "SECRET_XYZ")

        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['projectId'], "TEST_PROJECT_001")

    @patch('utils.http_client.post')
    @patch('utils.hardware_tools')
    def test_register_fail_no_project_id(self, mock_hw, mock_post):
        """测试无项目ID"""
        client_settings._config["project_id"] = ""
        result = self.auth_manager.register_client()
        self.assertFalse(result)

    @patch('utils.http_client.post')
    @patch('utils.hardware_tools')
    def test_check_auth_success(self, mock_hw, mock_post):
        """测试鉴权成功"""
        client_settings._config["client_id"] = "CLIENT_001"
        client_settings._config["client_secret"] = "SECRET_XYZ"
        mock_hw.get_machine_code.return_value = "UUID-1234"

        mock_post.return_value = {"code": 200, "msg": "OK"}

        result = self.auth_manager.check_auth()
        self.assertTrue(result)

        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['projectId'], "TEST_PROJECT_001")
        self.assertEqual(kwargs['json']['id'], "CLIENT_001")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    unittest.main()
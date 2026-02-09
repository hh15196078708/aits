# -*- coding: utf-8 -*-
"""
@模块名称: 授权模块单元测试 (tests/test_auth_module.py)
@功能描述: 测试加密、硬件特征格式、授权逻辑。
"""

import unittest
import os
import sys
import json
from unittest.mock import MagicMock, patch

# 添加项目根目录到Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.crypto_tools import CryptoManager
from utils.hardware_tools import HardwareCollector
from core.authorize import AuthManager, AuthStatus


class TestAuthModule(unittest.TestCase):

    def test_crypto_aes256(self):
        """测试AES-256加解密完整性"""
        text = "Hello Traffic Client 2024!"
        encrypted = CryptoManager.encrypt_aes256(text)
        self.assertNotEqual(text, encrypted)
        decrypted = CryptoManager.decrypt_aes256(encrypted)
        self.assertEqual(text, decrypted)

    def test_md5_generation(self):
        """测试MD5生成长度"""
        h = CryptoManager.generate_md5("test")
        self.assertEqual(len(h), 32)

    def test_hardware_collection(self):
        """测试硬件采集字段完整性"""
        features = HardwareCollector.collect_all_features()
        self.assertIn("cpu_serial", features)
        self.assertIn("board_sn", features)
        self.assertIn("mac_addr", features)
        self.assertIn("disk_id", features)
        print(f"\n[Info] Collected Features: {features}")

    @patch('utils.http_client.SecureHttpClient.post')
    def test_auth_login_success(self, mock_post):
        """模拟授权成功场景"""
        # Mock 服务端返回
        mock_post.return_value = {
            "code": 200,
            "data": {
                "client_id": "CLI-TEST-001",
                "expiry": "2099-12-31",
                "signature": "SIGN_XYZ"
            }
        }

        manager = AuthManager()
        # 清理旧数据文件以免影响测试
        if os.path.exists(manager.auth_info_path):
            os.remove(manager.auth_info_path)

        success = manager.login("Valid-Code")

        self.assertTrue(success)
        self.assertEqual(manager.status, AuthStatus.AUTHORIZED)
        self.assertEqual(manager.client_id, "CLI-TEST-001")

        # 验证文件持久化
        saved_info = manager._load_auth_info()
        self.assertIsNotNone(saved_info)
        self.assertEqual(saved_info['client_id'], "CLI-TEST-001")

    @patch('utils.http_client.SecureHttpClient.post')
    def test_auth_login_failure(self, mock_post):
        """模拟授权失败场景"""
        mock_post.return_value = {
            "code": 401,
            "msg": "Invalid Code"
        }

        manager = AuthManager()
        success = manager.login("Invalid-Code")

        self.assertFalse(success)
        self.assertEqual(manager.status, AuthStatus.UNAUTHORIZED)


if __name__ == '__main__':
    unittest.main()
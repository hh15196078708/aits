# -*- coding: utf-8 -*-
"""
@模块名称: 加密工具类 (utils/crypto_tools.py)
@功能描述: 提供AES-256数据加解密与MD5哈希生成能力。
@安全标准: AES-256-CBC, PKCS7 Padding, SHA-256 Key Derivation
"""

import hashlib
import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


class CryptoManager:
    # 生产环境中，此密钥应通过混淆或密钥管理系统分发
    # 这里使用硬编码的盐值和密钥种子演示
    _MASTER_KEY_SEED = b"TrafficAnalysisClient_2024_Secure_Seed"
    _SALT = b"Static_Salt_Value_For_Demo"

    @staticmethod
    def get_aes_key() -> bytes:
        """基于种子派生32字节(256位)的AES密钥"""
        # 修正：参数名应为 hash_name 而非 algorithm
        kdf = hashlib.pbkdf2_hmac(
            hash_name='sha256',
            password=CryptoManager._MASTER_KEY_SEED,
            salt=CryptoManager._SALT,
            iterations=100000,
            dklen=32  # AES-256 requires 32 bytes
        )
        return kdf

    @staticmethod
    def encrypt_aes256(plaintext: str) -> str:
        """
        AES-256 加密
        :param plaintext: 明文字符串
        :return: Base64编码的密文 (IV + Ciphertext)
        """
        try:
            if not plaintext:
                return ""

            key = CryptoManager.get_aes_key()
            # 生成随机IV (16 bytes)
            iv = os.urandom(16)

            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            # PKCS7 Padding
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()

            ciphertext = encryptor.update(padded_data) + encryptor.finalize()

            # 返回 Base64(IV + Ciphertext)
            return base64.b64encode(iv + ciphertext).decode('utf-8')
        except Exception as e:
            # 实际项目中建议记录日志
            print(f"[Crypto Error] Encryption failed: {e}")
            return ""

    @staticmethod
    def decrypt_aes256(ciphertext_b64: str) -> str:
        """
        AES-256 解密
        :param ciphertext_b64: Base64编码的密文
        :return: 明文字符串
        """
        try:
            if not ciphertext_b64:
                return ""

            data = base64.b64decode(ciphertext_b64)
            if len(data) < 16:
                raise ValueError("Data too short")

            iv = data[:16]
            actual_ciphertext = data[16:]

            key = CryptoManager.get_aes_key()
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()

            padded_plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()

            # Unpad
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

            return plaintext.decode('utf-8')
        except Exception as e:
            print(f"[Crypto Error] Decryption failed: {e}")
            return ""

    @staticmethod
    def generate_md5(text: str) -> str:
        """生成32位小写MD5特征码"""
        if not text:
            return ""
        m = hashlib.md5()
        m.update(text.encode('utf-8'))
        return m.hexdigest()


# 简单自测
if __name__ == "__main__":
    original = "Critical_Device_Info_2024"
    encrypted = CryptoManager.encrypt_aes256(original)
    print(f"Original: {original}")
    print(f"Encrypted: {encrypted}")

    if encrypted:
        decrypted = CryptoManager.decrypt_aes256(encrypted)
        print(f"Decrypted: {decrypted}")

    print(f"MD5: {CryptoManager.generate_md5(original)}")
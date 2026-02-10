# -*- coding: utf-8 -*-
"""
@模块名称: 加密工具类 (utils/crypto_tools.py)
@功能描述:
    1. CryptoManager: 提供AES-256数据加解密（用于日志/数据存储）。
    2. LicenseManager: 提供基于AES-128的授权校验（用于和服务端通信校验）。
@安全标准:
    - 数据加密: AES-256-CBC, PKCS7 Padding
    - 授权校验: AES-128-ECB, PKCS7 Padding (匹配Java端 Hutool默认行为)
"""

import hashlib
import os
import base64
import binascii
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


class CryptoManager:
    # 生产环境中，此密钥应通过混淆或密钥管理系统分发
    _MASTER_KEY_SEED = b"TrafficAnalysisClient_2024_Secure_Seed"
    _SALT = b"Static_Salt_Value_For_Demo"

    @staticmethod
    def get_aes_key() -> bytes:
        """基于种子派生32字节(256位)的AES密钥"""
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
        """AES-256-CBC 加密 (内部数据使用)"""
        try:
            if not plaintext:
                return ""
            key = CryptoManager.get_aes_key()
            iv = os.urandom(16)
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            return base64.b64encode(iv + ciphertext).decode('utf-8')
        except Exception as e:
            print(f"[Crypto Error] Encryption failed: {e}")
            return ""

    @staticmethod
    def decrypt_aes256(ciphertext_b64: str) -> str:
        """AES-256-CBC 解密 (内部数据使用)"""
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


class LicenseManager:
    """
    授权校验专用类
    用于校验服务端下发的 SafeSecret 是否由本机 SafeCode 加密而来
    """
    # 必须与 Java 服务端代码中的 SECRET_KEY 保持完全一致 (16字节)
    # Traffic(7) + Client(6) + Key(3) = 16 bytes (128 bit)
    _LICENSE_KEY = b"TrafficClientKey"

    @staticmethod
    def verify_license(secret_hex: str, machine_code: str) -> bool:
        """
        验证授权密钥是否合规
        :param secret_hex: 服务端返回的 SafeSecret (Hex字符串)
        :param machine_code: 本机机器码
        :return: Boolean
        """
        if not secret_hex or not machine_code:
            return False

        try:
            # 1. 解密服务端发来的 Hex 密钥
            decrypted_code = LicenseManager._decrypt_aes_ecb_hex(secret_hex)

            # 2. 比对解密结果与本机机器码
            # 注意：去除可能存在的空格或大小写差异
            is_valid = decrypted_code.strip() == machine_code.strip()
            if not is_valid:
                print(f"[License] Mismatch! Server: {decrypted_code}, Local: {machine_code}")
            return is_valid

        except Exception as e:
            # print(f"[License] Verify failed: {e}") # 调试时可开启
            return False

    @staticmethod
    def _decrypt_aes_ecb_hex(hex_str: str) -> str:
        """
        解密 Java Hutool 生成的 AES/ECB/PKCS5Padding Hex字符串
        """
        try:
            # Hex -> Bytes
            encrypted_bytes = binascii.unhexlify(hex_str)

            # AES ECB Mode (无需IV)
            cipher = Cipher(
                algorithms.AES(LicenseManager._LICENSE_KEY),
                modes.ECB(),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()

            # Decrypt
            padded_plaintext = decryptor.update(encrypted_bytes) + decryptor.finalize()

            # Unpad (PKCS7 compatible with PKCS5)
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

            return plaintext.decode('utf-8')
        except Exception as e:
            raise e


# 简单自测
if __name__ == "__main__":
    original = "Critical_Device_Info_2024"
    print(f"MD5: {CryptoManager.generate_md5(original)}")
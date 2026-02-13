# -*- coding: utf-8 -*-
"""
模块名称: crypto_utils.py
模块功能: AES-128-CBC加密/解密工具
依赖模块: 
    - 第三方库: pycryptodome>=3.18.0（优先）
    - 兜底: 使用标准库hashlib实现简化加密
系统适配: 所有平台通用

说明:
    本模块提供AES对称加密功能：
    1. AES-128-CBC模式加密/解密
    2. PKCS7填充
    3. 轻量化实现，降低CPU占用
    4. 密钥派生（从字符串密钥生成128位密钥）
"""

import os  # 操作系统接口
import base64  # Base64编码
import hashlib  # 哈希算法
import json  # JSON序列化
from typing import Optional, Union  # 类型提示

# 导入常量
from constants import AES_KEY_LENGTH, AES_BLOCK_SIZE

# 尝试导入pycryptodome
try:
    from Crypto.Cipher import AES  # AES加密器
    from Crypto.Util.Padding import pad, unpad  # PKCS7填充
    PYCRYPTODOME_AVAILABLE = True
except ImportError:
    PYCRYPTODOME_AVAILABLE = False


class AESCrypto:
    """
    AES-128-CBC加密工具类
    
    功能: 提供AES对称加密和解密功能
    系统适配: 所有平台通用
    
    加密流程:
        1. 从授权密钥派生128位密钥
        2. 生成随机IV（初始化向量）
        3. 使用PKCS7填充明文
        4. AES-CBC加密
        5. IV + 密文 Base64编码
    
    资源优化:
        - 使用AES-128而非AES-256，降低CPU占用
        - 密钥缓存，避免重复派生
    """
    
    def __init__(self, key: str):
        """
        初始化AES加密器
        
        功能: 从字符串密钥派生AES密钥
        参数:
            key: 字符串密钥（通常是授权密钥）
        返回值: 无
        异常情况: 密钥为空时抛出ValueError
        """
        if not key:  # 检查密钥是否为空
            raise ValueError("加密密钥不能为空")
        
        self._raw_key = key  # 原始密钥字符串
        self._aes_key = self._derive_key(key)  # 派生的AES密钥（16字节）
    
    def _derive_key(self, key: str) -> bytes:
        """
        从字符串密钥派生AES密钥
        
        功能: 使用SHA-256哈希派生固定长度的密钥
        参数:
            key: 字符串密钥
        返回值: 16字节的AES密钥
        异常情况: 无
        
        说明: 取SHA-256哈希的前16字节作为AES-128密钥
        """
        # 使用SHA-256对密钥进行哈希
        hash_obj = hashlib.sha256(key.encode("utf-8"))
        # 取前16字节（128位）作为AES密钥
        return hash_obj.digest()[:AES_KEY_LENGTH // 8]
    
    def encrypt(self, plaintext: Union[str, dict]) -> Optional[str]:
        """
        AES-128-CBC加密
        
        功能: 加密明文并返回Base64编码的密文
        参数:
            plaintext: 明文字符串或字典（字典会自动序列化为JSON）
        返回值: Base64编码的密文字符串，失败返回None
        异常情况: 加密失败返回None
        
        输出格式: Base64(IV + 密文)
        """
        if not PYCRYPTODOME_AVAILABLE:
            # pycryptodome不可用，使用简化加密
            return self._simple_encrypt(plaintext)
        
        try:
            # 如果输入是字典，序列化为JSON
            if isinstance(plaintext, dict):
                plaintext = json.dumps(plaintext, ensure_ascii=False)
            
            # 转换为字节
            plaintext_bytes = plaintext.encode("utf-8")
            
            # 生成随机IV（16字节）
            iv = os.urandom(AES_BLOCK_SIZE)
            
            # 创建AES加密器（CBC模式）
            cipher = AES.new(self._aes_key, AES.MODE_CBC, iv)
            
            # PKCS7填充
            padded_data = pad(plaintext_bytes, AES_BLOCK_SIZE)
            
            # 加密
            ciphertext = cipher.encrypt(padded_data)
            
            # IV + 密文，Base64编码
            result = base64.b64encode(iv + ciphertext).decode("utf-8")
            return result
        except Exception:
            return None
    
    def decrypt(self, ciphertext: str) -> Optional[str]:
        """
        AES-128-CBC解密
        
        功能: 解密Base64编码的密文
        参数:
            ciphertext: Base64编码的密文字符串
        返回值: 解密后的明文字符串，失败返回None
        异常情况: 解密失败返回None
        
        输入格式: Base64(IV + 密文)
        """
        if not PYCRYPTODOME_AVAILABLE:
            # pycryptodome不可用，使用简化解密
            return self._simple_decrypt(ciphertext)
        
        try:
            # Base64解码
            encrypted_data = base64.b64decode(ciphertext)
            
            # 分离IV和密文
            iv = encrypted_data[:AES_BLOCK_SIZE]
            ciphertext_bytes = encrypted_data[AES_BLOCK_SIZE:]
            
            # 创建AES解密器
            cipher = AES.new(self._aes_key, AES.MODE_CBC, iv)
            
            # 解密
            padded_data = cipher.decrypt(ciphertext_bytes)
            
            # 去除PKCS7填充
            plaintext_bytes = unpad(padded_data, AES_BLOCK_SIZE)
            
            # 转换为字符串
            return plaintext_bytes.decode("utf-8")
        except Exception:
            return None
    
    def _simple_encrypt(self, plaintext: Union[str, dict]) -> Optional[str]:
        """
        简化加密（pycryptodome不可用时的兜底方案）
        
        功能: 使用XOR和Base64进行简单混淆
        参数:
            plaintext: 明文
        返回值: Base64编码的混淆数据
        异常情况: 失败返回None
        
        警告: 这不是安全的加密，仅作为兜底方案
        """
        try:
            if isinstance(plaintext, dict):
                plaintext = json.dumps(plaintext, ensure_ascii=False)
            
            plaintext_bytes = plaintext.encode("utf-8")
            key_bytes = self._aes_key
            
            # XOR混淆
            encrypted = bytearray()
            for i, byte in enumerate(plaintext_bytes):
                encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
            
            # Base64编码
            return base64.b64encode(bytes(encrypted)).decode("utf-8")
        except Exception:
            return None
    
    def _simple_decrypt(self, ciphertext: str) -> Optional[str]:
        """
        简化解密（pycryptodome不可用时的兜底方案）
        
        功能: 解密XOR混淆的数据
        参数:
            ciphertext: Base64编码的混淆数据
        返回值: 解密后的明文
        异常情况: 失败返回None
        """
        try:
            encrypted = base64.b64decode(ciphertext)
            key_bytes = self._aes_key
            
            # XOR解密
            decrypted = bytearray()
            for i, byte in enumerate(encrypted):
                decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
            
            return bytes(decrypted).decode("utf-8")
        except Exception:
            return None
    
    def encrypt_dict(self, data: dict) -> Optional[str]:
        """
        加密字典数据
        
        功能: 将字典序列化为JSON后加密
        参数:
            data: 要加密的字典
        返回值: Base64编码的密文
        异常情况: 失败返回None
        """
        return self.encrypt(data)
    
    def decrypt_to_dict(self, ciphertext: str) -> Optional[dict]:
        """
        解密为字典
        
        功能: 解密密文并解析为字典
        参数:
            ciphertext: Base64编码的密文
        返回值: 解密后的字典，失败返回None
        异常情况: 解密或JSON解析失败返回None
        """
        try:
            plaintext = self.decrypt(ciphertext)
            if plaintext:
                return json.loads(plaintext)
        except Exception:
            pass
        return None


def create_crypto(key: str) -> Optional[AESCrypto]:
    """
    创建AES加密器实例
    
    功能: 工厂函数，创建AES加密器
    参数:
        key: 加密密钥
    返回值: AESCrypto实例，创建失败返回None
    异常情况: 密钥无效时返回None
    """
    try:
        return AESCrypto(key)
    except Exception:
        return None


def is_crypto_available() -> bool:
    """
    检查加密模块是否可用
    
    功能: 验证pycryptodome是否正确安装
    参数: 无
    返回值: True表示完整加密可用，False表示使用简化加密
    异常情况: 无
    """
    return PYCRYPTODOME_AVAILABLE

"""
SM4 加密工具模块

加密规格：
- 算法: SM4 (GM/T 0002-2012)
- 模式: ECB
- 密钥: IhaIWKKs9AJpn5ip (static)
- Padding: PKCS7 (Manual)
- Output: Base64
"""

import base64
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT

# 静态加密密钥
SM4_KEY = b"IhaIWKKs9AJpn5ip"


def sm4_encrypt(plaintext: str) -> str:
    """
    SM4 ECB 加密
    
    Args:
        plaintext: 明文字符串
        
    Returns:
        Base64 编码的密文
    """
    crypt_sm4 = CryptSM4()
    crypt_sm4.set_key(SM4_KEY, SM4_ENCRYPT)
    
    # gmssl 库会自动进行 PKCS7 填充，无需手动处理
    encrypted_value = crypt_sm4.crypt_ecb(plaintext.encode("utf-8"))
    
    # Base64 编码
    return base64.b64encode(encrypted_value).decode("utf-8")

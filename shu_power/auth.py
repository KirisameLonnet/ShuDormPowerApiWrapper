"""
认证模块 - 支持账号密码和 HMAC 签名两种认证方式
"""

import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional

from .crypto import sm4_encrypt
from .models import Token, Credentials
from .exceptions import AuthenticationError, NetworkError


# 配置日志
logger = logging.getLogger(__name__)

# API 基础配置
BASE_URL = "http://10.10.10.147/openservice"
LOGIN_PATH = "/epeortalAuth/login"
HMAC_LOGIN_PATH = "/epeortalAuth/hmacLogin"
TOKEN_VALIDITY_SECONDS = 7200  # Token 有效期 2 小时


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self._token: Optional[Token] = None

    @property
    def token(self) -> Optional[Token]:
        """获取当前 Token"""
        return self._token

    def is_token_valid(self) -> bool:
        """检查 Token 是否有效"""
        if self._token is None:
            return False
        return datetime.now() < self._token.expires_at

    def clear_token(self) -> None:
        """清除 Token"""
        self._token = None

    async def login(self, credentials: Credentials) -> Token:
        """
        使用凭证登录获取 Token
        
        根据凭证类型自动选择登录方式：
        - HMAC 签名认证（优先）
        - 账号密码认证
        """
        if not credentials.is_valid():
            logger.error("凭证无效：需要提供 HMAC 签名或账号密码")
            raise AuthenticationError("凭证无效：需要提供 HMAC 签名或账号密码")

        if credentials.is_hmac_auth():
            logger.info(f"使用 HMAC 签名登录，学号: {credentials.stuempno}")
            return await self._login_with_hmac(credentials)
        else:
            logger.info(f"使用账号密码登录，学号: {credentials.stuempno}, 姓名: {credentials.custname}")
            return await self._login_with_password(credentials)

    async def _login_with_password(self, credentials: Credentials) -> Token:
        """使用账号密码登录"""
        url = f"{BASE_URL}{LOGIN_PATH}"
        
        # 加密密码
        encrypted_pwd = sm4_encrypt(credentials.password)
        logger.info(f"🔐 密码加密结果: {encrypted_pwd}")
        
        payload = {
            "custname": credentials.custname,
            "stuempno": credentials.stuempno,
            "pwd": encrypted_pwd,
        }

        logger.info(f"📤 发送登录请求: POST {url}")
        logger.info(f"📤 请求体: {payload}")
        
        try:
            async with httpx.AsyncClient() as client:
                # 使用 content 发送 JSON 字符串，确保格式与 curl 一致
                import json
                response = await client.post(
                    url,
                    content=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile)",
                        "Referer": "http://10.10.10.147/epeortal/pages/h5/elecQuery",
                    },
                    timeout=30.0,
                )
                logger.info(f"📥 登录响应状态码: {response.status_code}")
                response_text = response.text
                logger.info(f"📥 登录响应内容: {response_text[:500] if response_text else '(空)'}")
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as e:
            logger.error(f"❌ 无法连接到服务器: {e}")
            raise NetworkError(f"无法连接到服务器 {BASE_URL}: {e}")
        except httpx.RequestError as e:
            logger.error(f"❌ 网络请求失败: {e}")
            raise NetworkError(f"网络请求失败: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP 错误: {e.response.status_code}, 响应: {e.response.text[:200]}")
            raise NetworkError(f"HTTP 错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"❌ 解析响应失败: {e}")
            raise NetworkError(f"解析响应失败: {e}")

        if data.get("retcode") != "0":
            logger.error(f"❌ 登录失败: {data.get('retmsg', '未知错误')}")
            raise AuthenticationError(f"登录失败: {data.get('retmsg', '未知错误')}")

        access_token = data.get("data", {}).get("token")
        if not access_token:
            logger.error("❌ 登录响应中没有 Token")
            raise AuthenticationError("登录响应中没有 Token")

        logger.info("✅ 登录成功，获取到 Token")
        
        self._token = Token(
            access_token=access_token,
            expires_at=datetime.now() + timedelta(seconds=TOKEN_VALIDITY_SECONDS),
            token_type=data.get("data", {}).get("type", "SHU"),
        )
        return self._token

    async def _login_with_hmac(self, credentials: Credentials) -> Token:
        """使用 HMAC 签名登录"""
        url = f"{BASE_URL}{HMAC_LOGIN_PATH}"
        
        payload = {
            "sign": credentials.hmac_sign,
            "sign_method": "HMAC",
            "stuempno": credentials.stuempno,
            "timestamp": credentials.hmac_timestamp,
        }

        logger.info(f"📤 发送 HMAC 登录请求: POST {url}")

        try:
            async with httpx.AsyncClient() as client:
                import json
                response = await client.post(
                    url,
                    content=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile)",
                        "Referer": "http://10.10.10.147/epeortal/pages/h5/elecQuery",
                    },
                    timeout=30.0,
                )
                logger.info(f"📥 HMAC 登录响应状态码: {response.status_code}")
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as e:
            logger.error(f"❌ 无法连接到服务器: {e}")
            raise NetworkError(f"无法连接到服务器 {BASE_URL}: {e}")
        except httpx.RequestError as e:
            logger.error(f"❌ 网络请求失败: {e}")
            raise NetworkError(f"网络请求失败: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP 错误: {e.response.status_code}")
            raise NetworkError(f"HTTP 错误: {e.response.status_code}")

        if data.get("retcode") != "0":
            logger.error(f"❌ HMAC 登录失败: {data.get('retmsg', '未知错误')}")
            raise AuthenticationError(f"HMAC 登录失败: {data.get('retmsg', '未知错误')}")

        access_token = data.get("data", {}).get("token")
        if not access_token:
            logger.error("❌ 登录响应中没有 Token")
            raise AuthenticationError("登录响应中没有 Token")

        logger.info("✅ HMAC 登录成功，获取到 Token")
        
        self._token = Token(
            access_token=access_token,
            expires_at=datetime.now() + timedelta(seconds=TOKEN_VALIDITY_SECONDS),
            token_type=data.get("data", {}).get("type", "SHU"),
        )
        return self._token

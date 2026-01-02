"""
SHU Power 客户端 - 封装认证和查询逻辑
"""

import os
import logging
import httpx
from datetime import datetime
from typing import Optional

from .auth import AuthManager, BASE_URL
from .models import Token, PowerInfo, QueryRequest, Credentials
from .exceptions import (
    ShuPowerError,
    AuthenticationError,
    NetworkError,
    QueryError,
    TokenExpiredError,
)


# 配置日志
logger = logging.getLogger(__name__)

# 电费查询路径
QUERY_PATH = "/miniprogram/queryroominfo"


class ShuPowerClient:
    """
    SHU Power API 客户端
    
    支持两种使用方式：
    1. 从环境变量读取凭证（每次查询实时读取，支持热更新）
    2. 使用用户提供的凭证（优先级更高）
    """

    def __init__(self):
        self._auth_manager = AuthManager()

    def _get_credentials_from_env(self) -> Optional[Credentials]:
        """
        从环境变量实时读取凭证
        每次调用都重新读取，支持运行时热更新
        """
        stuempno = os.environ.get("SHU_STUEMPNO")
        if not stuempno:
            logger.warning("环境变量 SHU_STUEMPNO 未设置")
            return None

        # 优先使用 HMAC 认证
        hmac_sign = os.environ.get("SHU_HMAC_SIGN")
        hmac_timestamp = os.environ.get("SHU_HMAC_TIMESTAMP")
        
        if hmac_sign and hmac_timestamp:
            logger.info(f"从环境变量读取 HMAC 凭证，学号: {stuempno}")
            return Credentials(
                stuempno=stuempno,
                hmac_sign=hmac_sign,
                hmac_timestamp=hmac_timestamp,
            )

        # 其次使用账号密码认证
        custname = os.environ.get("SHU_CUSTNAME")
        password = os.environ.get("SHU_PASSWORD")
        
        if custname and password:
            logger.info(f"从环境变量读取账号密码凭证，学号: {stuempno}, 姓名: {custname}")
            return Credentials(
                stuempno=stuempno,
                custname=custname,
                password=password,
            )

        logger.warning("环境变量中未找到完整的凭证配置")
        return None

    def _build_credentials(
        self,
        stuempno: Optional[str] = None,
        hmac_sign: Optional[str] = None,
        hmac_timestamp: Optional[str] = None,
    ) -> Credentials:
        """
        构建凭证
        优先级: 用户提供的 HMAC > 环境变量 HMAC > 环境变量账号密码
        """
        # 如果用户提供了 HMAC 凭证，优先使用
        if stuempno and hmac_sign and hmac_timestamp:
            logger.info(f"使用用户提供的 HMAC 凭证，学号: {stuempno}")
            return Credentials(
                stuempno=stuempno,
                hmac_sign=hmac_sign,
                hmac_timestamp=hmac_timestamp,
            )

        # 否则从环境变量读取
        env_credentials = self._get_credentials_from_env()
        if env_credentials:
            return env_credentials

        logger.error("未找到有效凭证")
        raise AuthenticationError(
            "未找到有效凭证：请设置环境变量 (SHU_STUEMPNO, SHU_HMAC_SIGN, SHU_HMAC_TIMESTAMP) "
            "或 (SHU_STUEMPNO, SHU_CUSTNAME, SHU_PASSWORD)，或在请求中提供 HMAC 凭证"
        )

    async def _ensure_token(self, credentials: Credentials) -> Token:
        """确保有有效的 Token"""
        # 每次都重新登录以确保使用最新凭证
        # 这支持运行时切换访问角色
        return await self._auth_manager.login(credentials)

    async def query_power(
        self,
        elcsysid: str,
        areaid: str,
        districtid: str,
        buildid: str,
        floorid: str,
        roomid: str,
        stuempno: Optional[str] = None,
        hmac_sign: Optional[str] = None,
        hmac_timestamp: Optional[str] = None,
    ) -> PowerInfo:
        """
        查询电费信息 - 6级级联
        
        Args:
            elcsysid: 系统ID (1=嘉定校区, 2=宝山校内, 3=宝山南区, 4=宝山新世纪)
            areaid: 校区ID
            districtid: 区域ID
            buildid: 楼栋ID
            floorid: 楼层ID
            roomid: 房间ID
            stuempno: 可选，用户学号（用于 HMAC 认证）
            hmac_sign: 可选，HMAC 签名（优先使用）
            hmac_timestamp: 可选，HMAC 时间戳
            
        Returns:
            PowerInfo: 电费信息
        """
        logger.info(f"🔍 开始查询电费: 系统={elcsysid}, 校区={areaid}, 区域={districtid}, 楼栋={buildid}, 楼层={floorid}, 房间={roomid}")
        
        # 构建凭证（每次查询都实时读取环境变量）
        credentials = self._build_credentials(stuempno, hmac_sign, hmac_timestamp)
        
        # 获取 Token
        token = await self._ensure_token(credentials)
        
        # 构建查询请求
        query = QueryRequest(
            elcsysid=elcsysid,
            areaid=areaid,
            districtid=districtid,
            buildid=buildid,
            floorid=floorid,
            roomid=roomid,
        )
        
        # 执行查询
        return await self._do_query(token, query)

    async def _do_query(self, token: Token, query: QueryRequest) -> PowerInfo:
        """执行电费查询"""
        url = f"{BASE_URL}{QUERY_PATH}"
        
        payload = {
            "elcsysid": query.elcsysid,
            "areaid": query.areaid,
            "districtid": query.districtid,
            "buildid": query.buildid,
            "floorid": query.floorid,
            "roomid": query.roomid,
        }

        logger.info(f"📤 发送电费查询请求: POST {url}")
        logger.debug(f"📤 请求参数: {payload}")

        try:
            async with httpx.AsyncClient() as client:
                import json
                response = await client.post(
                    url,
                    content=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                    headers={
                        "Content-Type": "application/json",
                        "sw-authorization": f"Bearer {token.access_token}",
                        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile)",
                        "Referer": "http://10.10.10.147/epeortal/pages/h5/elecQuery",
                    },
                    timeout=30.0,
                )
                logger.info(f"📥 查询响应状态码: {response.status_code}")
                logger.info(f"📥 查询响应内容: {response.text}")
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
        except Exception as e:
            logger.error(f"❌ 解析响应失败: {e}")
            raise NetworkError(f"解析响应失败: {e}")

        if data.get("retcode") != "0":
            logger.error(f"❌ 查询失败: {data.get('retmsg', '未知错误')}")
            raise QueryError(f"查询失败: {data.get('retmsg', '未知错误')}")

        result_data = data.get("data", {})
        
        power_info = PowerInfo(
            roomid=result_data.get("roomId", query.roomid),
            room_name=result_data.get("roomName", ""),
            rest_elec_degree=float(result_data.get("restElecDegree", 0)),
            areaid=result_data.get("areaId", query.areaid),
            buildid=result_data.get("buiId", query.buildid),
            query_time=datetime.now(),
        )
        
        logger.info(f"✅ 查询成功: 房间={power_info.room_name}, 剩余电量={power_info.rest_elec_degree}度")
        
        return power_info

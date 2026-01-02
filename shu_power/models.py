"""
数据模型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Token:
    """认证 Token"""

    access_token: str
    expires_at: datetime
    token_type: str = "SHU"


@dataclass
class QueryRequest:
    """电费查询请求参数 - 6级级联"""

    elcsysid: str  # 系统ID: 1=嘉定校区, 2=宝山校内, 3=宝山南区, 4=宝山新世纪
    areaid: str       # 校区ID
    districtid: str   # 区域ID
    buildid: str      # 楼栋ID
    floorid: str      # 楼层ID
    roomid: str       # 房间ID


@dataclass
class PowerInfo:
    """电费信息"""

    roomid: str
    room_name: str
    rest_elec_degree: float  # 剩余电量(度)
    areaid: str
    buildid: str
    query_time: datetime = field(default_factory=datetime.now)


@dataclass
class Credentials:
    """认证凭证 - 支持账号密码或HMAC"""

    stuempno: str
    custname: Optional[str] = None
    password: Optional[str] = None
    hmac_sign: Optional[str] = None
    hmac_timestamp: Optional[str] = None

    def is_hmac_auth(self) -> bool:
        """是否使用 HMAC 认证"""
        return self.hmac_sign is not None and self.hmac_timestamp is not None

    def is_password_auth(self) -> bool:
        """是否使用账号密码认证"""
        return (
            self.custname is not None
            and self.password is not None
            and not self.is_hmac_auth()
        )

    def is_valid(self) -> bool:
        """凭证是否有效"""
        return self.is_hmac_auth() or self.is_password_auth()

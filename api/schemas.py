"""
API 请求/响应模型
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """电费查询请求 - 6级级联"""

    elcsysid: str = Field(..., description="系统ID: 1=嘉定校区, 2=宝山校内, 3=宝山南区, 4=宝山新世纪")
    areaid: str = Field(..., description="校区ID")
    districtid: str = Field(..., description="区域ID")
    buildid: str = Field(..., description="楼栋ID")
    floorid: str = Field(..., description="楼层ID")
    roomid: str = Field(..., description="房间ID")
    
    # 可选：用户携带的 HMAC 凭证（优先使用）
    stuempno: Optional[str] = Field(None, description="学号（使用自己的HMAC时需要）")
    hmac_sign: Optional[str] = Field(None, description="HMAC签名（优先使用）")
    hmac_timestamp: Optional[str] = Field(None, description="HMAC时间戳")


class PowerData(BaseModel):
    """电费数据"""

    roomid: str
    room_name: str
    rest_elec_degree: float = Field(..., description="剩余电量(度)")
    areaid: str
    buildid: str


class QueryResponse(BaseModel):
    """查询响应"""

    success: bool
    data: Optional[PowerData] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """错误响应"""

    success: bool = False
    error: str


# ============ 友好查询接口 ============

class FriendlyQueryRequest(BaseModel):
    """友好查询请求 - 使用中文名称"""
    
    building: str = Field(..., description="楼栋名称，如 '嘉定一号楼'")
    room: str = Field(..., description="房间号，如 '102' 或 '102房间'")
    
    # 可选：用户携带的 HMAC 凭证
    stuempno: Optional[str] = Field(None, description="学号")
    hmac_sign: Optional[str] = Field(None, description="HMAC签名")
    hmac_timestamp: Optional[str] = Field(None, description="HMAC时间戳")


class FriendlyQueryResponse(BaseModel):
    """友好查询响应"""
    
    success: bool
    data: Optional[PowerData] = None
    location: Optional[str] = Field(None, description="匹配到的完整位置名称")
    error: Optional[str] = None


class SearchRequest(BaseModel):
    """搜索请求"""
    
    keyword: str = Field(..., description="搜索关键词，如 '嘉定一号楼'")
    limit: int = Field(10, ge=1, le=50, description="返回结果数量")


class SearchResult(BaseModel):
    """搜索结果项"""
    
    full_name: str
    building_name: str
    room_name: str
    elcsysid: str
    areaid: str
    districtid: str
    buildid: str
    floorid: str
    roomid: str


class SearchResponse(BaseModel):
    """搜索响应"""
    
    success: bool
    count: int = 0
    results: List[SearchResult] = []
    error: Optional[str] = None

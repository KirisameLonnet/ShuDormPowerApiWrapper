"""
SHU Power API - FastAPI 应用入口

电费查询 API 服务，支持：
- 使用环境变量中的凭证查询
- 用户携带自己的 HMAC 签名查询（优先使用）
- 环境变量实时读取（支持运行时热更新）
"""

import os
import logging
import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .schemas import (
    QueryRequest, QueryResponse, PowerData, ErrorResponse,
    FriendlyQueryRequest, FriendlyQueryResponse,
    SearchRequest, SearchResult, SearchResponse,
)
from shu_power import ShuPowerClient
from shu_power.dorm_lookup import dorm_service
from shu_power.auth import BASE_URL
from shu_power.exceptions import (
    ShuPowerError,
    AuthenticationError,
    NetworkError,
    QueryError,
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def check_server_reachable() -> bool:
    """检查上海大学服务器是否可达"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(BASE_URL)
            return True
    except Exception:
        return False


def check_env_credentials() -> dict:
    """检查环境变量中的凭证配置"""
    result = {
        "stuempno": os.environ.get("SHU_STUEMPNO"),
        "hmac_sign": os.environ.get("SHU_HMAC_SIGN"),
        "hmac_timestamp": os.environ.get("SHU_HMAC_TIMESTAMP"),
        "custname": os.environ.get("SHU_CUSTNAME"),
        "password": bool(os.environ.get("SHU_PASSWORD")),  # 仅显示是否设置
    }
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动时健康检查"""
    logger.info("=" * 60)
    logger.info("🚀 SHU Power API 启动中...")
    logger.info("=" * 60)
    
    # 检查服务器连接
    logger.info(f"📡 检查上海大学服务器连接: {BASE_URL}")
    server_ok = await check_server_reachable()
    if server_ok:
        logger.info("✅ 上海大学服务器可达")
    else:
        logger.warning("⚠️  警告: 无法连接到上海大学服务器!")
        logger.warning("⚠️  请确保您在校园网环境下，或通过 VPN 连接")
    
    # 检查环境变量
    logger.info("🔑 检查环境变量凭证配置...")
    creds = check_env_credentials()
    
    has_stuempno = bool(creds["stuempno"])
    if has_stuempno:
        logger.info(f"   SHU_STUEMPNO: {creds['stuempno']}")
    else:
        logger.warning("   ⚠️  SHU_STUEMPNO 未设置 (所有认证方式均需此项)")
    
    # 检查认证组合
    has_credentials = False
    if has_stuempno:
        if creds["hmac_sign"] and creds["hmac_timestamp"]:
            logger.info("   ✅ HMAC 签名凭证组合已配置 (学号+签名+时间戳)")
            has_credentials = True
        elif creds["custname"] and creds["password"]:
            logger.info(f"   ✅ 账号密码凭证组合已配置 (学号+姓名: {creds['custname']}+密码)")
            has_credentials = True
    
    if not has_credentials:
        logger.warning("   ⚠️  警告: 未找到完整的凭证配置组合!")
        logger.warning("   请配置以下组合之一:")
        logger.warning("   1. SHU_STUEMPNO + SHU_HMAC_SIGN + SHU_HMAC_TIMESTAMP")
        logger.warning("   2. SHU_STUEMPNO + SHU_CUSTNAME + SHU_PASSWORD")
    
    # 尝试登录获取 Token
    token_ok = False
    if server_ok and has_credentials:
        logger.info("🔐 尝试登录获取访问 Token...")
        try:
            from shu_power.auth import AuthManager
            from shu_power.models import Credentials
            
            auth = AuthManager()
            if creds["hmac_sign"] and creds["hmac_timestamp"]:
                credentials = Credentials(
                    stuempno=creds["stuempno"],
                    hmac_sign=creds["hmac_sign"],
                    hmac_timestamp=creds["hmac_timestamp"],
                )
            else:
                credentials = Credentials(
                    stuempno=creds["stuempno"],
                    custname=creds["custname"],
                    password=os.environ.get("SHU_PASSWORD"),
                )
            
            token = await auth.login(credentials)
            logger.info(f"✅ 登录成功! Token 类型: {token.token_type}")
            logger.info(f"   Token 有效期至: {token.expires_at.strftime('%H:%M:%S')}")
            token_ok = True
        except Exception as e:
            logger.error(f"❌ 登录失败: {e}")
    
    logger.info("=" * 60)
    if server_ok and token_ok:
        logger.info("✅ 服务就绪，凭证验证通过")
    elif server_ok and has_credentials:
        logger.warning("⚠️  服务启动，但凭证验证失败")
    else:
        logger.warning("⚠️  服务启动，但存在配置问题")
    logger.info("=" * 60)
    
    yield  # 应用运行中
    
    logger.info("🛑 SHU Power API 关闭")


app = FastAPI(
    title="SHU Power API",
    description="上海大学宿舍电费查询 API",
    version="0.1.0",
    lifespan=lifespan,
)


# 全局客户端实例
client = ShuPowerClient()


@app.post(
    "/query",
    response_model=QueryResponse,
    responses={
        200: {"description": "查询成功"},
        401: {"model": ErrorResponse, "description": "认证失败"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def query_power(request: QueryRequest) -> QueryResponse:
    """
    查询电费信息
    
    - 如果提供了 stuempno, hmac_sign, hmac_timestamp，则使用用户提供的凭证（优先）
    - 否则使用环境变量中的凭证
    - 环境变量在每次查询时实时读取，支持运行时热更新
    """
    try:
        power_info = await client.query_power(
            elcsysid=request.elcsysid,
            areaid=request.areaid,
            districtid=request.districtid,
            buildid=request.buildid,
            floorid=request.floorid,
            roomid=request.roomid,
            stuempno=request.stuempno,
            hmac_sign=request.hmac_sign,
            hmac_timestamp=request.hmac_timestamp,
        )
        
        return QueryResponse(
            success=True,
            data=PowerData(
                roomid=power_info.roomid,
                room_name=power_info.room_name,
                rest_elec_degree=power_info.rest_elec_degree,
                areaid=power_info.areaid,
                buildid=power_info.buildid,
            ),
        )
    except AuthenticationError as e:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": str(e)},
        )
    except NetworkError as e:
        return JSONResponse(
            status_code=502,
            content={"success": False, "error": f"网络错误: {e}"},
        )
    except QueryError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)},
        )
    except ShuPowerError as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"未知错误: {e}"},
        )


@app.get("/health")
async def health_check():
    """健康检查 - 返回服务状态和配置信息"""
    server_ok = await check_server_reachable()
    creds = check_env_credentials()
    
    has_credentials = bool(
        creds["stuempno"] and (
            (creds["hmac_sign"] and creds["hmac_timestamp"]) or
            (creds["custname"] and creds["password"])
        )
    )
    
    return {
        "status": "ok" if (server_ok and has_credentials) else "degraded",
        "server_reachable": server_ok,
        "credentials_configured": has_credentials,
    }


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "SHU Power API",
        "version": "0.2.0",
        "docs": "/docs",
        "endpoints": [
            {"path": "/query", "description": "原始查询（需要完整ID）"},
            {"path": "/query/friendly", "description": "友好查询（使用中文名称）"},
            {"path": "/search", "description": "搜索房间ID"},
        ]
    }


# ============ 友好查询接口 ============

@app.post(
    "/query/friendly",
    response_model=FriendlyQueryResponse,
    responses={
        200: {"description": "查询成功"},
        404: {"description": "房间未找到"},
        401: {"model": ErrorResponse, "description": "认证失败"},
    },
)
async def query_power_friendly(request: FriendlyQueryRequest) -> FriendlyQueryResponse:
    """
    友好查询接口 - 使用中文名称查询电费
    
    示例：
    - building: "嘉定一号楼"
    - room: "102"
    
    服务器会自动查找对应的 ID 链并执行查询。
    """
    # 1. 查找房间
    try:
        dorm_info = dorm_service.find_exact(request.building, request.room)
    except FileNotFoundError as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"服务器配置错误: {e}"},
        )
    
    if not dorm_info:
        return JSONResponse(
            status_code=404,
            content={
                "success": False, 
                "error": f"未找到房间: {request.building} {request.room}",
                "hint": "请使用 /search 接口确认房间名称",
            },
        )
    
    logger.info(f"📍 匹配到房间: {dorm_info.full_name}")
    
    # 2. 执行电费查询
    try:
        power_info = await client.query_power(
            elcsysid=dorm_info.elcsysid,
            areaid=dorm_info.areaid,
            districtid=dorm_info.districtid,
            buildid=dorm_info.buildid,
            floorid=dorm_info.floorid,
            roomid=dorm_info.roomid,
            stuempno=request.stuempno,
            hmac_sign=request.hmac_sign,
            hmac_timestamp=request.hmac_timestamp,
        )
        
        return FriendlyQueryResponse(
            success=True,
            location=dorm_info.full_name,
            data=PowerData(
                roomid=power_info.roomid,
                room_name=power_info.room_name,
                rest_elec_degree=power_info.rest_elec_degree,
                areaid=power_info.areaid,
                buildid=power_info.buildid,
            ),
        )
    except AuthenticationError as e:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": str(e)},
        )
    except NetworkError as e:
        return JSONResponse(
            status_code=502,
            content={"success": False, "error": f"网络错误: {e}"},
        )
    except QueryError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"未知错误: {e}"},
        )


@app.post(
    "/search",
    response_model=SearchResponse,
)
async def search_rooms(request: SearchRequest) -> SearchResponse:
    """
    搜索房间 - 根据关键词查找房间 ID
    
    示例搜索：
    - "嘉定一号楼" - 列出该楼所有房间
    - "嘉定一号楼 102" - 查找特定房间
    - "嘉定 一号楼" - 多关键词匹配
    """
    try:
        results = dorm_service.search(request.keyword, limit=request.limit)
        
        return SearchResponse(
            success=True,
            count=len(results),
            results=[
                SearchResult(
                    full_name=r.full_name,
                    building_name=r.building_name,
                    room_name=r.room_name,
                    elcsysid=r.elcsysid,
                    areaid=r.areaid,
                    districtid=r.districtid,
                    buildid=r.buildid,
                    floorid=r.floorid,
                    roomid=r.roomid,
                )
                for r in results
            ],
        )
    except FileNotFoundError as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"服务器配置错误: {e}"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"搜索失败: {e}"},
        )


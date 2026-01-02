"""
SHU Power API - 上海大学宿舍电费查询库
"""

from .client import ShuPowerClient
from .models import Token, PowerInfo, QueryRequest
from .exceptions import (
    ShuPowerError,
    AuthenticationError,
    NetworkError,
    TokenExpiredError,
)

__all__ = [
    "ShuPowerClient",
    "Token",
    "PowerInfo",
    "QueryRequest",
    "ShuPowerError",
    "AuthenticationError",
    "NetworkError",
    "TokenExpiredError",
]

__version__ = "0.1.0"

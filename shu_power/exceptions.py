"""
自定义异常类
"""


class ShuPowerError(Exception):
    """SHU Power API 基础异常"""

    pass


class AuthenticationError(ShuPowerError):
    """认证失败异常"""

    pass


class TokenExpiredError(AuthenticationError):
    """Token 已过期异常"""

    pass


class NetworkError(ShuPowerError):
    """网络请求异常"""

    pass


class QueryError(ShuPowerError):
    """查询失败异常"""

    pass

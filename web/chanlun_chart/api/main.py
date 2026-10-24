"""FastAPI 应用对象与路由装配入口。

应用按系统状态、缠论分析和 TradingView 协议三个边界组织路由。工厂函数只
负责创建应用及注册路由，不主动连接行情源、数据库或交易服务，因此模块导入
过程不会触发外部业务操作。

``app`` 是 Uvicorn 使用的标准 ASGI 应用对象；``create_app`` 可供独立进程、
自动化检查或其他 ASGI 容器创建彼此隔离的应用实例。
"""

from fastapi import FastAPI

from .routers.analysis import router as analysis_router
from .routers.system import router as system_router
from .routers.tradingview import router as tradingview_router


def create_app() -> FastAPI:
    """创建并返回完成路由注册的 FastAPI 应用。

    API 文档统一放在 ``/api`` 命名空间下，业务路由的具体前缀、请求模型与
    响应结构由各自的 router 模块定义。
    """
    application = FastAPI(
        title="ChanNexus",
        version="1",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    # 路由按职责集中装配，避免启动入口直接包含业务处理逻辑。
    application.include_router(system_router)
    application.include_router(analysis_router)
    application.include_router(tradingview_router)
    return application


# Uvicorn 默认加载的 ASGI 应用实例。
app = create_app()

"""FastAPI 服务的本地进程入口。

本模块负责准备项目导入路径、读取 Web 监听配置，并交由 Uvicorn 加载
``web.chanlun_chart.api.main:app``。路由注册、请求校验和缠论计算均由 API
包内对应模块负责，入口本身不保存业务状态。

推荐从项目根目录执行 ``python web/chanlun_chart/fastapi_app.py``。直接运行
文件时无需额外安装项目包；下方路径初始化会确保项目根目录和 ``src`` 目录
可以被 Python 正确导入。
"""

from __future__ import annotations

import pathlib
import sys


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
# 支持直接以脚本方式启动，同时保证本地源码优先于全局同名包。
for path in (PROJECT_ROOT, SRC_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def main() -> None:
    """读取项目配置并启动 Uvicorn 服务。

    监听地址和端口分别来自 ``WEB_HOST`` 与 ``WEB_PORT``。服务启动后，
    Uvicorn 会导入 API 应用对象并接管 HTTP 请求；关闭进程时由 Uvicorn
    完成连接回收和事件循环退出。
    """
    import uvicorn

    from chanlun import config

    # 使用导入字符串加载应用，确保 Uvicorn 按标准 ASGI 生命周期管理服务。
    uvicorn.run(
        "web.chanlun_chart.api.main:app",
        host=config.WEB_HOST,
        port=getattr(config, "WEB_PORT", 9910),
        reload=False,
    )


if __name__ == "__main__":
    main()

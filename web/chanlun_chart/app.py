"""Tornado 承载的 Web 图表服务入口。

本模块负责准备源码导入路径、创建 Web 应用、配置线程池并启动 Tornado 事件
循环。业务页面、图表数据和接口路由由 ``cl_app.create_app`` 统一装配，入口不
直接处理行情或缠论计算。

启动阶段统一识别依赖缺失、项目路径、源码语法和应用初始化错误，并输出对应
的检查命令。默认启动后会打开浏览器；命令行传入 ``nobrowser`` 时仅启动服务，
适用于后台运行和终端联调。
"""

from __future__ import annotations

import pathlib
import sys
import traceback


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
WEB_PATH = pathlib.Path(__file__).resolve().parent
# 直接运行入口文件时，显式加入源码和 Web 包目录。
for path in (SRC_PATH, WEB_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


PIP_PACKAGES = {
    "apscheduler": "apscheduler",
    "flask": "flask",
    "flask_login": "flask-login",
    "pinyin": "pinyin",
    "pytz": "pytz",
    "tzlocal": "tzlocal",
    "tornado": "tornado",
    "numpy": "numpy",
    "pandas": "pandas",
    "talib": "TA-Lib",
    "loguru": "loguru",
    "dotenv": "python-dotenv",
    "sqlalchemy": "sqlalchemy",
    "redis": "redis",
    "pymysql": "pymysql",
    "requests": "requests",
    "pyecharts": "pyecharts",
    "lark_oapi": "lark-oapi",
    "openai": "openai",
    "MyTT": "mytt",
    "pytdx": "pytdx",
}


def _print_startup_error(exc: BaseException) -> None:
    """将启动故障转换为清晰、可操作的诊断信息。"""
    print("\n" + "=" * 72, file=sys.stderr)
    print("Web服务启动失败", file=sys.stderr)
    print(f"Python: {sys.executable}", file=sys.stderr)
    print(f"项目目录: {PROJECT_ROOT}", file=sys.stderr)

    if isinstance(exc, ModuleNotFoundError):
        module = (exc.name or "未知模块").split(".")[0]
        if module in {"chanlun", "cl_app"}:
            print("[PATH_ERROR] 项目模块无法导入。", file=sys.stderr)
            print(f'执行: export PYTHONPATH="{SRC_PATH}"', file=sys.stderr)
        else:
            package = PIP_PACKAGES.get(module, module.replace("_", "-"))
            print(f"[DEPENDENCY_ERROR] 缺少Python模块: {module}", file=sys.stderr)
            print(f'执行: "{sys.executable}" -m pip install {package}', file=sys.stderr)
            print(
                f'批量自检: "{sys.executable}" script/scan_dependencies.py --check',
                file=sys.stderr,
            )
    elif isinstance(exc, SyntaxError):
        print("[SYNTAX_ERROR] Python源码存在语法错误。", file=sys.stderr)
        print(
            f"文件: {exc.filename or '未知'} 行: {exc.lineno or '未知'} "
            f"内容: {(exc.text or '').strip()}",
            file=sys.stderr,
        )
        print(f'执行: "{sys.executable}" -m compileall -q src web script', file=sys.stderr)
    elif isinstance(exc, (FileNotFoundError, NotADirectoryError)):
        print(f"[PATH_ERROR] 文件或目录不存在: {exc}", file=sys.stderr)
        print(f'执行: cd "{PROJECT_ROOT}"', file=sys.stderr)
        print(f'执行: export PYTHONPATH="{SRC_PATH}"', file=sys.stderr)
    else:
        print(f"[INITIALIZATION_ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("依赖已经导入，但应用初始化或服务创建失败，请查看下方堆栈。", file=sys.stderr)

    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
    print("=" * 72, file=sys.stderr)


def main() -> int:
    """创建应用并启动 Tornado 服务，返回标准进程退出码。

    正常停止或收到键盘中断时返回 ``0``；启动阶段发生异常时打印分类诊断信息
    并返回 ``1``。依赖在函数内加载，使所有导入故障都能进入统一诊断流程。
    """
    try:
        from concurrent.futures import ThreadPoolExecutor
        import webbrowser

        from tornado.httpserver import HTTPServer
        from tornado.ioloop import IOLoop
        from tornado.wsgi import WSGIContainer

        import chanlun.encodefix  # noqa: F401
        from chanlun import config
        from cl_app import create_app

        # WSGI 应用通过固定线程池接入 Tornado，事件循环只负责网络调度。
        app = create_app()
        server = HTTPServer(WSGIContainer(app, executor=ThreadPoolExecutor(10)))
        web_port = getattr(config, "WEB_PORT", 9910)
        server.bind(web_port, config.WEB_HOST)
        server.start(1)

        # 浏览器始终使用本机地址访问，监听地址仍由 WEB_HOST 控制。
        url = f"http://127.0.0.1:{web_port}"
        print(f"启动成功: {url}")
        if "nobrowser" not in sys.argv[1:]:
            webbrowser.open(url)
        IOLoop.current().start()
        return 0
    except KeyboardInterrupt:
        print("收到中断信号，Web服务已停止")
        return 0
    except BaseException as exc:
        _print_startup_error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

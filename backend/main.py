"""
FastAPI 应用入口模块

负责创建应用实例、注册中间件、挂载路由、配置CORS等启动初始化工作。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import AppConfig
from backend.api.routes.script_routes import router as script_router


def create_app() -> FastAPI:
    """
    创建并配置FastAPI应用实例。

    执行以下初始化操作：
    1. 设置应用元数据（标题、描述、版本）
    2. 配置CORS中间件，允许前端跨域访问
    3. 注册剧本转换相关API路由

    Returns:
        FastAPI: 配置完成的应用实例，可直接由uvicorn启动

    Note:
        CORS origins 从 AppConfig.CORS_ORIGINS 读取，默认允许所有来源（开发模式）
    """
    app = FastAPI(
        title="Novel2Script-AI API",
        description="AI小说转剧本工具后端服务 - 将长篇小说文本转换为结构化YAML剧本",
        version="1.0.0",
    )

    # CORS 中间件配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=AppConfig.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(script_router, prefix="/api")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

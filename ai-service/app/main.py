"""
FastAPI 主应用入口
"""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.routers import chat, grading, legal, rag, plan_agent

# 设置日志
setup_logging()
logger = get_logger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于 LangChain 的智能教育 AI 服务",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.debug else None,
        },
    )


# 健康检查
@app.get("/health", tags=["健康检查"])
async def health_check():
    """服务健康检查端点"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "model": settings.openai_model,
    }


# 注册路由
app.include_router(chat.router, prefix="/chat", tags=["智能问答"])
app.include_router(grading.router, prefix="/grading", tags=["作业批阅"])
app.include_router(legal.router, prefix="/legal", tags=["法律法规"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
app.include_router(plan_agent.router, prefix="/plan-agent", tags=["教案Agent"])


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(
        "AI Service started",
        app_name=settings.app_name,
        version=settings.app_version,
        model=settings.openai_model,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("AI Service stopped")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
    )

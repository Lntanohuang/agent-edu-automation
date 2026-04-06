"""
日志配置
"""
import logging
import sys
from typing import Any, Dict

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """配置结构化日志"""
    
    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取日志记录器"""
    return structlog.get_logger(name)


def get_traced_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取自动绑定当前请求 trace_id 的日志记录器。

    在中间件注入 trace_id 后，任何模块调用此函数即可获得
    带 trace_id 的 BoundLogger，无需手动 .bind()。
    """
    from app.core.middleware import trace_id_var
    return structlog.get_logger(name).bind(trace_id=trace_id_var.get())

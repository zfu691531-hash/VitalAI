# -*- coding: utf-8 -*-
"""
请求日志中间件
==============
记录所有请求的路径、方法、状态码、耗时。
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from utils.logger import logger


class LogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 记录开始时间
        start_time = time.time()
        
        # 处理请求
        response = await call_next(request)
        
        # 计算耗时
        process_time = (time.time() - start_time) * 1000  # 毫秒
        
        # 记录日志
        logger.info(
            f"[{request.method}] {request.url.path} "
            f"- {response.status_code} - {process_time:.2f}ms"
        )
        
        # 添加响应头
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        
        return response

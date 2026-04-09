# -*- coding: utf-8 -*-
"""
日志配置模块
============
配置 Python logging，按类型分类输出日志：
- 操作日志: 用户登录、数据增删改等操作记录
- AI调用日志: AI接口调用时间、功能类型、参数摘要、结果状态
- 异常日志: 系统异常、关联ID异常等错误信息
输出到文件和控制台，支持按日期轮转。
"""

import logging
from pathlib import Path
import os

# 日志格式
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _create_formatter() -> logging.Formatter:
    """创建统一的日志格式化器。"""
    return logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)


def _get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """获取或创建指定名称的 Logger，仅使用控制台输出。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = _create_formatter()

    # 控制台输出（DEBUG 级别）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 三类日志实例
logger = _get_logger("aistu")
operation_logger = _get_logger("aistu.operation")
ai_logger = _get_logger("aistu.ai")
error_logger = _get_logger("aistu.error")

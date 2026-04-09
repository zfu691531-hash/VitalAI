# -*- coding: utf-8 -*-
"""
全局配置模块
============
使用 pydantic-settings 从 .env 文件读取配置，提供类型安全的配置项。
包含：数据库连接、JWT密钥与过期时间、AI大模型API地址与密钥、服务端口等。
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """全局配置，从 .env 文件读取，全局单例。"""

    # 数据库连接（MySQL 8.0）
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "aistu"

    # JWT 配置
    JWT_SECRET: str = "change_this_secret_key_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # AI 大模型 API 配置
    AI_API_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_MODEL_NAME: str = ""
    AI_MODEL_NAME_LIGHT: str = ""
    AI_MODEL_NAME_STRONG: str = ""
    AI_TIMEOUT: int = 60
    AI_EMBEDDING_MODEL_NAME: str = ""
    AI_EMBEDDING_DIM: int = 1024
    STUDENT_CARE_FACT_WEB_SEARCH: bool = False
    NEO4J_ENABLED: bool = False
    NEO4J_URI: str = "bolt://127.0.0.1:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"

    # Milvus
    MILVUS_URI: str = ""
    MILVUS_TOKEN: str = ""
    MILVUS_COLLECTION: str = "school_rule_chunks"

    # 服务配置
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = False

    model_config = {"env_file": str(ENV_FILE), "env_file_encoding": "utf-8"}

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """兼容布尔值和常见环境标记，避免 .env 写法差异导致启动失败。"""
        if isinstance(value, bool):
            return value
        if value is None:
            return False

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
            return False
        return False

    @property
    def DATABASE_URL(self) -> str:
        """MySQL 连接字符串，强制 utf8mb4 字符集。"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )


settings = Settings()

"""Lazy client accessors for optional Base client integrations."""

from __future__ import annotations


def get_asr_client():
    """Load the ASR client only when it is actually requested."""
    from Base.Client.asrClient import asr_client

    return asr_client


def get_minio_client(is_async: bool = False):
    """Load the MinIO client lazily so unrelated imports do not require minio."""
    from Base.Client.minioClient import async_minio_client, default_minio_client

    return async_minio_client if is_async else default_minio_client


def get_redis_client():
    """Load the Redis client only when Redis-backed features need it."""
    from Base.Client.redisClient import redis_client

    return redis_client


__all__ = ["get_asr_client", "get_minio_client", "get_redis_client"]

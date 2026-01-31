"""
RQ queue helpers.
"""

import redis
from rq import Queue

from src.config.settings import settings


def get_redis_connection() -> redis.Redis:
    return redis.from_url(settings.redis_url)


def get_queue(name: str | None = None) -> Queue:
    return Queue(name or settings.rq_queue_name, connection=get_redis_connection())

import redis.asyncio as redis

from core.config import env

REDIS_URL = env.redis_url

redis_client = redis.from_url(
    REDIS_URL,
    encoding="utf-8",
    decode_responses=False,
    max_connections=100,
    socket_timeout=5,
    socket_connect_timeout=5,
    health_check_interval=30,
    retry_on_timeout=True,
)

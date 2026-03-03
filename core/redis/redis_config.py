import redis.asyncio as redis

from core.config import env

REDIS_URL = env.redis_url

redis_client = redis.from_url(
    REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)

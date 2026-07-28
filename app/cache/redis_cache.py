import hashlib
import json
import os
from typing import Any

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

def get_redis_client() -> redis.Redis:

    return redis.from_url(
        REDIS_URL, 
        decode_responses=True,
    )

def create_cache_key(prefix: str, payload: Any) -> str:

    serialized_payload = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    hash_to_digest = hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()

    return f"{prefix}:{hash_to_digest}"

def get_json_cache(key: str) -> Any | None:
    client = get_redis_client()
    cached = client.get(key)

    if cached is None:
        return None

    return json.loads(cached)

def set_json_cache(key: str, value: Any, ttl: int = 300) -> None:
    client = get_redis_client()
    client.set(
        key,
        json.dumps(value, ensure_ascii=False, default=str),
        ex=ttl
    )

def delete_cache_key(key: str) -> None:
    client = get_redis_client()
    client.delete(key)
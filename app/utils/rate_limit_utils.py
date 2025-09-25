# app/utils/rate_limit_utils.py

import time
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

attempt_cache = {}

def is_rate_limited(key: str, limit: int, period_seconds: int) -> bool:
    """
    Check if the key exceeded the limit in the last period_seconds.
    """
    now = time.time()
    attempts = attempt_cache.get(key, [])

    attempts = [ts for ts in attempts if now - ts < period_seconds]
    attempt_cache[key] = attempts

    if len(attempts) >= limit:
        logger.warning(f"Rate limit exceeded for key {key}")
        return True
    return False

def add_attempt(key: str):
    """
    Add a new attempt timestamp for the key.
    """
    now = time.time()
    attempts = attempt_cache.get(key, [])
    attempts.append(now)
    attempt_cache[key] = attempts

def rate_limit(key: str, limit: int, period_seconds: int):
    """
    Enforce rate limiting for a key.
    Raise HTTPException if rate limited.
    """
    if is_rate_limited(key, limit, period_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please try again later."
        )
    add_attempt(key)

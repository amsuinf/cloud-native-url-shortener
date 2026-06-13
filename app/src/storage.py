"""Storage layer backed by Redis.

Kept behind a small interface so the service code never talks to Redis
directly. That makes the handlers trivial to unit-test against a fake and
leaves room to swap in DynamoDB/Postgres later without touching the API.
"""
from __future__ import annotations

import secrets
import string
from typing import Protocol

import redis

_ALPHABET = string.ascii_letters + string.digits


class Store(Protocol):
    """Minimal contract the API depends on."""

    def save(self, code: str, url: str, ttl_seconds: int = 0) -> None: ...

    def lookup(self, code: str) -> str | None: ...

    def exists(self, code: str) -> bool: ...

    def ping(self) -> bool: ...


class RedisStore:
    """Production store. One Redis key per short code -> long URL."""

    def __init__(self, url: str) -> None:
        # decode_responses gives us str in/str out instead of bytes.
        self._client = redis.Redis.from_url(url, decode_responses=True)

    def save(self, code: str, url: str, ttl_seconds: int = 0) -> None:
        if ttl_seconds > 0:
            self._client.set(self._key(code), url, ex=ttl_seconds)
        else:
            self._client.set(self._key(code), url)

    def lookup(self, code: str) -> str | None:
        return self._client.get(self._key(code))

    def exists(self, code: str) -> bool:
        return bool(self._client.exists(self._key(code)))

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except redis.RedisError:
            return False

    @staticmethod
    def _key(code: str) -> str:
        return f"url:{code}"


def generate_code(length: int) -> str:
    """Cryptographically-random short code.

    secrets (not random) so codes are not guessable/enumerable, which would
    otherwise leak how many links exist and enable scraping.
    """
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))

"""Runtime configuration loaded from environment variables.

Twelve-factor style: every tunable is an env var with a sane default so the
same image runs unchanged in local Docker, CI, and Kubernetes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Base host used when returning the fully-qualified short URL to clients.
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")
    # Length of the generated short code.
    code_length: int = int(os.getenv("CODE_LENGTH", "7"))
    # Optional TTL (seconds) for links; 0 means links never expire.
    link_ttl_seconds: int = int(os.getenv("LINK_TTL_SECONDS", "0"))
    environment: str = os.getenv("ENVIRONMENT", "local")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()

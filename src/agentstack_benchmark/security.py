from __future__ import annotations

import hmac
import math
import threading
import time
from dataclasses import dataclass
from typing import Any

SECURITY_SCHEMA_VERSION = "agentstack-benchmark.security.v0.1"


@dataclass(frozen=True)
class SecurityConfig:
    auth_token: str | None = None
    rate_limit_requests: int | None = None
    rate_limit_window_seconds: int = 60

    @classmethod
    def disabled(cls) -> "SecurityConfig":
        return cls(auth_token=None, rate_limit_requests=None, rate_limit_window_seconds=60)

    @classmethod
    def from_token(
        cls,
        token: str | None,
        *,
        rate_limit_requests: int | None = None,
        rate_limit_window_seconds: int = 60,
    ) -> "SecurityConfig":
        cleaned_token = token.strip() if isinstance(token, str) and token.strip() else None
        cleaned_requests = (
            rate_limit_requests if rate_limit_requests and rate_limit_requests > 0 else None
        )
        if rate_limit_window_seconds <= 0:
            raise ValueError("rate_limit_window_seconds must be positive")
        return cls(
            auth_token=cleaned_token,
            rate_limit_requests=cleaned_requests,
            rate_limit_window_seconds=rate_limit_window_seconds,
        )

    @property
    def auth_enabled(self) -> bool:
        return self.auth_token is not None

    @property
    def rate_limit_enabled(self) -> bool:
        return self.rate_limit_requests is not None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": SECURITY_SCHEMA_VERSION,
            "auth": {
                "enabled": self.auth_enabled,
                "mode": "bearer" if self.auth_enabled else "none",
                "tokenConfigured": self.auth_enabled,
            },
            "rateLimit": {
                "enabled": self.rate_limit_enabled,
                "requests": self.rate_limit_requests,
                "windowSeconds": self.rate_limit_window_seconds,
            },
        }

    def validate_authorization_header(self, header_value: str | None) -> tuple[bool, int, str, str]:
        if not self.auth_enabled:
            return True, 200, "", ""
        if not header_value or not header_value.startswith("Bearer "):
            return False, 401, "AUTH_REQUIRED", "Bearer token required"
        candidate = header_value.removeprefix("Bearer ").strip()
        assert self.auth_token is not None
        if not hmac.compare_digest(candidate, self.auth_token):
            return False, 403, "AUTH_INVALID", "Bearer token is invalid"
        return True, 200, "", ""


class InMemoryRateLimiter:
    def __init__(self, config: SecurityConfig) -> None:
        self._config = config
        self._clients: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, client_id: str, now: float | None = None) -> tuple[bool, int]:
        if not self._config.rate_limit_enabled:
            return True, 0
        assert self._config.rate_limit_requests is not None
        current = time.monotonic() if now is None else now
        window = float(self._config.rate_limit_window_seconds)
        with self._lock:
            window_start, count = self._clients.get(client_id, (current, 0))
            if current - window_start >= window:
                window_start, count = current, 0
            if count >= self._config.rate_limit_requests:
                retry_after = max(1, int(math.ceil(window - (current - window_start))))
                return False, retry_after
            self._clients[client_id] = (window_start, count + 1)
        return True, 0

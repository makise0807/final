"""Credential loading for future real OpenEO adapters.

This module only reads environment variables and validates configuration.
It never performs any network requests.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any


def _truthy(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}***{value[-2:]}"


@dataclass(slots=True)
class OpenEOCredentials:
    backend_url: str | None
    auth_mode: str = "none"
    username: str | None = None
    password: str | None = None
    token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    verify_ssl: bool = True
    allow_real_network: bool = False
    warnings: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.auth_mode == "basic":
            if not self.username or not self.password:
                errors.append("basic_auth_requires_username_password")
        elif self.auth_mode == "token":
            if not self.token:
                errors.append("token_auth_requires_token")
        elif self.auth_mode == "oidc":
            if not self.client_id:
                errors.append("oidc_requires_client_id")
        if not self.verify_ssl:
            self.warnings.append("insecure_verify_ssl_disabled")
        return list(dict.fromkeys(errors))

    def masked_summary(self) -> dict[str, Any]:
        return {
            "backend_url": self.backend_url,
            "auth_mode": self.auth_mode,
            "username": _mask_secret(self.username),
            "password": "***" if self.password else None,
            "token": _mask_secret(self.token),
            "client_id": _mask_secret(self.client_id),
            "client_secret": "***" if self.client_secret else None,
            "verify_ssl": self.verify_ssl,
            "allow_real_network": self.allow_real_network,
            "warnings": list(dict.fromkeys(self.warnings)),
            "validation_errors": self.validate(),
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __repr__(self) -> str:
        return f"OpenEOCredentials({self.masked_summary()!r})"


def load_openeo_credentials_from_env(env: dict[str, str] | None = None) -> OpenEOCredentials:
    env_map = env if env is not None else os.environ
    credentials = OpenEOCredentials(
        backend_url=env_map.get("OPENEO_BACKEND_URL"),
        auth_mode=env_map.get("OPENEO_AUTH_MODE", "none"),
        username=env_map.get("OPENEO_USERNAME"),
        password=env_map.get("OPENEO_PASSWORD"),
        token=env_map.get("OPENEO_TOKEN"),
        client_id=env_map.get("OPENEO_CLIENT_ID"),
        client_secret=env_map.get("OPENEO_CLIENT_SECRET"),
        verify_ssl=_truthy(env_map.get("OPENEO_VERIFY_SSL"), True),
        allow_real_network=_truthy(env_map.get("OPENEO_ALLOW_REAL_NETWORK"), False),
    )
    credentials.validate()
    return credentials

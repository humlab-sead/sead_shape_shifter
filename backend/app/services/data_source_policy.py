"""Policy helpers for server-managed data source configurations."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.core.config import Settings, get_settings
from src.loaders.driver_metadata import DriverSchema, DriverSchemaRegistry
from src.path_resolution import resolve_contained_path

_ENV_REF_PATTERN = re.compile(r"\$\{([^}]+)\}")
_APPROVED_HOST_ENV_VARS = ("SEAD_HOST",)
_APPROVED_PORT_ENV_VARS = ("SEAD_PORT",)
_DEFAULT_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class ValidatedDataSourceConfig:
    """Validated server-managed data source configuration."""

    config: Any
    schema: DriverSchema
    options: dict[str, Any]


def _split_csv_values(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _allowed_env_var_prefixes(settings: Settings) -> tuple[str, ...]:
    return tuple(prefix for prefix in _split_csv_values(settings.DATA_SOURCE_ALLOWED_ENV_VAR_PREFIXES))


def _collect_string_values(value: Any) -> list[str]:
    values: list[str] = []
    if value is None:
        return values
    if isinstance(value, str):
        values.append(value)
        return values
    if isinstance(value, dict):
        for item in value.values():
            values.extend(_collect_string_values(item))
        return values
    if isinstance(value, (list, tuple, set)):
        for item in value:
            values.extend(_collect_string_values(item))
        return values

    get_secret_value = getattr(value, "get_secret_value", None)
    if callable(get_secret_value):
        try:
            secret_value = get_secret_value()
        except Exception:  # pylint: disable=broad-except
            return values
        if isinstance(secret_value, str):
            values.append(secret_value)
    return values


def _raw_payload(config: Any) -> dict[str, Any]:
    payload = config.model_dump(exclude_none=True)
    password = getattr(config, "password", None)
    if password is not None:
        get_secret_value = getattr(password, "get_secret_value", None)
        if callable(get_secret_value):
            payload["password"] = get_secret_value()
    return payload


def _extract_env_var_names(config: Any) -> set[str]:
    env_var_names: set[str] = set()
    for raw_value in _collect_string_values(_raw_payload(config)):
        for match in _ENV_REF_PATTERN.finditer(raw_value):
            env_var_names.add(match.group(1))
    return env_var_names


def _is_path_field(field_name: str) -> bool:
    return field_name in {"filename", "filepath", "path"} or field_name.endswith(("_dir", "_path"))


def _get_field_value(config: Any, schema: DriverSchema, field_name: str) -> Any:
    value = getattr(config, field_name, None)
    if value not in (None, ""):
        return value

    options = config.options if getattr(config, "options", None) else {}
    if field_name in options and options[field_name] not in (None, ""):
        return options[field_name]

    field = next((item for item in schema.fields if item.name == field_name), None)
    if field and field.aliases:
        for alias in field.aliases:
            alias_value = options.get(alias)
            if alias_value not in (None, ""):
                return alias_value

    return value


def _canonical_options(config: Any, schema: DriverSchema) -> dict[str, Any]:
    options: dict[str, Any] = {}

    for field in schema.fields:
        value = None

        if field.type == "file_path" and getattr(config, "options", None):
            value = config.options.get(field.name)

        if value is None:
            value = getattr(config, field.name, None)

        if value is None and getattr(config, "options", None):
            value = config.options.get(field.name)

            if value is None and field.aliases:
                for alias in field.aliases:
                    value = config.options.get(alias)
                    if value is not None:
                        break

        if value is None or value == "":
            if field.default is not None:
                value = field.default
            elif field.required:
                raise ValueError(f"Required field missing: {field.name}")
            else:
                continue

        options[field.name] = value

    if getattr(config, "options", None):
        for key, value in config.options.items():
            if key not in options and value is not None:
                options[key] = value

    return options


def _is_allowed_host(host: str) -> bool:
    if host in _DEFAULT_ALLOWED_HOSTS:
        return True

    approved_host_values = {os.getenv(name) for name in _APPROVED_HOST_ENV_VARS if os.getenv(name)}
    if host in approved_host_values:
        return True

    try:
        ip_address = ipaddress.ip_address(host)
    except ValueError:
        try:
            resolved_addresses = {
                candidate[4][0] for candidate in socket.getaddrinfo(host, None) if candidate and candidate[4] and candidate[4][0]
            }
        except socket.gaierror:
            return False

        if not resolved_addresses:
            return False

        return all(_is_allowed_host(resolved_address) for resolved_address in resolved_addresses)

    return ip_address.is_loopback or ip_address.is_private


def _approved_ports() -> set[int]:
    ports = {5432}
    for name in _APPROVED_PORT_ENV_VARS:
        value = os.getenv(name)
        if value and value.isdigit():
            ports.add(int(value))
    return ports


def validate_server_managed_data_source(config: Any, settings: Settings | None = None) -> ValidatedDataSourceConfig:
    """Validate a data source for server-managed execution."""

    settings = settings or get_settings()
    env_var_prefixes = _allowed_env_var_prefixes(settings)
    raw_env_var_names = _extract_env_var_names(config)

    disallowed_env_vars = sorted(name for name in raw_env_var_names if not any(name.startswith(prefix) for prefix in env_var_prefixes))
    if disallowed_env_vars:
        raise ValueError(f"Data source references unapproved environment variables: {', '.join(disallowed_env_vars)}")

    resolved_config = config.resolve_config_env_vars()
    if getattr(resolved_config, "connection_string", None):
        raise ValueError("Custom connection strings are not allowed for server-managed data sources")

    schema = DriverSchemaRegistry.get(resolved_config.driver)
    if not schema:
        raise ValueError(f"Unknown driver: {resolved_config.driver}")

    if schema.category == "internal":
        raise ValueError("Internal data sources are not allowed in server-managed data-source policy")

    options = _canonical_options(resolved_config, schema)

    for field in schema.fields:
        value = _get_field_value(resolved_config, schema, field.name)
        if value in (None, ""):
            continue

        if _is_path_field(field.name) or field.type == "file_path":
            resolve_contained_path(str(value), settings.application_root, allow_absolute=True)

    host = _get_field_value(resolved_config, schema, "host")
    if host not in (None, "") and not _is_allowed_host(str(host)):
        raise ValueError(f"Data source host '{host}' is not in an approved destination")

    port = _get_field_value(resolved_config, schema, "port")
    if port not in (None, ""):
        try:
            port_value = int(port)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Data source port '{port}' is not valid") from exc
        if port_value not in _approved_ports():
            raise ValueError(f"Data source port '{port_value}' is not in an approved destination")

    return ValidatedDataSourceConfig(config=resolved_config, schema=schema, options=options)

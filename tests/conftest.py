"""Shared fixtures for simple_log_factory_ext_otel tests."""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk._logs.export import LogExportResult

from simple_log_factory_ext_otel import OtelLogHandler


class InMemoryLogExporter:
    """A minimal in-memory exporter for testing.

    Collects exported log records so tests can assert on them without
    requiring a live OTel backend.
    """

    def __init__(self) -> None:
        self.records: list[Any] = []
        self._shutdown = False

    def export(self, batch: Any) -> LogExportResult:
        if self._shutdown:
            return LogExportResult.FAILURE
        self.records.extend(batch)
        return LogExportResult.SUCCESS

    def shutdown(self) -> None:
        self._shutdown = True

    def force_flush(self, timeout_millis: int = 0) -> bool:
        return True


@pytest.fixture()
def grpc_handler() -> Generator[OtelLogHandler, None, None]:
    """Create an OtelLogHandler with gRPC protocol using a mocked exporter."""
    with patch(
        "simple_log_factory_ext_otel.handler.GrpcLogExporter",
        return_value=MagicMock(),
    ):
        handler = OtelLogHandler(service_name="test-grpc", protocol="grpc")
        yield handler
        handler.shutdown()


@pytest.fixture()
def http_handler() -> Generator[OtelLogHandler, None, None]:
    """Create an OtelLogHandler with HTTP protocol using a mocked exporter."""
    with patch(
        "simple_log_factory_ext_otel.handler.HttpLogExporter",
        return_value=MagicMock(),
    ):
        handler = OtelLogHandler(service_name="test-http", protocol="http")
        yield handler
        handler.shutdown()


@pytest.fixture()
def mock_record() -> logging.LogRecord:
    """Create a basic LogRecord for testing."""
    return logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=None,
        exc_info=None,
    )


@pytest.fixture()
def handler_kwargs() -> dict[str, Any]:
    """Default keyword arguments for OtelLogHandler construction."""
    return {
        "service_name": "test-service",
        "endpoint": "http://localhost:4317",
        "protocol": "grpc",
    }

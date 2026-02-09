"""Unit tests for OtelLogHandler."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.resources import Resource

from simple_log_factory_ext_otel import OtelLogHandler

# ------------------------------------------------------------------
# Initialization
# ------------------------------------------------------------------


class TestHandlerInit:
    """Tests for OtelLogHandler construction."""

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter")
    def test_init_grpc_creates_grpc_exporter(self, mock_grpc_cls: MagicMock) -> None:
        handler = OtelLogHandler(service_name="svc", protocol="grpc")
        mock_grpc_cls.assert_called_once()
        assert isinstance(handler.provider, LoggerProvider)
        handler.shutdown()

    @patch("simple_log_factory_ext_otel.handler.HttpLogExporter")
    def test_init_http_creates_http_exporter(self, mock_http_cls: MagicMock) -> None:
        handler = OtelLogHandler(service_name="svc", protocol="http")
        mock_http_cls.assert_called_once()
        assert isinstance(handler.provider, LoggerProvider)
        handler.shutdown()

    def test_invalid_protocol_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid protocol 'websocket'"):
            OtelLogHandler(service_name="svc", protocol="websocket")

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter")
    def test_custom_resource_attributes(self, _mock: MagicMock) -> None:
        handler = OtelLogHandler(
            service_name="svc",
            resource_attributes={"deployment.environment": "staging", "team": "platform"},
        )
        resource_attrs = dict(handler.provider.resource.attributes)
        assert resource_attrs["service.name"] == "svc"
        assert resource_attrs["deployment.environment"] == "staging"
        assert resource_attrs["team"] == "platform"
        handler.shutdown()

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter")
    def test_default_resource_has_service_name(self, _mock: MagicMock) -> None:
        handler = OtelLogHandler(service_name="my-app")
        resource_attrs = dict(handler.provider.resource.attributes)
        assert resource_attrs["service.name"] == "my-app"
        handler.shutdown()

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter")
    def test_log_level_sets_handler_level(self, _mock: MagicMock) -> None:
        handler = OtelLogHandler(service_name="svc", log_level=logging.WARNING)
        assert handler.level == logging.WARNING
        handler.shutdown()

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter")
    def test_grpc_exporter_receives_correct_kwargs(self, mock_grpc_cls: MagicMock) -> None:
        OtelLogHandler(
            service_name="svc",
            endpoint="http://otel:4317",
            protocol="grpc",
            insecure=False,
            headers={"x-api-key": "secret"},
            export_timeout_millis=5000,
        ).shutdown()

        mock_grpc_cls.assert_called_once_with(
            endpoint="http://otel:4317",
            insecure=False,
            headers={"x-api-key": "secret"},
            timeout=5000,
        )

    @patch("simple_log_factory_ext_otel.handler.HttpLogExporter")
    def test_http_exporter_receives_correct_kwargs(self, mock_http_cls: MagicMock) -> None:
        OtelLogHandler(
            service_name="svc",
            endpoint="http://otel:4318/v1/logs",
            protocol="http",
            headers={"Authorization": "Bearer tok"},
            export_timeout_millis=10000,
        ).shutdown()

        mock_http_cls.assert_called_once_with(
            endpoint="http://otel:4318/v1/logs",
            headers={"Authorization": "Bearer tok"},
            timeout=10000,
        )

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter")
    def test_pre_built_resource_is_used(self, _mock: MagicMock) -> None:
        resource = Resource.create({"service.name": "shared-svc", "custom.attr": "value"})
        handler = OtelLogHandler(service_name="ignored", resource=resource)
        assert handler.provider.resource is resource
        handler.shutdown()

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter")
    def test_resource_none_falls_back_to_create_resource(self, _mock: MagicMock) -> None:
        handler = OtelLogHandler(service_name="fallback-svc", resource=None)
        assert handler.provider.resource.attributes["service.name"] == "fallback-svc"
        handler.shutdown()


# ------------------------------------------------------------------
# emit()
# ------------------------------------------------------------------


class TestEmit:
    """Tests for the emit() method."""

    def test_emit_delegates_to_otel_handler(
        self,
        grpc_handler: OtelLogHandler,
        mock_record: logging.LogRecord,
    ) -> None:
        grpc_handler._otel_handler = MagicMock()
        grpc_handler.emit(mock_record)
        grpc_handler._otel_handler.emit.assert_called_once_with(mock_record)

    def test_emit_never_raises_on_internal_error(
        self,
        grpc_handler: OtelLogHandler,
        mock_record: logging.LogRecord,
    ) -> None:
        grpc_handler._otel_handler = MagicMock()
        grpc_handler._otel_handler.emit.side_effect = RuntimeError("boom")

        # Must not raise
        grpc_handler.emit(mock_record)

    def test_emit_calls_handle_error_on_failure(
        self,
        grpc_handler: OtelLogHandler,
        mock_record: logging.LogRecord,
    ) -> None:
        grpc_handler._otel_handler = MagicMock()
        grpc_handler._otel_handler.emit.side_effect = RuntimeError("boom")
        grpc_handler.handleError = MagicMock()  # type: ignore[assignment]

        grpc_handler.emit(mock_record)
        grpc_handler.handleError.assert_called_once_with(mock_record)


# ------------------------------------------------------------------
# flush()
# ------------------------------------------------------------------


class TestFlush:
    """Tests for the flush() method."""

    def test_flush_delegates_to_provider(self, grpc_handler: OtelLogHandler) -> None:
        grpc_handler._provider = MagicMock(spec=LoggerProvider)
        grpc_handler.flush()
        grpc_handler._provider.force_flush.assert_called_once()

    def test_flush_skips_after_shutdown(self, grpc_handler: OtelLogHandler) -> None:
        grpc_handler._provider = MagicMock(spec=LoggerProvider)
        grpc_handler.shutdown()
        grpc_handler.flush()
        grpc_handler._provider.force_flush.assert_not_called()


# ------------------------------------------------------------------
# shutdown() & close()
# ------------------------------------------------------------------


class TestShutdown:
    """Tests for shutdown() and close() lifecycle methods."""

    def test_shutdown_calls_provider_shutdown(self, grpc_handler: OtelLogHandler) -> None:
        grpc_handler._provider = MagicMock(spec=LoggerProvider)
        grpc_handler._shutdown_called = False
        grpc_handler.shutdown()
        grpc_handler._provider.shutdown.assert_called_once()

    def test_shutdown_is_idempotent(self, grpc_handler: OtelLogHandler) -> None:
        grpc_handler._provider = MagicMock(spec=LoggerProvider)
        grpc_handler._shutdown_called = False

        grpc_handler.shutdown()
        grpc_handler.shutdown()
        grpc_handler.shutdown()

        # Provider.shutdown should only be called once
        grpc_handler._provider.shutdown.assert_called_once()

    def test_close_triggers_shutdown(self, grpc_handler: OtelLogHandler) -> None:
        grpc_handler._provider = MagicMock(spec=LoggerProvider)
        grpc_handler._shutdown_called = False

        grpc_handler.close()
        grpc_handler._provider.shutdown.assert_called_once()


# ------------------------------------------------------------------
# Formatter / Level isolation
# ------------------------------------------------------------------


class TestFormatterIsolation:
    """Verify that setFormatter/setLevel on the outer handler does not
    affect the inner OTel handler."""

    def test_set_formatter_does_not_affect_otel_handler(
        self,
        grpc_handler: OtelLogHandler,
    ) -> None:
        original_otel_formatter = grpc_handler._otel_handler.formatter
        grpc_handler.setFormatter(logging.Formatter("%(message)s"))

        # The outer handler's formatter changed, but the inner one is untouched
        assert grpc_handler._otel_handler.formatter is original_otel_formatter

    def test_set_level_does_not_affect_otel_handler(
        self,
        grpc_handler: OtelLogHandler,
    ) -> None:
        original_otel_level = grpc_handler._otel_handler.level
        grpc_handler.setLevel(logging.CRITICAL)

        assert grpc_handler.level == logging.CRITICAL
        assert grpc_handler._otel_handler.level == original_otel_level

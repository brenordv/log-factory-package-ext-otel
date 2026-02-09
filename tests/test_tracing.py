"""Unit tests for OtelTracer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Tracer, TracerProvider

from simple_log_factory_ext_otel.tracing import OtelTracer

# ------------------------------------------------------------------
# Initialization
# ------------------------------------------------------------------


class TestOtelTracerInit:
    """Tests for OtelTracer construction."""

    @patch("simple_log_factory_ext_otel.tracing.GrpcSpanExporter")
    def test_init_grpc_creates_grpc_exporter(self, mock_grpc_cls: MagicMock) -> None:
        tracer = OtelTracer(service_name="svc", protocol="grpc")
        mock_grpc_cls.assert_called_once()
        assert isinstance(tracer.provider, TracerProvider)
        tracer.shutdown()

    @patch("simple_log_factory_ext_otel.tracing.HttpSpanExporter")
    def test_init_http_creates_http_exporter(self, mock_http_cls: MagicMock) -> None:
        tracer = OtelTracer(service_name="svc", protocol="http")
        mock_http_cls.assert_called_once()
        assert isinstance(tracer.provider, TracerProvider)
        tracer.shutdown()

    def test_invalid_protocol_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid protocol 'websocket'"):
            OtelTracer(service_name="svc", protocol="websocket")

    @patch("simple_log_factory_ext_otel.tracing.GrpcSpanExporter")
    def test_custom_resource_attributes(self, _mock: MagicMock) -> None:
        tracer = OtelTracer(
            service_name="svc",
            resource_attributes={"deployment.environment": "staging"},
        )
        attrs = dict(tracer.provider.resource.attributes)
        assert attrs["service.name"] == "svc"
        assert attrs["deployment.environment"] == "staging"
        tracer.shutdown()

    @patch("simple_log_factory_ext_otel.tracing.GrpcSpanExporter")
    def test_pre_built_resource_is_used(self, _mock: MagicMock) -> None:
        resource = Resource.create({"service.name": "shared"})
        tracer = OtelTracer(service_name="ignored", resource=resource)
        assert tracer.provider.resource is resource
        tracer.shutdown()

    @patch("simple_log_factory_ext_otel.tracing.GrpcSpanExporter")
    def test_grpc_exporter_receives_correct_kwargs(self, mock_grpc_cls: MagicMock) -> None:
        OtelTracer(
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

    @patch("simple_log_factory_ext_otel.tracing.HttpSpanExporter")
    def test_http_exporter_receives_correct_kwargs(self, mock_http_cls: MagicMock) -> None:
        OtelTracer(
            service_name="svc",
            endpoint="http://otel:4318/v1/traces",
            protocol="http",
            headers={"Authorization": "Bearer tok"},
            export_timeout_millis=10000,
        ).shutdown()

        mock_http_cls.assert_called_once_with(
            endpoint="http://otel:4318/v1/traces",
            headers={"Authorization": "Bearer tok"},
            timeout=10000,
        )


# ------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------


class TestOtelTracerProperties:
    """Tests for tracer and provider properties."""

    def test_tracer_returns_tracer_instance(self, grpc_tracer: OtelTracer) -> None:
        assert isinstance(grpc_tracer.tracer, Tracer)

    def test_provider_returns_tracer_provider(self, grpc_tracer: OtelTracer) -> None:
        assert isinstance(grpc_tracer.provider, TracerProvider)


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------


class TestOtelTracerLifecycle:
    """Tests for flush, shutdown, and close."""

    def test_flush_delegates_to_provider(self, grpc_tracer: OtelTracer) -> None:
        grpc_tracer._provider = MagicMock(spec=TracerProvider)
        grpc_tracer.flush()
        grpc_tracer._provider.force_flush.assert_called_once()

    def test_flush_skips_after_shutdown(self, grpc_tracer: OtelTracer) -> None:
        grpc_tracer._provider = MagicMock(spec=TracerProvider)
        grpc_tracer.shutdown()
        grpc_tracer.flush()
        grpc_tracer._provider.force_flush.assert_not_called()

    def test_shutdown_is_idempotent(self, grpc_tracer: OtelTracer) -> None:
        grpc_tracer._provider = MagicMock(spec=TracerProvider)
        grpc_tracer._shutdown_called = False

        grpc_tracer.shutdown()
        grpc_tracer.shutdown()
        grpc_tracer.shutdown()

        grpc_tracer._provider.shutdown.assert_called_once()

    def test_close_triggers_shutdown(self, grpc_tracer: OtelTracer) -> None:
        grpc_tracer._provider = MagicMock(spec=TracerProvider)
        grpc_tracer._shutdown_called = False

        grpc_tracer.close()
        grpc_tracer._provider.shutdown.assert_called_once()

"""OpenTelemetry log and tracing plugin for simple_log_factory."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource

from simple_log_factory_ext_otel._resource import create_resource
from simple_log_factory_ext_otel.handler import OtelLogHandler
from simple_log_factory_ext_otel.traced_logger import TracedLogger
from simple_log_factory_ext_otel.tracing import OtelTracer

__all__ = [
    "OtelLogHandler",
    "OtelTracer",
    "TracedLogger",
    "create_resource",
    "setup_otel",
]
__version__ = "1.1.0"


def setup_otel(
    service_name: str,
    endpoint: str = "http://localhost:4317",
    protocol: str = "grpc",
    insecure: bool = True,
    headers: dict[str, str] | None = None,
    resource_attributes: dict[str, str] | None = None,
    export_timeout_millis: int = 30_000,
    log_level: int = 0,
) -> tuple[OtelLogHandler, OtelTracer]:
    """One-call setup for both OTel logging and tracing pipelines.

    Creates a shared ``Resource``, wires up an ``OtelLogHandler`` and an
    ``OtelTracer``, and registers the ``TracerProvider`` globally so that
    auto-instrumentation libraries share the same provider.

    Args:
        service_name: Logical name of the service.
        endpoint: OTLP receiver endpoint.
        protocol: Transport protocol — ``"grpc"`` or ``"http"``.
        insecure: Whether to use an insecure (plaintext) connection.
        headers: Optional metadata headers sent with every export request.
        resource_attributes: Extra OTel Resource attributes.
        export_timeout_millis: Timeout in milliseconds for each export batch.
        log_level: Minimum severity forwarded to the OTel log pipeline.

    Returns:
        A ``(handler, tracer)`` tuple.
    """
    resource: Resource = create_resource(service_name, resource_attributes)

    handler = OtelLogHandler(
        service_name=service_name,
        endpoint=endpoint,
        protocol=protocol,
        insecure=insecure,
        headers=headers,
        export_timeout_millis=export_timeout_millis,
        log_level=log_level,
        resource=resource,
    )

    otel_tracer = OtelTracer(
        service_name=service_name,
        endpoint=endpoint,
        protocol=protocol,
        insecure=insecure,
        headers=headers,
        export_timeout_millis=export_timeout_millis,
        resource=resource,
    )

    trace.set_tracer_provider(otel_tracer.provider)

    return handler, otel_tracer

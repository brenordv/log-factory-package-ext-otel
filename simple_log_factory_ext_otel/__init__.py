"""OpenTelemetry log and tracing plugin for simple_log_factory."""

from __future__ import annotations

from typing import Any

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
    "otel_log_factory",
    "setup_otel",
]
__version__ = "1.3.0"

_otel_logger_map: dict[str, TracedLogger] = {}


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


def otel_log_factory(
    service_name: str,
    otel_exporter_endpoint: str,
    log_name: str | None = None,
    cache_logger: bool = True,
    use_http_protocol: bool = True,
    **kwargs: Any,
) -> TracedLogger:
    """All-in-one factory that creates a ``TracedLogger`` wired to an OTel backend.

    Combines ``setup_otel``-style OTel wiring with ``simple_log_factory.log_factory``
    logger creation in a single call.  The returned ``TracedLogger`` is ready to
    use for both logging and tracing.

    When *cache_logger* is ``True`` (the default), loggers are cached by a
    composite key of ``(otel_exporter_endpoint, service_name, log_name)``.  This
    allows multiple independent loggers for different services or endpoints
    while still reusing the same instance when the same combination is
    requested again.

    Args:
        service_name: Logical name of the service emitting logs and traces.
        otel_exporter_endpoint: Base URL of the OpenTelemetry collector endpoint
            (e.g. ``"http://localhost:4318"``).  Path suffixes are appended
            automatically when using HTTP protocol.
        log_name: Name passed to ``log_factory``.  Defaults to
            *service_name* when ``None``.
        cache_logger: If ``True``, cache and reuse the logger for the same
            endpoint/service/log-name combination.
        use_http_protocol: If ``True`` use HTTP transport (appends
            ``/v1/logs`` and ``/v1/traces``); if ``False`` use gRPC
            (endpoint is used as-is).
        **kwargs: Extra keyword arguments forwarded to
            ``simple_log_factory.log_factory``.

    Returns:
        A ``TracedLogger`` with both logging and tracing configured.

    Raises:
        ValueError: If *service_name* or *otel_exporter_endpoint* is empty or
            whitespace-only.
    """
    from simple_log_factory import log_factory

    if not otel_exporter_endpoint or otel_exporter_endpoint.isspace():
        raise ValueError("otel_exporter_endpoint must be set.")

    if service_name is None or service_name.isspace():
        raise ValueError("service_name must be set.")

    if log_name is None:
        log_name = service_name

    cache_key = f"{otel_exporter_endpoint}:{service_name}:{log_name}"

    if cache_logger and cache_key in _otel_logger_map:
        return _otel_logger_map[cache_key]

    resource = create_resource(service_name)

    if use_http_protocol:
        protocol = "http"
        base = otel_exporter_endpoint.rstrip("/")
        log_handler_url = f"{base}/v1/logs"
        tracer_handler_url = f"{base}/v1/traces"
    else:
        protocol = "grpc"
        log_handler_url = otel_exporter_endpoint
        tracer_handler_url = otel_exporter_endpoint

    log_handler = OtelLogHandler(
        service_name=service_name,
        endpoint=log_handler_url,
        protocol=protocol,
        resource=resource,
    )

    otel_tracer = OtelTracer(
        service_name=service_name,
        endpoint=tracer_handler_url,
        protocol=protocol,
        resource=resource,
    )

    trace.set_tracer_provider(otel_tracer.provider)

    existing_handlers = kwargs.get("custom_handlers")
    if existing_handlers is not None:
        kwargs["custom_handlers"] = [*existing_handlers, log_handler]
    else:
        kwargs["custom_handlers"] = [log_handler]

    logger = log_factory(log_name=log_name, **kwargs)

    otel_logger = TracedLogger(logger=logger, tracer=otel_tracer.tracer)

    if cache_logger:
        _otel_logger_map[cache_key] = otel_logger

    return otel_logger

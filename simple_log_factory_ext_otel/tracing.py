"""OpenTelemetry tracing support for simple_log_factory.

Provides ``OtelTracer``, a thin wrapper around the OTel ``TracerProvider``
that mirrors the structure of ``OtelLogHandler``.
"""

from __future__ import annotations

import atexit

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GrpcSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HttpSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Tracer, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from simple_log_factory_ext_otel._constants import (
    DEFAULT_ENDPOINT,
    DEFAULT_EXPORT_TIMEOUT_MILLIS,
    DEFAULT_PROTOCOL,
    VALID_PROTOCOLS,
)
from simple_log_factory_ext_otel._resource import create_resource


class OtelTracer:
    """Manages an OTel ``TracerProvider`` with OTLP span export.

    Mirrors ``OtelLogHandler`` in structure and constructor parameters so
    that both pipelines can be configured consistently.

    Args:
        service_name: Logical name of the service emitting spans.
        endpoint: OTLP receiver endpoint.
        protocol: Transport protocol — ``"grpc"`` or ``"http"``.
        insecure: Whether to use an insecure (plaintext) connection.
        headers: Optional metadata headers sent with every export request.
        resource_attributes: Extra key/value pairs merged into the OTel
            ``Resource`` alongside ``service.name``.  Ignored when
            *resource* is provided.
        export_timeout_millis: Timeout in milliseconds for each export batch.
        resource: Pre-built ``Resource`` instance.  When provided,
            *service_name* and *resource_attributes* are not used for
            resource creation.

    Raises:
        ValueError: If *protocol* is not ``"grpc"`` or ``"http"``.
    """

    def __init__(
        self,
        service_name: str,
        endpoint: str = DEFAULT_ENDPOINT,
        protocol: str = DEFAULT_PROTOCOL,
        insecure: bool = True,
        headers: dict[str, str] | None = None,
        resource_attributes: dict[str, str] | None = None,
        export_timeout_millis: int = DEFAULT_EXPORT_TIMEOUT_MILLIS,
        resource: Resource | None = None,
    ) -> None:
        if protocol not in VALID_PROTOCOLS:
            raise ValueError(f"Invalid protocol {protocol!r}. Must be one of {sorted(VALID_PROTOCOLS)}.")

        # --- Resource --------------------------------------------------
        if resource is None:
            resource = create_resource(service_name, resource_attributes)

        # --- Exporter --------------------------------------------------
        exporter = self._create_exporter(
            protocol=protocol,
            endpoint=endpoint,
            insecure=insecure,
            headers=headers,
            timeout=export_timeout_millis,
        )

        # --- Processor & Provider -------------------------------------
        self._processor = BatchSpanProcessor(exporter)
        self._provider = TracerProvider(resource=resource)
        self._provider.add_span_processor(self._processor)

        self._shutdown_called = False
        atexit.register(self.shutdown)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def tracer(self) -> Tracer:
        """Return a ``Tracer`` from the managed provider."""
        return self._provider.get_tracer(__name__)  # type: ignore[return-value]

    @property
    def provider(self) -> TracerProvider:
        """Expose the underlying ``TracerProvider`` for advanced use cases."""
        return self._provider

    def flush(self) -> None:
        """Force-flush any buffered spans."""
        if not self._shutdown_called:
            self._provider.force_flush()

    def shutdown(self) -> None:
        """Gracefully shut down the OTel tracing pipeline.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._shutdown_called:
            return
        self._shutdown_called = True
        self._provider.shutdown()

    def close(self) -> None:
        """Alias for :meth:`shutdown`."""
        self.shutdown()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_exporter(
        protocol: str,
        endpoint: str,
        insecure: bool,
        headers: dict[str, str] | None,
        timeout: int,
    ) -> GrpcSpanExporter | HttpSpanExporter:
        """Instantiate the appropriate OTLP span exporter."""
        if protocol == "grpc":
            return GrpcSpanExporter(
                endpoint=endpoint,
                insecure=insecure,
                headers=headers or {},
                timeout=timeout,
            )
        # protocol == "http"
        return HttpSpanExporter(
            endpoint=endpoint,
            headers=headers or {},
            timeout=timeout,
        )

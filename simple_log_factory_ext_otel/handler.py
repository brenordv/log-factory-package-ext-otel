"""OpenTelemetry log handler for simple_log_factory.

Provides ``OtelLogHandler``, a standard ``logging.Handler`` that ships log
records to an OpenTelemetry-compatible backend via gRPC or HTTP.  Designed
as a drop-in plugin for ``simple_log_factory``'s ``custom_handlers``
parameter.
"""

from __future__ import annotations

import atexit
import logging

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter as GrpcLogExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter as HttpLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from simple_log_factory_ext_otel._constants import (
    DEFAULT_ENDPOINT,
    DEFAULT_EXPORT_TIMEOUT_MILLIS,
    DEFAULT_PROTOCOL,
    VALID_PROTOCOLS,
)


class OtelLogHandler(logging.Handler):
    """A logging handler that ships log records to an OpenTelemetry backend.

    Designed as a drop-in plugin for ``simple_log_factory``'s
    ``custom_handlers`` parameter.  Internally manages the OTel
    ``LoggerProvider``, exporter, and processor lifecycle.

    The handler uses **composition** rather than inheriting from the OTel SDK's
    ``LoggingHandler``.  This is critical because ``log_factory`` calls
    ``handler.setFormatter()`` and ``handler.setLevel()`` on every handler it
    receives — if we inherited from ``LoggingHandler``, the factory's formatter
    would overwrite OTel's internal translation.  By wrapping it, both
    pipelines stay independent.

    Args:
        service_name: Logical name of the service emitting logs.
        endpoint: OTLP receiver endpoint.
        protocol: Transport protocol — ``"grpc"`` or ``"http"``.
        insecure: Whether to use an insecure (plaintext) connection.
        headers: Optional metadata headers sent with every export request.
        resource_attributes: Extra key/value pairs merged into the OTel
            ``Resource`` alongside ``service.name``.
        log_level: Minimum severity for records forwarded to the OTel
            pipeline.  Uses standard ``logging`` level constants.
        export_timeout_millis: Timeout in milliseconds for each export batch.

    Raises:
        ValueError: If *protocol* is not ``"grpc"`` or ``"http"``.

    Example::

        from simple_log_factory import log_factory
        from simple_log_factory_ext_otel import OtelLogHandler

        handler = OtelLogHandler(
            service_name="my-service",
            endpoint="http://localhost:4317",
        )
        logger = log_factory(__name__, custom_handlers=[handler])
        logger.info("Hello from OTel!")
        handler.shutdown()
    """

    def __init__(
        self,
        service_name: str,
        endpoint: str = DEFAULT_ENDPOINT,
        protocol: str = DEFAULT_PROTOCOL,
        insecure: bool = True,
        headers: dict[str, str] | None = None,
        resource_attributes: dict[str, str] | None = None,
        log_level: int = logging.NOTSET,
        export_timeout_millis: int = DEFAULT_EXPORT_TIMEOUT_MILLIS,
    ) -> None:
        super().__init__(level=log_level)

        if protocol not in VALID_PROTOCOLS:
            raise ValueError(f"Invalid protocol {protocol!r}. Must be one of {sorted(VALID_PROTOCOLS)}.")

        # --- Resource --------------------------------------------------
        attributes: dict[str, str] = {"service.name": service_name}
        if resource_attributes:
            attributes.update(resource_attributes)
        resource = Resource.create(attributes)

        # --- Exporter --------------------------------------------------
        exporter = self._create_exporter(
            protocol=protocol,
            endpoint=endpoint,
            insecure=insecure,
            headers=headers,
            timeout=export_timeout_millis,
        )

        # --- Processor & Provider -------------------------------------
        self._processor = BatchLogRecordProcessor(exporter)
        self._provider = LoggerProvider(resource=resource)
        self._provider.add_log_record_processor(self._processor)

        # --- Inner OTel handler (does LogRecord → OTel translation) ----
        self._otel_handler = LoggingHandler(logger_provider=self._provider)

        self._shutdown_called = False
        atexit.register(self.shutdown)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(self, record: logging.LogRecord) -> None:
        """Translate and forward *record* to the OTel pipeline.

        Exceptions are silently handled via ``handleError`` so the calling
        application is never disrupted by telemetry failures.
        """
        try:
            self._otel_handler.emit(record)
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        """Force-flush any buffered log records."""
        if not self._shutdown_called:
            self._provider.force_flush()
        super().flush()

    def shutdown(self) -> None:
        """Gracefully shut down the OTel pipeline.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._shutdown_called:
            return
        self._shutdown_called = True
        self._provider.shutdown()  # type: ignore[no-untyped-call]

    def close(self) -> None:
        """Called by the logging framework on handler removal."""
        self.shutdown()
        super().close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def provider(self) -> LoggerProvider:
        """Expose the underlying ``LoggerProvider`` for advanced use cases."""
        return self._provider

    @staticmethod
    def _create_exporter(
        protocol: str,
        endpoint: str,
        insecure: bool,
        headers: dict[str, str] | None,
        timeout: int,
    ) -> GrpcLogExporter | HttpLogExporter:
        """Instantiate the appropriate OTLP log exporter."""
        if protocol == "grpc":
            return GrpcLogExporter(
                endpoint=endpoint,
                insecure=insecure,
                headers=headers or {},
                timeout=timeout,
            )
        # protocol == "http"
        return HttpLogExporter(
            endpoint=endpoint,
            headers=headers or {},
            timeout=timeout,
        )

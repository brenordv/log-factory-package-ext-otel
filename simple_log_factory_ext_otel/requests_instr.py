"""Drop-in ``requests`` library instrumentation.

Activates OTel auto-instrumentation for the ``requests`` library so that
every outgoing HTTP call creates a ``CLIENT`` span with ``http.method``,
``http.url``, ``http.status_code``, etc.

Must be called **after** :func:`setup_otel` or :func:`otel_log_factory` so the
global ``TracerProvider`` is already registered.
"""

from __future__ import annotations

from typing import Any


def instrument_requests(*, excluded_urls: str | None = None) -> None:
    """Activate OTel auto-instrumentation for the ``requests`` library.

    Args:
        excluded_urls: Comma-delimited string of regex patterns for URLs
            that should **not** be traced (e.g. ``"health,ready"``).

    Raises:
        ImportError: If ``opentelemetry-instrumentation-requests`` is not
            installed.
    """
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
    except ImportError:
        raise ImportError(
            "To instrument requests, install the extra: " "pip install simple-log-factory-ext-otel[requests]"
        )

    instrumentor = RequestsInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        kwargs: dict[str, Any] = {}
        if excluded_urls is not None:
            kwargs["excluded_urls"] = excluded_urls
        instrumentor.instrument(**kwargs)


def uninstrument_requests() -> None:
    """Deactivate OTel auto-instrumentation for the ``requests`` library.

    Raises:
        ImportError: If ``opentelemetry-instrumentation-requests`` is not
            installed.
    """
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
    except ImportError:
        raise ImportError(
            "To uninstrument requests, install the extra: " "pip install simple-log-factory-ext-otel[requests]"
        )

    RequestsInstrumentor().uninstrument()

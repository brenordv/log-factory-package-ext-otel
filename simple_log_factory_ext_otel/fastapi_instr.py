"""Drop-in FastAPI instrumentation.

Activates OTel auto-instrumentation for FastAPI so that every incoming HTTP
request creates a ``SERVER`` span with ``http.method``, ``http.route``,
``http.status_code``, etc.

Must be called **after** :func:`setup_otel` or :func:`otel_log_factory` so the
global ``TracerProvider`` is already registered.
"""

from __future__ import annotations

from typing import Any


def instrument_fastapi(app: Any | None = None, *, excluded_urls: str | None = None) -> None:
    """Activate OTel auto-instrumentation for FastAPI.

    Two modes are supported:

    * **Global** (``app=None``): instruments all FastAPI applications via
      ``FastAPIInstrumentor().instrument()``.
    * **App-specific** (``app=<FastAPI instance>``): instruments only the
      given application via ``FastAPIInstrumentor.instrument_app(app)``.

    Args:
        app: Optional ``FastAPI`` application instance.  When ``None``,
            global instrumentation is applied.
        excluded_urls: Comma-delimited string of regex patterns for URLs
            that should **not** be traced (e.g. ``"health,ready"``).

    Raises:
        ImportError: If ``opentelemetry-instrumentation-fastapi`` is not
            installed.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        raise ImportError(
            "To instrument FastAPI, install the extra: " "pip install simple-log-factory-ext-otel[fastapi]"
        )

    if app is not None:
        kwargs: dict[str, Any] = {}
        if excluded_urls is not None:
            kwargs["excluded_urls"] = excluded_urls
        FastAPIInstrumentor.instrument_app(app, **kwargs)
    else:
        instrumentor = FastAPIInstrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            kwargs = {}
            if excluded_urls is not None:
                kwargs["excluded_urls"] = excluded_urls
            instrumentor.instrument(**kwargs)


def uninstrument_fastapi(app: Any | None = None) -> None:
    """Deactivate OTel auto-instrumentation for FastAPI.

    Args:
        app: Optional ``FastAPI`` application instance.  When ``None``,
            global instrumentation is removed.

    Raises:
        ImportError: If ``opentelemetry-instrumentation-fastapi`` is not
            installed.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        raise ImportError(
            "To uninstrument FastAPI, install the extra: " "pip install simple-log-factory-ext-otel[fastapi]"
        )

    if app is not None:
        FastAPIInstrumentor.uninstrument_app(app)
    else:
        FastAPIInstrumentor().uninstrument()

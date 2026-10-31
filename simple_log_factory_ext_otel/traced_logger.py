"""Traced logger that combines a standard ``logging.Logger`` with an OTel ``Tracer``.

Provides ``TracedLogger``, a convenience wrapper that proxies standard
logging methods and adds ``span()`` / ``trace()`` helpers for creating
OTel spans.
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any, TypeVar

from opentelemetry.sdk.trace import Tracer

F = TypeVar("F", bound=Callable[..., Any])


def _caller_stacklevel(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Raise ``stacklevel`` by one, so records name the proxy's caller instead of the proxy.

    Args:
        kwargs: Keyword arguments of the proxied logging call. Updated in place.

    Returns:
        The same *kwargs*, ready to forward to the ``logging.Logger`` method.
    """
    kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
    return kwargs


class TracedLogger:
    """Wraps a ``logging.Logger`` and an OTel ``Tracer``.

    All standard logging methods (debug, info, warning, error, exception,
    critical, log) are proxied to the underlying logger, and the records they
    create name the proxy's caller as their source (``funcName``, ``lineno``,
    ``pathname``, and the exported ``code.*`` attributes).  Logs emitted
    inside a ``span()`` or ``trace()`` are automatically correlated with
    the active span via OTel's context propagation.

    Args:
        logger: The standard library logger to proxy.
        tracer: The OTel ``Tracer`` used to create spans.
    """

    def __init__(self, logger: logging.Logger, tracer: Tracer) -> None:
        self._logger = logger
        self._tracer = tracer

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def logger(self) -> logging.Logger:
        """The underlying ``logging.Logger``."""
        return self._logger

    @property
    def tracer(self) -> Tracer:
        """The underlying OTel ``Tracer``."""
        return self._tracer

    # ------------------------------------------------------------------
    # Logging proxies
    # ------------------------------------------------------------------

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.debug``."""
        self._logger.debug(msg, *args, **_caller_stacklevel(kwargs))

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.info``."""
        self._logger.info(msg, *args, **_caller_stacklevel(kwargs))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.warning``."""
        self._logger.warning(msg, *args, **_caller_stacklevel(kwargs))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.error``."""
        self._logger.error(msg, *args, **_caller_stacklevel(kwargs))

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.exception``."""
        self._logger.exception(msg, *args, **_caller_stacklevel(kwargs))

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.critical``."""
        self._logger.critical(msg, *args, **_caller_stacklevel(kwargs))

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.log``."""
        self._logger.log(level, msg, *args, **_caller_stacklevel(kwargs))

    # ------------------------------------------------------------------
    # Database instrumentation
    # ------------------------------------------------------------------

    def instrument_db(self, *drivers: str, enable_commenter: bool = False) -> list[str]:
        """Activate OTel auto-instrumentation for database driver(s).

        Convenience wrapper around
        :func:`~simple_log_factory_ext_otel.db.instrument_db`.

        Args:
            *drivers: Driver names to instrument (e.g. ``"psycopg2"``).
            enable_commenter: If ``True``, append SQL comments with trace
                context to queries.

        Returns:
            List of driver names that were successfully instrumented.
        """
        from simple_log_factory_ext_otel.db import instrument_db

        return instrument_db(*drivers, enable_commenter=enable_commenter)

    # ------------------------------------------------------------------
    # HTTP instrumentation
    # ------------------------------------------------------------------

    def instrument_requests(self, *, excluded_urls: str | None = None) -> None:
        """Activate OTel auto-instrumentation for the ``requests`` library.

        Convenience wrapper around
        :func:`~simple_log_factory_ext_otel.requests_instr.instrument_requests`.

        Args:
            excluded_urls: Comma-delimited string of regex patterns for URLs
                that should not be traced.
        """
        from simple_log_factory_ext_otel.requests_instr import instrument_requests

        instrument_requests(excluded_urls=excluded_urls)

    def instrument_fastapi(self, app: Any | None = None, *, excluded_urls: str | None = None) -> None:
        """Activate OTel auto-instrumentation for FastAPI.

        Convenience wrapper around
        :func:`~simple_log_factory_ext_otel.fastapi_instr.instrument_fastapi`.

        Args:
            app: Optional ``FastAPI`` application instance.  When ``None``,
                global instrumentation is applied.
            excluded_urls: Comma-delimited string of regex patterns for URLs
                that should not be traced.
        """
        from simple_log_factory_ext_otel.fastapi_instr import instrument_fastapi

        instrument_fastapi(app=app, excluded_urls=excluded_urls)

    # ------------------------------------------------------------------
    # Tracing helpers
    # ------------------------------------------------------------------

    @contextmanager
    def span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Any, None, None]:
        """Context manager that creates an OTel span.

        Logs emitted inside this block are automatically correlated with the
        span via OTel's context propagation.

        Args:
            name: The span name.
            attributes: Optional span attributes.

        Yields:
            The active OTel span.
        """
        with self._tracer.start_as_current_span(name, attributes=attributes) as s:
            yield s

    @asynccontextmanager
    async def async_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> AsyncGenerator[Any, None]:
        """Async context manager that creates an OTel span.

        Async counterpart of :meth:`span` for use in ``async with`` blocks.

        Args:
            name: The span name.
            attributes: Optional span attributes.

        Yields:
            The active OTel span.
        """
        with self._tracer.start_as_current_span(name, attributes=attributes) as s:
            yield s

    def trace(
        self,
        name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Callable[[F], F]:
        """Decorator that wraps a function call in an OTel span.

        If the decorated function raises an exception, the span records it
        once as an exception event, its status is set to ``ERROR``, and the
        exception is re-raised (the default behavior of
        ``start_as_current_span``).

        Args:
            name: Span name.  Defaults to the function's qualified name.
            attributes: Optional span attributes.

        Returns:
            A decorator that wraps the function.
        """

        def decorator(func: F) -> F:
            span_name = name or func.__qualname__

            if inspect.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with self._tracer.start_as_current_span(span_name, attributes=attributes):
                        return await func(*args, **kwargs)

                return async_wrapper  # type: ignore[return-value]

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with self._tracer.start_as_current_span(span_name, attributes=attributes):
                    return func(*args, **kwargs)

            return wrapper  # type: ignore[return-value]

        return decorator

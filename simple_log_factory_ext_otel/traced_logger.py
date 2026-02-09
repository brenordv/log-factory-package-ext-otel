"""Traced logger that combines a standard ``logging.Logger`` with an OTel ``Tracer``.

Provides ``TracedLogger``, a convenience wrapper that proxies standard
logging methods and adds ``span()`` / ``trace()`` helpers for creating
OTel spans.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Callable, TypeVar

from opentelemetry.sdk.trace import Tracer
from opentelemetry.trace import StatusCode

F = TypeVar("F", bound=Callable[..., Any])


class TracedLogger:
    """Wraps a ``logging.Logger`` and an OTel ``Tracer``.

    All standard logging methods (debug, info, warning, error, exception,
    critical, log) are proxied to the underlying logger.  Logs emitted
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
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.info``."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.warning``."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.error``."""
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.exception``."""
        self._logger.exception(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.critical``."""
        self._logger.critical(msg, *args, **kwargs)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Proxy to ``logger.log``."""
        self._logger.log(level, msg, *args, **kwargs)

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

    def trace(
        self,
        name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Callable[[F], F]:
        """Decorator that wraps a function call in an OTel span.

        If the decorated function raises an exception, it is recorded on
        the span and re-raised.

        Args:
            name: Span name.  Defaults to the function's qualified name.
            attributes: Optional span attributes.

        Returns:
            A decorator that wraps the function.
        """

        def decorator(func: F) -> F:
            span_name = name or func.__qualname__

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with self._tracer.start_as_current_span(span_name, attributes=attributes) as s:
                    try:
                        return func(*args, **kwargs)
                    except Exception as exc:
                        s.set_status(StatusCode.ERROR, str(exc))
                        s.record_exception(exc)
                        raise

            return wrapper  # type: ignore[return-value]

        return decorator

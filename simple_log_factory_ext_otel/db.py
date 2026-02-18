"""Drop-in database driver instrumentation.

Activates OTel auto-instrumentation for supported database drivers so that
every SQL query creates a ``CLIENT`` span with ``db.system``, ``db.statement``,
etc.

Must be called **after** :func:`setup_otel` or :func:`otel_log_factory` so the
global ``TracerProvider`` is already registered.
"""

from __future__ import annotations

SUPPORTED_DRIVERS: tuple[str, ...] = ("psycopg2", "psycopg")


def instrument_db(*drivers: str, enable_commenter: bool = False) -> list[str]:
    """Activate OTel auto-instrumentation for the given database driver(s).

    Args:
        *drivers: Driver names to instrument.  Supported: ``"psycopg2"``,
            ``"psycopg"``.
        enable_commenter: If ``True``, append SQL comments with trace context
            to queries (useful for ``pg_stat_statements`` correlation).

    Returns:
        List of driver names that were successfully instrumented.

    Raises:
        ValueError: If an unsupported driver name is passed.
        ImportError: If the required instrumentation package is not installed.
    """
    instrumented: list[str] = []
    for driver in drivers:
        if driver not in SUPPORTED_DRIVERS:
            raise ValueError(f"Unsupported driver: {driver!r}. Supported: {sorted(SUPPORTED_DRIVERS)}")

        _instrument_single(driver, enable_commenter=enable_commenter)
        instrumented.append(driver)

    return instrumented


def uninstrument_db(*drivers: str) -> list[str]:
    """Deactivate OTel auto-instrumentation for the given driver(s).

    Useful for testing teardown or dynamic reconfiguration.

    Args:
        *drivers: Driver names to uninstrument.  Supported: ``"psycopg2"``,
            ``"psycopg"``.

    Returns:
        List of driver names that were successfully uninstrumented.

    Raises:
        ValueError: If an unsupported driver name is passed.
        ImportError: If the required instrumentation package is not installed.
    """
    uninstrumented: list[str] = []
    for driver in drivers:
        if driver not in SUPPORTED_DRIVERS:
            raise ValueError(f"Unsupported driver: {driver!r}. Supported: {sorted(SUPPORTED_DRIVERS)}")

        _uninstrument_single(driver)
        uninstrumented.append(driver)

    return uninstrumented


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _instrument_single(driver: str, *, enable_commenter: bool) -> None:
    """Instrument a single driver, with idempotency guard."""
    if driver == "psycopg2":
        try:
            from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
        except ImportError:
            raise ImportError(
                "To instrument psycopg2, install the extra: " "pip install simple-log-factory-ext-otel[psycopg2]"
            )

        instrumentor = Psycopg2Instrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument(enable_commenter=enable_commenter)

    elif driver == "psycopg":
        try:
            from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
        except ImportError:
            raise ImportError(
                "To instrument psycopg, install the extra: " "pip install simple-log-factory-ext-otel[psycopg]"
            )

        instrumentor = PsycopgInstrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument(enable_commenter=enable_commenter)


def _uninstrument_single(driver: str) -> None:
    """Uninstrument a single driver."""
    if driver == "psycopg2":
        try:
            from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
        except ImportError:
            raise ImportError(
                "To uninstrument psycopg2, install the extra: " "pip install simple-log-factory-ext-otel[psycopg2]"
            )

        Psycopg2Instrumentor().uninstrument()

    elif driver == "psycopg":
        try:
            from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
        except ImportError:
            raise ImportError(
                "To uninstrument psycopg, install the extra: " "pip install simple-log-factory-ext-otel[psycopg]"
            )

        PsycopgInstrumentor().uninstrument()

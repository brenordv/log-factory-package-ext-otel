"""Unit tests for requests library instrumentation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from simple_log_factory_ext_otel.requests_instr import instrument_requests, uninstrument_requests

# ------------------------------------------------------------------
# instrument_requests()
# ------------------------------------------------------------------


class TestInstrumentRequests:
    """Tests for instrument_requests()."""

    def test_instrument_with_defaults(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_module = MagicMock()
        mock_module.RequestsInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.requests": mock_module}):
            instrument_requests()

        mock_instrumentor.instrument.assert_called_once_with()

    def test_instrument_with_excluded_urls(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_module = MagicMock()
        mock_module.RequestsInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.requests": mock_module}):
            instrument_requests(excluded_urls="health,ready")

        mock_instrumentor.instrument.assert_called_once_with(excluded_urls="health,ready")

    def test_missing_package_raises_import_error(self) -> None:
        with patch.dict("sys.modules", {"opentelemetry.instrumentation.requests": None}):
            with pytest.raises(ImportError, match="pip install simple-log-factory-ext-otel\\[requests\\]"):
                instrument_requests()


# ------------------------------------------------------------------
# Idempotency guard
# ------------------------------------------------------------------


class TestRequestsIdempotencyGuard:
    """Tests that instrument_requests() skips when already instrumented."""

    def test_already_instrumented_is_skipped(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = True
        mock_module = MagicMock()
        mock_module.RequestsInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.requests": mock_module}):
            instrument_requests()

        mock_instrumentor.instrument.assert_not_called()


# ------------------------------------------------------------------
# uninstrument_requests()
# ------------------------------------------------------------------


class TestUninstrumentRequests:
    """Tests for uninstrument_requests()."""

    def test_uninstrument(self) -> None:
        mock_instrumentor = MagicMock()
        mock_module = MagicMock()
        mock_module.RequestsInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.requests": mock_module}):
            uninstrument_requests()

        mock_instrumentor.uninstrument.assert_called_once()

    def test_missing_package_raises_import_error(self) -> None:
        with patch.dict("sys.modules", {"opentelemetry.instrumentation.requests": None}):
            with pytest.raises(ImportError, match="pip install simple-log-factory-ext-otel\\[requests\\]"):
                uninstrument_requests()

"""Unit tests for FastAPI instrumentation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from simple_log_factory_ext_otel.fastapi_instr import instrument_fastapi, uninstrument_fastapi

# ------------------------------------------------------------------
# instrument_fastapi() — global mode
# ------------------------------------------------------------------


class TestInstrumentFastapiGlobal:
    """Tests for instrument_fastapi() in global mode (app=None)."""

    def test_instrument_with_defaults(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_module = MagicMock()
        mock_module.FastAPIInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": mock_module}):
            instrument_fastapi()

        mock_instrumentor.instrument.assert_called_once_with()

    def test_instrument_with_excluded_urls(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_module = MagicMock()
        mock_module.FastAPIInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": mock_module}):
            instrument_fastapi(excluded_urls="health,ready")

        mock_instrumentor.instrument.assert_called_once_with(excluded_urls="health,ready")

    def test_missing_package_raises_import_error(self) -> None:
        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": None}):
            with pytest.raises(ImportError, match="pip install simple-log-factory-ext-otel\\[fastapi\\]"):
                instrument_fastapi()


# ------------------------------------------------------------------
# instrument_fastapi() — app-specific mode
# ------------------------------------------------------------------


class TestInstrumentFastapiAppSpecific:
    """Tests for instrument_fastapi() with a specific app instance."""

    def test_instrument_app(self) -> None:
        mock_app = MagicMock()
        mock_module = MagicMock()

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": mock_module}):
            instrument_fastapi(app=mock_app)

        mock_module.FastAPIInstrumentor.instrument_app.assert_called_once_with(mock_app)

    def test_instrument_app_with_excluded_urls(self) -> None:
        mock_app = MagicMock()
        mock_module = MagicMock()

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": mock_module}):
            instrument_fastapi(app=mock_app, excluded_urls="health,ready")

        mock_module.FastAPIInstrumentor.instrument_app.assert_called_once_with(mock_app, excluded_urls="health,ready")


# ------------------------------------------------------------------
# Idempotency guard
# ------------------------------------------------------------------


class TestFastapiIdempotencyGuard:
    """Tests that global instrument_fastapi() skips when already instrumented."""

    def test_already_instrumented_is_skipped(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = True
        mock_module = MagicMock()
        mock_module.FastAPIInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": mock_module}):
            instrument_fastapi()

        mock_instrumentor.instrument.assert_not_called()


# ------------------------------------------------------------------
# uninstrument_fastapi()
# ------------------------------------------------------------------


class TestUninstrumentFastapi:
    """Tests for uninstrument_fastapi()."""

    def test_uninstrument_global(self) -> None:
        mock_instrumentor = MagicMock()
        mock_module = MagicMock()
        mock_module.FastAPIInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": mock_module}):
            uninstrument_fastapi()

        mock_instrumentor.uninstrument.assert_called_once()

    def test_uninstrument_app(self) -> None:
        mock_app = MagicMock()
        mock_module = MagicMock()

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": mock_module}):
            uninstrument_fastapi(app=mock_app)

        mock_module.FastAPIInstrumentor.uninstrument_app.assert_called_once_with(mock_app)

    def test_missing_package_raises_import_error(self) -> None:
        with patch.dict("sys.modules", {"opentelemetry.instrumentation.fastapi": None}):
            with pytest.raises(ImportError, match="pip install simple-log-factory-ext-otel\\[fastapi\\]"):
                uninstrument_fastapi()

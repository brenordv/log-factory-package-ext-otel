"""Unit tests for database driver instrumentation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from simple_log_factory_ext_otel.db import SUPPORTED_DRIVERS, instrument_db, uninstrument_db

# ------------------------------------------------------------------
# instrument_db()
# ------------------------------------------------------------------


class TestInstrumentDb:
    """Tests for instrument_db()."""

    @patch("simple_log_factory_ext_otel.db.Psycopg2Instrumentor", create=True)
    def test_instrument_psycopg2(self, mock_cls: MagicMock) -> None:
        instance = MagicMock()
        instance.is_instrumented_by_opentelemetry = False
        mock_cls.return_value = instance

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg2": MagicMock()}):
            with patch(
                "simple_log_factory_ext_otel.db._instrument_single",
                wraps=None,
            ) as _:
                pass

        # Use the real function with a patched import
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_module = MagicMock()
        mock_module.Psycopg2Instrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg2": mock_module}):
            result = instrument_db("psycopg2")

        assert result == ["psycopg2"]
        mock_instrumentor.instrument.assert_called_once_with(enable_commenter=False)

    def test_instrument_psycopg(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_module = MagicMock()
        mock_module.PsycopgInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg": mock_module}):
            result = instrument_db("psycopg")

        assert result == ["psycopg"]
        mock_instrumentor.instrument.assert_called_once_with(enable_commenter=False)

    def test_instrument_psycopg2_with_enable_commenter(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = False
        mock_module = MagicMock()
        mock_module.Psycopg2Instrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg2": mock_module}):
            result = instrument_db("psycopg2", enable_commenter=True)

        assert result == ["psycopg2"]
        mock_instrumentor.instrument.assert_called_once_with(enable_commenter=True)

    def test_instrument_multiple_drivers(self) -> None:
        mock_psycopg2_instrumentor = MagicMock()
        mock_psycopg2_instrumentor.is_instrumented_by_opentelemetry = False
        mock_psycopg2_module = MagicMock()
        mock_psycopg2_module.Psycopg2Instrumentor.return_value = mock_psycopg2_instrumentor

        mock_psycopg_instrumentor = MagicMock()
        mock_psycopg_instrumentor.is_instrumented_by_opentelemetry = False
        mock_psycopg_module = MagicMock()
        mock_psycopg_module.PsycopgInstrumentor.return_value = mock_psycopg_instrumentor

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry.instrumentation.psycopg2": mock_psycopg2_module,
                "opentelemetry.instrumentation.psycopg": mock_psycopg_module,
            },
        ):
            result = instrument_db("psycopg2", "psycopg")

        assert result == ["psycopg2", "psycopg"]
        mock_psycopg2_instrumentor.instrument.assert_called_once()
        mock_psycopg_instrumentor.instrument.assert_called_once()

    def test_unsupported_driver_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported driver: 'mysql'"):
            instrument_db("mysql")

    def test_missing_psycopg2_package_raises_import_error(self) -> None:
        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg2": None}):
            with pytest.raises(ImportError, match="pip install simple-log-factory-ext-otel\\[psycopg2\\]"):
                instrument_db("psycopg2")

    def test_missing_psycopg_package_raises_import_error(self) -> None:
        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg": None}):
            with pytest.raises(ImportError, match="pip install simple-log-factory-ext-otel\\[psycopg\\]"):
                instrument_db("psycopg")

    def test_no_drivers_returns_empty_list(self) -> None:
        result = instrument_db()
        assert result == []


# ------------------------------------------------------------------
# Idempotency guard
# ------------------------------------------------------------------


class TestIdempotencyGuard:
    """Tests that instrument_db() skips already-instrumented drivers."""

    def test_psycopg2_already_instrumented_is_skipped(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = True
        mock_module = MagicMock()
        mock_module.Psycopg2Instrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg2": mock_module}):
            result = instrument_db("psycopg2")

        assert result == ["psycopg2"]
        mock_instrumentor.instrument.assert_not_called()

    def test_psycopg_already_instrumented_is_skipped(self) -> None:
        mock_instrumentor = MagicMock()
        mock_instrumentor.is_instrumented_by_opentelemetry = True
        mock_module = MagicMock()
        mock_module.PsycopgInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg": mock_module}):
            result = instrument_db("psycopg")

        assert result == ["psycopg"]
        mock_instrumentor.instrument.assert_not_called()


# ------------------------------------------------------------------
# uninstrument_db()
# ------------------------------------------------------------------


class TestUninstrumentDb:
    """Tests for uninstrument_db()."""

    def test_uninstrument_psycopg2(self) -> None:
        mock_instrumentor = MagicMock()
        mock_module = MagicMock()
        mock_module.Psycopg2Instrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg2": mock_module}):
            result = uninstrument_db("psycopg2")

        assert result == ["psycopg2"]
        mock_instrumentor.uninstrument.assert_called_once()

    def test_uninstrument_psycopg(self) -> None:
        mock_instrumentor = MagicMock()
        mock_module = MagicMock()
        mock_module.PsycopgInstrumentor.return_value = mock_instrumentor

        with patch.dict("sys.modules", {"opentelemetry.instrumentation.psycopg": mock_module}):
            result = uninstrument_db("psycopg")

        assert result == ["psycopg"]
        mock_instrumentor.uninstrument.assert_called_once()

    def test_uninstrument_multiple_drivers(self) -> None:
        mock_psycopg2_instrumentor = MagicMock()
        mock_psycopg2_module = MagicMock()
        mock_psycopg2_module.Psycopg2Instrumentor.return_value = mock_psycopg2_instrumentor

        mock_psycopg_instrumentor = MagicMock()
        mock_psycopg_module = MagicMock()
        mock_psycopg_module.PsycopgInstrumentor.return_value = mock_psycopg_instrumentor

        with patch.dict(
            "sys.modules",
            {
                "opentelemetry.instrumentation.psycopg2": mock_psycopg2_module,
                "opentelemetry.instrumentation.psycopg": mock_psycopg_module,
            },
        ):
            result = uninstrument_db("psycopg2", "psycopg")

        assert result == ["psycopg2", "psycopg"]
        mock_psycopg2_instrumentor.uninstrument.assert_called_once()
        mock_psycopg_instrumentor.uninstrument.assert_called_once()

    def test_unsupported_driver_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported driver: 'sqlite'"):
            uninstrument_db("sqlite")

    def test_no_drivers_returns_empty_list(self) -> None:
        result = uninstrument_db()
        assert result == []


# ------------------------------------------------------------------
# SUPPORTED_DRIVERS constant
# ------------------------------------------------------------------


class TestSupportedDrivers:
    """Tests for the SUPPORTED_DRIVERS constant."""

    def test_supported_drivers_contains_expected_values(self) -> None:
        assert "psycopg2" in SUPPORTED_DRIVERS
        assert "psycopg" in SUPPORTED_DRIVERS

    def test_supported_drivers_is_tuple(self) -> None:
        assert isinstance(SUPPORTED_DRIVERS, tuple)

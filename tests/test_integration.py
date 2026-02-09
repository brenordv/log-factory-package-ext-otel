"""Integration tests for OtelLogHandler with simple_log_factory."""

from __future__ import annotations

import logging
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from simple_log_factory_ext_otel import OtelLogHandler, OtelTracer, TracedLogger, setup_otel

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_handler(**kwargs: Any) -> OtelLogHandler:
    """Create an OtelLogHandler with a mocked gRPC exporter."""
    with patch("simple_log_factory_ext_otel.handler.GrpcLogExporter", return_value=MagicMock()):
        return OtelLogHandler(service_name="integration-test", **kwargs)


def _unique_logger_name(prefix: str) -> str:
    """Generate a unique logger name to avoid cross-test pollution."""
    return f"{prefix}.{uuid.uuid4().hex[:8]}"


# ------------------------------------------------------------------
# Integration with simple_log_factory
# ------------------------------------------------------------------


class TestLogFactoryIntegration:
    """Tests that require simple_log_factory to be installed."""

    @pytest.fixture(autouse=True)
    def _check_simple_log_factory(self) -> None:
        """Skip all tests in this class if simple_log_factory is not installed."""
        pytest.importorskip("simple_log_factory")

    def test_handler_works_with_log_factory(self) -> None:
        from simple_log_factory import log_factory

        handler = _make_handler()
        handler._otel_handler = MagicMock()

        logger = log_factory(
            _unique_logger_name("test.integration.basic"),
            custom_handlers=[handler],
            to_console=False,
        )
        logger.info("Integration test message")

        handler._otel_handler.emit.assert_called_once()
        record = handler._otel_handler.emit.call_args[0][0]
        assert record.getMessage() == "Integration test message"
        handler.shutdown()

    def test_level_filtering_with_log_factory(self) -> None:
        """Verify that log_factory's log_level parameter gates handler emission.

        log_factory calls handler.setLevel(log_level) on every handler it
        receives.  When log_level=WARNING, INFO records should be filtered
        out by the handler's level gate before reaching emit().
        """
        from simple_log_factory import log_factory

        handler = _make_handler()
        handler._otel_handler = MagicMock()

        logger = log_factory(
            _unique_logger_name("test.integration.level"),
            custom_handlers=[handler],
            log_level=logging.WARNING,
            to_console=False,
        )
        logger.info("Should be filtered out")

        handler._otel_handler.emit.assert_not_called()
        handler.shutdown()

    def test_unique_handler_types_prevents_duplicate_on_second_call(self) -> None:
        """Verify unique_handler_types dedup across successive log_factory calls.

        log_factory's _attach_handlers checks handler types already present
        on the logger.  A second call with unique_handler_types=True should
        skip adding another OtelLogHandler if one is already attached.
        """
        from simple_log_factory import log_factory

        logger_name = _unique_logger_name("test.integration.dedup")

        handler1 = _make_handler()
        handler1._otel_handler = MagicMock()

        # First call attaches handler1
        log_factory(
            logger_name,
            custom_handlers=[handler1],
            to_console=False,
        )

        handler2 = _make_handler()
        handler2._otel_handler = MagicMock()

        # Second call with unique_handler_types=True — handler2 should be
        # skipped because an OtelLogHandler is already on the logger.
        logger = log_factory(
            logger_name,
            custom_handlers=[handler2],
            unique_handler_types=True,
            to_console=False,
        )
        logger.info("Dedup test")

        handler1._otel_handler.emit.assert_called_once()
        handler2._otel_handler.emit.assert_not_called()

        handler1.shutdown()
        handler2.shutdown()


# ------------------------------------------------------------------
# Standalone integration (no simple_log_factory dependency)
# ------------------------------------------------------------------


class TestStandaloneIntegration:
    """Tests that OtelLogHandler works with the standard logging module."""

    def test_handler_with_stdlib_logger(self) -> None:
        handler = _make_handler()
        handler._otel_handler = MagicMock()

        logger = logging.getLogger(_unique_logger_name("test.standalone"))
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        try:
            logger.warning("Standalone warning")
            handler._otel_handler.emit.assert_called_once()
            record = handler._otel_handler.emit.call_args[0][0]
            assert record.getMessage() == "Standalone warning"
        finally:
            logger.removeHandler(handler)
            handler.shutdown()

    def test_handler_respects_level_gate(self) -> None:
        handler = _make_handler(log_level=logging.ERROR)
        handler._otel_handler = MagicMock()

        logger = logging.getLogger(_unique_logger_name("test.standalone.level"))
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        try:
            logger.info("Should not reach OTel")
            handler._otel_handler.emit.assert_not_called()

            logger.error("Should reach OTel")
            handler._otel_handler.emit.assert_called_once()
        finally:
            logger.removeHandler(handler)
            handler.shutdown()


# ------------------------------------------------------------------
# setup_otel() integration
# ------------------------------------------------------------------


class TestSetupOtel:
    """Tests for the setup_otel() convenience function."""

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter", return_value=MagicMock())
    @patch("simple_log_factory_ext_otel.tracing.GrpcSpanExporter", return_value=MagicMock())
    def test_setup_otel_returns_handler_and_tracer(self, _span: MagicMock, _log: MagicMock) -> None:
        handler, tracer = setup_otel(service_name="test-svc")
        assert isinstance(handler, OtelLogHandler)
        assert isinstance(tracer, OtelTracer)
        handler.shutdown()
        tracer.shutdown()

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter", return_value=MagicMock())
    @patch("simple_log_factory_ext_otel.tracing.GrpcSpanExporter", return_value=MagicMock())
    def test_setup_otel_shares_resource(self, _span: MagicMock, _log: MagicMock) -> None:
        handler, tracer = setup_otel(
            service_name="shared-svc",
            resource_attributes={"env": "test"},
        )
        handler_resource = handler.provider.resource
        tracer_resource = tracer.provider.resource
        assert handler_resource is tracer_resource
        assert handler_resource.attributes["service.name"] == "shared-svc"
        assert handler_resource.attributes["env"] == "test"
        handler.shutdown()
        tracer.shutdown()

    @patch("simple_log_factory_ext_otel.handler.GrpcLogExporter", return_value=MagicMock())
    @patch("simple_log_factory_ext_otel.tracing.GrpcSpanExporter", return_value=MagicMock())
    def test_traced_logger_with_log_factory(self, _span: MagicMock, _log: MagicMock) -> None:
        handler, otel_tracer = setup_otel(service_name="tl-svc")
        handler._otel_handler = MagicMock()

        stdlib_logger = logging.getLogger(_unique_logger_name("test.traced_logger"))
        stdlib_logger.setLevel(logging.DEBUG)
        stdlib_logger.addHandler(handler)

        traced = TracedLogger(logger=stdlib_logger, tracer=otel_tracer.tracer)

        try:
            with traced.span("my-op"):
                traced.info("inside span")

            handler._otel_handler.emit.assert_called_once()
            record = handler._otel_handler.emit.call_args[0][0]
            assert record.getMessage() == "inside span"
        finally:
            stdlib_logger.removeHandler(handler)
            handler.shutdown()
            otel_tracer.shutdown()

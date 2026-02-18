"""Unit tests for TracedLogger."""

from __future__ import annotations

import inspect
import logging
from unittest.mock import MagicMock

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import get_current_span

from simple_log_factory_ext_otel.traced_logger import TracedLogger


@pytest.fixture()
def tracer_provider() -> TracerProvider:
    """Create a real TracerProvider for testing (no exporter needed)."""
    return TracerProvider()


@pytest.fixture()
def traced_logger(tracer_provider: TracerProvider) -> TracedLogger:
    """Create a TracedLogger backed by a real tracer and a mock logger."""
    tracer = tracer_provider.get_tracer("test")
    logger = MagicMock(spec=logging.Logger)
    return TracedLogger(logger=logger, tracer=tracer)


# ------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------


class TestProperties:
    """Tests for logger and tracer properties."""

    def test_logger_property(self, traced_logger: TracedLogger) -> None:
        assert isinstance(traced_logger.logger, MagicMock)

    def test_tracer_property(self, traced_logger: TracedLogger) -> None:
        assert traced_logger.tracer is not None


# ------------------------------------------------------------------
# Logging proxies
# ------------------------------------------------------------------


class TestLoggingProxies:
    """Tests that logging methods delegate to the underlying logger."""

    def test_debug(self, traced_logger: TracedLogger) -> None:
        traced_logger.debug("msg %s", "arg")
        traced_logger.logger.debug.assert_called_once_with("msg %s", "arg")

    def test_info(self, traced_logger: TracedLogger) -> None:
        traced_logger.info("msg")
        traced_logger.logger.info.assert_called_once_with("msg")

    def test_warning(self, traced_logger: TracedLogger) -> None:
        traced_logger.warning("msg")
        traced_logger.logger.warning.assert_called_once_with("msg")

    def test_error(self, traced_logger: TracedLogger) -> None:
        traced_logger.error("msg")
        traced_logger.logger.error.assert_called_once_with("msg")

    def test_exception(self, traced_logger: TracedLogger) -> None:
        traced_logger.exception("msg")
        traced_logger.logger.exception.assert_called_once_with("msg")

    def test_critical(self, traced_logger: TracedLogger) -> None:
        traced_logger.critical("msg")
        traced_logger.logger.critical.assert_called_once_with("msg")

    def test_log(self, traced_logger: TracedLogger) -> None:
        traced_logger.log(logging.INFO, "msg")
        traced_logger.logger.log.assert_called_once_with(logging.INFO, "msg")


# ------------------------------------------------------------------
# span() context manager
# ------------------------------------------------------------------


class TestSpanContextManager:
    """Tests for the span() context manager."""

    def test_span_creates_active_span(self, traced_logger: TracedLogger) -> None:
        with traced_logger.span("test-span") as s:
            assert s is not None
            assert s.name == "test-span"
            # Span should be the current active span
            assert get_current_span() is s

    def test_span_with_attributes(self, traced_logger: TracedLogger) -> None:
        with traced_logger.span("test-span", attributes={"key": "value"}) as s:
            assert s.attributes["key"] == "value"

    def test_nested_spans(self, traced_logger: TracedLogger) -> None:
        with traced_logger.span("outer") as outer:
            with traced_logger.span("inner") as inner:
                assert inner.name == "inner"
                assert inner.parent is not None
                assert inner.parent.span_id == outer.context.span_id


# ------------------------------------------------------------------
# trace() decorator
# ------------------------------------------------------------------


class TestTraceDecorator:
    """Tests for the trace() decorator."""

    def test_trace_creates_span(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("my-operation")
        def my_func() -> str:
            # Verify span is active during execution
            span = get_current_span()
            assert span.is_recording()
            return "result"

        assert my_func() == "result"

    def test_trace_default_name_is_qualname(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace()
        def some_function() -> None:
            span = get_current_span()
            assert "some_function" in span.name

        some_function()

    def test_trace_records_exception(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("failing-op")
        def failing() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            failing()

    def test_trace_with_attributes(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("op", attributes={"op.type": "test"})
        def my_op() -> str:
            return "ok"

        assert my_op() == "ok"

    def test_trace_preserves_function_metadata(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("op")
        def documented_func() -> None:
            """My docstring."""

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "My docstring."


# ------------------------------------------------------------------
# async_span() context manager
# ------------------------------------------------------------------


class TestAsyncSpanContextManager:
    """Tests for the async_span() async context manager."""

    @pytest.mark.asyncio
    async def test_async_span_creates_active_span(self, traced_logger: TracedLogger) -> None:
        async with traced_logger.async_span("async-test-span") as s:
            assert s is not None
            assert s.name == "async-test-span"
            assert get_current_span() is s

    @pytest.mark.asyncio
    async def test_async_span_with_attributes(self, traced_logger: TracedLogger) -> None:
        async with traced_logger.async_span("async-span", attributes={"key": "value"}) as s:
            assert s.attributes["key"] == "value"

    @pytest.mark.asyncio
    async def test_async_nested_spans(self, traced_logger: TracedLogger) -> None:
        async with traced_logger.async_span("outer") as outer:
            async with traced_logger.async_span("inner") as inner:
                assert inner.name == "inner"
                assert inner.parent is not None
                assert inner.parent.span_id == outer.context.span_id


# ------------------------------------------------------------------
# trace() decorator — async path
# ------------------------------------------------------------------


class TestTraceDecoratorAsync:
    """Tests for the trace() decorator with async functions."""

    @pytest.mark.asyncio
    async def test_trace_async_creates_span(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("async-op")
        async def my_async_func() -> str:
            span = get_current_span()
            assert span.is_recording()
            return "async-result"

        assert await my_async_func() == "async-result"

    @pytest.mark.asyncio
    async def test_trace_async_default_name_is_qualname(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace()
        async def some_async_function() -> None:
            span = get_current_span()
            assert "some_async_function" in span.name

        await some_async_function()

    @pytest.mark.asyncio
    async def test_trace_async_records_exception(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("failing-async-op")
        async def failing_async() -> None:
            raise ValueError("async boom")

        with pytest.raises(ValueError, match="async boom"):
            await failing_async()

    @pytest.mark.asyncio
    async def test_trace_async_with_attributes(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("async-op", attributes={"op.type": "async-test"})
        async def my_async_op() -> str:
            return "ok"

        assert await my_async_op() == "ok"

    @pytest.mark.asyncio
    async def test_trace_async_preserves_function_metadata(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("op")
        async def documented_async_func() -> None:
            """My async docstring."""

        assert documented_async_func.__name__ == "documented_async_func"
        assert documented_async_func.__doc__ == "My async docstring."

    @pytest.mark.asyncio
    async def test_trace_async_returns_coroutine_function(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("op")
        async def my_coro() -> None:
            pass

        assert inspect.iscoroutinefunction(my_coro)

    def test_trace_sync_not_coroutine_function(self, traced_logger: TracedLogger) -> None:
        @traced_logger.trace("op")
        def my_sync() -> None:
            pass

        assert not inspect.iscoroutinefunction(my_sync)


# ------------------------------------------------------------------
# instrument_db() convenience method
# ------------------------------------------------------------------


class TestInstrumentDb:
    """Tests for TracedLogger.instrument_db() delegation."""

    def test_instrument_db_delegates_to_db_module(self, traced_logger: TracedLogger) -> None:
        from unittest.mock import patch as _patch

        with _patch("simple_log_factory_ext_otel.db.instrument_db") as mock_fn:
            mock_fn.return_value = ["psycopg2"]
            result = traced_logger.instrument_db("psycopg2")

        assert result == ["psycopg2"]
        mock_fn.assert_called_once_with("psycopg2", enable_commenter=False)

    def test_instrument_db_passes_enable_commenter(self, traced_logger: TracedLogger) -> None:
        from unittest.mock import patch as _patch

        with _patch("simple_log_factory_ext_otel.db.instrument_db") as mock_fn:
            mock_fn.return_value = ["psycopg2"]
            result = traced_logger.instrument_db("psycopg2", enable_commenter=True)

        assert result == ["psycopg2"]
        mock_fn.assert_called_once_with("psycopg2", enable_commenter=True)

    def test_instrument_db_multiple_drivers(self, traced_logger: TracedLogger) -> None:
        from unittest.mock import patch as _patch

        with _patch("simple_log_factory_ext_otel.db.instrument_db") as mock_fn:
            mock_fn.return_value = ["psycopg2", "psycopg"]
            result = traced_logger.instrument_db("psycopg2", "psycopg")

        assert result == ["psycopg2", "psycopg"]
        mock_fn.assert_called_once_with("psycopg2", "psycopg", enable_commenter=False)

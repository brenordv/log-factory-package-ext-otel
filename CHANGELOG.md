# Changelog

## [2.0.0]
### Changed
- Requires Python 3.11+ (dropped 3.9 and 3.10).
- Minimum OpenTelemetry versions raised to API/SDK/exporters 1.45.2 and instrumentations 0.66b2.
- `OtelLogHandler` translates records with the `LoggingHandler` from `opentelemetry-instrumentation-logging` (now a
  dependency); the SDK's own `LoggingHandler` is deprecated as of 1.45. Records keep exporting `code.*` attributes.
- `OtelLogHandler.close()` only flushes. Provider shutdown happens in `shutdown()` and the `atexit` hook.
- Dev dependencies moved to a `dev` dependency group; black and isort replaced by `ruff format` and ruff's import sorting.

### Fixed
- `simple-log-factory` is now a runtime dependency. `otel_log_factory()` imports it, so a plain install raised
  `ModuleNotFoundError`.
- `export_timeout_millis` is converted to seconds before it reaches the OTLP exporters, which take seconds. The
  default of 30000 used to mean 30000 seconds.
- OTel log export no longer stops after `logging.config.dictConfig` runs (uvicorn does at startup): reconfiguration
  closes every handler, and closing used to shut the provider down for good.
- `otel_log_factory()` rejects an empty `service_name`, as documented.
- `otel_log_factory()` accepts a single handler in `custom_handlers`, like `log_factory()` does.
- `TracedLogger` logging methods report the caller's function, file and line (`funcName`, `lineno`, `pathname` and the
  exported `code.*` attributes) instead of `traced_logger.py`. A `stacklevel` you pass is counted from your own call,
  so callers that added 1 to work around the wrapper should drop that.
- `TracedLogger.trace()` records an exception once per span instead of twice.

## [1.5.0]
### Added
- `instrument_requests()` / `uninstrument_requests()` — activate or deactivate OTel auto-instrumentation for the `requests` library (outgoing HTTP calls). Includes idempotency guard.
- `instrument_fastapi()` / `uninstrument_fastapi()` — activate or deactivate OTel auto-instrumentation for FastAPI (incoming HTTP requests). Supports both global and app-specific instrumentation modes. Includes idempotency guard.
- `TracedLogger.instrument_requests()` — convenience method that delegates to `instrument_requests()`.
- `TracedLogger.instrument_fastapi()` — convenience method that delegates to `instrument_fastapi()`.
- `otel_log_factory()` now accepts `instrument_requests` and `instrument_fastapi` parameters for drop-in HTTP tracing setup. Accepts `True` for defaults or a `dict` of kwargs forwarded to the standalone function.
- Optional dependency extras: `requests`, `fastapi`, `cross-resource` (both).

## [1.4.0]
### Added
- `instrument_db()` / `uninstrument_db()` — activate or deactivate OTel auto-instrumentation for database drivers (`psycopg2`, `psycopg`). Includes idempotency guard to prevent double-instrumentation.
- `TracedLogger.instrument_db()` — convenience method that delegates to `instrument_db()`.
- `otel_log_factory()` now accepts an `instrument_db` parameter (dict mapping driver names to options) for drop-in database tracing setup.
- `SUPPORTED_DRIVERS` constant listing all supported database driver names.
- Optional dependency extras: `psycopg2`, `psycopg`, `db` (all drivers).

### Changed
- Bumped minimum version for `opentelemetry-instrumentation-psycopg2` and `opentelemetry-instrumentation-psycopg` from `0.44b0` to `0.60b1`.
- Bumped minimum `ruff` dev dependency from `0.1.0` to `0.15.1`.

### Fixed
- `otel_log_factory()` no longer emits "Overriding of current TracerProvider is not allowed" warnings when called multiple times with different `log_name` values. The `OtelTracer` is now cached and reused for the same endpoint/service combination.

### Removed
- Redundant `grpc` and `http` optional dependency extras. Both OTLP exporters (gRPC and HTTP) are always installed as base dependencies.

## [1.3.0]
### Changed
- `otel_log_factory()` parameter `otel_exporter_http` renamed to `otel_exporter_endpoint`.

## [1.2.0]
### Added
- `otel_log_factory()` — all-in-one factory that creates a `TracedLogger` wired to an OTel backend, combining OTel setup and `simple_log_factory.log_factory` logger creation in a single call. Supports per-endpoint/service/log-name caching (multiple independent loggers) and both HTTP/gRPC protocols.
- `otel_log_factory()` validates `service_name` and `otel_exporter_http` (raises `ValueError` on empty/whitespace).
- `otel_log_factory()` defaults `log_name` to `service_name` when not provided.

## [1.1.0]
### Added
- `OtelTracer` — manages a `TracerProvider` with OTLP span export (gRPC/HTTP), mirroring `OtelLogHandler` in structure.
- `TracedLogger` — wraps a `logging.Logger` and an OTel `Tracer` with `span()` context manager and `trace()` decorator for easy span creation.
- `setup_otel()` — one-call convenience function that creates both logging and tracing pipelines with a shared `Resource` and registers the `TracerProvider` globally.
- `create_resource()` — shared helper for building OTel `Resource` instances.
- `OtelLogHandler` now accepts an optional `resource` parameter to use a pre-built `Resource`.

## [1.0.1]
Nothing really. Just updating version to include readme, license, and changelog.

## [1.0.0]
Initial version.

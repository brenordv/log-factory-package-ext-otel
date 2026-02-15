# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-02-14
### Changed
- `otel_log_factory()` parameter `otel_exporter_http` renamed to `otel_exporter_endpoint`.

## [1.2.0] - 2026-02-14
### Added
- `otel_log_factory()` — all-in-one factory that creates a `TracedLogger` wired to an OTel backend, combining OTel setup and `simple_log_factory.log_factory` logger creation in a single call. Supports per-endpoint/service/log-name caching (multiple independent loggers) and both HTTP/gRPC protocols.
- `otel_log_factory()` validates `service_name` and `otel_exporter_http` (raises `ValueError` on empty/whitespace).
- `otel_log_factory()` defaults `log_name` to `service_name` when not provided.

## [1.1.0] - 2026-02-12
### Added
- `OtelTracer` — manages a `TracerProvider` with OTLP span export (gRPC/HTTP), mirroring `OtelLogHandler` in structure.
- `TracedLogger` — wraps a `logging.Logger` and an OTel `Tracer` with `span()` context manager and `trace()` decorator for easy span creation.
- `setup_otel()` — one-call convenience function that creates both logging and tracing pipelines with a shared `Resource` and registers the `TracerProvider` globally.
- `create_resource()` — shared helper for building OTel `Resource` instances.
- `OtelLogHandler` now accepts an optional `resource` parameter to use a pre-built `Resource`.

## [1.0.1] - 2025-02-07
Nothing really. Just updating version to include readme, license, and changelog.

## [1.0.0] - 2025-02-07
Initial version.

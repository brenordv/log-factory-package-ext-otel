# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0rc1] - 2026-02-08

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

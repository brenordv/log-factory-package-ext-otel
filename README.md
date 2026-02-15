# simple-log-factory-ext-otel

OpenTelemetry log handler and tracing plugin for [simple_log_factory](https://github.com/raccoon/simple-log-factory).

Ship your log messages **and traces** to any OpenTelemetry-compatible backend (Tempo, Jaeger, Grafana Cloud, SigNoz, etc.) without changing any existing logging code.

## Installation

```bash
pip install simple-log-factory-ext-otel
```

Or with [UV](https://docs.astral.sh/uv/):

```bash
uv add simple-log-factory-ext-otel
```

## Quick Start

### Pattern 1 — Logs Only

```python
from simple_log_factory import log_factory
from simple_log_factory_ext_otel import OtelLogHandler

# 1. Initialize the handler
otel_handler = OtelLogHandler(
    service_name="my-service",
    endpoint="http://localhost:4317",
)

# 2. Pass it to log_factory — done
logger = log_factory(
    __name__,
    custom_handlers=[otel_handler],
)

logger.info("This goes to console AND to your OTel backend")

# 3. Clean shutdown (optional but recommended)
otel_handler.shutdown()
```

### Pattern 2 — All-in-One with `otel_log_factory()`

```python
from simple_log_factory_ext_otel import otel_log_factory

# One call — creates logger, OTel handler, and tracer
traced = otel_log_factory(
    service_name="my-service",
    otel_exporter_endpoint="http://localhost:4318",
)

# Logging works immediately
traced.info("Service started")

# Spans are ready too
with traced.span("process-order", attributes={"order.id": "123"}):
    traced.info("Processing order")

# Subsequent calls with the same endpoint/service/log_name return the
# cached instance (cache_logger=True by default)
same_traced = otel_log_factory(
    service_name="my-service",
    otel_exporter_endpoint="http://localhost:4318",
)
assert same_traced is traced

# Different service names or endpoints get independent loggers
payments_traced = otel_log_factory(
    service_name="payment-service",
    otel_exporter_endpoint="http://localhost:4318",
)
```

### Pattern 3 — Logs + Tracing with `setup_otel()`

```python
from simple_log_factory import log_factory
from simple_log_factory_ext_otel import setup_otel, TracedLogger

# 1. One-call setup — creates both log handler and tracer
#    with a shared Resource; registers TracerProvider globally
handler, otel_tracer = setup_otel(
    service_name="my-service",
    endpoint="http://localhost:4317",
)

# 2. Create a logger with the OTel handler
logger = log_factory(__name__, custom_handlers=[handler])

# 3. Wrap with TracedLogger for span support
traced = TracedLogger(logger=logger, tracer=otel_tracer.tracer)

# 4. Use span() to create correlated spans
with traced.span("process-order", attributes={"order.id": "123"}):
    traced.info("Processing order")   # auto-correlated with the span
    # ... your business logic ...

# 5. Or use @trace() as a decorator
@traced.trace("fetch-user")
def fetch_user(user_id: int) -> dict:
    traced.info("Fetching user %d", user_id)
    return {"id": user_id, "name": "Alice"}

fetch_user(42)
```

## Configuration

### `OtelLogHandler` Parameters

| Parameter               | Type             | Default                 | Description                                     |
|-------------------------|------------------|-------------------------|-------------------------------------------------|
| `service_name`          | `str`            | *(required)*            | Logical name of the service emitting logs       |
| `endpoint`              | `str`            | `http://localhost:4317` | OTLP receiver endpoint                          |
| `protocol`              | `str`            | `"grpc"`                | Transport protocol — `"grpc"` or `"http"`       |
| `insecure`              | `bool`           | `True`                  | Use plaintext (insecure) connection             |
| `headers`               | `Dict[str, str]` | `None`                  | Metadata headers sent with every export request |
| `resource_attributes`   | `Dict[str, str]` | `None`                  | Extra OTel Resource attributes                  |
| `log_level`             | `int`            | `logging.NOTSET`        | Minimum severity forwarded to the OTel pipeline |
| `export_timeout_millis` | `int`            | `30000`                 | Timeout in ms for each export batch             |

### Using HTTP Instead of gRPC

```python
from simple_log_factory_ext_otel import OtelLogHandler

handler = OtelLogHandler(
    service_name="my-service",
    endpoint="http://localhost:4318/v1/logs",
    protocol="http",
)
```

### Custom Resource Attributes

```python
from simple_log_factory_ext_otel import OtelLogHandler

handler = OtelLogHandler(
    service_name="my-service",
    resource_attributes={
        "deployment.environment": "production",
        "service.version": "1.2.3",
    },
)
```

### Authenticated Endpoints

```python
from simple_log_factory_ext_otel import OtelLogHandler

handler = OtelLogHandler(
    service_name="my-service",
    endpoint="https://otel.example.com:4317",
    insecure=False,
    headers={"Authorization": "Bearer <token>"},
)
```

### Level Filtering

Only export warnings and above to your OTel backend:

```python
import logging

from simple_log_factory_ext_otel import OtelLogHandler

handler = OtelLogHandler(
    service_name="my-service",
    log_level=logging.WARNING,
)
```

### `TracedLogger` API

`TracedLogger` wraps a standard `logging.Logger` and an OTel `Tracer`:

- **`span(name, attributes)`** — context manager that creates an OTel span. Logs inside the block are auto-correlated.
- **`trace(name, attributes)`** — decorator that wraps a function in a span. Exceptions are recorded on the span and re-raised.
- **`debug/info/warning/error/exception/critical/log`** — proxy to the underlying logger.
- **`logger` / `tracer`** properties — escape hatches for direct access.

### `setup_otel()` Parameters

| Parameter               | Type             | Default                 | Description                                      |
|-------------------------|------------------|-------------------------|--------------------------------------------------|
| `service_name`          | `str`            | *(required)*            | Logical name of the service                      |
| `endpoint`              | `str`            | `http://localhost:4317` | OTLP receiver endpoint                           |
| `protocol`              | `str`            | `"grpc"`                | Transport protocol — `"grpc"` or `"http"`        |
| `insecure`              | `bool`           | `True`                  | Use plaintext (insecure) connection              |
| `headers`               | `Dict[str, str]` | `None`                  | Metadata headers sent with every export request  |
| `resource_attributes`   | `Dict[str, str]` | `None`                  | Extra OTel Resource attributes                   |
| `export_timeout_millis` | `int`            | `30000`                 | Timeout in ms for each export batch              |
| `log_level`             | `int`            | `logging.NOTSET`        | Minimum severity forwarded to the OTel pipeline  |

Returns a `(OtelLogHandler, OtelTracer)` tuple. The `TracerProvider` is registered globally so auto-instrumentation libraries (FastAPI, psycopg2, etc.) share the same provider.

### `otel_log_factory()` Parameters

| Parameter           | Type   | Default        | Description                                                                 |
|---------------------|--------|----------------|-----------------------------------------------------------------------------|
| `service_name`      | `str`  | *(required)*   | Logical name of the service                                                 |
| `otel_exporter_endpoint`| `str`  | *(required)*   | Base URL of the OTel collector (e.g. `http://localhost:4318`)               |
| `log_name`          | `str`  | `service_name` | Name passed to `log_factory`. Defaults to `service_name` when `None`        |
| `cache_logger`      | `bool` | `True`         | Cache and reuse the logger for the same endpoint/service/log-name combo     |
| `use_http_protocol` | `bool` | `True`         | `True` for HTTP (appends `/v1/logs` and `/v1/traces`), `False` for gRPC    |
| `**kwargs`          |        |                | Extra keyword arguments forwarded to `simple_log_factory.log_factory`       |

Returns a `TracedLogger` with both logging and tracing configured. The `TracerProvider` is registered globally. Loggers are cached by the composite key `(otel_exporter_endpoint, service_name, log_name)`, so different services or endpoints get independent loggers.

## How It Works

`OtelLogHandler` extends `logging.Handler` directly (not OTel's `LoggingHandler`) and internally composes the OTel pipeline:

```
Your code
  └─► log_factory (attaches handler, sets formatter & level)
        └─► OtelLogHandler.emit(record)
              └─► Internal OTel LoggingHandler (LogRecord → OTel translation)
                    └─► BatchLogRecordProcessor
                          └─► OTLPLogExporter (gRPC or HTTP)
                                └─► OTel Collector / Backend
```

This composition pattern is critical: `log_factory` calls `setFormatter()` and `setLevel()` on every handler it receives. If we inherited from OTel's `LoggingHandler`, the factory's formatter would overwrite OTel's internal translation. By wrapping it, both pipelines stay independent.

### Trace Context Correlation

When using `setup_otel()` or sharing a `Resource` between `OtelLogHandler` and `OtelTracer`, span and trace IDs are automatically attached to log records emitted inside active spans. No extra configuration needed.

## Lifecycle Management

The handler registers an `atexit` hook to flush and shut down on interpreter exit. For explicit control:

```python
# Force-flush buffered records
otel_handler.flush()

# Graceful shutdown (idempotent, safe to call multiple times)
otel_handler.shutdown()
```

## Local Development

Create a virtual environment with [UV](https://docs.astral.sh/uv/):

```bash
uv venv
uv pip install -e ".[dev]"
```

Run tests:

```bash
pytest --cov=simple_log_factory_ext_otel --cov-report=term-missing
```

Run linters:

```bash
black --check .
isort --check .
ruff check .
mypy simple_log_factory_ext_otel
```

## License

GPL-3.0 — see [LICENSE.md](LICENSE.md) for details.

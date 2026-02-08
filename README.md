# simple-log-factory-ext-otel

OpenTelemetry log handler plugin for [simple_log_factory](https://github.com/raccoon/simple-log-factory).

Ship your log messages to any OpenTelemetry-compatible backend (Tempo, Jaeger, Grafana Cloud, SigNoz, etc.) without changing any existing logging code.

## Installation

```bash
pip install simple-log-factory-ext-otel
```

Or with [UV](https://docs.astral.sh/uv/):

```bash
uv add simple-log-factory-ext-otel
```

## Quick Start

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

If you're using OpenTelemetry tracing, span and trace IDs are automatically attached to log records. No extra configuration needed.

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

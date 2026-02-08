"""Default constants for the OTel log handler plugin."""

DEFAULT_ENDPOINT = "http://localhost:4317"
DEFAULT_PROTOCOL = "grpc"
DEFAULT_EXPORT_TIMEOUT_MILLIS = 30_000

VALID_PROTOCOLS = frozenset({"grpc", "http"})

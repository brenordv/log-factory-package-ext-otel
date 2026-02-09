"""Unit tests for the shared Resource creation helper."""

from __future__ import annotations

from opentelemetry.sdk.resources import Resource

from simple_log_factory_ext_otel._resource import create_resource


class TestCreateResource:
    """Tests for create_resource()."""

    def test_service_name_is_set(self) -> None:
        resource = create_resource("my-service")
        assert resource.attributes["service.name"] == "my-service"

    def test_returns_resource_instance(self) -> None:
        resource = create_resource("svc")
        assert isinstance(resource, Resource)

    def test_custom_attributes_merged(self) -> None:
        resource = create_resource(
            "svc",
            resource_attributes={"deployment.environment": "staging", "team": "platform"},
        )
        attrs = dict(resource.attributes)
        assert attrs["service.name"] == "svc"
        assert attrs["deployment.environment"] == "staging"
        assert attrs["team"] == "platform"

    def test_none_attributes_ignored(self) -> None:
        resource = create_resource("svc", resource_attributes=None)
        assert resource.attributes["service.name"] == "svc"

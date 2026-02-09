"""Shared OTel Resource creation helper."""

from __future__ import annotations

from opentelemetry.sdk.resources import Resource


def create_resource(
    service_name: str,
    resource_attributes: dict[str, str] | None = None,
) -> Resource:
    """Create an OTel ``Resource`` with the given service name and optional attributes.

    Args:
        service_name: Logical name of the service (sets ``service.name``).
        resource_attributes: Extra key/value pairs merged into the resource.

    Returns:
        A configured ``Resource`` instance.
    """
    attributes: dict[str, str] = {"service.name": service_name}
    if resource_attributes:
        attributes.update(resource_attributes)
    return Resource.create(attributes)

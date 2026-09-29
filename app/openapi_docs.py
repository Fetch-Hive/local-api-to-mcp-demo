"""Descriptions for OpenAPI fields that FastAPI generates itself."""

from __future__ import annotations

SCHEMA_DESCRIPTIONS = {
    "HTTPValidationError": (
        "The request body or a path parameter failed validation. "
        "Each item in detail names the field and the reason it was rejected."
    ),
    "ValidationError": "One value that failed validation.",
}

FIELD_DESCRIPTIONS = {
    ("HTTPValidationError", "detail"): (
        "List of validation problems. Each item names the field and the reason the value was rejected."
    ),
    ("ValidationError", "loc"): (
        "Path to the field that failed validation, for example ['body', 'title']."
    ),
    ("ValidationError", "msg"): "Human-readable reason the value was rejected.",
    ("ValidationError", "type"): (
        "Machine-readable validation error type, for example missing or string_too_short."
    ),
    ("ValidationError", "input"): "The value that failed validation.",
    ("ValidationError", "ctx"): (
        "Extra values that explain the constraint, such as a minimum length."
    ),
}


def apply_field_descriptions(schema: dict) -> None:
    components = schema.get("components", {}).get("schemas", {})
    for name, component in components.items():
        if not isinstance(component, dict):
            continue
        if "description" not in component and name in SCHEMA_DESCRIPTIONS:
            component["description"] = SCHEMA_DESCRIPTIONS[name]
        properties = component.get("properties")
        if not isinstance(properties, dict):
            continue
        for prop, details in properties.items():
            if not isinstance(details, dict) or "description" in details:
                continue
            text = FIELD_DESCRIPTIONS.get((name, prop))
            if text:
                details["description"] = text

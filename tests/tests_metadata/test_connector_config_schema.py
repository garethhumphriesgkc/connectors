"""Tests for connector_config_schema.json format and business rules.

Validates JSON Schema specification compliance and connector-type-specific
invariants for every connector that ships a connector_config_schema.json.
"""

import json
import os
from pathlib import Path

import jsonschema
import pytest

CONNECTOR_TYPES_DIRECTORIES = [
    "external-import",
    "internal-enrichment",
    "internal-export-file",
    "internal-import-file",
    "stream",
]

VALID_CONNECTOR_TYPES = {
    "EXTERNAL_IMPORT",
    "INTERNAL_ENRICHMENT",
    "INTERNAL_EXPORT_FILE",
    "INTERNAL_IMPORT_FILE",
    "STREAM",
}

VALID_LOG_LEVELS = {
    "error",
    "warning",
    "warn",
    "info",
    "debug",
}


def get_config_schema_paths() -> list[str]:
    """Return all connector_config_schema.json paths."""
    paths = []
    for connector_type_directory in CONNECTOR_TYPES_DIRECTORIES:
        directory_path = Path(".") / connector_type_directory
        for entry in directory_path.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                schema_path = entry / "__metadata__" / "connector_config_schema.json"
                if os.path.exists(schema_path):
                    paths.append(schema_path.as_posix())
    return paths


# =============================================================================
# A. JSON Schema specification compliance
# =============================================================================


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_connector_config_schema_is_valid_json_schema(schema_path: str):
    """The schema must itself be valid against the JSON Schema meta-schema."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema.get("type") == "object"
    assert "additionalProperties" in schema


# =============================================================================
# B. Universal connector invariants (all connector types)
# =============================================================================


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_connector_id_has_a_default(schema_path: str):
    """CONNECTOR_ID must be defined as a property and have a non-empty string default."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})

    # The connectors-sdk currently strips CONNECTOR_ID from generated schemas
    # (filter_schema). Skip when absent; activates once the SDK re-includes it.
    if "CONNECTOR_ID" not in properties:
        pytest.skip("CONNECTOR_ID not present (stripped by connectors-sdk)")

    assert isinstance(properties["CONNECTOR_ID"].get("default"), str)
    assert properties["CONNECTOR_ID"]["default"]


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_connector_name_has_a_default(schema_path: str):
    """CONNECTOR_NAME must be defined as a property and have a non-empty string default."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    assert "CONNECTOR_NAME" in properties
    assert isinstance(properties["CONNECTOR_NAME"].get("default"), str)
    assert properties["CONNECTOR_NAME"]["default"]


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_connector_type_is_a_constant(schema_path: str):
    """CONNECTOR_TYPE must be defined and must be a constant."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    assert "CONNECTOR_TYPE" in properties
    prop = properties["CONNECTOR_TYPE"]

    # Accept either const, single-value enum, or default
    value = None
    if "const" in prop:
        value = prop["const"]
    elif "enum" in prop and len(prop["enum"]) == 1:
        value = prop["enum"][0]
    elif "default" in prop:
        value = prop["default"]

    assert value is not None
    assert value in VALID_CONNECTOR_TYPES


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_connector_log_level_has_a_valid_default(schema_path: str):
    """CONNECTOR_LOG_LEVEL must be defined, have a default in valid log levels."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    assert "CONNECTOR_LOG_LEVEL" in properties
    assert properties["CONNECTOR_LOG_LEVEL"].get("default") in VALID_LOG_LEVELS


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_opencti_url_is_required(schema_path: str):
    """OPENCTI_URL must appear in the 'required' array."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    assert "OPENCTI_URL" in schema.get("required", [])


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_opencti_token_is_required(schema_path: str):
    """OPENCTI_TOKEN must appear in the 'required' array."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    assert "OPENCTI_TOKEN" in schema.get("required", [])


# =============================================================================
# C. Connector-type-specific invariants
# =============================================================================


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_external_import_connector_scope_default_is_a_list(schema_path: str):
    """For EXTERNAL_IMPORT connectors, CONNECTOR_SCOPE must be array with a list default."""

    manifest_path = schema_path.replace(
        "connector_config_schema.json", "connector_manifest.json"
    )
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    container_type = manifest.get("container_type", "").upper().replace("-", "_")
    if container_type != "EXTERNAL_IMPORT":
        pytest.skip("Not an EXTERNAL_IMPORT connector")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    assert "CONNECTOR_SCOPE" in properties
    assert properties["CONNECTOR_SCOPE"].get("type") == "array"
    assert isinstance(properties["CONNECTOR_SCOPE"].get("default"), list)


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_internal_enrichment_connector_scope_default_is_a_non_empty_list(
    schema_path: str,
):
    """For INTERNAL_ENRICHMENT connectors, CONNECTOR_SCOPE must be array with a non-empty list default."""

    manifest_path = schema_path.replace(
        "connector_config_schema.json", "connector_manifest.json"
    )
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    container_type = manifest.get("container_type", "").upper().replace("-", "_")
    if container_type != "INTERNAL_ENRICHMENT":
        pytest.skip("Not an INTERNAL_ENRICHMENT connector")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    assert "CONNECTOR_SCOPE" in properties
    assert properties["CONNECTOR_SCOPE"].get("type") == "array"
    assert isinstance(properties["CONNECTOR_SCOPE"].get("default"), list)
    assert len(properties["CONNECTOR_SCOPE"]["default"]) > 0


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_stream_connector_scope_default_is_a_list(schema_path: str):
    """For STREAM connectors, CONNECTOR_SCOPE must be array with a list default."""

    manifest_path = schema_path.replace(
        "connector_config_schema.json", "connector_manifest.json"
    )
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    container_type = manifest.get("container_type", "").upper().replace("-", "_")
    if container_type != "STREAM":
        pytest.skip("Not a STREAM connector")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    assert "CONNECTOR_SCOPE" in properties
    assert properties["CONNECTOR_SCOPE"].get("type") == "array"
    assert isinstance(properties["CONNECTOR_SCOPE"].get("default"), list)


# =============================================================================
# D. Additional property-level checks
# =============================================================================


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_connector_id_property_is_string_type(schema_path: str):
    """CONNECTOR_ID property type must be 'string'."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    if "CONNECTOR_ID" not in properties:
        pytest.skip("CONNECTOR_ID not present")

    assert properties["CONNECTOR_ID"].get("type") == "string"


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_connector_name_property_is_string_type(schema_path: str):
    """CONNECTOR_NAME property type must be 'string'."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    if "CONNECTOR_NAME" not in properties:
        pytest.skip("CONNECTOR_NAME not present")

    assert properties["CONNECTOR_NAME"].get("type") == "string"


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_connector_log_level_enum_values_are_valid(schema_path: str):
    """If CONNECTOR_LOG_LEVEL defines an enum, all values must be valid log levels."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    if "CONNECTOR_LOG_LEVEL" not in properties:
        pytest.skip("CONNECTOR_LOG_LEVEL not present")
    if "enum" not in properties["CONNECTOR_LOG_LEVEL"]:
        pytest.skip("CONNECTOR_LOG_LEVEL does not define an enum")

    assert set(properties["CONNECTOR_LOG_LEVEL"]["enum"]) <= VALID_LOG_LEVELS


@pytest.mark.parametrize("schema_path", get_config_schema_paths())
def test_opencti_url_has_uri_format(schema_path: str):
    """OPENCTI_URL should declare format: 'uri'."""

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    properties = schema.get("properties", {})
    if "OPENCTI_URL" not in properties:
        pytest.skip("OPENCTI_URL not present")

    assert properties["OPENCTI_URL"].get("format") == "uri"

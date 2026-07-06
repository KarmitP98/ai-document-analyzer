"""
Comprehensive tests for locations_build_url.py module.

Tests the URL building classes, marshmallow schemas, and URL encoding
for Bing Maps location services.
"""

import pytest
from marshmallow import ValidationError

from classes.locations_build_url import (
    Location,
    LocationByQuerySchema,
    LocationByQueryUrl,
    LocationUrl,
)


def test_location_url_protocol_http():
    """Test LocationUrl protocol property with HTTP."""
    data = {"q": "test", "key": "test123"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.protocol == "http:/"


def test_location_url_protocol_https():
    """Test LocationUrl protocol property with HTTPS."""
    data = {"q": "test", "key": "test123"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "https", schema)
    assert url.protocol == "https:/"


def test_location_url_main_url():
    """Test LocationUrl main_url property."""
    data = {"q": "test", "key": "test123"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.main_url == "dev.virtualearth.net"


def test_location_url_rest():
    """Test LocationUrl rest property."""
    data = {"q": "test", "key": "test123"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.rest == "REST"


def test_location_url_version():
    """Test LocationUrl version property."""
    data = {"q": "test", "key": "test123", "version": "v1"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.version == "v1"


def test_location_url_version_none():
    """Test LocationUrl version property when None."""
    data = {"q": "test", "key": "test123"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.version == "v1"


def test_location_url_rest_api():
    """Test LocationUrl restApi property."""
    data = {"q": "test", "key": "test123", "restApi": "Locations"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.restApi == "Locations"


def test_location_url_rest_api_none():
    """Test LocationUrl restApi property when None."""
    data = {"q": "test", "key": "test123"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.restApi == "Locations"


def test_location_url_resource_path():
    """Test LocationUrl resourcePath property."""
    data = {"q": "test", "key": "test123", "resourcePath": "US/WA/Seattle"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.resourcePath == "US/WA/Seattle"


def test_location_url_resource_path_none():
    """Test LocationUrl resourcePath property when None."""
    data = {"q": "test", "key": "test123"}
    schema = LocationByQuerySchema()
    url = LocationUrl(data, "http", schema)
    assert url.resourcePath is None


def test_location_schema_defaults():
    """Test Location schema applies default values."""
    schema = Location()
    result = schema.dump({})

    assert result["version"] == "v1"
    assert result["restApi"] == "Locations"


def test_location_schema_custom_version():
    """Test Location schema with custom version."""
    schema = Location()
    result = schema.dump({"version": "v2"})

    assert result["version"] == "v2"


def test_location_schema_custom_rest_api():
    """Test Location schema with custom restApi."""
    schema = Location()
    result = schema.dump({"restApi": "CustomApi"})

    assert result["restApi"] == "CustomApi"


def test_location_schema_resource_path():
    """Test Location schema with resourcePath."""
    schema = Location()
    result = schema.dump({"resourcePath": "US/CA/LosAngeles"})

    assert result["resourcePath"] == "US/CA/LosAngeles"


def test_location_by_query_schema_required_q():
    """Test LocationByQuerySchema requires q field."""
    schema = LocationByQuerySchema()

    with pytest.raises(ValidationError) as exc_info:
        schema.load({"key": "test123"})

    assert "q" in str(exc_info.value)


def test_location_by_query_schema_required_key():
    """Test LocationByQuerySchema requires key field."""
    schema = LocationByQuerySchema()

    with pytest.raises(ValidationError) as exc_info:
        schema.load({"q": "Space Needle"})

    assert "key" in str(exc_info.value)


def test_location_by_query_schema_defaults():
    """Test LocationByQuerySchema applies default values."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Space Needle", "key": "test123"})

    assert result["version"] == "v1"
    assert result["restApi"] == "Locations"
    assert "query" in result
    assert "includeNeighborhood=0" in result["query"]
    assert "include=ciso2" in result["query"]
    assert "maxResults=20" in result["query"]


def test_location_by_query_schema_custom_include_neighborhood():
    """Test LocationByQuerySchema with custom includeNeighborhood."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Space Needle", "key": "test123", "includeNeighborhood": 1})

    assert "includeNeighborhood=1" in result["query"]


def test_location_by_query_schema_custom_include():
    """Test LocationByQuerySchema with custom include."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Space Needle", "key": "test123", "include": "queryParse"})

    assert "include=queryParse" in result["query"]


def test_location_by_query_schema_custom_max_results():
    """Test LocationByQuerySchema with custom maxResults."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Space Needle", "key": "test123", "maxResults": 50})

    assert "maxResults=50" in result["query"]


def test_location_by_query_schema_culture():
    """Test LocationByQuerySchema with culture parameter."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Space Needle", "key": "test123", "c": "en-US"})

    assert "c=en-US" in result["query"]


def test_location_by_query_schema_output_format():
    """Test LocationByQuerySchema with output format parameter."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Space Needle", "key": "test123", "o": "xml"})

    assert "o=xml" in result["query"]


def test_location_by_query_schema_url_encoding_space():
    """Test LocationByQuerySchema URL encodes spaces."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Space Needle Seattle", "key": "test123"})

    assert "query" in result
    assert "%20" in result["query"]


def test_location_by_query_schema_url_encoding_comma():
    """Test LocationByQuerySchema URL encodes commas."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Seattle, WA", "key": "test123"})

    assert "query" in result
    assert "%2C" in result["query"]


def test_location_by_query_schema_url_encoding_special_chars():
    """Test LocationByQuerySchema URL encodes special characters."""
    schema = LocationByQuerySchema()
    result = schema.dump({"q": "Café & Restaurant", "key": "test123"})

    assert "query" in result
    assert "%C3%A9" in result["query"]


def test_location_by_query_url_init():
    """Test LocationByQueryUrl initialization."""
    data = {"q": "Space Needle", "key": "test123"}
    url = LocationByQueryUrl(data, "http")

    assert url.protocol == "http:/"
    assert url.main_url == "dev.virtualearth.net"
    assert url.version == "v1"


def test_location_by_query_url_query_property():
    """Test LocationByQueryUrl query property returns formatted query string."""
    data = {"q": "Space Needle", "key": "test123"}
    url = LocationByQueryUrl(data, "http")

    query = url.query

    assert query.startswith("?")
    assert "q=" in query
    assert "key=" in query


def test_location_by_query_url_full_url():
    """Test LocationByQueryUrl builds complete URL."""
    data = {"q": "Space Needle", "key": "test123"}
    url = LocationByQueryUrl(data, "http")

    full_url = url.protocol + url.main_url + "/" + url.rest + "/" + url.version + "/" + url.restApi + url.query

    assert "http:/" in full_url
    assert "dev.virtualearth.net" in full_url
    assert "REST" in full_url
    assert "v1" in full_url
    assert "Locations" in full_url
    assert "?" in full_url
    assert "q=" in full_url


def test_location_by_query_url_https():
    """Test LocationByQueryUrl with HTTPS."""
    data = {"q": "Space Needle", "key": "test123"}
    url = LocationByQueryUrl(data, "https")

    assert url.protocol == "https:/"


def test_location_by_query_url_custom_max_results():
    """Test LocationByQueryUrl with custom maxResults."""
    data = {"q": "Space Needle", "key": "test123", "maxResults": 50}
    url = LocationByQueryUrl(data, "http")

    query = url.query

    assert "maxResults=50" in query


def test_location_by_query_url_all_parameters():
    """Test LocationByQueryUrl with all optional parameters."""
    data = {
        "q": "Space Needle",
        "key": "test123",
        "includeNeighborhood": 1,
        "include": "queryParse",
        "c": "en-US",
        "o": "xml",
        "maxResults": 30,
    }
    url = LocationByQueryUrl(data, "http")

    query = url.query

    assert "includeNeighborhood=1" in query
    assert "include=queryParse" in query
    assert "c=en-US" in query
    assert "o=xml" in query
    assert "maxResults=30" in query


def test_location_by_query_url_resource_path():
    """Test LocationByQueryUrl with resourcePath."""
    data = {"q": "Space Needle", "key": "test123", "resourcePath": "US/WA"}
    url = LocationByQueryUrl(data, "http")

    assert url.resourcePath == "US/WA"


def test_location_schema_field_ordering():
    """Test Location schema maintains field order."""
    schema = Location()
    result = schema.dump({"version": "v1", "restApi": "Locations", "resourcePath": "US"})

    keys = list(result.keys())
    assert keys.index("version") < keys.index("restApi")
    assert keys.index("restApi") < keys.index("resourcePath")


def test_location_by_query_schema_load_and_dump():
    """Test LocationByQuerySchema load and dump roundtrip."""
    schema = LocationByQuerySchema()
    input_data = {"q": "Space Needle, Seattle", "key": "test123"}

    loaded = schema.load(input_data)
    assert loaded["q"] == "Space Needle, Seattle"
    assert loaded["key"] == "test123"

    dumped = schema.dump(loaded)
    assert "query" in dumped
    assert "q=" in dumped["query"]


def test_location_by_query_schema_empty_q():
    """Test LocationByQuerySchema with empty q field validates correctly."""
    schema = LocationByQuerySchema()
    result = schema.load({"q": "", "key": "test123"})
    assert result["q"] == ""


def test_location_by_query_schema_empty_key():
    """Test LocationByQuerySchema with empty key field validates correctly."""
    schema = LocationByQuerySchema()
    result = schema.load({"q": "Space Needle", "key": ""})
    assert result["key"] == ""


def test_location_by_query_url_with_version():
    """Test LocationByQueryUrl with custom version."""
    data = {"q": "Space Needle", "key": "test123", "version": "v2"}
    url = LocationByQueryUrl(data, "http")

    assert url.version == "v2"

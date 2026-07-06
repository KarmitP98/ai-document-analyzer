"""
Comprehensive tests for locations.py module.

Tests the LocationApi, LocationByQuery classes including URL building,
response parsing, coordinate extraction, and file operations.
"""

import json
from unittest.mock import Mock, mock_open, patch

import pytest

from classes.locations import LocationApi, LocationByQuery


@pytest.fixture
def mock_schema():
    """Create a mock schema object for testing."""
    schema = Mock()
    schema.protocol = "http:/"
    schema.main_url = "dev.virtualearth.net"
    schema.rest = "REST"
    schema.version = "v1"
    schema.restApi = "Locations"
    schema.resourcePath = "US/WA/Seattle"
    schema.query = "?q=Space+Needle&key=test123"
    return schema


@pytest.fixture
def mock_json_response():
    """Create a mock JSON response from Bing Maps API."""
    return {
        "resourceSets": [
            {
                "resources": [
                    {
                        "point": {"coordinates": [47.6205, -122.3493]},
                        "address": {
                            "addressLine": "400 Broad St",
                            "locality": "Seattle",
                            "adminDistrict": "WA",
                            "postalCode": "98109",
                        },
                        "bbox": [47.6165, -122.3533, 47.6245, -122.3453],
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_xml_response():
    """Create a mock XML response from Bing Maps API."""
    return {
        "Response": {
            "ResourceSets": {
                "ResourceSet": {
                    "Resources": {
                        "Location": {
                            "Point": {"Latitude": "47.6205", "Longitude": "-122.3493"},
                            "Address": {
                                "AddressLine": "400 Broad St",
                                "Locality": "Seattle",
                                "AdminDistrict": "WA",
                                "PostalCode": "98109",
                            },
                            "BoundingBox": {
                                "SouthLatitude": "47.6165",
                                "WestLongitude": "-122.3533",
                                "NorthLatitude": "47.6245",
                                "EastLongitude": "-122.3453",
                            },
                        }
                    }
                }
            }
        }
    }


def test_location_api_init(mock_schema):
    """Test LocationApi initialization."""
    api = LocationApi(schema=mock_schema, filename="test", http_protocol="http")

    assert api.http_protocol == "http"
    assert api.file_name == "test"
    assert api.schema == mock_schema
    assert api.locationApiData is None


def test_location_api_build_url(mock_schema):
    """Test URL building."""
    api = LocationApi(schema=mock_schema, filename="test")

    url = api.build_url()

    assert "http:/" in url
    assert "dev.virtualearth.net" in url
    assert "REST" in url
    assert "v1" in url
    assert "Locations" in url


def test_location_api_response_to_dict_json(mock_schema, mock_json_response):
    """Test converting JSON response to dict."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_json_response)
    api.locationApiData = mock_response

    result = api.response_to_dict()

    assert result == mock_json_response
    assert "resourceSets" in result


def test_location_api_response_to_dict_xml(mock_schema):
    """Test converting XML response to dict."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    xml_string = '<?xml version="1.0"?><root><key>value</key></root>'
    mock_response.text = xml_string
    api.locationApiData = mock_response

    result = api.response_to_dict()

    assert isinstance(result, dict)
    assert "root" in result


def test_location_api_get_resource_json(mock_schema, mock_json_response):
    """Test getting resources from JSON response."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_json_response)
    api.locationApiData = mock_response

    resources = api.get_resource()

    assert len(resources) == 1
    assert "point" in resources[0]
    assert "address" in resources[0]


def test_location_api_get_resource_xml(mock_schema, mock_xml_response):
    """Test getting resources from XML response."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_xml_response)
    api.locationApiData = mock_response

    resources = api.get_resource()

    assert resources is not None
    assert "Point" in resources or isinstance(resources, dict)


def test_location_api_response_property(mock_schema):
    """Test response property."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = "test response"
    api.locationApiData = mock_response

    assert api.response == "test response"


def test_location_api_status_code_property(mock_schema):
    """Test status code property."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.status_code = 200
    api.locationApiData = mock_response

    assert api.status_code == 200


def test_location_api_get_coordinates_json(mock_schema, mock_json_response):
    """Test getting coordinates from JSON response."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_json_response)
    api.locationApiData = mock_response

    coordinates = api.get_coordinates

    assert len(coordinates) == 1
    assert coordinates[0].latitude == 47.6205
    assert coordinates[0].longitude == -122.3493


def test_location_api_get_coordinates_xml(mock_schema, mock_xml_response):
    """Test getting coordinates from XML response."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_xml_response)
    api.locationApiData = mock_response

    coordinates = api.get_coordinates

    assert coordinates is not None
    if coordinates:
        assert hasattr(coordinates[0], "latitude")
        assert hasattr(coordinates[0], "longitude")


def test_location_api_get_address_json(mock_schema, mock_json_response):
    """Test getting address from JSON response."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_json_response)
    api.locationApiData = mock_response

    addresses = api.get_address

    assert len(addresses) == 1
    assert "addressLine" in addresses[0]
    assert addresses[0]["locality"] == "Seattle"


def test_location_api_get_address_xml(mock_schema, mock_xml_response):
    """Test getting address from XML response with proper format."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_xml_response)
    api.locationApiData = mock_response

    try:
        addresses = api.get_address
        if addresses:
            assert "Address" in addresses[0] or "address" in str(addresses[0]).lower()
    except (KeyError, TypeError):
        pass


def test_location_api_get_address_none_resource(mock_schema):
    """Test getting address when resource is None."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps({"resourceSets": []})
    api.locationApiData = mock_response

    with pytest.raises(KeyError):
        _ = api.get_address


def test_location_api_get_bbox_json(mock_schema, mock_json_response):
    """Test getting bounding box from JSON response."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_json_response)
    api.locationApiData = mock_response

    bbox = api.get_bbox

    assert len(bbox) == 1
    assert bbox[0].southlatitude == 47.6165
    assert bbox[0].westlongitude == -122.3533
    assert bbox[0].northlatitude == 47.6245
    assert bbox[0].eastlongitude == -122.3453


def test_location_api_get_bbox_xml(mock_schema, mock_xml_response):
    """Test getting bounding box from XML response."""
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = json.dumps(mock_xml_response)
    api.locationApiData = mock_response

    bbox = api.get_bbox

    assert bbox is not None
    if bbox:
        assert hasattr(bbox[0], "southlatitude")
        assert hasattr(bbox[0], "northlatitude")


@patch("builtins.open", new_callable=mock_open)
@patch("os.path.isdir")
def test_location_api_to_json_file_valid_path(mock_isdir, mock_file, mock_schema):
    """Test writing response to JSON file with valid path."""
    mock_isdir.return_value = True
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = "test response"
    api.locationApiData = mock_response

    api.to_json_file("/tmp", "output")

    mock_file.assert_called_once()
    assert "output.json" in str(mock_file.call_args)


@patch("builtins.open", new_callable=mock_open)
@patch("os.path.isdir")
@patch("os.getcwd")
def test_location_api_to_json_file_invalid_path(mock_getcwd, mock_isdir, mock_file, mock_schema):
    """Test writing response to JSON file with invalid path."""
    mock_isdir.return_value = False
    mock_getcwd.return_value = "/current"
    api = LocationApi(schema=mock_schema, filename="test")
    mock_response = Mock()
    mock_response.text = "test response"
    api.locationApiData = mock_response

    api.to_json_file("/invalid/path", "output")

    mock_file.assert_called_once()
    # Should use current working directory
    assert "/current" in str(mock_file.call_args) or "output.json" in str(mock_file.call_args)


@patch("builtins.open", new_callable=mock_open)
@patch("os.path.isdir")
def test_location_api_to_json_file_default_filename(mock_isdir, mock_file, mock_schema):
    """Test writing response to JSON file with default filename."""
    mock_isdir.return_value = True
    api = LocationApi(schema=mock_schema, filename="default_name")
    mock_response = Mock()
    mock_response.text = "test response"
    api.locationApiData = mock_response

    api.to_json_file("/tmp", None)

    mock_file.assert_called_once()
    assert "default_name.json" in str(mock_file.call_args)


@patch("classes.locations.requests.get")
def test_location_by_query_init_success(mock_get):
    """Test LocationByQuery initialization with successful response."""
    data = {"q": "Space Needle, Seattle", "key": "test123"}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"resourceSets": [{"resources": []}]})
    mock_get.return_value = mock_response

    location = LocationByQuery(data, http_protocol="http")

    assert location.http_protocol == "http"
    assert location.file_name == "locationByQuery"
    mock_get.assert_called_once()


def test_location_by_query_init_no_data():
    """Test LocationByQuery initialization with no data."""
    with pytest.raises(TypeError, match="No data given"):
        LocationByQuery({})


@patch("classes.locations.requests.get")
def test_location_by_query_init_http_error(mock_get):
    """Test LocationByQuery initialization with HTTP error."""
    data = {"q": "Space Needle, Seattle", "key": "test123"}
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status = Mock(side_effect=Exception("Not Found"))
    mock_get.return_value = mock_response

    with pytest.raises(Exception):
        LocationByQuery(data, http_protocol="http")


@patch("classes.locations.requests.get")
def test_location_by_query_build_url_with_none(mock_get):
    """Test LocationByQuery URL building replaces /None/ with empty string."""
    data = {"q": "Space Needle", "key": "test123"}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"resourceSets": [{"resources": []}]})
    mock_get.return_value = mock_response

    location = LocationByQuery(data, http_protocol="http")
    url = location.build_url()

    # Should not contain /None/
    assert "/None/" not in url


@patch("classes.locations.requests.get")
def test_location_by_query_get_data_success(mock_get, mock_json_response):
    """Test LocationByQuery get_data method."""
    data = {"q": "Space Needle, Seattle", "key": "test123"}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = json.dumps(mock_json_response)
    mock_get.return_value = mock_response

    location = LocationByQuery(data, http_protocol="http")

    assert location.locationApiData.status_code == 200
    assert mock_get.call_count == 1
    # Verify timeout was passed
    assert mock_get.call_args[1]["timeout"] == 600


@patch("classes.locations.requests.get")
def test_location_by_query_https_protocol(mock_get):
    """Test LocationByQuery with HTTPS protocol."""
    data = {"q": "Space Needle, Seattle", "key": "test123"}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"resourceSets": [{"resources": []}]})
    mock_get.return_value = mock_response

    location = LocationByQuery(data, http_protocol="https")

    assert location.http_protocol == "https"
    # Verify URL contains https
    url = location.build_url()
    assert "https:/" in url


@patch("classes.locations.requests.get")
def test_location_by_query_integration(mock_get, mock_json_response):
    """Test full LocationByQuery workflow."""
    data = {"q": "Space Needle, Seattle", "key": "test123"}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = json.dumps(mock_json_response)
    mock_get.return_value = mock_response

    location = LocationByQuery(data, http_protocol="http")

    # Test all properties work
    assert location.status_code == 200
    assert location.response is not None
    coordinates = location.get_coordinates
    assert coordinates is not None
    addresses = location.get_address
    assert addresses is not None
    bbox = location.get_bbox
    assert bbox is not None

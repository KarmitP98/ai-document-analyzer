"""Unit tests for netx_connection module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from classes.src.netx_connection import (
    clean_up_attributes,
    extract_asset_attributes,
    get_asset_ids,
    get_auth_key,
    get_number_of_assets,
    get_root_folder_list,
    netx_api_get_assets,
)


@pytest.fixture
def mock_requests():
    """Mock requests module."""
    with patch("classes.src.netx_connection.requests") as mock:
        yield mock


def test_get_auth_key(mock_requests):
    """Test getting authentication key from NetX."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"sessionKey": "test-session-key-12345"}}
    mock_response.text = '{"result": {"sessionKey": "test-session-key-12345"}}'
    mock_requests.get.return_value = mock_response

    authkey = get_auth_key(url="https://netx.test.com/api", username="testuser", password="testpass")

    assert authkey == "test-session-key-12345"
    mock_requests.get.assert_called_once()


def test_get_auth_key_no_result(mock_requests):
    """Test getting auth key when no result returned."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "Invalid credentials"}
    mock_response.text = '{"error": "Invalid credentials"}'
    mock_requests.get.return_value = mock_response

    authkey = get_auth_key(url="https://netx.test.com/api", username="baduser", password="badpass")

    assert authkey is None


def test_get_root_folder_list(mock_requests):
    """Test getting root folder list."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "results": [
                {"id": "folder1", "base": "Folder 1", "children": {"assetCount": 10}},
                {"id": "folder2", "base": "Folder 2", "children": {"assetCount": 5}},
            ]
        }
    }
    mock_requests.get.return_value = mock_response

    folders = get_root_folder_list(folder_id="root", url="https://netx.test.com/api", authkey="test-key")

    assert len(folders) == 2
    assert folders[0]["id"] == "folder1"
    assert folders[1]["id"] == "folder2"


def test_get_number_of_assets(mock_requests):
    """Test getting total number of assets."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {"results": [{"children": {"assetCount": 10}}, {"children": {"assetCount": 15}}, {"children": {"assetCount": 5}}]}
    }
    mock_requests.get.return_value = mock_response

    total = get_number_of_assets(url="https://netx.test.com/api", authkey="test-key", folder_id_containing_assets="folder123")

    assert total == 30  # 10 + 15 + 5


def test_get_number_of_assets_empty_folder(mock_requests):
    """Test getting number of assets from empty folder."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"results": []}}
    mock_requests.get.return_value = mock_response

    total = get_number_of_assets(url="https://netx.test.com/api", authkey="test-key", folder_id_containing_assets="empty_folder")

    assert total == 0


def test_get_asset_ids(mock_requests):
    """Test getting asset IDs from folder."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "results": [
                {"id": "asset1", "base": "Asset 1"},
                {"id": "asset2", "base": "Asset 2"},
                {"id": "asset3", "base": "Asset 3"},
            ]
        }
    }
    mock_requests.get.return_value = mock_response

    asset_ids = get_asset_ids(url="https://netx.test.com/api", authkey="test-key", folder_id_containing_assets="folder123", number_of_assets=10)

    assert len(asset_ids) == 3
    assert asset_ids == ["asset1", "asset2", "asset3"]


def test_extract_asset_attributes(mock_requests):
    """Test extracting asset attributes."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": [
            {"id": "asset1", "attributes": {"title": "Test Asset 1", "description": "Description 1"}},
            {"id": "asset2", "attributes": {"title": "Test Asset 2", "description": "Description 2"}},
        ]
    }
    mock_requests.get.return_value = mock_response

    results = extract_asset_attributes(url="https://netx.test.com/api", authkey="test-key", asset_id_list=["asset1", "asset2"])

    assert len(results) == 2
    assert results[0]["id"] == "asset1"
    assert results[0]["attributes"]["title"] == "Test Asset 1"


def test_netx_api_get_assets(mock_requests):
    """Test complete workflow to get assets."""
    # Mock authentication
    auth_response = MagicMock()
    auth_response.json.return_value = {"result": {"sessionKey": "test-key"}}
    auth_response.text = '{"result": {"sessionKey": "test-key"}}'

    # Mock folder count
    folder_response = MagicMock()
    folder_response.json.return_value = {"result": {"results": [{"children": {"assetCount": 2}}]}}

    # Mock asset IDs
    ids_response = MagicMock()
    ids_response.json.return_value = {"result": {"results": [{"id": "asset1"}, {"id": "asset2"}]}}

    # Mock asset attributes
    attrs_response = MagicMock()
    attrs_response.json.return_value = {"result": [{"id": "asset1", "attributes": {}}, {"id": "asset2", "attributes": {}}]}

    mock_requests.get.side_effect = [auth_response, folder_response, ids_response, attrs_response]

    results = netx_api_get_assets(url="https://netx.test.com/api", username="user", password="pass", folder_id_containing_assets="folder123")

    assert len(results) == 2
    assert mock_requests.get.call_count == 4


def test_clean_up_attributes_program_type():
    """Test cleaning up program type attributes."""
    attributes = {
        "Performance Title": ["Romeo and Juliet"],
        "Choreographer": ["John Neumeier"],
        "Composer": ["Sergei Prokofiev"],
        "Donors": ["John Doe", "Jane Smith"],  # Should be removed for program type
    }

    cleaned = clean_up_attributes(attributes=attributes, asset_type="Program", remove_donor=True)

    assert "Performance Title" in cleaned
    assert "Choreographer" in cleaned
    assert "Composer" in cleaned
    assert "Donors" not in cleaned


def test_clean_up_attributes_donor_type():
    """Test cleaning up donor type attributes."""
    attributes = {
        "Performance Title": ["Romeo and Juliet"],  # Kept for donor type
        "Donors": ["John Doe", "Jane Smith"],
    }

    cleaned = clean_up_attributes(attributes=attributes, asset_type="Donors", remove_donor=False)

    assert "Donors" in cleaned
    # Performance Title is kept for donor type (only removed when remove_donor=True)
    assert "Performance Title" in cleaned
    # Asset Type is always added
    assert "Asset Type" in cleaned
    assert cleaned["Asset Type"] == ["Donors"]


def test_clean_up_attributes_company_type():
    """Test cleaning up company type attributes."""
    attributes = {
        "Performance Title": ["Show"],  # Kept for company type
        "Organization": ["Ballet Company"],
        "Staff": ["Director", "Manager"],
    }

    cleaned = clean_up_attributes(attributes=attributes, asset_type="Company", remove_donor=True)

    assert "Organization" in cleaned
    # Performance Title is kept (only Extras and Donors are removed when remove_donor=True)
    assert "Performance Title" in cleaned
    # Asset Type is always added
    assert "Asset Type" in cleaned
    assert cleaned["Asset Type"] == ["Company"]
    # Donors should be removed because remove_donor=True
    assert "Donors" not in cleaned


def test_clean_up_attributes_keep_donors():
    """Test that donors are kept when remove_donor is False."""
    attributes = {
        "Performance Title": ["Show"],
        "Donors": ["Donor 1", "Donor 2"],
    }

    cleaned = clean_up_attributes(attributes=attributes, asset_type="Program", remove_donor=False)

    assert "Donors" in cleaned
    assert cleaned["Donors"] == ["Donor 1", "Donor 2"]


def test_clean_up_attributes_empty():
    """Test cleaning up empty attributes."""
    attributes = {}

    cleaned = clean_up_attributes(attributes=attributes, asset_type="Program", remove_donor=True)

    # clean_up_attributes always adds Asset Type
    assert cleaned == {"Asset Type": ["Program"]}


def test_get_auth_key_with_timeout(mock_requests):
    """Test that auth key request includes timeout."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"sessionKey": "test-key"}}
    mock_response.text = '{"result": {"sessionKey": "test-key"}}'
    mock_requests.get.return_value = mock_response

    get_auth_key(url="https://netx.test.com/api", username="user", password="pass")

    # Verify timeout was passed
    call_kwargs = mock_requests.get.call_args[1]
    assert "timeout" in call_kwargs
    assert call_kwargs["timeout"] == 600


def test_extract_asset_attributes_empty_list(mock_requests):
    """Test extracting attributes with empty asset list."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": []}
    mock_requests.get.return_value = mock_response

    results = extract_asset_attributes(url="https://netx.test.com/api", authkey="test-key", asset_id_list=[])

    assert results == []


def test_extract_attribute_values():
    """Test extracting attribute values from list."""
    from classes.src.netx_connection import extract_attribute_values

    attr_list = [{"value": "val1"}, {"value": "val2"}, {"value": "val3"}]

    result = extract_attribute_values(attr_list)

    assert result == ["val1", "val2", "val3"]


def test_combine_attributes_with_list():
    """Test combining attributes from list of pages."""
    from classes.src.netx_connection import combine_attributes

    asset_attributes = [
        {"attributes": {"Choreographer": [{"value": "John Doe"}]}},
        {"attributes": {"Composer": [{"value": "Ludwig"}]}},
    ]

    result = combine_attributes(asset_attributes, "", "dance")

    assert isinstance(result, dict)
    assert len(result) > 0


@patch("classes.src.netx_connection.requests.post")
def test_create_asset_folder(mock_post):
    """Test creating asset folder."""
    from classes.src.netx_connection import create_asset_folder

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"folder": {"id": "folder123"}}}
    mock_post.return_value = mock_response

    result = create_asset_folder("https://test.netx.net", "session_key", "/root", "test.pdf")

    assert result.json()["result"]["folder"]["id"] == "folder123"
    mock_post.assert_called_once()


@patch("classes.src.netx_connection.requests.post")
def test_create_folder_by_path(mock_post):
    """Test creating folder by path."""
    from classes.src.netx_connection import create_folder_by_path

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"folder": {"id": "folder123"}}}
    mock_post.return_value = mock_response

    result = create_folder_by_path("https://test.netx.net", "session_key", "/root/subfolder")

    assert result.json()["result"]["folder"]["id"] == "folder123"
    mock_post.assert_called_once()


@patch("classes.src.netx_connection.requests.post")
def test_get_folder_by_path(mock_post):
    """Test getting folder by path."""
    from classes.src.netx_connection import get_folder_by_path

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"folder": {"id": "folder123"}}}
    mock_post.return_value = mock_response

    result = get_folder_by_path("https://test.netx.net", "session_key", "/root/subfolder")

    assert result.json()["result"]["folder"]["id"] == "folder123"
    mock_post.assert_called_once()


@patch("classes.src.netx_connection.requests.post")
@patch("builtins.open", create=True)
def test_upload_pdf_file(mock_open_func, mock_post):
    """Test uploading PDF file."""
    from classes.src.netx_connection import upload_pdf_file

    mock_open_func.return_value.__enter__.return_value.read.return_value = b"fake pdf content"
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"assetId": "asset123"}}
    mock_post.return_value = mock_response

    result = upload_pdf_file("https://test.netx.net/upload", "session_key", "folder123", "/tmp/test.pdf", "test.pdf")

    assert result.json()["result"]["assetId"] == "asset123"


@patch("classes.src.netx_connection.requests.post")
def test_create_asset(mock_post):
    """Test creating asset."""
    from classes.src.netx_connection import create_asset

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"assetId": "asset123"}}
    mock_post.return_value = mock_response

    result = create_asset("https://test.netx.net", "session_key", "folder123", "test.pdf")

    assert result.json()["result"]["assetId"] == "asset123"
    mock_post.assert_called_once()


@patch("classes.src.netx_connection.requests.post")
def test_set_asset_attributes(mock_post):
    """Test setting asset attributes."""
    from classes.src.netx_connection import set_asset_attributes

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    attributes = {"Choreographer": "John Doe", "Composer": "Ludwig"}
    result = set_asset_attributes("https://test.netx.net", "session_key", "asset123", attributes)

    assert result.status_code == 200
    mock_post.assert_called_once()


def test_get_temp_file_path():
    """Test getting temporary file path."""
    from classes.src.netx_connection import get_temp_file_path

    result = get_temp_file_path()

    assert isinstance(result, str)
    assert len(result) > 0


@patch("classes.src.netx_connection.TableClient")
def test_get_entity_list(mock_table_client):
    """Test getting entity list from table."""
    from classes.src.netx_connection import get_entity_list

    mock_table = MagicMock()
    mock_table.query_entities.return_value = [{"PartitionKey": "test.pdf", "RowKey": "page_0", "attributes": json.dumps({"key": "value"})}]

    result = get_entity_list(mock_table, "test.pdf")

    assert len(result) == 1
    # The function returns entities as-is, doesn't parse JSON in attributes field
    assert result[0]["PartitionKey"] == "test.pdf"
    assert "attributes" in result[0]


@patch("classes.src.netx_connection.BlobServiceClient")
@patch("builtins.open", create=True)
@patch("os.remove")
def test_write_json_to_blob(mock_remove, mock_open_func, mock_blob_service):
    """Test writing JSON to blob storage."""
    from classes.src.netx_connection import write_json_to_blob

    mock_blob_client = MagicMock()
    mock_blob_service_instance = MagicMock()
    mock_blob_service_instance.get_blob_client.return_value = mock_blob_client

    data = {"test": "data"}

    with patch("tempfile.gettempdir", return_value="/tmp"):
        write_json_to_blob(mock_blob_service_instance, "container", "blob_name.json", data, "/tmp")

    mock_blob_client.upload_blob.assert_called_once()


@patch("classes.src.netx_connection.BlobServiceClient")
@patch("builtins.open", create=True)
def test_download_pdf(mock_open_func, mock_blob_service):
    """Test downloading PDF from blob storage."""
    from classes.src.netx_connection import download_pdf

    mock_blob_client = MagicMock()
    mock_blob_client.download_blob().readall.return_value = b"fake pdf"
    mock_blob_service_instance = MagicMock()
    mock_blob_service_instance.get_blob_client.return_value = mock_blob_client

    with patch("tempfile.gettempdir", return_value="/tmp"):
        result = download_pdf(mock_blob_service_instance, "container", "test.pdf", "/tmp")

    assert "/tmp" in result or "test.pdf" in result


def test_validate_required_fields_all_present():
    """Test validation when all required fields present."""
    from classes.src.netx_connection import validate_required_fields

    data = {
        "session_key": "key123",
        "client_id": "client1",
        "upload_url": "https://test.com",
        "url": "https://test.com",
        "pdf_names": ["test.pdf"],
    }

    is_valid, message = validate_required_fields(data)

    assert is_valid is True
    assert message == ""


def test_validate_required_fields_missing_session_key():
    """Test validation when session_key missing."""
    from classes.src.netx_connection import validate_required_fields

    data = {
        "client_id": "client1",
        "upload_url": "https://test.com",
        "url": "https://test.com",
        "pdf_names": ["test.pdf"],
    }

    is_valid, message = validate_required_fields(data)

    assert is_valid is False
    assert "session_key" in message


@patch("classes.src.netx_connection.requests.post")
def test_netx_upload_single_page_pdf(mock_post):
    """Test upload with authenticated session."""
    from classes.src.netx_connection import authenticate_session

    # Mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"sessionKey": "test_session_key"}}
    mock_response.text = "response text"

    with patch("classes.src.netx_connection.get_auth_key", return_value="test_session_key"):
        with patch("os.getenv", side_effect=lambda x: {"NetXURL": "https://test.netx.net", "NetXUsername": "testuser", "NetXPassword": "testpass"}.get(x)):
            json_body = {"pdf_name": "test.pdf"}
            result = authenticate_session(json_body)

            assert result is not None
            assert len(result) > 2  # Returns tuple with multiple values


def test_download_json_from_blob():
    """Test downloading JSON from blob."""
    from classes.src.netx_connection import download_json_from_blob

    mock_blob_service = MagicMock()
    mock_blob_client = MagicMock()
    mock_blob_client.download_blob().readall.return_value = b'{"test": "data"}'
    mock_blob_service.get_blob_client.return_value = mock_blob_client

    with patch("builtins.open", create=True):
        with patch("json.load", return_value={"test": "data"}):
            result = download_json_from_blob(mock_blob_service, "container/path", "file.json", "/tmp")

    assert result == {"test": "data"}


def test_update_or_create_entity_create():
    """Test creating new entity when not exists."""
    from classes.src.netx_connection import update_or_create_entity

    mock_table = MagicMock()
    mock_table.query_entities.return_value = []  # No existing entities

    entity_list = []
    update_or_create_entity(mock_table, entity_list, "test.pdf", "In Progress")

    mock_table.create_entity.assert_called_once()


def test_update_or_create_entity_update():
    """Test updating existing entity."""
    from classes.src.netx_connection import update_or_create_entity

    mock_table = MagicMock()
    existing_entity = {"PartitionKey": "test.pdf", "RowKey": "page_0", "status": "Old"}
    mock_table.query_entities.return_value = [existing_entity]

    entity_list = [existing_entity]
    update_or_create_entity(mock_table, entity_list, "test.pdf", "Complete")

    mock_table.update_entity.assert_called_once()


@patch.dict("os.environ", {"STORAGE_CONNECTION_STRING": "test_conn_str", "AZURE_TABLE_STORAGE_PROGRAM_TABLE_NAME": "ProgramTable"})
@patch("classes.src.netx_connection.TableServiceClient")
def test_update_program_status_not_found(mock_table_service):
    """Test updating program status when program not found."""
    from classes.src.netx_connection import update_program_status

    mock_table_client = MagicMock()
    mock_table_service.from_connection_string.return_value.get_table_client.return_value = mock_table_client
    mock_table_client.query_entities.return_value = []  # No matching program

    update_program_status("nonexistent_program", "Complete")

    # Should log error but not crash
    assert True


def test_extract_attribute_values_with_nested_dict():
    """Test extracting values from nested dict structures."""
    from classes.src.netx_connection import extract_attribute_values

    attr_list = [{"value": "val1", "confidence": 0.9}, {"value": "val2", "confidence": 0.8}]

    result = extract_attribute_values(attr_list)

    assert "val1" in result
    assert "val2" in result
    assert len(result) == 2


@patch("classes.src.netx_connection.requests.post")
def test_netx_upload_pipeline_success(mock_post):
    """Test complete netx upload pipeline."""
    from classes.src.netx_connection import netx_upload_pipeline

    # Mock all the responses
    mock_upload_response = MagicMock()
    mock_upload_response.status_code = 200

    mock_create_response = MagicMock()
    mock_create_response.json.return_value = {"result": {"id": "12345"}}
    mock_create_response.status_code = 200

    mock_attr_response = MagicMock()
    mock_attr_response.status_code = 200

    mock_post.side_effect = [mock_upload_response, mock_create_response, mock_attr_response]

    with patch("builtins.open", MagicMock()):
        result = netx_upload_pipeline(
            "http://upload.url", "http://base.url", "test_session_key", "folder_123", "/path/to/test.pdf", "test.pdf", {"Title": "Test Document"}
        )

    assert len(result) == 3
    assert result[0].status_code == 200
    assert result[1].status_code == 200
    assert result[2].status_code == 200


def test_authenticate_session_with_session_key():
    """Test authentication using existing session key."""
    from classes.src.netx_connection import authenticate_session

    json_body = {"session_key": "existing_key_123", "username": "", "password": "", "url": "http://test.url"}

    session_key, success, error = authenticate_session(json_body)

    assert session_key == "existing_key_123"
    assert success is True
    assert error == ""


@patch("classes.src.netx_connection.get_auth_key")
def test_authenticate_session_with_credentials(mock_get_auth_key):
    """Test authentication using username and password."""
    from classes.src.netx_connection import authenticate_session

    mock_get_auth_key.return_value = "new_session_key_456"

    json_body = {"session_key": "", "username": "testuser", "password": "testpass", "url": "http://test.url"}

    session_key, success, error = authenticate_session(json_body)

    assert session_key == "new_session_key_456"
    assert success is True
    assert error == ""
    mock_get_auth_key.assert_called_once_with("http://test.url", "testuser", "testpass")


@patch("classes.src.netx_connection.get_auth_key")
def test_authenticate_session_failure(mock_get_auth_key):
    """Test authentication failure when auth key is None."""
    from classes.src.netx_connection import authenticate_session

    mock_get_auth_key.return_value = None

    json_body = {"session_key": "", "username": "testuser", "password": "testpass", "url": "http://test.url"}

    session_key, success, error = authenticate_session(json_body)

    assert session_key is None
    assert success is False
    assert "Session key is None" in error


@patch("classes.src.netx_connection.get_auth_key")
def test_authenticate_session_exception(mock_get_auth_key):
    """Test authentication exception handling."""
    from classes.src.netx_connection import authenticate_session

    mock_get_auth_key.side_effect = Exception("Connection error")

    json_body = {"session_key": "", "username": "testuser", "password": "testpass", "url": "http://test.url"}

    session_key, success, error = authenticate_session(json_body)

    assert session_key is None
    assert success is False
    assert "Connection error" in error


def test_extract_attribute_values_empty_list():
    """Test extracting values from empty list returns default."""
    from classes.src.netx_connection import extract_attribute_values

    result = extract_attribute_values([], default_value="default")

    assert result == ["default"]


def test_extract_attribute_values_string_items():
    """Test extracting values when items are strings."""
    from classes.src.netx_connection import extract_attribute_values

    attr_list = ["value1", "value2", "value3"]

    result = extract_attribute_values(attr_list)

    assert result == ["value1", "value2", "value3"]


def test_extract_attribute_values_mixed_types():
    """Test extracting values with mixed dict and string items."""
    from classes.src.netx_connection import extract_attribute_values

    attr_list = [{"value": "dict_val1"}, "string_val", {"value": "dict_val2"}]

    result = extract_attribute_values(attr_list)

    assert "dict_val1" in result
    assert "string_val" in result
    assert "dict_val2" in result
    assert len(result) == 3


@patch.dict("os.environ", {"STORAGE_CONNECTION_STRING": "test_conn_str", "AZURE_TABLE_STORAGE_PROGRAM_TABLE_NAME": "ProgramTable"})
@patch("classes.src.netx_connection.TableServiceClient")
@patch("classes.src.netx_connection.get_entity_list")
def test_update_program_status_success(mock_get_entity_list, mock_table_service):
    """Test successfully updating program status."""
    from classes.src.netx_connection import update_program_status

    mock_table_client = MagicMock()
    mock_table_service.from_connection_string.return_value.create_table_if_not_exists.return_value = mock_table_client

    existing_entity = {"PartitionKey": "test", "RowKey": "test_program", "Status": "Processing"}
    mock_get_entity_list.return_value = [existing_entity]

    update_program_status("test_program", "Complete")

    mock_table_client.update_entity.assert_called_once()


def test_combine_attributes_simple():
    """Test combining attributes from simple structure."""
    from classes.src.netx_connection import combine_attributes

    pages = [{"attributes": {"Company": "Test Co", "Page": "1"}}, {"attributes": {"Company": "Test Co", "Page": "2"}}]

    result = combine_attributes(pages, "TEST")

    assert isinstance(result, dict)


def test_validate_required_fields_partial_missing():
    """Test validation with some fields missing."""
    from classes.src.netx_connection import validate_required_fields

    json_body = {
        "url": "http://test.url",
        "session_key": "key123",
        # Missing upload_url, client_id, pdf_names
    }

    is_valid, missing = validate_required_fields(json_body)

    assert is_valid is False
    assert "upload_url" in missing
    assert "client_id" in missing
    assert "pdf_names" in missing


def test_validate_required_fields_pdf_names_not_list():
    """Test validation when pdf_names is not a list."""
    from classes.src.netx_connection import validate_required_fields

    json_body = {"url": "http://test.url", "session_key": "key123", "client_id": "client1", "upload_url": "http://upload.url", "pdf_names": "not_a_list"}

    is_valid, error = validate_required_fields(json_body)

    assert is_valid is False
    assert "must be an array" in error


def test_validate_required_fields_pdf_names_empty():
    """Test validation when pdf_names is an empty list."""
    from classes.src.netx_connection import validate_required_fields

    json_body = {"url": "http://test.url", "session_key": "key123", "client_id": "client1", "upload_url": "http://upload.url", "pdf_names": []}

    is_valid, error = validate_required_fields(json_body)

    assert is_valid is False
    # Empty list is checked, not as missing field but as empty array
    assert "Missing required fields" in error or "cannot be empty" in error


@patch("classes.src.netx_connection.requests.post")
def test_get_folder_by_path_success(mock_post):
    """Test getting folder by path successfully."""
    from classes.src.netx_connection import get_folder_by_path

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"id": "123", "name": "Test Folder"}}
    mock_post.return_value = mock_response

    result = get_folder_by_path("http://test.url", "session_key", "/path/to/folder")

    assert result.json()["result"]["id"] == "123"
    mock_post.assert_called_once()


@patch("classes.src.netx_connection.requests.post")
def test_create_folder_by_path_success(mock_post):
    """Test creating folder by path successfully."""
    from classes.src.netx_connection import create_folder_by_path

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"id": "456", "name": "New Folder"}}
    mock_post.return_value = mock_response

    result = create_folder_by_path("http://test.url", "session_key", "/path/to/new/folder")

    assert result.json()["result"]["id"] == "456"
    mock_post.assert_called_once()


@patch.dict("os.environ", {"STORAGE_CONNECTION_STRING": "test_conn_str"})
@patch("classes.src.netx_connection.TableServiceClient")
@patch("classes.src.netx_connection.get_entity_list")
def test_update_program_status_exception(mock_get_entity_list, mock_table_service):
    """Test update_program_status handles exceptions properly."""
    from classes.src.netx_connection import update_program_status

    # Make TableServiceClient raise an exception
    mock_table_service.from_connection_string.side_effect = Exception("Connection failed")

    # Should not crash, just log error
    try:
        update_program_status("test_program", "Complete")
        assert False, "Should have raised exception"
    except Exception as e:
        assert "Connection failed" in str(e)


def test_authenticate_session_with_empty_session_key_no_credentials():
    """Test authentication with empty session key and no credentials."""
    from classes.src.netx_connection import authenticate_session

    json_body = {"session_key": "", "username": "", "password": "", "url": "http://test.url"}

    # Since both session_key is empty and username/password are empty,
    # it should attempt to use the session_key path
    session_key, success, error = authenticate_session(json_body)

    assert session_key == ""
    assert success is True
    assert error == ""


def test_clean_up_attributes_success():
    """Test clean_up_attributes function."""
    from classes.src.netx_connection import clean_up_attributes

    attributes = {"test_attr": "test_value"}
    result = clean_up_attributes(attributes, "program", False)

    # The function adds Asset Type
    assert "Asset Type" in result
    assert result["Asset Type"] == ["program"]
    assert "test_attr" in result


def test_clean_up_attributes_remove_donor():
    """Test clean_up_attributes removes donor when flag is True."""
    from classes.src.netx_connection import clean_up_attributes

    attributes = {"test_attr": "test_value", "Donors": "donor_data", "Extras": "extra_data"}
    result = clean_up_attributes(attributes, "program", True)

    assert "Donors" not in result
    assert "Extras" not in result
    assert "Asset Type" in result
    assert "test_attr" in result


def test_clean_up_attributes_keep_donor():
    """Test clean_up_attributes keeps donor when flag is False."""
    from classes.src.netx_connection import clean_up_attributes

    attributes = {"test_attr": "test_value", "Donors": "donor_data", "Extras": "extra_data"}
    result = clean_up_attributes(attributes, "program", False)

    assert "Donors" in result
    assert "Extras" not in result
    assert "Asset Type" in result


def test_extract_attribute_values_no_value_key():
    """Test extracting values when dict items don't have value key."""
    from classes.src.netx_connection import extract_attribute_values

    attr_list = [{"name": "item1"}, {"name": "item2"}]

    result = extract_attribute_values(attr_list)

    # Should return default when no 'value' key found
    assert len(result) == 1
    assert result[0] == ""


def test_extract_attribute_values_custom_key():
    """Test extracting values with custom key."""
    from classes.src.netx_connection import extract_attribute_values

    attr_list = [{"name": "item1"}, {"name": "item2"}]

    result = extract_attribute_values(attr_list, key="name")

    assert "item1" in result
    assert "item2" in result
    assert len(result) == 2


def test_extract_attribute_values_custom_default():
    """Test extracting values with custom default value."""
    from classes.src.netx_connection import extract_attribute_values

    result = extract_attribute_values([], default_value="custom_default")

    assert result == ["custom_default"]


@patch("classes.src.netx_connection.requests.get")
def test_get_auth_key_success(mock_get):
    """Test getting auth key successfully."""
    from classes.src.netx_connection import get_auth_key

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"sessionKey": "auth_key_123"}}
    mock_get.return_value = mock_response

    result = get_auth_key("http://test.url", "user", "pass")

    assert result == "auth_key_123"
    mock_get.assert_called_once()


@patch("classes.src.netx_connection.requests.get")
def test_get_auth_key_failure(mock_get):
    """Test getting auth key when authentication fails."""
    from classes.src.netx_connection import get_auth_key

    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "Invalid credentials"}
    mock_get.return_value = mock_response

    result = get_auth_key("http://test.url", "user", "wrong_pass")

    assert result is None


@patch("classes.src.netx_connection.requests.get")
def test_get_asset_ids_success(mock_get):
    """Test extracting asset IDs from response."""
    from classes.src.netx_connection import get_asset_ids

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": {"results": [{"id": 1, "name": "asset1"}, {"id": 2, "name": "asset2"}]}}
    mock_get.return_value = mock_response

    result = get_asset_ids("http://test.url", "auth_key", "folder123", 10)

    assert 1 in result
    assert 2 in result
    assert len(result) == 2


@patch("classes.src.netx_connection.BlobServiceClient")
@patch("os.remove")
def test_write_json_to_blob_with_cleanup(mock_remove, mock_blob_service):
    """Test writing JSON to blob."""
    from classes.src.netx_connection import write_json_to_blob

    mock_blob_client = MagicMock()
    mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client

    data = {"test": "data"}
    temp_path = "/temp/dir"

    with patch("builtins.open", MagicMock()):
        write_json_to_blob(mock_blob_service(), "test_container", "test.json", data, temp_path)

        mock_blob_client.upload_blob.assert_called_once()

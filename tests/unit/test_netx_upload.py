import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from azure.data.tables import TableClient
from azure.storage.blob import BlobServiceClient

from classes.src.constants import LOCAL_DEBUG
from classes.src.netx_connection import (
    authenticate_session,
    combine_attributes,
    download_json_from_blob,
    download_pdf,
    get_entity_list,
    update_or_create_entity,
    write_json_to_blob,
)

PDF_FIXTURE_PATH = Path("data/pdf/OBC_Program 2003-11-07_mt3.pdf")


@pytest.fixture
def mock_table_client():
    """Fixture for a mock TableClient."""
    return MagicMock(spec=TableClient)


@pytest.fixture
def mock_blob_service_client():
    """Fixture for a mock BlobServiceClient."""
    return MagicMock(spec=BlobServiceClient)


@pytest.fixture
def mock_entity_list():
    return [{"PartitionKey": "example.pdf", "RowKey": "", "fileName": "example.pdf", "status": "Pending"}]


@pytest.fixture
def combined_attributes_mock_json():
    # Load mock_labelled_new_attributes.json and preprocess to asset_attributes format
    with open("./data/json/combine_attributes_mock.json", "r") as file:
        mock_json = json.load(file)
    return mock_json


@pytest.fixture
def fake_request():
    req = MagicMock()
    req.get_json.return_value = {
        "pdf_name": "OBC_Program 2003-11-07_mt3.pdf",
        "client_id": "test",
        "url": "https://obclegacy.netx.net/external/api/json",
        "upload_url": "https://obclegacy.netx.net/servlet/FileUploader",
        "root_folder": "OBC Demo/Subfolder 1/Subfolder 2",
        "session_key": "fake_key",
        "create_sub_folder": True,
    }
    return req


def test_combine_attributes(combined_attributes_mock_json):
    mock_json = combined_attributes_mock_json.copy()
    print(mock_json)
    expected_attribute_keys = [
        "Administration-Company & School",
        "Advisory Board",
        "Board of Directors",
        "Board of Trustees",
        "Venue",
        "City",
        "State/Province",
        "Country",
        "Date of Performance",
        "Performance Title",
        "Composer",
        "Choreographer",
        "Set Designer",
        "Costume Designer",
        "Lighting Designer",
        "Artist/Performer",
        "Donors",
        "Department",
        "Extras",
    ]
    for feature in mock_json:
        attributes = feature.get("attributes", {})
        for key in attributes.keys():
            if key not in expected_attribute_keys:
                expected_attribute_keys.append(key)

    combined = combine_attributes(mock_json, client_prefix="Test")
    if LOCAL_DEBUG:
        # write result to file (test.json)
        with open("./test_results/test_combine_attributes.json", "w") as file:
            json.dump(combined, file, indent=4)
    # print(combined)
    # confirm that the attributes have the prefix "Test" appended to all of the attribute key names
    # Assert all keys in combined have the prefix "Test-"
    for key in expected_attribute_keys:
        assert f"Test-{key}" in combined

    # Assert that the values are lists
    for value in combined.values():
        assert isinstance(value, list)

    assert combined["Test-Administration-Company & School"] == [""]
    assert combined["Test-Advisory Board"] == [""]
    assert combined["Test-Board of Directors"] == [""]
    assert combined["Test-Board of Trustees"] == [""]
    assert combined["Test-Venue"] == ["New York City Center"]
    assert combined["Test-City"] == ["New York"]
    assert combined["Test-State/Province"] == ["New York"]
    assert combined["Test-Country"] == ["United States"]
    assert combined["Test-Date of Performance"] == [""]
    assert combined["Test-Performance Title"] == [""]
    assert combined["Test-Composer"] == [""]
    assert combined["Test-Choreographer"] == [""]
    assert combined["Test-Set Designer"] == [""]
    assert combined["Test-Costume Designer"] == [""]
    assert combined["Test-Lighting Designer"] == [""]
    assert combined["Test-Artist/Performer"] == ["Lydia Abarca", "Hinton Battle", "Stephanie Baxter", "Karen Brown"]
    assert combined["Test-Donors"] == [""]
    assert combined["Test-Department"] == [""]
    assert combined["Test-Extras"] == [""]


def test_combine_attributes_no_prefix(combined_attributes_mock_json):
    mock_json = combined_attributes_mock_json.copy()
    print(mock_json)
    expected_attribute_keys = [
        "Administration-Company & School",
        "Advisory Board",
        "Board of Directors",
        "Board of Trustees",
        "Venue",
        "City",
        "State/Province",
        "Country",
        "Date of Performance",
        "Performance Title",
        "Composer",
        "Choreographer",
        "Set Designer",
        "Costume Designer",
        "Lighting Designer",
        "Artist/Performer",
        "Donors",
        "Department",
        "Extras",
    ]
    for feature in mock_json:
        attributes = feature.get("attributes", {})
        for key in attributes.keys():
            if key not in expected_attribute_keys:
                expected_attribute_keys.append(key)

    combined = combine_attributes(mock_json, client_prefix="")
    if LOCAL_DEBUG:
        # write result to file (test.json)
        with open("./test_results/test_combine_attributes_no_prefix.json", "w") as file:
            json.dump(combined, file, indent=4)
    # print(combined)
    # Assert all keys in combined do NOT have the prefix "Test-"
    for key in expected_attribute_keys:
        assert f"Test-{key}" not in combined
        assert f"{key}" in combined

    # Assert that the values are lists
    for value in combined.values():
        assert isinstance(value, list)

    assert combined["Administration-Company & School"] == [""]
    assert combined["Advisory Board"] == [""]
    assert combined["Board of Directors"] == [""]
    assert combined["Board of Trustees"] == [""]
    assert combined["Venue"] == ["New York City Center"]
    assert combined["City"] == ["New York"]
    assert combined["State/Province"] == ["New York"]
    assert combined["Country"] == ["United States"]
    assert combined["Date of Performance"] == [""]
    assert combined["Performance Title"] == [""]
    assert combined["Composer"] == [""]
    assert combined["Choreographer"] == [""]
    assert combined["Set Designer"] == [""]
    assert combined["Costume Designer"] == [""]
    assert combined["Lighting Designer"] == [""]
    assert combined["Artist/Performer"] == ["Lydia Abarca", "Hinton Battle", "Stephanie Baxter", "Karen Brown"]
    assert combined["Donors"] == [""]
    assert combined["Department"] == [""]
    assert combined["Extras"] == [""]


def test_get_entity_list_returns_entities(mock_table_client):
    mock_table_client.query_entities.return_value = [{"PartitionKey": "example.pdf"}]
    result = get_entity_list(mock_table_client, "example.pdf")
    assert isinstance(result, list)
    assert result[0]["PartitionKey"] == "example.pdf"


def test_write_json_to_blob(tmp_path, mock_blob_service_client):
    container = "test-container"
    blob_name = "test.json"
    data = {"foo": "bar"}
    temp_file_path = str(tmp_path)
    blob_client = MagicMock()
    mock_blob_service_client.get_blob_client.return_value = blob_client

    write_json_to_blob(mock_blob_service_client, container, blob_name, data, temp_file_path)
    mock_blob_service_client.get_blob_client.assert_called_with(container=container, blob=blob_name)
    blob_client.upload_blob.assert_called()
    # File should be removed after upload
    assert not (tmp_path / blob_name).exists()


def test_update_or_create_entity_creates_entity_when_none_exist(mock_table_client):
    mock_table_client.create_entity = MagicMock()
    update_or_create_entity(
        cd_table=mock_table_client, entity_list=[], pdf_name="example.pdf", status="Test Status", error_message="", extra_fields={"updatedAt": datetime.now()}
    )
    mock_table_client.create_entity.assert_called_once()


def test_update_or_create_entity_updates_entity_when_exists(mock_table_client, mock_entity_list):
    mock_table_client.update_entity = MagicMock()
    update_or_create_entity(
        cd_table=mock_table_client,
        entity_list=mock_entity_list,
        pdf_name="example.pdf",
        status="Test Status",
        error_message="",
        extra_fields={"updatedAt": datetime.now()},
    )
    mock_table_client.update_entity.assert_called_once()


def test_authenticate_session_success(monkeypatch):
    # Patch get_auth_key to return a fake session key
    monkeypatch.setattr("classes.src.netx_connection.get_auth_key", lambda url, username, password: "fake_session_key")
    json_body = {"url": "http://test", "username": "user", "password": "pass"}
    session_key, connection_success, error_message = authenticate_session(json_body)
    assert session_key == "fake_session_key"
    assert connection_success is True
    assert error_message == ""


def test_authenticate_session_failure(monkeypatch):
    # Patch get_auth_key to raise an exception
    def raise_exc(url, username, password):
        raise Exception("Auth failed")

    monkeypatch.setattr("classes.src.netx_connection.get_auth_key", raise_exc)
    json_body = {"url": "http://test", "username": "user", "password": "pass"}
    session_key, connection_success, error_message = authenticate_session(json_body)
    assert session_key is None
    assert connection_success is False
    assert "Auth failed" in error_message


def test_download_pdf(tmp_path, mock_blob_service_client):
    container = "test-container"
    pdf_name = "OBC_Program 2003-11-07_mt3.pdf"
    temp_file_path = str(tmp_path)
    blob_client = MagicMock()
    # Simulate reading the real PDF file
    with open(PDF_FIXTURE_PATH, "rb") as f:
        pdf_bytes = f.read()
    blob_client.download_blob.return_value.readall.return_value = pdf_bytes
    mock_blob_service_client.get_blob_client.return_value = blob_client

    result_path = download_pdf(mock_blob_service_client, container, pdf_name, temp_file_path)
    assert (tmp_path / pdf_name).exists()
    with open(tmp_path / pdf_name, "rb") as f:
        assert f.read() == pdf_bytes
    assert result_path == f"{temp_file_path}/{pdf_name}"


def test_download_json_from_blob(tmp_path, mock_blob_service_client):
    # Prepare mock blob client and data
    container_path = "test-container"
    file_name = "test.json"
    temp_file_path = str(tmp_path)
    expected_data = {"foo": "bar"}

    mock_blob_client = MagicMock()
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.download_blob.return_value.readall.return_value = json.dumps(expected_data).encode("utf-8")

    # Call the function
    result = download_json_from_blob(
        blob_service_client=mock_blob_service_client,
        container_path=container_path,
        file_name=file_name,
        temp_file_path=temp_file_path,
    )
    assert result == expected_data
    # The file should exist and contain the expected data
    with open(f"{temp_file_path}/vocab.json", "r") as f:
        assert json.load(f) == expected_data


def test_download_json_from_blob_handles_str_blob(tmp_path, mock_blob_service_client):
    # Simulate blob returning a string instead of bytes
    container_path = "test-container"
    file_name = "test.json"
    temp_file_path = str(tmp_path)
    expected_data = {"foo": "bar"}

    mock_blob_client = MagicMock()
    mock_blob_service_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.download_blob.return_value.readall.return_value = json.dumps(expected_data)

    result = download_json_from_blob(
        blob_service_client=mock_blob_service_client,
        container_path=container_path,
        file_name=file_name,
        temp_file_path=temp_file_path,
    )
    assert result == expected_data


def test_download_json_from_blob_raises_on_error(mock_blob_service_client):
    mock_blob_service_client.get_blob_client.side_effect = Exception("Blob error")
    with pytest.raises(Exception) as excinfo:
        download_json_from_blob(blob_service_client=mock_blob_service_client, container_path="container", file_name="file.json", temp_file_path="tmp")
    assert "Error downloading file" in str(excinfo.value)


def make_fake_request(pdf_names=None):
    req = MagicMock()
    req.get_json.return_value = {
        "session_key": "fake-session",
        "client_id": "test-client",
        "upload_url": "https://fake-upload-url",
        "url": "https://fake-api-url",
        "pdf_names": pdf_names or ["test1.pdf", "test2.pdf"],
        "create_sub_folder": False,
        "root_folder": "TestFolder",
    }
    return req

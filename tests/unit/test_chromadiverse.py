"""Unit tests for ChromaDiverse class."""

import json
import tempfile
from unittest.mock import MagicMock, mock_open, patch

import pytest

from classes.chromadiverse import ChromaDiverse


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv("CV_KEY", "test-cv-key")
    monkeypatch.setenv("CV_ENDPOINT", "https://test-cv.cognitiveservices.azure.com/")
    monkeypatch.setenv("TA_KEY", "test-ta-key")
    monkeypatch.setenv("TA_ENDPOINT", "https://test-ta.cognitiveservices.azure.com/")
    monkeypatch.setenv("STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=test")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test-openai.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")


@pytest.fixture
def mock_blob_service():
    """Mock BlobServiceClient."""
    with patch("classes.chromadiverse.BlobServiceClient") as mock:
        mock_client = MagicMock()
        mock.from_connection_string.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_azure_clients():
    """Mock Azure CV and TA clients."""
    with patch("classes.chromadiverse.azure_cv_client") as mock_cv, patch("classes.chromadiverse.azure_ta_client") as mock_ta:
        yield mock_cv, mock_ta


@pytest.fixture
def mock_features_json():
    """Mock features JSON structure."""
    return {
        "pdf_name": "test_program.pdf",
        "features": [
            {"page_number": 0, "text": "Test page 1", "person": 5, "organization": 2},
            {"page_number": 1, "text": "Test page 2", "person": 3, "organization": 1},
        ],
        "first ocr": [[1, [["Test", 100, 100, 200, 120, 100, 20, 0.95]]]],
        "final ocr": [[1, [["Test", 100, 100, 200, 120, 100, 20, 0.95]]]],
    }


def test_chromadiverse_init_with_env_vars(mock_env_vars, mock_blob_service, mock_azure_clients):
    """Test ChromaDiverse initialization with environment variables."""
    cd = ChromaDiverse(pdf_name="test.pdf")

    assert cd.pdf_name == "test.pdf"
    assert cd.azure_openai_endpoint == "https://test-openai.openai.azure.com/"
    assert cd.azure_openai_api_key == "test-openai-key"
    assert cd.openai_deployment == "gpt-4o"
    assert cd.temp_blob_pdf.endswith("test_blob.pdf")
    assert cd.temp_json.endswith("test_features.json")


def test_chromadiverse_init_with_explicit_params(mock_blob_service, mock_azure_clients):
    """Test ChromaDiverse initialization with explicit parameters."""
    cd = ChromaDiverse(
        cv_key="custom-cv-key",
        cv_endpoint="https://custom-cv.com/",
        ta_key="custom-ta-key",
        ta_endpoint="https://custom-ta.com/",
        storage_connection_string="custom-connection",
        pdf_name="custom.pdf",
    )

    assert cd.pdf_name == "custom.pdf"


@patch("builtins.open", new_callable=mock_open)
def test_download_pdf(mock_file, mock_env_vars, mock_blob_service, mock_azure_clients):
    """Test downloading PDF from blob storage."""
    cd = ChromaDiverse(pdf_name="test.pdf")

    mock_blob_client = MagicMock()
    mock_blob_client.download_blob().readall.return_value = b"PDF content"
    cd.blob_service_client.get_blob_client.return_value = mock_blob_client

    result = cd.download_pdf(container_name="test-container")

    assert result == "PDF Downloaded successfully."
    cd.blob_service_client.get_blob_client.assert_called_once_with(container="test-container", blob="test.pdf")
    mock_file.assert_called_once()


@patch("builtins.open", new_callable=mock_open)
def test_download_pdf_with_string_content(mock_file, mock_env_vars, mock_blob_service, mock_azure_clients):
    """Test downloading PDF when blob returns string instead of bytes."""
    cd = ChromaDiverse(pdf_name="test.pdf")

    mock_blob_client = MagicMock()
    mock_blob_client.download_blob().readall.return_value = "PDF content string"
    cd.blob_service_client.get_blob_client.return_value = mock_blob_client

    result = cd.download_pdf(container_name="test-container")

    assert result == "PDF Downloaded successfully."


@patch("classes.chromadiverse.label_pages_with_openai")
@patch("builtins.open", new_callable=mock_open)
def test_extract_features(mock_file, mock_label_pages, mock_env_vars, mock_blob_service, mock_azure_clients):
    """Test feature extraction pipeline."""
    cd = ChromaDiverse(pdf_name="test.pdf")
    cd.feature_container = "features"

    # Mock the pipeline functions
    with (
        patch("classes.chromadiverse.resize_pdf"),  # as mock_resize,
        patch("classes.chromadiverse.azure_ocr") as mock_ocr,
        patch("classes.chromadiverse.merge_pipeline") as mock_merge,
        patch("classes.chromadiverse.column_merger_pipeline") as mock_col_merge,
        patch("classes.chromadiverse.consume_original_boxes") as mock_consume,
        patch("classes.chromadiverse.extract_bb_text") as mock_extract,
        patch("classes.chromadiverse.azure_ner") as mock_ner,
        patch("classes.chromadiverse.append_count_tfidf") as mock_append,
    ):
        mock_ocr.return_value = [[1, [["Test", 100, 100, 200, 120]]]]
        mock_merge.return_value = [[1, [["Test", 100, 100, 200, 120]]]]
        mock_col_merge.return_value = [[1, [["Test", 100, 100, 200, 120]]]]
        mock_consume.return_value = [[1, [["Test", 100, 100, 200, 120]]]]
        mock_extract.return_value = "Test text"
        mock_ner.return_value = [["Test", "Person"]]
        mock_append.return_value = [{"page_number": 0, "text": "Test"}]

        mock_file().read.return_value = json.dumps({"test": "data"})

        result = cd.extract_features(dpi=145, skip_blob_write=True)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "pdf_name" in parsed
        assert "features" in parsed
        assert "first ocr" in parsed


@patch("builtins.open", new_callable=mock_open)
def test_json_to_blob(mock_file, mock_env_vars, mock_blob_service, mock_azure_clients):
    """Test uploading JSON to blob storage."""
    cd = ChromaDiverse(pdf_name="test.pdf")

    mock_blob_client = MagicMock()
    cd.blob_service_client.get_blob_client.return_value = mock_blob_client

    mock_file().read.return_value = b'{"test": "data"}'

    result = cd.json_to_blob(container_name="test-container", path_file_to_blob="/tmp/test.json")

    assert result == "JSON uploaded to Blob."
    cd.blob_service_client.get_blob_client.assert_called_once()
    mock_blob_client.upload_blob.assert_called_once()


@patch("builtins.open", new_callable=mock_open)
def test_json_to_blob_with_suffix(mock_file, mock_env_vars, mock_blob_service, mock_azure_clients):
    """Test uploading JSON with suffix."""
    cd = ChromaDiverse(pdf_name="test.pdf")

    mock_blob_client = MagicMock()
    cd.blob_service_client.get_blob_client.return_value = mock_blob_client

    result = cd.json_to_blob(container_name="test-container", path_file_to_blob="/tmp/test.json", suffix="_labelled")

    assert result == "JSON uploaded to Blob."
    # Verify the blob name includes the suffix
    call_args = cd.blob_service_client.get_blob_client.call_args
    assert "_labelled.json" in str(call_args)


def test_load_all_models_deprecated(mock_env_vars, mock_blob_service, mock_azure_clients):
    """Test deprecated load_all_models method."""
    cd = ChromaDiverse(pdf_name="test.pdf")

    result = cd.load_all_models(program_model_path="path1", company_model_path="path2", donor_model_path="path3")

    assert "Azure OpenAI" in result


@patch("classes.chromadiverse.label_pages_with_openai")
@patch("builtins.open", new_callable=mock_open)
def test_make_predictions(mock_file, mock_label_pages, mock_env_vars, mock_blob_service, mock_azure_clients, mock_features_json):
    """Test making predictions with Azure OpenAI."""
    cd = ChromaDiverse(pdf_name="test.pdf")
    cd.labelled_container = "labelled"

    # Mock file reads
    mock_file().read.return_value = json.dumps(mock_features_json)
    mock_label_pages.return_value = ["Title", "Program"]

    json_str, labels = cd.make_predictions(skip_blob_write=True)

    assert isinstance(json_str, str)
    assert isinstance(labels, list)
    assert len(labels) == 2
    assert labels == ["Title", "Program"]

    parsed = json.loads(json_str)
    assert parsed["features"][0]["label"] == "Title"
    assert parsed["features"][1]["label"] == "Program"


@patch("classes.chromadiverse.label_pages_with_openai")
@patch("builtins.open", new_callable=mock_open)
def test_make_predictions_with_blob_upload(mock_file, mock_label_pages, mock_env_vars, mock_blob_service, mock_azure_clients, mock_features_json):
    """Test predictions with blob upload."""
    cd = ChromaDiverse(pdf_name="test.pdf")
    cd.labelled_container = "labelled"

    mock_blob_client = MagicMock()
    cd.blob_service_client.get_blob_client.return_value = mock_blob_client

    mock_file().read.return_value = json.dumps(mock_features_json)
    mock_label_pages.return_value = ["Title", "Program"]

    json_str, labels = cd.make_predictions(skip_blob_write=False)

    assert isinstance(json_str, str)
    mock_blob_client.upload_blob.assert_called_once()


@patch("classes.chromadiverse.label_pages_with_openai")
@patch("builtins.open", new_callable=mock_open)
def test_make_predictions_handles_more_pages_than_labels(mock_file, mock_label_pages, mock_env_vars, mock_blob_service, mock_azure_clients, mock_features_json):
    """Test predictions when there are more pages than labels."""
    cd = ChromaDiverse(pdf_name="test.pdf")

    # Add an extra page
    mock_features_json["features"].append({"page_number": 2, "text": "Test page 3"})

    mock_file().read.return_value = json.dumps(mock_features_json)
    mock_label_pages.return_value = ["Title", "Program"]  # Only 2 labels for 3 pages

    json_str, labels = cd.make_predictions(skip_blob_write=True)

    parsed = json.loads(json_str)
    # Third page should get "Other" label
    assert parsed["features"][2]["label"] == "Other"


@patch("classes.chromadiverse.label_pages_with_openai")
@patch("builtins.open", new_callable=mock_open)
def test_make_predictions_error_handling(mock_file, mock_label_pages, mock_env_vars, mock_blob_service, mock_azure_clients, mock_features_json):
    """Test error handling in predictions."""
    cd = ChromaDiverse(pdf_name="test.pdf")

    mock_file().read.return_value = json.dumps(mock_features_json)
    mock_label_pages.side_effect = Exception("OpenAI API Error")

    with pytest.raises(Exception) as exc_info:
        cd.make_predictions(skip_blob_write=True)

    assert "OpenAI API Error" in str(exc_info.value)


def test_chromadiverse_temp_file_paths(mock_env_vars, mock_blob_service, mock_azure_clients):
    """Test that temporary file paths are correctly constructed."""
    cd = ChromaDiverse(pdf_name="my_program.pdf")

    temp_dir = tempfile.gettempdir().replace("\\", "/")
    assert cd.temp_blob_pdf == f"{temp_dir}/my_program_blob.pdf"
    assert cd.temp_json == f"{temp_dir}/my_program_features.json"
    assert cd.prediction_json == f"{temp_dir}/my_program_predictions.json"
    assert cd.temp_pdf == f"{temp_dir}/"

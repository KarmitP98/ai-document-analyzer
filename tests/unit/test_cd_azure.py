import io
import json
import os
import re
import tempfile
import warnings
import zipfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from azure.ai.textanalytics import TextAnalyticsClient
from azure.cognitiveservices.vision.computervision.models import Line as ReadLine
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes, ReadOperationResult, ReadResult
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

from classes.src.cd_azure import (
    append_count_tfidf,
    azure_ner,
    azure_ocr,
    calculate_idf,
    check_overlap,
    column_merger_pipeline,
    combined_ner,
    consume_original_boxes,
    download_program_data,
    download_vocab,
    extract_bb_text,
    get_client_prefix,
    get_client_program_type,
    get_overlapped_boxes,
    merge_boxes,
    merge_pipeline,
    resize_pdf,
    sanitize_filename,
    text_ner,
    unmangle_utf8,
    update_entity_status,
)


@pytest.fixture
def mock_table_client():
    """Fixture for a mock TableClient."""
    return MagicMock()


@pytest.fixture
def mock_labelled_json():
    """Fixture for a mock labelled JSON."""
    with open("./data/json/mock_labelled.json", "r") as file:
        labelled_json = json.load(file)
    return labelled_json


@pytest.fixture
def mock_json_body(mock_labelled_json):
    """Fixture for a mock JSON body."""
    return {
        "pdf_name": mock_labelled_json["pdf_name"],
        "clientId": "fake-client-id",
        "features": mock_labelled_json["features"],
        "first ocr": mock_labelled_json["first ocr"],
        "final ocr": mock_labelled_json["final ocr"],
    }


@pytest.fixture
def mock_blob_service_client():
    """Fixture for a mock BlobServiceClient."""
    return MagicMock(spec=BlobServiceClient)


@pytest.fixture
def mock_table_service_client():
    """Fixture for a mock TableServiceClient."""
    return MagicMock(spec=TableServiceClient)


def test_azure_ocr(mocker):
    # Suppress DeprecationWarning for 'method_whitelist'
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="urllib3")

    load_dotenv("classes/env_var_folder/.env")
    original_pdf = "./data/pdf/OBC_Program 2003-11-07.pdf"
    processed_pdf = "./data/pdf/intermediate_pdf/OBC_Program 2003-11-07.pdf"
    dpi = 145
    # Mock the ComputerVisionClient
    mock_cv_client = mocker.Mock()

    # Mock the response of read_in_stream
    mock_read_response = mocker.Mock()
    mock_read_response.headers = {"Operation-Location": "https://example.com/operation-id"}
    mock_cv_client.read_in_stream.return_value = mock_read_response

    # Mock the response of get_read_result
    mock_read_result = mocker.Mock(spec=ReadOperationResult)
    mock_read_result.status = "succeeded"

    # Create mock read results
    mock_read_results = [
        mocker.Mock(
            spec=ReadResult,
            page=1,
            lines=[
                mocker.Mock(spec=ReadLine, bounding_box=[1.3857, 0.5241, 3.9703, 0.6318, 3.9416, 1.1344, 1.3785, 1.1272], text="1"),
                mocker.Mock(spec=ReadLine, bounding_box=[3.3744, 9.7283, 4.6236, 9.7355, 4.6236, 9.9221, 3.3744, 9.9149], text="2"),
                mocker.Mock(spec=ReadLine, bounding_box=[1.9887, 0.7539, 3.2882, 0.7467, 3.2954, 0.9262, 1.9887, 0.9405], text="3"),
                mocker.Mock(spec=ReadLine, bounding_box=[1.3498, 6.3898, 2.2759, 6.397, 2.2759, 6.6698, 1.3498, 6.6698], text="1"),
                mocker.Mock(spec=ReadLine, bounding_box=[2.6349, 6.3754, 3.08, 6.3754, 3.08, 6.6411, 2.6277, 6.6411], text="2"),
                mocker.Mock(spec=ReadLine, bounding_box=[1.3569, 6.6698, 2.2975, 6.6698, 2.2975, 6.9211, 1.3569, 6.9211], text="3"),
                mocker.Mock(spec=ReadLine, bounding_box=[2.6421, 6.6483, 3.0585, 6.6411, 3.0585, 6.7559, 2.6421, 6.7631], text="4"),
            ],
        ),
        mocker.Mock(
            spec=ReadResult,
            page=2,
            lines=[
                mocker.Mock(spec=ReadLine, bounding_box=[2.0031, 1.0698, 3.3026, 1.0698, 3.3026, 1.2277, 2.0031, 1.2349], text="1"),
                mocker.Mock(spec=ReadLine, bounding_box=[3.5108, 6.5621, 4.4154, 6.5477, 4.4226, 6.7201, 3.5108, 6.7344], text="5"),
                mocker.Mock(spec=ReadLine, bounding_box=[2.6421, 6.7847, 3.0585, 6.7847, 3.0657, 6.9211, 2.6421, 6.9211], text="6"),
            ],
        ),
        mocker.Mock(
            spec=ReadResult,
            page=3,
            lines=[
                mocker.Mock(spec=ReadLine, bounding_box=[0.8041, 9.8647, 4.638, 9.8575, 4.638, 10.0442, 0.8041, 10.0442], text="7"),
                mocker.Mock(spec=ReadLine, bounding_box=[0.4236, 10.0514, 5.0329, 10.0514, 5.0329, 10.238, 0.4236, 10.238], text="8"),
                mocker.Mock(spec=ReadLine, bounding_box=[0.3662, 10.2452, 5.0903, 10.2452, 5.0903, 10.4319, 0.3662, 10.4319], text="9"),
                mocker.Mock(spec=ReadLine, bounding_box=[1.4144, 10.4391, 4.0205, 10.4391, 4.0205, 10.6185, 1.4144, 10.6114], text="10"),
                mocker.Mock(spec=ReadLine, bounding_box=[4.2288, 10.8124, 5.2411, 10.8267, 5.2339, 10.9775, 4.2288, 10.9488], text="11"),
                mocker.Mock(spec=ReadLine, bounding_box=[2.24, 1.7877, 3.2882, 1.7805, 3.2954, 1.9385, 2.24, 1.9457], text="12"),
            ],
        ),
    ]
    mock_read_result.analyze_result = mocker.Mock()
    mock_read_result.status = OperationStatusCodes.succeeded
    mock_cv_client.get_read_result = mocker.Mock()

    mock_read_result.analyze_result.read_results = mock_read_results
    mock_cv_client.get_read_result.return_value = mock_read_result

    # Mock the azure_cv_client function to return the mocked client
    mocker.patch("classes.src.cd_azure.azure_cv_client", return_value=mock_cv_client)

    # Modelling
    resize_pdf(in_path=original_pdf, path_to_poppler="notebooks/poppler/poppler-22.01.0/Library/bin", out_path=processed_pdf, dpi=dpi)
    print("Resizing Done.")

    # Send and get response from Azure CV Client
    page_details = azure_ocr(pdf_name=processed_pdf, cv_client=mock_cv_client, dpi=dpi)
    print("OCR Done.")
    print(page_details)
    # a list of lists of length 2 where the first element is the page number
    # and the second element is a list of dictionaries with the bounding box coordinates
    # [17, []], [18, []]]
    # page numbers are 1-indexed in the output
    assert page_details is not None, "OCR failed to return page details."


def test_unmangle_utf8():
    # Test valid UTF-8 sequence
    result = re.sub(r"(?i)(?:\\u00[0-9a-f]{2})+", unmangle_utf8, "This is a valid UTF-8 sequence: €")
    assert result == "This is a valid UTF-8 sequence: €", "Failed to decode valid UTF-8 sequence"


def test_text_ner(mocker):
    # Mock the TextAnalyticsClient
    mock_ta_client = mocker.Mock(spec=TextAnalyticsClient)
    mock_response = mocker.Mock()
    mock_response.entities = [
        mocker.Mock(text="John Doe", category="Person", subcategory=None, confidence_score=0.95),
        mocker.Mock(text="Microsoft", category="Organization", subcategory=None, confidence_score=0.89),
        mocker.Mock(text="Jim", category="Person", subcategory=None, confidence_score=1),
    ]
    mock_ta_client.recognize_entities.return_value = [mock_response]

    # Test text_ner function
    text = "John Doe works at Microsoft."
    result = text_ner(mock_ta_client, text)
    assert len(result) == 3, "Failed to extract entities"
    assert result[0] == ["John Doe", "Person", None, 0.95], "Incorrect entity extraction"
    assert result[1] == ["Microsoft", "Organization", None, 0.89], "Incorrect entity extraction"
    # same test but with over 5000 characters
    very_long_text = "John Doe works at Microsoft."
    for i in range(5000):
        very_long_text += "Jim. "
    result = text_ner(mock_ta_client, very_long_text)
    assert len(result) >= 3, "Failed to extract entities"


def test_azure_ner(mocker):
    # Mock the text_ner function
    mocker.patch(
        "classes.src.cd_azure.text_ner",
        return_value=[
            ["John Doe", "Person", None, 0.95],
            ["Microsoft", "Organization", None, 0.89],
        ],
    )

    # Test azure_ner function
    text = ["John Doe works at Microsoft."]
    mock_ta_client = mocker.Mock(spec=TextAnalyticsClient)
    result = azure_ner(text, mock_ta_client, conf_threshold=0.9)
    assert len(result) == 1, "Failed to filter entities by confidence threshold"
    assert result[0][1] == [["John Doe", "Person", None, 0.95]], "Incorrect entity filtering"


def test_check_overlap():
    # Test overlapping boxes
    box1 = ["Text", 10, 10, 50, 50, 40, 40]
    box2 = ["Text", 30, 30, 70, 70, 40, 40]
    assert check_overlap(box1, box2, threshold=10) is True, "Failed to detect overlapping boxes"

    # Test non-overlapping boxes
    box2 = ["Text", 100, 100, 140, 140, 40, 40]
    assert check_overlap(box1, box2, threshold=10) is False, "Incorrectly detected overlap"


def test_get_overlapped_boxes():
    # Test overlapping boxes
    box1 = ["Text", 10, 10, 50, 50, 40, 40]
    parsed_info = [
        ["Text", 30, 30, 70, 70, 40, 40],
        ["Text", 100, 100, 140, 140, 40, 40],
    ]
    result = get_overlapped_boxes(box1, 0, parsed_info, threshold=10)
    assert result == [0], "Failed to detect overlapping boxes"


def test_merge_boxes():
    # Test merging multiple overlapping boxes row-wise
    overlaps = [0, 1, 2]
    parsed_info = [
        ["Text1", 10, 10, 50, 50, 40, 40],
        ["Text2", 30, 30, 70, 70, 40, 40],
        ["Text3", 20, 20, 60, 60, 40, 40],
    ]
    result_row = merge_boxes(overlaps, parsed_info, merge_by="row-wise", join_method=" ")

    # Check merged text for row-wise
    assert result_row[0] == "Text1 Text2 Text3", "Failed to merge text from multiple overlapping boxes row-wise"

    # Check merged bounding box coordinates for row-wise
    assert result_row[1:5] == [10, 10, 70, 70], "Failed to merge bounding box coordinates from multiple overlapping boxes row-wise"

    # Test merging multiple overlapping boxes column-wise
    overlaps = [0, 1, 2]
    parsed_info = [
        ["Text1", 10, 10, 50, 50, 40, 40],
        ["Text2", 10, 60, 50, 100, 40, 40],
        ["Text3", 10, 110, 50, 150, 40, 40],
    ]
    result_column = merge_boxes(overlaps, parsed_info, merge_by="column-wise", join_method=" ")

    # Check merged text for column-wise
    assert result_column[0] == "Text1 Text2 Text3", "Failed to merge text from multiple overlapping boxes column-wise"

    # Check merged bounding box coordinates for column-wise
    assert result_column[1:5] == [10, 10, 50, 150], "Failed to merge bounding box coordinates from multiple overlapping boxes column-wise"


def test_merge_pipeline():
    # Test merging pipeline
    parsed_info = [
        [1, [["Text1", 10, 10, 50, 50, 40, 40], ["Text2", 30, 30, 70, 70, 40, 40]]],
    ]
    result = merge_pipeline(parsed_info, threshold=10, merge_by="row-wise", join_method=" ")
    assert len(result) == 1, "Failed to process pages"
    assert len(result[0][1]) == 1, "Failed to merge bounding boxes"
    assert result[0][1][0][0] == "Text1 Text2", "Failed to merge text in pipeline"


def test_column_merger_pipeline():
    # Test merging bounding boxes with column structure
    merged_info = [
        [1, [["Text1", 10, 10, 50, 50, 40, 40], ["Text2", 10, 60, 50, 100, 40, 40]]],
        [2, [["Text3", 10, 10, 50, 50, 40, 40], ["Text4", 10, 60, 50, 100, 40, 40]]],
    ]
    result = column_merger_pipeline(merged_info, threshold=10)
    assert len(result) == 2, "Failed to process pages"
    assert len(result[0][1]) == 1, "Failed to merge bounding boxes for page 1"
    assert len(result[1][1]) == 1, "Failed to merge bounding boxes for page 2"


def test_consume_original_boxes():
    # Test consuming original bounding boxes and merging text
    column_merged = [
        [1, [["MergedText", 10, 10, 50, 50, 40, 40]]],
        [2, [["MergedText2", 10, 10, 50, 50, 40, 40]]],
    ]
    page_details = [
        [1, [["Text1", 10, 10, 50, 50, 40, 40], ["Text2", 30, 30, 70, 70, 40, 40]]],
        [2, [["Text3", 10, 10, 50, 50, 40, 40], ["Text4", 30, 30, 70, 70, 40, 40]]],
    ]
    result = consume_original_boxes(column_merged, page_details, join_method=" ")
    assert len(result) == 2, "Failed to process pages"
    assert result[0][1][0][0] == "Text1 Text2", "Failed to merge text for page 1"
    assert result[1][1][0][0] == "Text3 Text4", "Failed to merge text for page 2"


def test_extract_bb_text():
    # Test extracting text from bounding boxes
    parsed_info = [
        [1, [["Text1", 10, 10, 50, 50, 40, 40], ["Text2", 30, 30, 70, 70, 40, 40]]],
        [2, [["Text3", 10, 10, 50, 50, 40, 40], ["Text4", 30, 30, 70, 70, 40, 40]]],
    ]
    result = extract_bb_text(parsed_info, pages=[0, 1])
    assert len(result) == 4, "Failed to extract text from bounding boxes"
    assert result == ["Text1", "Text2", "Text3", "Text4"], "Incorrect text extraction"


def test_combined_ner(mocker):
    # Mock the TextAnalyticsClient
    mock_ta_client = mocker.Mock(spec=TextAnalyticsClient)
    mock_response = mocker.Mock()
    mock_response.entities = [
        mocker.Mock(text="John Doe", category="Person", subcategory=None, confidence_score=0.95),
        mocker.Mock(text="Microsoft", category="Organization", subcategory=None, confidence_score=0.89),
    ]
    mock_ta_client.recognize_entities.return_value = [mock_response]

    # Mock the SpaCy NLP model
    mock_spacy_nlp = mocker.Mock()
    mock_spacy_nlp.return_value.ents = [
        mocker.Mock(text="Microsoft", label_="ORG"),
        mocker.Mock(text="Python", label_="LANGUAGE"),
    ]

    # Test combined_ner function
    final_list = [
        [1, [["Text1", 10, 10, 50, 50, 40, 40]]],
        [2, [["Text2", 30, 30, 70, 70, 40, 40]]],
    ]
    result = combined_ner(final_list, mock_ta_client, mock_spacy_nlp, az_conf_threshold=0.5)
    assert len(result) == 2, "Failed to process pages"
    assert len(result[0]["details"]) == 1, "Failed to combine NER results for page 1"
    assert len(result[1]["details"]) == 1, "Failed to combine NER results for page 2"
    assert result[0]["details"][0][1][0][0] == "John Doe", "Failed to include Azure NER results"
    assert result[0]["details"][0][1][1][0] == "Microsoft", "Failed to include SpaCy NER results"


def test_calculate_idf():
    # Test when N is equal to doc_count
    N = 10
    doc_count = 10
    result = calculate_idf(N, doc_count)
    assert result < 0.11, "Failed to handle case where N equals doc_count"

    # Test when N is greater than doc_count
    N = 10
    doc_count = 5
    result = calculate_idf(N, doc_count)
    assert result > 0.3, "Failed to calculate IDF when N is greater than doc_count"


def test_append_count_tfidf():
    # Mock input data
    pdf_ner = [
        {
            "details": [
                ["Text1", [["Person", "Person", None, 0.9], ["Skill", "Skill", None, 0.8]]],
                ["Text2", [["Organization", "Org", None, 0.85]]],
            ]
        },
        {
            "details": [
                ["Text3", [["Location", "GPE", None, 0.7]]],
                ["Text4", [["Date", "DateTime", None, 0.95]]],
            ]
        },
    ]
    stop_words = set(["the", "and", "of"])

    # Test append_count_tfidf
    result = append_count_tfidf(pdf_ner, stop_words)
    assert "tf-idf" in result[0], "Failed to append TF-IDF scores"
    assert "person" in result[0]["tf-idf"], "Failed to calculate TF-IDF for 'person'"
    assert result[0]["tf-idf"]["person"] > 0, "TF-IDF score for 'person' should be greater than 0"


def test_update_entity_status_create_entity(mock_table_client):
    """Test update_entity_status when the entity does not exist."""
    # Mock the query_entities method to return an empty list
    mock_table_client.query_entities.return_value = []

    # Call the function
    pdf_name = "example.pdf"
    status = "Entity Tagging In Progress"
    update_entity_status(mock_table_client, pdf_name, status, None, None)

    # Assertions
    mock_table_client.query_entities.assert_called_once_with(f"PartitionKey eq '{pdf_name}'")
    mock_table_client.create_entity.assert_called_once()
    created_entity = mock_table_client.create_entity.call_args[1]["entity"]
    assert created_entity["PartitionKey"] == pdf_name
    assert created_entity["status"] == status


def test_update_entity_status_update_entity(mock_table_client):
    """Test update_entity_status when the entity already exists."""
    # Mock the query_entities method to return an existing entity
    existing_entity = {
        "PartitionKey": "example.pdf",
        "RowKey": "1",
        "status": "Pending",
        "updatedAt": "",
        "EntityTaggingStartTime": "",
        "EntityTaggingEndTime": "",
        "ErrorMessage": "",
    }
    mock_table_client.query_entities.return_value = [existing_entity]

    # Call the function
    pdf_name = "example.pdf"
    status = "Entity Tagging Completed"
    update_entity_status(mock_table_client, pdf_name, status, datetime.now(), datetime.now())

    # Assertions
    mock_table_client.query_entities.assert_called_once_with(f"PartitionKey eq '{pdf_name}'")
    mock_table_client.update_entity.assert_called_once()
    updated_entity = mock_table_client.update_entity.call_args[1]["entity"]
    assert updated_entity["PartitionKey"] == pdf_name
    assert updated_entity["status"] == status


def test_update_entity_status_with_error_message(mock_table_client):
    """Test update_entity_status with an error message."""
    # Mock the query_entities method to return an existing entity
    existing_entity = {
        "PartitionKey": "example.pdf",
        "RowKey": "1",
        "status": "Pending",
        "updatedAt": "",
        "EntityTaggingStartTime": "",
        "EntityTaggingEndTime": "",
        "ErrorMessage": "",
    }
    mock_table_client.query_entities.return_value = [existing_entity]

    # Call the function
    pdf_name = "example.pdf"
    status = "Entity Tagging Error"
    error_message = "An error occurred"
    update_entity_status(mock_table_client, pdf_name, status, datetime.now(), datetime.now(), error_message)

    # Assertions
    mock_table_client.query_entities.assert_called_once_with(f"PartitionKey eq '{pdf_name}'")
    mock_table_client.update_entity.assert_called_once()
    updated_entity = mock_table_client.update_entity.call_args[1]["entity"]
    assert updated_entity["PartitionKey"] == pdf_name
    assert updated_entity["status"] == status
    assert updated_entity["ErrorMessage"] == error_message


def test_get_client_program_type():
    # Mock the TableServiceClient and TableClient
    mock_table_service_client = MagicMock()
    mock_table_actual_client = MagicMock()
    mock_table_service_client.get_table_client.return_value = mock_table_actual_client

    # Mock the entity returned by next(query_entities())
    mock_entity = {"programType": "symphony"}
    mock_table_actual_client.query_entities.return_value = iter([mock_entity])

    # Call the function
    program_type = get_client_program_type(mock_table_service_client, client_id="fake-client-id")

    # Assertions
    mock_table_service_client.get_table_client.assert_called_once_with(table_name="Clients")
    mock_table_actual_client.query_entities.assert_called_once_with("PartitionKey eq 'fake-client-id'")
    assert program_type == "symphony"


def test_get_client_prefix():
    # Mock the TableServiceClient and TableClient
    mock_table_service_client = MagicMock()
    mock_table_actual_client = MagicMock()
    mock_table_service_client.get_table_client.return_value = mock_table_actual_client

    # Mock the entity returned by next(query_entities())
    mock_entity = {"prefix": "test"}
    mock_table_actual_client.query_entities.return_value = iter([mock_entity])

    # Call the function
    client_prefix = get_client_prefix(mock_table_service_client, client_id="fake-client-id")

    # Assertions
    mock_table_service_client.get_table_client.assert_called_once_with(table_name="Clients")
    mock_table_actual_client.query_entities.assert_called_once_with("PartitionKey eq 'fake-client-id'")
    assert client_prefix == "test"


def test_download_vocab(mock_json_body, mock_blob_service_client):
    """Test download_vocab for downloading vocab from Azure Blob Storage."""
    with patch("builtins.open", MagicMock()) as mock_open:
        mock_blob_client = MagicMock()
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        mock_blob_client.download_blob.return_value.readall.return_value = b'{"Choreographer": ["Mock Choreographer"]}'

        mock_open.return_value.__enter__.return_value.read.return_value = '{"Choreographer": ["Mock Choreographer"]}'

        temp_file_path = tempfile.gettempdir()
        vocab = download_vocab(mock_blob_service_client, mock_json_body["clientId"], temp_file_path)

        assert "Choreographer" in vocab
        assert vocab["Choreographer"] == ["Mock Choreographer"]
        mock_blob_service_client.get_blob_client.assert_called_once_with(container=f"data/{mock_json_body['clientId']}/vocabs", blob="vocab.json")
        mock_open.assert_called()


def test_download_program_data(monkeypatch, mocker):
    # Set up paths for mock data
    temp_file_path = "./data/program_assets"
    pdf_names = ["OBC_Program 2003-11-07.pdf"]
    entities_json_path = os.path.join("./data/json", "OBC_Program 2003-11-07_mt3_entities.json")
    pdf_path = os.path.join(temp_file_path, "OBC_Program 2003-11-07.pdf")

    monkeypatch.setenv("STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=Test123;AccountKey=Test123;EndpointSuffix=Test123")
    # Mock get_temp_file_path to return our data directory
    mocker.patch("classes.src.cd_azure.get_temp_file_path", return_value=temp_file_path)

    # Mock get_entity_list to return a mock entity for the PDF
    mock_entity = {"PartitionKey": "OBC_Program 2003-11-07.pdf"}
    mocker.patch("classes.src.cd_azure.get_entity_list", return_value=[mock_entity])

    # Mock download_json_from_blob to load the local entities JSON
    def mock_download_json_from_blob(blob_service_client, container_name, blob_name, temp_file_path):
        with open(entities_json_path, "r", encoding="utf-8") as f:
            import json

            return json.load(f)

    mocker.patch("classes.src.cd_azure.download_json_from_blob", side_effect=mock_download_json_from_blob)
    # Mock download_pdf to just return the local PDF path
    mocker.patch("classes.src.cd_azure.download_pdf", return_value=pdf_path)
    mocker.patch("classes.src.cd_azure.download_parsed_vocab", return_value=None)

    # Mock get_client_prefix and get_client_program_type
    mocker.patch("classes.src.cd_azure.get_client_prefix", return_value="Test")
    mocker.patch("classes.src.cd_azure.get_client_program_type", return_value="dance")

    # Mock TableServiceClient and BlobServiceClient
    mocker.patch("classes.src.cd_azure.TableServiceClient")
    mocker.patch("classes.src.cd_azure.BlobServiceClient")

    # Now call the function
    zip_bytes: bytes = download_program_data(client_id="fake-client-id", pdf_names=pdf_names)
    assert zip_bytes is not None, "Failed to download program data"
    assert isinstance(zip_bytes, bytes), "Downloaded data is not in bytes format"
    assert len(zip_bytes) > 0, "Downloaded data is empty"

    # Check if the zip file contains the expected files
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zip_file:
        file_list = zip_file.namelist()
        print(f"Files in zip: {file_list}")

        # Basic file existence checks
        assert "OBC_Program 2003-11-07.pdf" in file_list, "Main PDF not found in the zip"
        assert "OBC_Program 2003-11-07.json" in file_list, "Main JSON not found in the zip"

        # Check for individual performance files (filenames are uppercase from sanitize_filename)
        monopoly_pdf = "OBC_Program 2003-11-07_MONOPOLY.pdf"
        monopoly_json = "OBC_Program 2003-11-07_MONOPOLY.json"
        opus45_pdf = "OBC_Program 2003-11-07_OPUS 45.pdf"
        opus45_json = "OBC_Program 2003-11-07_OPUS 45.json"
        trois_pdf = "OBC_Program 2003-11-07_TROIS GYMNOPEDIES.pdf"
        trois_json = "OBC_Program 2003-11-07_TROIS GYMNOPEDIES.json"

        assert monopoly_pdf in file_list, f"Monopoly PDF not found: {monopoly_pdf}"
        assert monopoly_json in file_list, f"Monopoly JSON not found: {monopoly_json}"
        assert opus45_pdf in file_list, f"Opus 45 PDF not found: {opus45_pdf}"
        assert opus45_json in file_list, f"Opus 45 JSON not found: {opus45_json}"
        assert trois_pdf in file_list, f"Trois Gymnopedies PDF not found: {trois_pdf}"
        assert trois_json in file_list, f"Trois Gymnopedies JSON not found: {trois_json}"

        # Read and examine the main JSON file
        with zip_file.open("OBC_Program 2003-11-07.json") as main_json_file:
            main_json_data = json.load(main_json_file)
            print(f"Main JSON Performance Titles: {main_json_data.get('Test-Performance Title', [])}")

            # Main JSON should contain all performance titles
            main_performance_titles = main_json_data.get("Test-Performance Title", [])
            assert "MONOPOLY" in main_performance_titles, "Monopoly not found in main JSON"
            assert "OPUS 45" in main_performance_titles, "Opus 45 not found in main JSON"
            assert "TROIS GYMNOPEDIES" in main_performance_titles, "Trois Gymnopedies not found in main JSON"

        # Read and examine the Monopoly JSON file
        with zip_file.open(monopoly_json) as monopoly_json_file:
            monopoly_json_data = json.load(monopoly_json_file)
            print(f"Monopoly JSON Performance Titles: {monopoly_json_data.get('Test-Performance Title', [])}")

            # Monopoly JSON should ONLY contain "Monopoly" as performance title
            monopoly_performance_titles = monopoly_json_data.get("Test-Performance Title", [])
            assert "MONOPOLY" in monopoly_performance_titles, "Monopoly not found in its own JSON"
            assert "OPUS 45" not in monopoly_performance_titles, "Opus 45 incorrectly found in Monopoly JSON"
            assert "TROIS GYMNOPEDIES" not in monopoly_performance_titles, "Trois Gymnopedies incorrectly found in Monopoly JSON"

        # Read and examine the Opus 45 JSON file
        with zip_file.open(opus45_json) as opus45_json_file:
            opus45_json_data = json.load(opus45_json_file)
            print(f"OPUS 45 JSON Performance Titles: {opus45_json_data.get('Test-Performance Title', [])}")

            # Opus 45 JSON should ONLY contain "Opus 45" as performance title
            opus45_performance_titles = opus45_json_data.get("Test-Performance Title", [])
            assert "OPUS 45" in opus45_performance_titles, "Opus 45 not found in its own JSON"
            assert "MONOPOLY" not in opus45_performance_titles, "Monopoly incorrectly found in Opus 45 JSON"
            assert "TROIS GYMNOPEDIES" not in opus45_performance_titles, "Trois Gymnopedies incorrectly found in Opus 45 JSON"

        # Read and examine the Trois Gymnopedies JSON file
        with zip_file.open(trois_json) as trois_json_file:
            trois_json_data = json.load(trois_json_file)
            print(f"Trois Gymnopedies JSON Performance Titles: {trois_json_data.get('Test-Performance Title', [])}")

            # Trois Gymnopedies JSON should ONLY contain "Trois Gymnopedies" as performance title
            trois_performance_titles = trois_json_data.get("Test-Performance Title", [])
            assert "TROIS GYMNOPEDIES" in trois_performance_titles, "Trois Gymnopedies not found in its own JSON"
            assert "MONOPOLY" not in trois_performance_titles, "Monopoly incorrectly found in Trois Gymnopedies JSON"
            assert "OPUS 45" not in trois_performance_titles, "Opus 45 incorrectly found in Trois Gymnopedies JSON"

        print("All individual performance JSON files contain only their respective performance titles - TEST PASSED!")


def test_sanitize_filename():
    # Basic invalid characters
    assert sanitize_filename("Hello:World?") == "Hello_World_"
    assert (
        sanitize_filename("A*B|C<D>E\\F\\G\\H\\I\\J\\K\\L\\M\\N\\O\\P\\Q\\R\\S\\T\\U\\V\\W\\X\\Y\\Z") == "A_B_C_D_E_F_G_H_I_J_K_L_M_N_O_P_Q_R_S_T_U_V_W_X_Y_Z"
    )
    # Leading/trailing spaces and periods
    assert sanitize_filename("  file.txt  ") == "file.txt"
    assert sanitize_filename(".hiddenfile.") == "hiddenfile"
    # Only invalid chars
    assert sanitize_filename('<>:"/\\|?*') == "_" * 9
    # Reserved Windows device names (should not change, but not error)
    assert sanitize_filename("CON") == "CON"
    assert sanitize_filename("NUL.txt") == "NUL.txt"
    # Unicode and normal text
    assert sanitize_filename("演目:バレエ?") == "演目_バレエ_"
    # Empty string
    assert sanitize_filename("") == ""

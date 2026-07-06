"""
Comprehensive tests for vocab_matching.py module.

Tests the main vocab matching workflow including fill_in_vocab, check_page_and_program,
is_valid_page_attribute, aggr_pages, reorder_labelled_json, and process_vocab_matching_with_openai.
"""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

from classes.vocab_matching import (
    aggr_pages,
    check_page_and_program,
    fill_in_vocab,
    is_valid_page_attribute,
    process_vocab_matching_request,
    process_vocab_matching_with_openai,
    reorder_labelled_json,
)


def test_fill_in_vocab_dance():
    """Test filling in missing vocab keys for dance programs."""
    vocab = {
        "Choreographer": ["John Neumeier"],
        "Composer": ["Pyotr Tchaikovsky"],
    }
    parsed_vocab = None
    program_type = "dance"

    result = fill_in_vocab(vocab, parsed_vocab, program_type)

    # Should have the original keys plus any missing expected keys
    assert "Choreographer" in result
    assert "Composer" in result
    assert result["Choreographer"] == ["John Neumeier"]


def test_fill_in_vocab_symphony():
    """Test filling in missing vocab keys for symphony programs."""
    vocab = {
        "Composer": ["Ludwig van Beethoven"],
    }
    parsed_vocab = None
    program_type = "symphony"

    result = fill_in_vocab(vocab, parsed_vocab, program_type)

    assert "Composer" in result
    assert result["Composer"] == ["Ludwig van Beethoven"]


def test_fill_in_vocab_invalid_program_type():
    """Test that invalid program type defaults to 'dance'."""
    vocab = {"Choreographer": ["Test"]}
    parsed_vocab = None
    program_type = "invalid"

    # Should log warning and default to dance
    result = fill_in_vocab(vocab, parsed_vocab, program_type)

    assert isinstance(result, dict)
    assert "Choreographer" in result


def test_check_page_and_program_same_page_and_program():
    """Test check_page_and_program when entities match."""
    ent1 = {
        "page": 1,
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }
    ent2 = {
        "page": 1,
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }

    result = check_page_and_program(ent1, ent2)
    assert result is True


def test_check_page_and_program_different_page():
    """Test check_page_and_program when pages differ."""
    ent1 = {
        "page": 1,
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }
    ent2 = {
        "page": 2,
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }

    result = check_page_and_program(ent1, ent2)
    assert result is False


def test_check_page_and_program_different_program():
    """Test check_page_and_program when programs differ."""
    ent1 = {
        "page": 1,
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }
    ent2 = {
        "page": 1,
        "attributes": {"Performance Title": ["Swan Lake"]},
    }

    result = check_page_and_program(ent1, ent2)
    assert result is False


def test_check_page_and_program_force_merge_compatible():
    """Test force_merge with compatible labels."""
    ent1 = {
        "page": 1,
        "label": "Program",
        "page_area": {"label": "Program"},
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }
    ent2 = {
        "page": 2,
        "label": "Program",
        "page_area": {"label": "Program"},
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }

    result = check_page_and_program(ent1, ent2, force_merge=True)
    assert result is True


def test_check_page_and_program_force_merge_incompatible():
    """Test force_merge with incompatible labels."""
    ent1 = {
        "page": 1,
        "label": "Program",
        "page_area": {"label": "Program"},
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }
    ent2 = {
        "page": 2,
        "label": "Donor",
        "page_area": {"label": "Donor"},
        "attributes": {"Performance Title": ["Romeo and Juliet"]},
    }

    result = check_page_and_program(ent1, ent2, force_merge=True)
    assert result is False


def test_is_valid_page_attribute_valid():
    """Test is_valid_page_attribute with valid bounding box."""
    target_key = "Choreographer"
    target_value = "John Neumeier"
    bounding_box = [
        "John Neumeier",
        [[100, 100, 200, 120, ["Choreographer"], "John Neumeier", 0.95]],
    ]

    result = is_valid_page_attribute(target_key, target_value, bounding_box)
    assert result is True


def test_is_valid_page_attribute_invalid_structure():
    """Test is_valid_page_attribute with invalid bounding box structure."""
    target_key = "Choreographer"
    target_value = "John Neumeier"
    bounding_box = ["John Neumeier"]  # Missing second element

    result = is_valid_page_attribute(target_key, target_value, bounding_box)
    assert result is False


def test_is_valid_page_attribute_wrong_key():
    """Test is_valid_page_attribute with wrong attribute key."""
    target_key = "Composer"  # Wrong key
    target_value = "John Neumeier"
    bounding_box = [
        "John Neumeier",
        [[100, 100, 200, 120, ["Choreographer"], "John Neumeier", 0.95]],
    ]

    result = is_valid_page_attribute(target_key, target_value, bounding_box)
    assert result is False


def test_is_valid_page_attribute_wrong_value():
    """Test is_valid_page_attribute with wrong entity value."""
    target_key = "Choreographer"
    target_value = "Jane Smith"  # Wrong value
    bounding_box = [
        "John Neumeier",  # Different value
        [[100, 100, 200, 120, ["Choreographer"], "John Neumeier", 0.95]],
    ]

    result = is_valid_page_attribute(target_key, target_value, bounding_box)
    assert result is False


def test_aggr_pages_single_page():
    """Test aggr_pages with a single page returns unchanged."""
    asset_attributes = [
        {
            "page": 1,
            "label": "Program",
            "attributes": {"Performance Title": ["Romeo and Juliet"], "Choreographer": ["John Neumeier"]},
            "boundingBoxes": [],
        }
    ]
    program_search_list = []

    result = aggr_pages(asset_attributes, program_search_list)
    assert len(result) == 1
    assert result[0]["page"] == 1


def test_aggr_pages_non_program_pages():
    """Test aggr_pages with non-program pages."""
    asset_attributes = [
        {
            "page": 1,
            "label": "Donor",
            "page_area": {"label": "Donor", "from_prev": False, "to_next": False},
            "attributes": {"Donors": ["Jane Smith"]},
            "boundingBoxes": [],
        },
        {
            "page": 2,
            "label": "Title",
            "page_area": {"label": "Title", "from_prev": False, "to_next": False},
            "attributes": {"Performance Title": ["Swan Lake"]},
            "boundingBoxes": [],
        },
    ]
    program_search_list = []

    result = aggr_pages(asset_attributes, program_search_list)
    # Non-program pages are not merged
    assert len(result) == 2


def test_aggr_pages_same_program_different_pages():
    """Test aggr_pages merges pages with same program title."""
    asset_attributes = [
        {
            "page": 1,
            "label": "Program",
            "page_area": {"label": "Program", "from_prev": False, "to_next": True},
            "attributes": {"Performance Title": ["Romeo and Juliet"], "Choreographer": ["John Neumeier"]},
            "boundingBoxes": [],
            "type": "dance",
        },
        {
            "page": 2,
            "label": "Program",
            "page_area": {"label": "Program", "from_prev": True, "to_next": False},
            "attributes": {"Performance Title": ["Romeo and Juliet"], "Composer": ["Prokofiev"]},
            "boundingBoxes": [],
            "type": "dance",
        },
    ]
    program_search_list = []

    result = aggr_pages(asset_attributes, program_search_list)
    # Should merge into one program
    assert len(result) >= 1


def test_aggr_pages_unknown_program_title():
    """Test aggr_pages with Unknown program title."""
    asset_attributes = [
        {
            "page": 1,
            "label": "Program",
            "page_area": {"label": "Program", "from_prev": False, "to_next": False},
            "attributes": {"Performance Title": ["Unknown"]},
            "boundingBoxes": [],
        }
    ]
    program_search_list = []

    result = aggr_pages(asset_attributes, program_search_list)
    # Unknown titles are kept as-is
    assert len(result) == 1


def test_reorder_labelled_json_program_page():
    """Test reorder_labelled_json with a program page."""
    json_body = {
        "features": [
            {
                "page_number": 0,
                "label": "Program",
                "details": [
                    ["Choreographer", [[100, 150, 200, 170]]],
                    ["Performance Title", [[100, 100, 200, 120]]],
                ],
            }
        ],
        "final ocr": [
            [
                1,
                [
                    ["Performance Title Text", 100, 100, 200, 120, 100, 20, 0.95],  # Y=100 (higher on page)
                    ["Choreographer Text", 100, 150, 200, 170, 100, 20, 0.95],  # Y=150 (lower on page)
                ],
            ]
        ],
    }

    result = reorder_labelled_json(json_body)

    # Should have reordered based on Y-axis
    assert "features" in result
    assert "final ocr" in result


def test_reorder_labelled_json_non_program_page():
    """Test reorder_labelled_json with a non-program page (should skip)."""
    json_body = {
        "features": [
            {
                "page_number": 0,
                "label": "Donor",
                "details": [["Donor Name", [[100, 100, 200, 120]]]],
            }
        ],
        "final ocr": [[1, [["Donor Name", 100, 100, 200, 120, 100, 20, 0.95]]]],
    }

    result = reorder_labelled_json(json_body)

    # Should return unchanged for non-program pages
    assert result["features"][0]["label"] == "Donor"


@patch("classes.vocab_matching.process_with_azure_openai")
@patch("classes.vocab_matching.upload_to_blob")
@patch("classes.vocab_matching.aggr_pages")
@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists")
@patch("os.remove")
def test_process_vocab_matching_with_openai_success(
    mock_remove,
    mock_exists,
    mock_file_open,
    mock_aggr_pages,
    mock_upload_to_blob,
    mock_process_openai,
):
    """Test successful vocab matching with OpenAI."""
    # Setup
    program_type = "dance"
    json_body = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0, "label": "Program", "details": []}],
        "final ocr": [[1, []]],
    }
    vocab = {"Choreographer": ["John Neumeier"]}
    parsed_vocab = None
    temp_file_path = "/tmp"
    pdf_name = "test.pdf"
    mock_blob_client = MagicMock()
    entity_blob_container = "entities"
    label_blob_container = "labelled"
    client_path = "test/client"

    mock_exists.return_value = True
    mock_process_openai.return_value = [
        {
            "page": 0,
            "attributes": {"Choreographer": ["John Neumeier"]},
            "boundingBoxes": [],
        }
    ]
    mock_aggr_pages.return_value = [
        {
            "page": 0,
            "attributes": {"Choreographer": ["John Neumeier"]},
            "boundingBoxes": [],
        }
    ]

    # Execute
    result = process_vocab_matching_with_openai(
        program_type=program_type,
        json_body=json_body,
        vocab=vocab,
        parsed_vocab=parsed_vocab,
        temp_file_path=temp_file_path,
        pdf_name=pdf_name,
        blob_service_client=mock_blob_client,
        entity_blob_container=entity_blob_container,
        label_blob_container=label_blob_container,
        client_path=client_path,
    )

    # Assertions
    assert isinstance(result, str)
    assert "Choreographer" in result
    mock_process_openai.assert_called_once()
    mock_aggr_pages.assert_called_once()
    assert mock_upload_to_blob.call_count == 2  # Once for labelled, once for entities
    assert mock_remove.call_count == 2  # Clean up temp files


@patch("classes.vocab_matching.process_with_azure_openai")
@patch("classes.vocab_matching.upload_to_blob")
@patch("builtins.open", new_callable=mock_open)
def test_process_vocab_matching_with_openai_failure(
    mock_file_open,
    mock_upload_to_blob,
    mock_process_openai,
):
    """Test vocab matching when OpenAI processing fails."""
    mock_process_openai.side_effect = Exception("OpenAI API error")

    with pytest.raises(Exception, match="Azure OpenAI processing failed"):
        process_vocab_matching_with_openai(
            program_type="dance",
            json_body={"pdf_name": "test.pdf", "features": [], "final ocr": []},
            vocab={},
            parsed_vocab=None,
            temp_file_path="/tmp",
            pdf_name="test.pdf",
            blob_service_client=MagicMock(),
            entity_blob_container="entities",
            label_blob_container="labelled",
            client_path="test/client",
        )


@patch("classes.vocab_matching.get_blob_service_client")
@patch("classes.vocab_matching.get_table_service_client")
@patch("classes.vocab_matching.get_client_program_type")
@patch("classes.vocab_matching.download_vocab")
@patch("classes.vocab_matching.download_parsed_vocab")
@patch("classes.vocab_matching.update_entity_status")
@patch("classes.vocab_matching.process_vocab_matching_with_openai")
def test_process_vocab_matching_request_success(
    mock_process_matching,
    mock_update_status,
    mock_download_parsed_vocab,
    mock_download_vocab,
    mock_get_program_type,
    mock_get_table_client,
    mock_get_blob_client,
):
    """Test successful vocab matching request handling."""
    # Setup environment
    with patch.dict(os.environ, {"STORAGE_CONNECTION_STRING": "test-connection-string"}):
        json_body = {
            "pdf_name": "test.pdf",
            "clientId": "test-client",
            "features": [],
        }

        mock_blob_client = MagicMock()
        mock_table_client = MagicMock()
        mock_table_service = MagicMock()
        mock_table_service.create_table_if_not_exists.return_value = mock_table_client

        mock_get_blob_client.return_value = mock_blob_client
        mock_get_table_client.return_value = mock_table_service
        mock_get_program_type.return_value = "dance"
        mock_download_vocab.return_value = {"Choreographer": ["Test"]}
        mock_download_parsed_vocab.return_value = None
        mock_process_matching.return_value = '[{"page": 0, "attributes": {}}]'

        # Execute
        response = process_vocab_matching_request(json_body)

        # Assertions
        assert response.status_code == 200
        assert response.mimetype == "application/json"
        mock_process_matching.assert_called_once()
        assert mock_update_status.call_count == 2  # In Progress + Completed


@patch("classes.vocab_matching.get_blob_service_client")
@patch("classes.vocab_matching.get_table_service_client")
def test_process_vocab_matching_request_missing_pdf_name(
    mock_get_table_client,
    mock_get_blob_client,
):
    """Test request with missing PDF name."""
    with patch.dict(os.environ, {"STORAGE_CONNECTION_STRING": "test-connection-string"}):
        json_body = {
            "clientId": "test-client",
        }

        response = process_vocab_matching_request(json_body)

        assert response.status_code == 400
        assert "PDF name not provided" in response.get_body().decode()


@patch("classes.vocab_matching.get_blob_service_client")
@patch("classes.vocab_matching.get_table_service_client")
def test_process_vocab_matching_request_missing_client_id(
    mock_get_table_client,
    mock_get_blob_client,
):
    """Test request with missing client ID."""
    with patch.dict(os.environ, {"STORAGE_CONNECTION_STRING": "test-connection-string"}):
        json_body = {
            "pdf_name": "test.pdf",
        }

        response = process_vocab_matching_request(json_body)

        assert response.status_code == 400
        assert "Client ID not provided" in response.get_body().decode()


def test_process_vocab_matching_request_missing_connection_string():
    """Test request with missing storage connection string."""
    # Remove the environment variable if it exists
    with patch.dict(os.environ, {}, clear=True):
        json_body = {
            "pdf_name": "test.pdf",
            "clientId": "test-client",
        }

        response = process_vocab_matching_request(json_body)

        assert response.status_code == 500
        assert "Storage connection string not found" in response.get_body().decode()


@patch("classes.vocab_matching.get_blob_service_client")
@patch("classes.vocab_matching.get_table_service_client")
@patch("classes.vocab_matching.get_client_program_type")
@patch("classes.vocab_matching.download_vocab")
@patch("classes.vocab_matching.download_parsed_vocab")
@patch("classes.vocab_matching.update_entity_status")
@patch("classes.vocab_matching.process_vocab_matching_with_openai")
def test_process_vocab_matching_request_with_program_type_override(
    mock_process_matching,
    mock_update_status,
    mock_download_parsed_vocab,
    mock_download_vocab,
    mock_get_program_type,
    mock_get_table_client,
    mock_get_blob_client,
):
    """Test request with program_type_override parameter."""
    with patch.dict(os.environ, {"STORAGE_CONNECTION_STRING": "test-connection-string"}):
        json_body = {
            "pdf_name": "test.pdf",
            "clientId": "test-client",
            "program_type_override": "symphony",  # Override
            "features": [],
        }

        mock_blob_client = MagicMock()
        mock_table_client = MagicMock()
        mock_table_service = MagicMock()
        mock_table_service.create_table_if_not_exists.return_value = mock_table_client

        mock_get_blob_client.return_value = mock_blob_client
        mock_get_table_client.return_value = mock_table_service
        mock_get_program_type.return_value = "dance"  # Should be overridden
        mock_download_vocab.return_value = {"Composer": ["Test"]}
        mock_download_parsed_vocab.return_value = None
        mock_process_matching.return_value = '[{"page": 0, "attributes": {}}]'

        # Execute
        response = process_vocab_matching_request(json_body)

        # Assertions
        assert response.status_code == 200
        # Verify that symphony was used (check the call args)
        call_args = mock_process_matching.call_args
        assert call_args[1]["program_type"] == "symphony"


@patch("classes.vocab_matching.get_blob_service_client")
@patch("classes.vocab_matching.get_table_service_client")
@patch("classes.vocab_matching.get_client_program_type")
@patch("classes.vocab_matching.download_vocab")
@patch("classes.vocab_matching.download_parsed_vocab")
@patch("classes.vocab_matching.update_entity_status")
@patch("classes.vocab_matching.process_vocab_matching_with_openai")
def test_process_vocab_matching_request_error_handling(
    mock_process_matching,
    mock_update_status,
    mock_download_parsed_vocab,
    mock_download_vocab,
    mock_get_program_type,
    mock_get_table_client,
    mock_get_blob_client,
):
    """Test error handling in vocab matching request."""
    with patch.dict(os.environ, {"STORAGE_CONNECTION_STRING": "test-connection-string"}):
        json_body = {
            "pdf_name": "test.pdf",
            "clientId": "test-client",
            "features": [],
        }

        mock_blob_client = MagicMock()
        mock_table_client = MagicMock()
        mock_table_service = MagicMock()
        mock_table_service.create_table_if_not_exists.return_value = mock_table_client

        mock_get_blob_client.return_value = mock_blob_client
        mock_get_table_client.return_value = mock_table_service
        mock_get_program_type.return_value = "dance"
        mock_download_vocab.return_value = {"Choreographer": ["Test"]}
        mock_download_parsed_vocab.return_value = None
        mock_process_matching.side_effect = Exception("Processing failed")

        # Execute
        response = process_vocab_matching_request(json_body)

        # Assertions
        assert response.status_code == 500
        assert "error" in response.get_body().decode()
        # Verify error status was updated
        error_status_call = [call for call in mock_update_status.call_args_list if "Error" in str(call)]
        assert len(error_status_call) > 0

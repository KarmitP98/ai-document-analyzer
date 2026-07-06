"""
Comprehensive tests for process_with_azure_openai function.

This function is the main entry point for Azure OpenAI entity matching with batching support.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from classes.src.azure_openai_helper import process_with_azure_openai


@pytest.fixture
def mock_env_vars():
    """Set up Azure OpenAI environment variables."""
    with patch.dict(
        os.environ,
        {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o",
        },
    ):
        yield


@pytest.fixture
def sample_labeled_json():
    """Sample labeled JSON with OCR data."""
    return {
        "pdf_name": "test_program.pdf",
        "features": [
            {
                "page_number": 0,
                "label": "Program",
                "page_areas": [{"label": "Program"}],
            },
            {
                "page_number": 1,
                "label": "Donor",
                "page_areas": [{"label": "Donor"}],
            },
        ],
        "final ocr": [
            [1, [["John Neumeier", 100, 100, 200, 120, 100, 20, 0.95]]],
            [2, [["Jane Smith", 100, 100, 200, 120, 100, 20, 0.95]]],
        ],
        "first ocr": [
            [1, [["John Neumeier", 100, 100, 200, 120, 100, 20, 0.95]]],
            [2, [["Jane Smith", 100, 100, 200, 120, 100, 20, 0.95]]],
        ],
    }


@pytest.fixture
def sample_vocab_json():
    """Sample vocabulary JSON."""
    return {
        "Choreographer": ["John Neumeier", "William Forsythe"],
        "Composer": ["Pyotr Tchaikovsky"],
        "Donors": ["Jane Smith", "John Doe"],
    }


@pytest.fixture
def mock_blob_client():
    """Mock BlobServiceClient."""
    return MagicMock()


@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
@patch("classes.src.azure_openai_helper.build_openai_prompt")
@patch("classes.src.azure_openai_helper.call_azure_openai")
@patch("classes.src.azure_openai_helper.parse_openai_response")
@patch("classes.src.azure_openai_helper.filter_invalid_categories")
@patch("classes.src.azure_openai_helper.convert_indices_to_bounding_boxes")
@patch("classes.src.azure_openai_helper.find_missing_bounding_boxes")
def test_process_with_azure_openai_basic(
    mock_find_missing,
    mock_convert_indices,
    mock_filter_invalid,
    mock_parse,
    mock_call_openai,
    mock_build_prompt,
    mock_download_context,
    mock_download_template,
    mock_env_vars,
    sample_labeled_json,
    sample_vocab_json,
    mock_blob_client,
):
    """Test basic processing with Azure OpenAI."""
    # Setup mocks
    mock_download_template.return_value = {"system_prompt": "test", "user_prompt": "test"}
    mock_download_context.return_value = {"notes": "test notes"}
    mock_build_prompt.return_value = [{"role": "user", "content": "test"}]
    mock_call_openai.return_value = {"choices": [{"message": {"content": '[{"page": 0, "attributes": {"Choreographer": ["John Neumeier"]}}]'}}]}
    mock_parse.return_value = [{"page": 0, "attributes": {"Choreographer": ["John Neumeier"]}}]
    mock_filter_invalid.return_value = [{"page": 0, "attributes": {"Choreographer": ["John Neumeier"]}}]
    mock_convert_indices.return_value = [{"page": 0, "attributes": {"Choreographer": ["John Neumeier"]}, "boundingBoxes": []}]
    mock_find_missing.return_value = [{"page": 0, "attributes": {"Choreographer": ["John Neumeier"]}, "boundingBoxes": []}]

    result = process_with_azure_openai(
        labeled_json=sample_labeled_json,
        vocab_json=sample_vocab_json,
        blob_service_client=mock_blob_client,
        client_path="test/client",
        temp_file_path="/tmp",
        program_type="dance",
        batch_size=2,
    )

    # Assertions
    assert len(result) > 0
    mock_download_template.assert_called_once()
    mock_download_context.assert_called_once()
    mock_call_openai.assert_called()


@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
def test_process_with_azure_openai_missing_env_vars(
    mock_download_context,
    mock_download_template,
    sample_labeled_json,
    sample_vocab_json,
    mock_blob_client,
):
    """Test that missing environment variables raises an exception."""
    # Don't set env vars - they should be missing
    with pytest.raises(Exception, match="AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set"):
        process_with_azure_openai(
            labeled_json=sample_labeled_json,
            vocab_json=sample_vocab_json,
            blob_service_client=mock_blob_client,
            client_path="test/client",
            temp_file_path="/tmp",
            program_type="dance",
        )


@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
def test_process_with_azure_openai_filters_other_pages(
    mock_download_context,
    mock_download_template,
    mock_env_vars,
    sample_vocab_json,
    mock_blob_client,
):
    """Test that pages labeled as 'Other' are filtered out."""
    labeled_json = {
        "pdf_name": "test_program.pdf",
        "features": [
            {"page_number": 0, "label": "Other", "page_areas": [{"label": "Other"}]},
            {"page_number": 1, "label": "Program", "page_areas": [{"label": "Program"}]},
            {"page_number": 2, "label": "Other", "page_areas": [{"label": "Other"}]},
        ],
        "first ocr": [
            [1, [["Text1", 100, 100, 200, 120, 100, 20, 0.95]]],
            [2, [["Text2", 100, 100, 200, 120, 100, 20, 0.95]]],
            [3, [["Text3", 100, 100, 200, 120, 100, 20, 0.95]]],
        ],
    }

    mock_download_template.return_value = {"system_prompt": "test", "user_prompt": "test"}
    mock_download_context.return_value = {}

    with patch("classes.src.azure_openai_helper.build_openai_prompt") as mock_build:
        with patch("classes.src.azure_openai_helper.call_azure_openai") as mock_call:
            with patch("classes.src.azure_openai_helper.parse_openai_response") as mock_parse:
                with patch("classes.src.azure_openai_helper.filter_invalid_categories") as mock_filter:
                    with patch("classes.src.azure_openai_helper.convert_indices_to_bounding_boxes") as mock_convert:
                        with patch("classes.src.azure_openai_helper.find_missing_bounding_boxes") as mock_find:
                            mock_build.return_value = [{"role": "user", "content": "test"}]
                            mock_call.return_value = {"choices": [{"message": {"content": '[{"page": 1, "attributes": {"Choreographer": ["Test"]}}]'}}]}
                            mock_parse.return_value = [{"page": 1, "attributes": {"Choreographer": ["Test"]}}]
                            mock_filter.return_value = [{"page": 1, "attributes": {"Choreographer": ["Test"]}}]
                            mock_convert.return_value = [{"page": 1, "attributes": {"Choreographer": ["Test"]}, "boundingBoxes": []}]
                            mock_find.return_value = [{"page": 1, "attributes": {"Choreographer": ["Test"]}, "boundingBoxes": []}]

                            result = process_with_azure_openai(
                                labeled_json=labeled_json,
                                vocab_json=sample_vocab_json,
                                blob_service_client=mock_blob_client,
                                client_path="test/client",
                                temp_file_path="/tmp",
                                program_type="dance",
                                batch_size=5,
                            )

                            # Should only process 1 page (page 1)
                            assert len(result) > 0
                            # Verify that only the Program page was included in processing
                            mock_build.assert_called()


@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
def test_process_with_azure_openai_all_other_pages(
    mock_download_context,
    mock_download_template,
    mock_env_vars,
    sample_vocab_json,
    mock_blob_client,
):
    """Test that when all pages are 'Other', returns empty list."""
    labeled_json = {
        "pdf_name": "test_program.pdf",
        "features": [
            {"page_number": 0, "label": "Other"},
            {"page_number": 1, "label": "Other"},
        ],
        "first ocr": [[1, []], [2, []]],
    }

    mock_download_template.return_value = {"system_prompt": "test", "user_prompt": "test"}
    mock_download_context.return_value = {}

    result = process_with_azure_openai(
        labeled_json=labeled_json,
        vocab_json=sample_vocab_json,
        blob_service_client=mock_blob_client,
        client_path="test/client",
        temp_file_path="/tmp",
        program_type="dance",
    )

    assert result == []


@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
@patch("classes.src.azure_openai_helper.process_large_page_with_chunking")
@patch("classes.src.azure_openai_helper.build_openai_prompt")
@patch("classes.src.azure_openai_helper.call_azure_openai")
@patch("classes.src.azure_openai_helper.parse_openai_response")
@patch("classes.src.azure_openai_helper.filter_invalid_categories")
@patch("classes.src.azure_openai_helper.convert_indices_to_bounding_boxes")
@patch("classes.src.azure_openai_helper.find_missing_bounding_boxes")
def test_process_with_azure_openai_large_pages(
    mock_find_missing,
    mock_convert_indices,
    mock_filter_invalid,
    mock_parse,
    mock_call_openai,
    mock_build_prompt,
    mock_process_chunking,
    mock_download_context,
    mock_download_template,
    mock_env_vars,
    sample_vocab_json,
    mock_blob_client,
):
    """Test processing large pages with chunking."""
    # Create a page with >150 OCR entries to trigger chunking
    large_ocr_entries = [[i, f"Entry {i}", 100, 100, 200, 120, 100, 20, 0.95] for i in range(200)]

    labeled_json = {
        "pdf_name": "test_program.pdf",
        "features": [
            {"page_number": 0, "label": "Donor", "page_areas": [{"label": "Donor"}]},
        ],
        "first ocr": [[1, large_ocr_entries]],
    }

    mock_download_template.return_value = {"system_prompt": "test", "user_prompt": "test"}
    mock_download_context.return_value = {}
    mock_process_chunking.return_value = [{"page": 0, "attributes": {"Donors": ["Test"]}, "boundingBoxes": []}]

    result = process_with_azure_openai(
        labeled_json=labeled_json,
        vocab_json=sample_vocab_json,
        blob_service_client=mock_blob_client,
        client_path="test/client",
        temp_file_path="/tmp",
        program_type="dance",
        batch_size=1,
    )

    # Should have called chunking for large page
    mock_process_chunking.assert_called_once()
    assert len(result) > 0


@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
@patch("classes.src.azure_openai_helper.build_openai_prompt")
@patch("classes.src.azure_openai_helper.call_azure_openai")
@patch("classes.src.azure_openai_helper.parse_openai_response")
@patch("classes.src.azure_openai_helper.filter_invalid_categories")
@patch("classes.src.azure_openai_helper.convert_indices_to_bounding_boxes")
@patch("classes.src.azure_openai_helper.find_missing_bounding_boxes")
def test_process_with_azure_openai_batching(
    mock_find_missing,
    mock_convert_indices,
    mock_filter_invalid,
    mock_parse,
    mock_call_openai,
    mock_build_prompt,
    mock_download_context,
    mock_download_template,
    mock_env_vars,
    sample_vocab_json,
    mock_blob_client,
):
    """Test batching of multiple pages."""
    # Create 5 pages to test batching with batch_size=2
    labeled_json = {
        "pdf_name": "test_program.pdf",
        "features": [{"page_number": i, "label": "Program", "page_areas": [{"label": "Program"}]} for i in range(5)],
        "first ocr": [[i + 1, [[f"Entry {i}", 100, 100, 200, 120, 100, 20, 0.95]]] for i in range(5)],
    }

    mock_download_template.return_value = {"system_prompt": "test", "user_prompt": "test"}
    mock_download_context.return_value = {}
    mock_build_prompt.return_value = [{"role": "user", "content": "test"}]

    # Return different responses for each call
    mock_call_openai.side_effect = [
        {"choices": [{"message": {"content": f'[{{"page": {i}, "attributes": {{"Choreographer": ["Test {i}"]}}}}]'}}]}
        for i in range(3)  # 5 pages / batch_size 2 = 3 batches
    ]

    mock_parse.side_effect = [[{"page": i, "attributes": {"Choreographer": [f"Test {i}"]}}] for i in range(3)]

    mock_filter_invalid.side_effect = [[{"page": i, "attributes": {"Choreographer": [f"Test {i}"]}}] for i in range(3)]

    mock_convert_indices.side_effect = [[{"page": i, "attributes": {"Choreographer": [f"Test {i}"]}, "boundingBoxes": []}] for i in range(3)]

    mock_find_missing.side_effect = [[{"page": i, "attributes": {"Choreographer": [f"Test {i}"]}, "boundingBoxes": []}] for i in range(3)]

    result = process_with_azure_openai(
        labeled_json=labeled_json,
        vocab_json=sample_vocab_json,
        blob_service_client=mock_blob_client,
        client_path="test/client",
        temp_file_path="/tmp",
        program_type="dance",
        batch_size=2,
    )

    # Should have processed all 5 pages in 3 batches (2+2+1)
    assert len(result) == 3
    # Should have called OpenAI 3 times (for 3 batches)
    assert mock_call_openai.call_count == 3


@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
def test_process_with_azure_openai_page_areas_priority(
    mock_download_context,
    mock_download_template,
    mock_env_vars,
    sample_vocab_json,
    mock_blob_client,
):
    """Test that page_areas label takes priority over root label."""
    # Root label says "Other" but page_areas says "Program"
    labeled_json = {
        "pdf_name": "test_program.pdf",
        "features": [
            {"page_number": 0, "label": "Other", "page_areas": [{"label": "Program"}]},  # Should be processed
            {"page_number": 1, "label": "Program", "page_areas": [{"label": "Other"}]},  # Should be skipped
        ],
        "first ocr": [
            [1, [["Text1", 100, 100, 200, 120, 100, 20, 0.95]]],
            [2, [["Text2", 100, 100, 200, 120, 100, 20, 0.95]]],
        ],
    }

    mock_download_template.return_value = {"system_prompt": "test", "user_prompt": "test"}
    mock_download_context.return_value = {}

    with patch("classes.src.azure_openai_helper.build_openai_prompt") as mock_build:
        with patch("classes.src.azure_openai_helper.call_azure_openai") as mock_call:
            with patch("classes.src.azure_openai_helper.parse_openai_response") as mock_parse:
                with patch("classes.src.azure_openai_helper.filter_invalid_categories") as mock_filter:
                    with patch("classes.src.azure_openai_helper.convert_indices_to_bounding_boxes") as mock_convert:
                        with patch("classes.src.azure_openai_helper.find_missing_bounding_boxes") as mock_find:
                            mock_build.return_value = [{"role": "user", "content": "test"}]
                            mock_call.return_value = {"choices": [{"message": {"content": '[{"page": 0, "attributes": {"Choreographer": ["Test"]}}]'}}]}
                            mock_parse.return_value = [{"page": 0, "attributes": {"Choreographer": ["Test"]}}]
                            mock_filter.return_value = [{"page": 0, "attributes": {"Choreographer": ["Test"]}}]
                            mock_convert.return_value = [{"page": 0, "attributes": {"Choreographer": ["Test"]}, "boundingBoxes": []}]
                            mock_find.return_value = [{"page": 0, "attributes": {"Choreographer": ["Test"]}, "boundingBoxes": []}]

                            result = process_with_azure_openai(
                                labeled_json=labeled_json,
                                vocab_json=sample_vocab_json,
                                blob_service_client=mock_blob_client,
                                client_path="test/client",
                                temp_file_path="/tmp",
                                program_type="dance",
                                batch_size=5,
                            )

                            # Should only process page 0 (page_areas says "Program")
                            assert len(result) > 0
                            # Verify processing happened
                            mock_call.assert_called_once()

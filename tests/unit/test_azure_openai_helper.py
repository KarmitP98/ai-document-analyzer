"""Unit tests for azure_openai_helper module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from classes.src.azure_openai_helper import (
    add_default_attributes_for_empty_pages,
    build_openai_prompt,
    call_azure_openai,
    chunk_large_page_ocr,
    convert_indices_to_bounding_boxes,
    degrade_confidence,
    download_client_context,
    download_prompt_template,
    filter_bounding_boxes_by_page_areas,
    filter_invalid_categories,
    find_missing_bounding_boxes,
    is_bbox_within_page_area,
    is_value_in_vocab,
    parse_openai_response,
    process_large_page_with_chunking,
    process_with_azure_openai,
    validate_and_adjust_confidence,
)


@pytest.fixture
def mock_vocab_json():
    """Mock vocabulary JSON."""
    return {
        "Choreographer": ["John Neumeier", "George Balanchine"],
        "Composer": ["Pyotr Tchaikovsky", "Igor Stravinsky"],
        "Donors": ["John Doe", "Jane Smith"],
    }


@pytest.fixture
def mock_labeled_json():
    """Mock labeled JSON with page data."""
    return {
        "pdf_name": "test_program.pdf",
        "features": [
            {
                "page_number": 1,
                "label": "Program",
                "page_areas": [{"label": "Program"}],
            }
        ],
        "first ocr": [
            [
                1,
                [
                    ["John Neumeier", 100, 100, 200, 120, 100, 20, 0.95],
                    ["Choreographer", 100, 125, 200, 145, 100, 20, 0.95],
                ],
            ]
        ],
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    response = MagicMock()
    response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(
                    [
                        {
                            "page": 1,
                            "label": "Program",
                            "page_areas": [{"label": "Program"}],
                            "attributes": {"Choreographer": ["John Neumeier"]},
                            "boundingBoxIndices": {"Choreographer": [{"value": "John Neumeier", "indices": [0]}]},
                        }
                    ]
                )
            ),
            finish_reason="stop",
        )
    ]
    response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    return response


def test_filter_invalid_categories(mock_vocab_json):
    """Test filtering of invalid categories."""
    entities = [
        {
            "page": 1,
            "attributes": {
                "Choreographer": ["John Neumeier"],
                "InvalidCategory": ["Some Value"],
                "Composer": ["Tchaikovsky"],
            },
        }
    ]

    result = filter_invalid_categories(entities, mock_vocab_json)

    assert len(result) == 1
    assert "Choreographer" in result[0]["attributes"]
    assert "Composer" in result[0]["attributes"]
    assert "InvalidCategory" not in result[0]["attributes"]


def test_build_openai_prompt(mock_labeled_json, mock_vocab_json):
    """Test building OpenAI prompt messages."""
    messages = build_openai_prompt(
        labeled_json=mock_labeled_json,
        vocab_json=mock_vocab_json,
        client_context={"context": "Test Ballet Company"},
        prompt_template={},
        program_type="dance",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Choreographer" in messages[1]["content"]


def test_parse_openai_response_success():
    """Test parsing successful OpenAI response."""
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "page": 1,
                                "label": "Program",
                                "page_areas": [{"label": "Program"}],
                                "attributes": {"Choreographer": ["John Neumeier"]},
                                "boundingBoxIndices": {"Choreographer": [{"value": "John Neumeier", "indices": [0]}]},
                            }
                        ]
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }

    result = parse_openai_response(response)

    assert len(result) == 1
    assert result[0]["page"] == 1
    assert "Choreographer" in result[0]["attributes"]


def test_parse_openai_response_truncated():
    """Test parsing truncated OpenAI response."""
    response = {
        "choices": [
            {
                "message": {"content": '{"incomplete": "json"'},
                "finish_reason": "length",
            }
        ]
    }

    with pytest.raises(Exception) as exc_info:
        parse_openai_response(response)

    assert "truncated" in str(exc_info.value).lower()


def test_convert_indices_to_bounding_boxes():
    """Test converting OCR indices to bounding boxes."""
    labeled_json = {
        "pdf_name": "test_program.pdf",
        "features": [
            {
                "page_number": 0,
                "label": "Program",
                "page_areas": [{"label": "Program"}],
            }
        ],
        "first ocr": [
            [
                1,  # Page 1 in OCR corresponds to page_number 0
                [
                    [0, "John Neumeier", 100, 100, 200, 120, 100, 20, 0.95],  # New format: [index, text, x, y, x2, y2, w, h, confidence]
                    [1, "Choreographer", 100, 125, 200, 145, 100, 20, 0.95],
                ],
            ]
        ],
    }

    entities = [
        {
            "page": 0,
            "attributes": {"Choreographer": ["John Neumeier"]},
            "boundingBoxIndices": [{"index": 0, "text": "John Neumeier"}],  # Flat list format
        }
    ]

    result = convert_indices_to_bounding_boxes(entities, labeled_json)

    assert len(result) == 1
    # Bounding boxes are added to a separate boundingBoxes array, not in attributes
    assert "boundingBoxes" in result[0]
    assert len(result[0]["boundingBoxes"]) == 1
    bbox = result[0]["boundingBoxes"][0]
    assert bbox["value"] == "John Neumeier"
    assert "coordinates" in bbox
    assert bbox["coordinates"]["x"] == 100


def test_find_missing_bounding_boxes():
    """Test finding missing bounding boxes via fuzzy matching."""
    labeled_json = {
        "pdf_name": "test_program.pdf",
        "features": [
            {
                "page_number": 0,
                "label": "Program",
                "page_areas": [{"label": "Program"}],
            }
        ],
        "first ocr": [
            [
                1,  # Page 1 in OCR corresponds to page_number 0
                [
                    [0, "John Neumeier", 100, 100, 200, 120, 100, 20, 0.95],  # New format
                    [1, "Choreographer", 100, 125, 200, 145, 100, 20, 0.95],
                ],
            ]
        ],
    }

    entities = [
        {
            "page": 0,
            "attributes": {"Choreographer": ["John Neumeier"]},  # Simple string format
        }
    ]

    result = find_missing_bounding_boxes(entities, labeled_json, similarity_threshold=85.0)

    assert len(result) == 1
    # Bounding boxes are added to a separate boundingBoxes array, not in attributes
    assert "boundingBoxes" in result[0]
    assert len(result[0]["boundingBoxes"]) == 1
    bbox = result[0]["boundingBoxes"][0]
    assert bbox["value"] == "John Neumeier"
    assert "coordinates" in bbox
    assert bbox["coordinates"]["x"] == 100


@patch("openai.AzureOpenAI")
def test_call_azure_openai(mock_azure_openai):
    """Test calling Azure OpenAI API."""
    mock_response = MagicMock()
    mock_response.id = "test-id"
    mock_response.object = "chat.completion"
    mock_response.created = 1234567890
    mock_response.model = "gpt-4o"

    mock_choice = MagicMock()
    mock_choice.index = 0
    mock_choice.message = MagicMock(role="assistant", content='{"test": "response"}')
    mock_choice.finish_reason = "stop"
    mock_response.choices = [mock_choice]

    mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_azure_openai.return_value = mock_client

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Extract entities."},
    ]

    result = call_azure_openai(
        messages=messages,
        azure_openai_endpoint="https://test.openai.azure.com",
        azure_openai_api_key="test-key",
        deployment_name="gpt-4o",
    )

    # call_azure_openai returns a dict with converted response data
    assert isinstance(result, dict)
    assert result["id"] == "test-id"
    assert result["model"] == "gpt-4o"
    assert len(result["choices"]) == 1
    assert result["choices"][0]["message"]["content"] == '{"test": "response"}'
    assert result["usage"]["total_tokens"] == 150
    mock_client.chat.completions.create.assert_called_once()


@patch("classes.src.azure_openai_helper.call_azure_openai")
@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
def test_process_large_page_with_chunking(mock_download_context, mock_download_template, mock_call_openai, mock_vocab_json):
    """Test processing large page with chunking."""
    mock_download_context.return_value = {"context": "Test Ballet Company"}
    mock_download_template.return_value = ""

    # Mock response should be dict, not MagicMock, since parse_openai_response expects dict
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "page": 0,
                                "label": "Donors",
                                "page_areas": [],
                                "attributes": {"Donors": ["John Doe"]},
                                "boundingBoxIndices": [{"index": 0, "text": "Donor 0"}],
                            }
                        ]
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }
    mock_call_openai.return_value = mock_response

    large_ocr_page = [
        1,  # OCR page 1 (corresponds to page_number 0)
        [[f"Donor {i}", 100, 100 + i * 20, 200, 120 + i * 20, 100, 20, 0.95] for i in range(200)],
    ]

    feature = {"page_number": 0, "label": "Donors", "page_areas": []}

    labeled_json = {"pdf_name": "test.pdf"}

    result = process_large_page_with_chunking(
        feature=feature,
        first_ocr_page=large_ocr_page,
        labeled_json=labeled_json,
        vocab_json=mock_vocab_json,
        client_context={"context": "Test Company"},
        prompt_template={},
        program_type="dance",
        azure_openai_endpoint="https://test.openai.azure.com",
        azure_openai_api_key="test-key",
        chunk_size=75,
    )

    assert isinstance(result, list)
    assert mock_call_openai.called


def test_convert_indices_to_bounding_boxes_missing_index(mock_labeled_json):
    """Test handling of missing OCR indices."""
    entities = [
        {
            "page": 1,
            "attributes": {"Choreographer": ["John Neumeier"]},
            "boundingBoxIndices": {"Choreographer": [{"value": "John Neumeier", "indices": [999]}]},
        }
    ]

    result = convert_indices_to_bounding_boxes(entities, mock_labeled_json)

    assert len(result) == 1
    choreographer_attr = result[0]["attributes"]["Choreographer"][0]
    assert "boundingBox" not in choreographer_attr or choreographer_attr.get("boundingBox") is None


def test_filter_invalid_categories_empty_attributes(mock_vocab_json):
    """Test filtering when attributes are empty."""
    entities = [{"page": 1, "attributes": {}}]

    result = filter_invalid_categories(entities, mock_vocab_json)

    assert len(result) == 1
    assert result[0]["attributes"] == {}


def test_build_openai_prompt_with_large_json(mock_labeled_json, mock_vocab_json):
    """Test that large JSON is stripped appropriately."""
    large_labeled_json = mock_labeled_json.copy()
    large_labeled_json["features"][0]["details"] = ["Lots", "of", "NLP", "data"] * 100
    large_labeled_json["features"][0]["count"] = {"word": 500}
    large_labeled_json["features"][0]["tf-idf"] = {"word": 0.5}

    messages = build_openai_prompt(
        labeled_json=large_labeled_json,
        vocab_json=mock_vocab_json,
        client_context={"context": "Test Company"},
        prompt_template={},
        program_type="dance",
    )

    user_content = messages[1]["content"]
    assert "details" not in user_content
    assert "count" not in user_content
    assert "tf-idf" not in user_content


def test_filter_invalid_categories_multiple_pages(mock_vocab_json):
    """Test filtering invalid categories across multiple pages."""
    entities = [
        {"page": 0, "attributes": {"Choreographer": ["John"], "InvalidCat1": ["Test"]}},
        {"page": 1, "attributes": {"Composer": ["Bach"], "InvalidCat2": ["Test2"]}},
    ]

    result = filter_invalid_categories(entities, mock_vocab_json)

    assert len(result) == 2
    assert "Choreographer" in result[0]["attributes"]
    assert "InvalidCat1" not in result[0]["attributes"]
    assert "Composer" in result[1]["attributes"]
    assert "InvalidCat2" not in result[1]["attributes"]


def test_parse_openai_response_with_pages_key():
    """Test parsing response with pages wrapper."""
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "pages": [
                                {
                                    "page": 0,
                                    "attributes": {"Choreographer": ["Test"]},
                                    "boundingBoxIndices": [],
                                    "page_areas": [],
                                }
                            ]
                        }
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }

    result = parse_openai_response(response)

    assert len(result) == 1
    assert result[0]["page"] == 0


def test_parse_openai_response_missing_fields():
    """Test parsing response with missing required fields."""
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                # Missing 'page', 'attributes', 'boundingBoxIndices', 'page_areas'
                                "label": "Program"
                            }
                        ]
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }

    result = parse_openai_response(response)

    # Should add missing fields with defaults
    assert len(result) == 1
    assert "page" in result[0]
    assert "attributes" in result[0]
    assert "boundingBoxIndices" in result[0]
    assert "page_areas" in result[0]


def test_convert_indices_to_bounding_boxes_no_ocr_data():
    """Test conversion when OCR data is missing."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0}],
        "first ocr": [],  # Empty OCR data
    }

    entities = [
        {
            "page": 0,
            "attributes": {"Choreographer": ["Test"]},
            "boundingBoxIndices": {"Choreographer": [{"value": "Test", "indices": [0]}]},
        }
    ]

    result = convert_indices_to_bounding_boxes(entities, labeled_json)

    # Should handle gracefully without crashing
    assert len(result) == 1


def test_find_missing_bounding_boxes_no_matches():
    """Test fuzzy matching when no matches found."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0}],
        "first ocr": [
            [
                1,
                [
                    ["Completely Different Text", 100, 100, 200, 120, 100, 20, 0.95],
                ],
            ]
        ],
    }

    entities = [
        {
            "page": 0,
            "attributes": {"Choreographer": [{"value": "John Neumeier"}]},
        }
    ]

    result = find_missing_bounding_boxes(entities, labeled_json, similarity_threshold=85.0)

    # Should return entities unchanged when no matches
    assert len(result) == 1
    assert "Choreographer" in result[0]["attributes"]


def test_find_missing_bounding_boxes_with_existing_bbox():
    """Test that existing bounding boxes are preserved."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0}],
        "first ocr": [[1, [["Test", 100, 100, 200, 120, 100, 20, 0.95]]]],
    }

    entities = [
        {
            "page": 0,
            "attributes": {
                "Choreographer": [
                    {
                        "value": "Test",
                        "boundingBox": {"x": 50, "y": 50, "x2": 150, "y2": 70},  # Already has bbox
                    }
                ]
            },
        }
    ]

    result = find_missing_bounding_boxes(entities, labeled_json)

    # Should preserve existing bbox
    assert result[0]["attributes"]["Choreographer"][0]["boundingBox"]["x"] == 50


def test_parse_openai_response_invalid_json():
    """Test handling of completely invalid JSON."""
    response = {"choices": [{"message": {"content": "This is not JSON at all"}, "finish_reason": "stop"}]}

    with pytest.raises(Exception) as exc_info:
        parse_openai_response(response)

    assert "Failed to parse" in str(exc_info.value)


def test_filter_invalid_categories_preserves_valid_only(mock_vocab_json):
    """Test that only valid categories are preserved."""
    entities = [
        {
            "page": 0,
            "attributes": {
                "Choreographer": ["Valid 1"],
                "Composer": ["Valid 2"],
                "Donors": ["Valid 3"],
                "FakeCategory1": ["Invalid 1"],
                "FakeCategory2": ["Invalid 2"],
            },
        }
    ]

    result = filter_invalid_categories(entities, mock_vocab_json)

    assert len(result[0]["attributes"]) == 3
    assert "Choreographer" in result[0]["attributes"]
    assert "Composer" in result[0]["attributes"]
    assert "Donors" in result[0]["attributes"]
    assert "FakeCategory1" not in result[0]["attributes"]
    assert "FakeCategory2" not in result[0]["attributes"]


@patch("openai.AzureOpenAI")
def test_call_azure_openai_with_custom_params(mock_azure_openai):
    """Test Azure OpenAI call with custom parameters."""
    mock_choice = MagicMock()
    mock_choice.index = 0
    mock_choice.message.role = "assistant"
    mock_choice.message.content = '{"test": "data"}'
    mock_choice.finish_reason = "stop"

    mock_response = MagicMock()
    mock_response.id = "chatcmpl-test123"
    mock_response.object = "chat.completion"
    mock_response.created = 1234567890
    mock_response.model = "gpt-4o-custom"
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_azure_openai.return_value = mock_client

    messages = [{"role": "user", "content": "Test"}]

    call_azure_openai(
        messages=messages,
        azure_openai_endpoint="https://custom.openai.azure.com",
        azure_openai_api_key="custom-key",
        deployment_name="gpt-4o-custom",
        temperature=0.5,
        max_tokens=8000,
    )

    # Verify custom parameters were used
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["max_tokens"] == 8000
    assert call_kwargs["model"] == "gpt-4o-custom"


def test_build_openai_prompt_with_program_type_symphony(mock_labeled_json, mock_vocab_json):
    """Test building prompt for symphony program type."""
    messages = build_openai_prompt(
        labeled_json=mock_labeled_json,
        vocab_json=mock_vocab_json,
        client_context={"context": "Symphony Orchestra"},
        prompt_template={},
        program_type="symphony",
    )

    assert len(messages) == 2
    assert "symphony" in messages[1]["content"].lower() or "Symphony" in messages[1]["content"]


def test_parse_openai_response_with_results_key():
    """Test parsing response with results wrapper instead of pages."""
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "results": [
                                {
                                    "page": 0,
                                    "attributes": {},
                                }
                            ]
                        }
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }

    result = parse_openai_response(response)

    assert len(result) == 1


@patch("builtins.open", create=True)
@patch("classes.src.azure_openai_helper.BlobServiceClient")
def test_download_prompt_template_success(mock_blob_service, mock_open_func):
    """Test successful download of prompt template."""

    mock_blob_client = MagicMock()
    mock_blob_client.download_blob().readall.return_value = b'{"test": "prompt"}'
    mock_blob_service_instance = MagicMock()
    mock_blob_service_instance.get_blob_client.return_value = mock_blob_client

    mock_file = MagicMock()
    mock_open_func.return_value.__enter__.return_value = mock_file
    mock_file.read.return_value = '{"test": "prompt"}'

    with patch("json.load", return_value={"test": "prompt"}):
        result = download_prompt_template(mock_blob_service_instance, "test_client", "/tmp")

    assert result == {"test": "prompt"}


@patch("builtins.open", create=True)
def test_download_prompt_template_exception(mock_open_func):
    """Test download with exception returns default."""

    mock_blob_service_instance = MagicMock()
    mock_blob_service_instance.get_blob_client.side_effect = Exception("Blob not found")

    result = download_prompt_template(mock_blob_service_instance, "test_client", "/tmp")

    assert isinstance(result, dict)


@patch("builtins.open", create=True)
def test_download_client_context_success(mock_open_func):
    """Test successful download of client context."""

    mock_blob_client = MagicMock()
    mock_blob_client.download_blob().readall.return_value = b'{"context": "test"}'
    mock_blob_service_instance = MagicMock()
    mock_blob_service_instance.get_blob_client.return_value = mock_blob_client

    mock_file = MagicMock()
    mock_open_func.return_value.__enter__.return_value = mock_file

    with patch("json.load", return_value={"context": "test"}):
        result = download_client_context(mock_blob_service_instance, "test_client", "/tmp")

    assert result == {"context": "test"}


@patch("builtins.open", create=True)
def test_download_client_context_exception(mock_open_func):
    """Test download with exception returns empty dict."""

    mock_blob_service_instance = MagicMock()
    mock_blob_service_instance.get_blob_client.side_effect = Exception("Blob not found")

    result = download_client_context(mock_blob_service_instance, "test_client", "/tmp")

    # Should return default context: {"context": "", "notes": []}
    assert isinstance(result, dict)
    assert "context" in result
    assert "notes" in result


def test_chunk_large_page_ocr_no_chunking_needed():
    """Test chunking when OCR data is below threshold."""

    feature = {"page_number": 1}
    ocr_data = [["Text1"], ["Text2"]]

    result = chunk_large_page_ocr(feature, ocr_data, max_ocr_entries=200)

    assert len(result) == 1
    assert result[0][0] == feature
    assert result[0][1] == ocr_data


def test_chunk_large_page_ocr_chunking_required():
    """Test chunking when OCR data exceeds threshold."""

    feature = {"page_number": 1}
    ocr_data = [[f"Text{i}"] for i in range(250)]

    result = chunk_large_page_ocr(feature, ocr_data, max_ocr_entries=100)

    assert len(result) == 3
    assert len(result[0][1]) == 100
    assert len(result[1][1]) == 100
    assert len(result[2][1]) == 50


@patch("classes.src.azure_openai_helper.download_prompt_template")
@patch("classes.src.azure_openai_helper.download_client_context")
@patch("classes.src.azure_openai_helper.call_azure_openai")
@patch("classes.src.azure_openai_helper.parse_openai_response")
@patch("classes.src.azure_openai_helper.filter_invalid_categories")
@patch("os.environ.get")
def test_process_with_azure_openai_single_page(mock_env, mock_filter, mock_parse, mock_call, mock_context, mock_template):
    """Test processing single page with Azure OpenAI."""

    # Mock environment variables
    mock_env.side_effect = lambda x, default=None: {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o",
    }.get(x, default)

    mock_template.return_value = {"system": "test", "user": "test"}
    mock_context.return_value = {"context": "test"}
    mock_call.return_value = {"choices": [{"message": {"content": "[]"}, "finish_reason": "stop"}]}
    mock_parse.return_value = [{"page": 0, "attributes": {}}]
    mock_filter.return_value = [{"page": 0, "attributes": {}}]

    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0, "label": "Program"}],
        "first ocr": [[0, [["text", 100, 100, 200, 120]]]],
    }
    vocab_json = {}
    mock_blob_client = MagicMock()

    result = process_with_azure_openai(
        labeled_json,
        vocab_json,
        mock_blob_client,
        "test_client",
        "/tmp",
        "dance",
        batch_size=1,
    )

    assert isinstance(result, list)


def test_degrade_confidence_high_to_medium():
    """Test confidence degradation from high to medium."""

    assert degrade_confidence(0.9) == 0.8
    assert degrade_confidence(0.85) == 0.8
    assert degrade_confidence(90) == 0.8  # Percentage format


def test_degrade_confidence_medium_to_low():
    """Test confidence degradation from medium to low."""

    assert degrade_confidence(0.7) == 0.5
    assert degrade_confidence(0.6) == 0.5
    assert degrade_confidence(65) == 0.5  # Percentage format


def test_degrade_confidence_low():
    """Test confidence degradation when low should remain the same."""

    assert degrade_confidence(0.4) == 0.4
    assert degrade_confidence(0.2) == 0.2
    assert degrade_confidence(30) == 0.30  # Percentage format


def test_degrade_confidence_none():
    """Test confidence degradation with None input."""

    assert degrade_confidence(None) == 0.5


def test_is_value_in_vocab_found():
    """Test checking if value exists in vocab."""

    vocab_json = {
        "Choreographer": ["John Neumeier", "George Balanchine"],
        "Composer": ["Pyotr Tchaikovsky", "Igor Stravinsky"],
    }

    assert is_value_in_vocab("Choreographer", "John Neumeier", vocab_json) is True
    assert is_value_in_vocab("Choreographer", "john neumeier", vocab_json) is True  # Case insensitive
    assert is_value_in_vocab("Composer", "Igor Stravinsky", vocab_json) is True


def test_is_value_in_vocab_not_found():
    """Test checking if value doesn't exist in vocab."""

    vocab_json = {
        "Choreographer": ["John Neumeier", "George Balanchine"],
        "Composer": ["Pyotr Tchaikovsky", "Igor Stravinsky"],
    }

    assert is_value_in_vocab("Choreographer", "Unknown Person", vocab_json) is False
    assert is_value_in_vocab("InvalidCategory", "John Neumeier", vocab_json) is False


def test_is_value_in_vocab_with_tags_format():
    """Test checking value in vocab with tags dict format."""

    vocab_json = {
        "Choreographer": {
            "tags": ["John Neumeier", "George Balanchine"],
            "excludedPageTypes": [],
        }
    }

    assert is_value_in_vocab("Choreographer", "John Neumeier", vocab_json) is True
    assert is_value_in_vocab("Choreographer", "Unknown", vocab_json) is False


def test_validate_and_adjust_confidence_degrades_for_missing_values():
    """Test that confidence is degraded when values are not in vocab."""

    matched_entities = [
        {
            "page": 0,
            "attributes": {"Choreographer": ["John Neumeier"], "Composer": ["Unknown Composer"]},
            "boundingBoxes": [
                {
                    "value": "John Neumeier",
                    "attributes": [{"value": "Choreographer", "vocabName": "John Neumeier", "score": 0.9}],
                    "coordinates": {"x": 100, "y": 100, "x2": 200, "y2": 120, "w": 100, "h": 20},
                },
                {
                    "value": "Unknown Composer",
                    "attributes": [{"value": "Composer", "vocabName": "Unknown Composer", "score": 0.85}],
                    "coordinates": {"x": 100, "y": 150, "x2": 200, "y2": 170, "w": 100, "h": 20},
                },
            ],
        }
    ]

    vocab_json = {
        "Choreographer": ["John Neumeier", "George Balanchine"],
        "Composer": ["Pyotr Tchaikovsky", "Igor Stravinsky"],
    }

    result = validate_and_adjust_confidence(matched_entities, vocab_json)

    # First bbox should keep high confidence (value in vocab)
    assert result[0]["boundingBoxes"][0]["attributes"][0]["score"] == 0.9

    # Second bbox should be degraded (value not in vocab: 0.85 -> 0.8)
    assert result[0]["boundingBoxes"][1]["attributes"][0]["score"] == 0.8


def test_find_missing_bounding_boxes_creates_placeholder_for_unmatched():
    """Test that unmatched entities get placeholder bboxes with low confidence."""
    from classes.src.azure_openai_helper import find_missing_bounding_boxes

    matched_entities = [
        {
            "page": 0,
            "attributes": {"Choreographer": ["John Neumeier"], "Composer": ["Not In OCR"]},
            "boundingBoxes": [
                {
                    "value": "John Neumeier",
                    "attributes": [{"value": "Choreographer", "vocabName": "John Neumeier", "score": 0.9}],
                    "coordinates": {"x": 100, "y": 100, "x2": 200, "y2": 120, "w": 100, "h": 20},
                }
            ],
        }
    ]

    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0}],
        "first ocr": [
            [
                1,
                [
                    [0, "John Neumeier", 100, 100, 200, 120, 100, 20, 0.95],
                    [1, "Some Other Text", 100, 150, 200, 170, 100, 20, 0.92],
                ],
            ]
        ],
    }

    result = find_missing_bounding_boxes(matched_entities, labeled_json, similarity_threshold=85.0)

    # Should have 2 bounding boxes now (original + placeholder for "Not In OCR")
    assert len(result[0]["boundingBoxes"]) == 2

    # Second bbox should be the placeholder with low confidence
    placeholder = result[0]["boundingBoxes"][1]
    assert placeholder["value"] == "Not In OCR"
    assert placeholder["attributes"][0]["score"] == 0.45
    assert placeholder["coordinates"]["x"] == 9999


def test_is_bbox_within_page_area():
    """Test bounding box containment check."""

    bbox = {"x": 100, "y": 100, "x2": 200, "y2": 200}
    page_area = {"x": 0, "y": 0, "x2": 300, "y2": 300}

    assert is_bbox_within_page_area(bbox, page_area) is True

    bbox_outside = {"x": 100, "y": 100, "x2": 400, "y2": 200}
    assert is_bbox_within_page_area(bbox_outside, page_area) is False

    bbox_partial = {"x": 50, "y": 50, "x2": 150, "y2": 150}
    page_area_small = {"x": 100, "y": 100, "x2": 200, "y2": 200}
    assert is_bbox_within_page_area(bbox_partial, page_area_small) is False


def test_filter_bounding_boxes_by_page_areas():
    """Test filtering bounding boxes by page areas."""

    matched_entities = [
        {
            "page": 0,
            "page_areas": [{"label": "Program", "bounding_box": {"x": 0, "y": 0, "x2": 400, "y2": 400}}],
            "boundingBoxes": [
                {"value": "Inside", "coordinates": {"x": 100, "y": 100, "x2": 200, "y2": 120}},
                {"value": "Outside", "coordinates": {"x": 500, "y": 500, "x2": 600, "y2": 520}},
                {"value": "AlsoInside", "coordinates": {"x": 200, "y": 200, "x2": 300, "y2": 220}},
            ],
        }
    ]

    result = filter_bounding_boxes_by_page_areas(matched_entities)

    assert len(result[0]["boundingBoxes"]) == 2
    assert result[0]["boundingBoxes"][0]["value"] == "Inside"
    assert result[0]["boundingBoxes"][1]["value"] == "AlsoInside"


def test_filter_bounding_boxes_no_page_areas():
    """Test that filtering does nothing when no page_areas defined."""

    matched_entities = [
        {
            "page": 0,
            "page_areas": [],
            "boundingBoxes": [
                {"value": "Item1", "coordinates": {"x": 100, "y": 100, "x2": 200, "y2": 120}},
                {"value": "Item2", "coordinates": {"x": 500, "y": 500, "x2": 600, "y2": 520}},
            ],
        }
    ]

    result = filter_bounding_boxes_by_page_areas(matched_entities)

    assert len(result[0]["boundingBoxes"]) == 2


def test_add_default_attributes_for_empty_pages():
    """Test adding default Extras attribute to pages with no attributes."""

    matched_entities = [
        {"page": 0, "label": "Title", "attributes": {}},
        {"page": 1, "label": "Program", "attributes": {"Choreographer": ["John Doe"]}},
        {"page": 2, "label": "Other", "attributes": {}},
        {"page": 3, "label": "Company", "attributes": {}},
    ]

    result = add_default_attributes_for_empty_pages(matched_entities)

    assert result[0]["attributes"] == {"Extras": ["No Valid Attributes Detected"]}
    assert result[1]["attributes"] == {"Choreographer": ["John Doe"]}
    assert result[2]["attributes"] == {}
    assert result[3]["attributes"] == {"Extras": ["No Valid Attributes Detected"]}


def test_add_default_attributes_skips_pages_with_attributes():
    """Test that pages with attributes are not modified."""

    matched_entities = [
        {"page": 0, "label": "Program", "attributes": {"Performance Title": ["Swan Lake"]}},
        {"page": 1, "label": "Donor", "attributes": {"Donors": ["John Smith"]}},
    ]

    result = add_default_attributes_for_empty_pages(matched_entities)

    assert result[0]["attributes"] == {"Performance Title": ["Swan Lake"]}
    assert result[1]["attributes"] == {"Donors": ["John Smith"]}


def test_add_default_attributes_skips_other_label():
    """Test that pages labeled as 'Other' are not given default attributes."""

    matched_entities = [
        {"page": 0, "label": "Other", "attributes": {}},
        {"page": 1, "label": "Other", "attributes": None},
    ]

    result = add_default_attributes_for_empty_pages(matched_entities)

    assert result[0]["attributes"] == {}
    assert result[1].get("attributes") is None or result[1].get("attributes") == {}


def test_add_default_attributes_handles_missing_label():
    """Test handling of pages without label field."""

    matched_entities = [
        {"page": 0, "attributes": {}},
        {"page": 1, "label": "", "attributes": {}},
    ]

    result = add_default_attributes_for_empty_pages(matched_entities)

    assert result[0]["attributes"] == {}
    assert result[1]["attributes"] == {}

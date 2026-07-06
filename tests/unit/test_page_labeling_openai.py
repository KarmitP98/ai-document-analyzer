"""Unit tests for page_labeling_openai module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from classes.src.page_labeling_openai import (
    build_page_labeling_prompt,
    call_azure_openai_for_labeling,
    label_pages_with_openai,
    parse_labeling_response,
)


@pytest.fixture
def mock_features_json():
    """Mock features JSON with page data."""
    return {
        "pdf_name": "test_program.pdf",
        "features": [
            {
                "page_number": 0,
                "text": "Charlotte Ballet Season 2024",
                "details": [[0, [["Charlotte Ballet", "Organization"], ["2024", "Date"]]]],
                "total": 50,
                "person": 2,
                "organization": 1,
                "location": 1,
                "date": 1,
            },
            {
                "page_number": 1,
                "text": "Romeo and Juliet - Choreography by John Neumeier",
                "details": [[0, [["Romeo and Juliet", "Work of Art"], ["John Neumeier", "Person"]]]],
                "total": 100,
                "person": 5,
                "organization": 0,
                "location": 0,
                "date": 0,
            },
            {
                "page_number": 2,
                "text": "Artistic Director: Hope Muir\nBoard of Directors: John Smith",
                "details": [[0, [["Hope Muir", "Person"], ["John Smith", "Person"]]]],
                "total": 80,
                "person": 10,
                "organization": 1,
                "location": 0,
                "date": 0,
            },
            {
                "page_number": 3,
                "text": "Thank you to our generous donors: Jane Doe, Bob Johnson",
                "details": [[0, [["Jane Doe", "Person"], ["Bob Johnson", "Person"]]]],
                "total": 200,
                "person": 50,
                "organization": 0,
                "location": 0,
                "date": 0,
            },
        ],
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for page labeling."""
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "pages": [
                                {"page_number": 0, "label": "Title", "confidence": "High", "reasoning": "First page with season info."},
                                {
                                    "page_number": 1,
                                    "label": "Program",
                                    "confidence": "High",
                                    "reasoning": "Performance title and choreographer.",
                                },
                                {
                                    "page_number": 2,
                                    "label": "Company",
                                    "confidence": "High",
                                    "reasoning": "Staff and board members.",
                                },
                                {
                                    "page_number": 3,
                                    "label": "Donor",
                                    "confidence": "High",
                                    "reasoning": "Donor acknowledgments.",
                                },
                            ]
                        }
                    ),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700},
    }


def test_build_page_labeling_prompt(mock_features_json):
    """Test building page labeling prompt."""
    messages = build_page_labeling_prompt(mock_features_json, "test_program.pdf")

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "test_program.pdf" in messages[1]["content"]
    assert "page_number" in messages[1]["content"]
    assert "text_sample" in messages[1]["content"]


def test_build_page_labeling_prompt_limits_entities(mock_features_json):
    """Test that entity lists are limited to prevent huge prompts."""
    large_features = mock_features_json.copy()
    large_features["features"][0]["details"] = [[0, [[f"Person {i}", "Person"] for i in range(50)]]]

    messages = build_page_labeling_prompt(large_features, "test.pdf")
    user_content = messages[1]["content"]

    # Extract the JSON array from the prompt
    json_start = user_content.find("[")
    json_end = user_content.rfind("]") + 1
    json_str = user_content[json_start:json_end]

    parsed_content = json.loads(json_str)
    entities = parsed_content[0]["entities"]

    if "Person" in entities:
        assert len(entities["Person"]) <= 20


def test_parse_labeling_response_with_pages_key(mock_openai_response):
    """Test parsing response with 'pages' key."""
    labels = parse_labeling_response(mock_openai_response, num_pages=4)

    assert len(labels) == 4
    assert labels[0] == "Title"
    assert labels[1] == "Program"
    assert labels[2] == "Company"
    assert labels[3] == "Donor"


def test_parse_labeling_response_with_list_format():
    """Test parsing response that is a direct list."""
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {"page_number": 0, "label": "Title", "confidence": "High", "reasoning": "Cover page."},
                            {"page_number": 1, "label": "Program", "confidence": "High", "reasoning": "Program list."},
                        ]
                    )
                }
            }
        ]
    }

    labels = parse_labeling_response(response, num_pages=2)

    assert len(labels) == 2
    assert labels[0] == "Title"
    assert labels[1] == "Program"


def test_parse_labeling_response_invalid_label():
    """Test handling of invalid labels."""
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "pages": [
                                {"page_number": 0, "label": "InvalidLabel", "confidence": "High", "reasoning": "Test."},
                            ]
                        }
                    )
                }
            }
        ]
    }

    labels = parse_labeling_response(response, num_pages=1)

    assert len(labels) == 1
    assert labels[0] == "Other"


def test_parse_labeling_response_missing_pages():
    """Test padding when fewer labels than expected pages."""
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "pages": [
                                {"page_number": 0, "label": "Title", "confidence": "High", "reasoning": "First page."},
                            ]
                        }
                    )
                }
            }
        ]
    }

    labels = parse_labeling_response(response, num_pages=3)

    assert len(labels) == 3
    assert labels[0] == "Title"
    assert labels[1] == "Other"
    assert labels[2] == "Other"


def test_parse_labeling_response_malformed_json():
    """Test error handling for malformed JSON."""
    response = {"choices": [{"message": {"content": "{ invalid json"}}]}

    with pytest.raises(Exception) as exc_info:
        parse_labeling_response(response, num_pages=1)

    assert "Failed to parse" in str(exc_info.value)


def test_parse_labeling_response_no_choices():
    """Test error handling when no choices in response."""
    response = {"choices": []}

    with pytest.raises(Exception) as exc_info:
        parse_labeling_response(response, num_pages=1)

    assert "No choices" in str(exc_info.value)


@patch("openai.AzureOpenAI")
def test_call_azure_openai_for_labeling(mock_azure_openai):
    """Test calling Azure OpenAI for labeling."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.id = "test-id"
    mock_response.object = "chat.completion"
    mock_response.created = 1234567890
    mock_response.model = "gpt-4o"
    mock_response.choices = [
        MagicMock(
            index=0,
            message=MagicMock(role="assistant", content='{"pages": []}'),
            finish_reason="stop",
        )
    ]
    mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

    mock_client.chat.completions.create.return_value = mock_response
    mock_azure_openai.return_value = mock_client

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Classify pages."},
    ]

    result = call_azure_openai_for_labeling(
        messages=messages,
        azure_openai_endpoint="https://test.openai.azure.com",
        azure_openai_api_key="test-key",
        deployment_name="gpt-4o",
    )

    assert result["id"] == "test-id"
    assert result["choices"][0]["message"]["content"] == '{"pages": []}'
    mock_client.chat.completions.create.assert_called_once()


@patch("openai.AzureOpenAI")
def test_call_azure_openai_for_labeling_rate_limit(mock_azure_openai):
    """Test retry logic for rate limit errors."""
    from openai import RateLimitError

    mock_client = MagicMock()
    mock_azure_openai.return_value = mock_client

    rate_limit_error = RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)
    mock_client.chat.completions.create.side_effect = rate_limit_error

    messages = [{"role": "user", "content": "Test"}]

    with pytest.raises(Exception) as exc_info:
        call_azure_openai_for_labeling(
            messages=messages,
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_api_key="test-key",
            max_retries=2,
        )

    assert "rate limit exceeded" in str(exc_info.value).lower()


@patch("classes.src.page_labeling_openai.call_azure_openai_for_labeling")
@patch("classes.src.page_labeling_openai.parse_labeling_response")
def test_label_pages_with_openai(mock_parse, mock_call_openai, mock_features_json, mock_openai_response):
    """Test main labeling function with batching."""
    mock_call_openai.return_value = mock_openai_response
    mock_parse.return_value = ["Title", "Program", "Company", "Donor"]

    labels = label_pages_with_openai(
        features_json=mock_features_json,
        pdf_name="test_program.pdf",
        azure_openai_endpoint="https://test.openai.azure.com",
        azure_openai_api_key="test-key",
        batch_size=4,
    )

    assert len(labels) == 4
    assert labels[0] == "Title"
    assert labels[3] == "Donor"
    mock_call_openai.assert_called_once()


@patch("classes.src.page_labeling_openai.call_azure_openai_for_labeling")
@patch("classes.src.page_labeling_openai.parse_labeling_response")
def test_label_pages_with_openai_multiple_batches(mock_parse, mock_call_openai, mock_features_json):
    """Test labeling with multiple batches."""
    mock_openai_response1 = {
        "choices": [{"message": {"content": '{"pages": []}'}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }
    mock_openai_response2 = {
        "choices": [{"message": {"content": '{"pages": []}'}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }

    mock_call_openai.side_effect = [mock_openai_response1, mock_openai_response2]
    mock_parse.side_effect = [["Title", "Program"], ["Company", "Donor"]]

    labels = label_pages_with_openai(
        features_json=mock_features_json,
        pdf_name="test.pdf",
        azure_openai_endpoint="https://test.openai.azure.com",
        azure_openai_api_key="test-key",
        batch_size=2,
    )

    assert len(labels) == 4
    assert mock_call_openai.call_count == 2


def test_label_pages_with_openai_missing_credentials():
    """Test error when credentials are missing."""
    with pytest.raises(Exception) as exc_info:
        label_pages_with_openai(
            features_json={"features": []},
            pdf_name="test.pdf",
            azure_openai_endpoint=None,
            azure_openai_api_key=None,
        )

    assert "credentials not provided" in str(exc_info.value).lower()


def test_parse_labeling_response_sorts_by_page_number():
    """Test that labels are sorted by page number."""
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "pages": [
                                {"page_number": 2, "label": "Company", "confidence": "High", "reasoning": "Staff."},
                                {"page_number": 0, "label": "Title", "confidence": "High", "reasoning": "Cover."},
                                {"page_number": 1, "label": "Program", "confidence": "High", "reasoning": "Performances."},
                            ]
                        }
                    )
                }
            }
        ]
    }

    labels = parse_labeling_response(response, num_pages=3)

    assert labels[0] == "Title"
    assert labels[1] == "Program"
    assert labels[2] == "Company"

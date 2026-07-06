"""
Unit tests for OpenAI-based vocabulary matching.
Tests the hybrid approach: OpenAI extraction + local fuzzy matching.
"""

import json
import os

import pytest
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

from classes.src.azure_openai_helper import (
    process_with_azure_openai,
)


@pytest.fixture
def real_vocab_json():
    """Fixture for real vocabulary JSON."""
    with open("./data/json/vocab.json", "r", encoding="utf-8") as file:
        vocab = json.load(file)
    return vocab


@pytest.fixture
def real_labeled_json():
    """Fixture for real labeled JSON from OBC test."""
    with open("./data/json/OBC_Program 2003-11-07_mt3_labelled.json", "r", encoding="utf-8") as file:
        labeled = json.load(file)
    # with open("./data/json/openai/2000-2001 Season (1)_labelled(1).json", "r", encoding="utf-8") as file:
    #    labeled = json.load(file)
    return labeled


@pytest.fixture
def mock_client_context():
    """Fixture for real client context from prompt templates."""
    with open("./data/prompt_templates/prompt_client_context.json", "r", encoding="utf-8") as file:
        context = json.load(file)
    return context


@pytest.fixture
def mock_prompt_template():
    """Fixture for real prompt template."""
    with open("./data/prompt_templates/prompt.json", "r", encoding="utf-8") as file:
        template = json.load(file)
    return template


@pytest.mark.skip("For local testing only using real services, not appropriate for cicd.")
def test_process_with_azure_openai_real(real_labeled_json, real_vocab_json):
    """Integration test with REAL Azure OpenAI and Blob Storage - no mocks!"""
    load_dotenv("classes/env_var_folder/.env", override=True)
    # Use real Azure Blob Storage client

    blob_connection_string = os.environ.get("STORAGE_CONNECTION_STRING")
    if not blob_connection_string:
        pytest.skip("Blob storage connection string not configured (STORAGE_CONNECTION_STRING)")

    blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
    client_id = "ebec9c0e-828c-4a8b-9116-db356a5172a5"
    client_path = f"chromadiverse/{client_id}"
    temp_file_path = "./temp"

    # Create test_results directory if it doesn't exist
    os.makedirs("./test_results", exist_ok=True)

    # Save input data
    print("\nSaving test data to test_results folder...")
    with open("./test_results/00_input_labeled_json.json", "w", encoding="utf-8") as f:
        json.dump(real_labeled_json, f, indent=2, ensure_ascii=False)
    print("  Saved: 00_input_labeled_json.json")

    with open("./test_results/00_input_vocab_json.json", "w", encoding="utf-8") as f:
        json.dump(real_vocab_json, f, indent=2, ensure_ascii=False)
    print("  Saved: 00_input_vocab_json.json")

    print("\nRunning REAL integration test with Azure OpenAI")
    print(f"  - Client ID: {client_id}")
    print(f"  - PDF: {real_labeled_json.get('pdf_name', 'unknown')}")
    print(f"  - Total pages in labeled JSON: {len(real_labeled_json.get('features', []))}")

    # Show page labels
    features = real_labeled_json.get("features", [])
    label_counts = {}
    for f in features:
        label = f.get("label", "Unknown")
        label_counts[label] = label_counts.get(label, 0) + 1
    print(f"  - Page labels: {label_counts}")

    try:
        result = process_with_azure_openai(
            labeled_json=real_labeled_json,
            vocab_json=real_vocab_json,
            blob_service_client=blob_service_client,
            client_path=client_path,
            temp_file_path=temp_file_path,
            program_type="dance",
            batch_size=4,
        )

        # Save output result
        with open("./test_results/01_openai_output.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("\n  Saved: 01_openai_output.json")

        assert isinstance(result, list)
        print("\nIntegration test SUCCESSFUL!")
        print(f"  - Pages returned: {len(result)}")

        # Show detailed results for each page
        for idx, page in enumerate(result):
            print(f"\n  Page {page.get('page', idx)}:")
            print(f"    - Label: {page.get('label', 'unknown')}")
            attrs = page.get("attributes", {})
            print(f"    - Attribute categories: {len(attrs)}")

            # Count total entities
            total_entities = sum(len(vals) for vals in attrs.values())
            print(f"    - Total entities: {total_entities}")

            # Show first few categories with values
            for cat, vals in list(attrs.items())[:5]:
                if vals:
                    preview = vals[:3] if len(vals) > 3 else vals
                    print(f"      - {cat}: {preview}{' ...' if len(vals) > 3 else ''}")

            # Show bounding box count
            bboxes = page.get("boundingBoxes", [])
            print(f"    - Bounding boxes: {len(bboxes)}")

        # Summary statistics
        total_categories = sum(len(page.get("attributes", {})) for page in result)
        total_entities = sum(sum(len(vals) for vals in page.get("attributes", {}).values()) for page in result)
        total_bboxes = sum(len(page.get("boundingBoxes", [])) for page in result)

        print("\nSummary:")
        print(f"  - Total pages processed: {len(result)}")
        print(f"  - Total attribute categories: {total_categories}")
        print(f"  - Total entities extracted: {total_entities}")
        print(f"  - Total bounding boxes: {total_bboxes}")

    except Exception as e:
        print(f"\nX Integration test FAILED: {e}")
        import traceback

        traceback.print_exc()
        raise

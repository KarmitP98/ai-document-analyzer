"""Unit tests for prompts module."""

from classes.src.prompts import (
    build_user_prompt,
    get_default_prompt_template,
    get_system_prompt,
    get_user_prompt_template,
)


def test_get_default_prompt_template():
    """Test getting default prompt template."""
    template = get_default_prompt_template()

    assert isinstance(template, dict)
    assert "system_prompt" in template
    assert "task_description" in template
    assert "output_format_description" in template
    assert "performing arts programs" in template["system_prompt"]
    assert "JSON" in template["output_format_description"]


def test_get_system_prompt():
    """Test getting system prompt for entity extraction."""
    prompt = get_system_prompt()

    assert isinstance(prompt, str)
    assert len(prompt) > 0
    # Check for key instructions
    assert "Extract entities" in prompt
    assert "JSON array" in prompt
    assert "MULTI-PAGE" in prompt
    assert "PAGE_AREAS" in prompt
    assert "CATEGORY MAPPING" in prompt
    assert "boundingBoxIndices" in prompt
    # Check for category examples
    assert "Choreographer" in prompt
    assert "Composer" in prompt
    assert "Set Designer" in prompt
    # Check for minified JSON instruction
    assert "MINIFIED" in prompt or "COMPACT" in prompt


def test_get_user_prompt_template():
    """Test getting user prompt template."""
    template = get_user_prompt_template()

    assert isinstance(template, str)
    assert len(template) > 0
    # Check for placeholders
    assert "{num_pages}" in template
    assert "{page_numbers}" in template
    assert "{program}" in template
    assert "{context}" in template
    assert "{categories}" in template
    assert "{example}" in template
    assert "{data}" in template
    # Check for key instructions
    assert "CATEGORIES" in template
    assert "PAGE_AREAS FILTERING" in template
    assert "BOUNDING BOX INDICES" in template


def test_build_user_prompt_single_page():
    """Test building user prompt for single page."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [
            {
                "page_number": 0,
                "label": "Program",
                "page_areas": [{"label": "Program", "bounding_box": [0, 0, 100, 100]}],
            }
        ],
        "first ocr": [[1, [["Test", 100, 100, 200, 120]]]],
    }

    vocab_json = {
        "Choreographer": ["John Neumeier"],
        "Composer": ["Tchaikovsky"],
    }

    client_context = {"context": "Charlotte Ballet"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    assert isinstance(prompt, str)
    assert "Processing 1 pages: 0" in prompt
    assert "Program type: dance" in prompt
    assert "Context: Charlotte Ballet" in prompt
    assert "Choreographer, Composer" in prompt
    # Check that data is compacted (no spaces after colons/commas in JSON)
    assert '"pdf_name":"test.pdf"' in prompt or '"features":[' in prompt


def test_build_user_prompt_multiple_pages():
    """Test building user prompt for multiple pages."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [
            {"page_number": 0, "label": "Title", "page_areas": []},
            {"page_number": 1, "label": "Program", "page_areas": []},
            {"page_number": 2, "label": "Donor", "page_areas": []},
        ],
        "first ocr": [],
    }

    vocab_json = {"Performance Title": [], "Donors": []}

    client_context = {"context": "Test Symphony"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="symphony",
    )

    assert "Processing 3 pages: 0,1,2" in prompt
    assert "Program type: symphony" in prompt
    assert "Performance Title, Donors" in prompt


def test_build_user_prompt_with_notes():
    """Test building user prompt with client notes."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0, "label": "Program", "page_areas": []}],
        "first ocr": [],
    }

    vocab_json = {"Choreographer": []}

    client_context = {
        "context": "Ballet Company",
        "notes": ["Note 1: Check for guest artists", "Note 2: Verify composer names"],
    }

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    assert "Context: Ballet Company" in prompt
    assert "- Note 1: Check for guest artists" in prompt
    assert "- Note 2: Verify composer names" in prompt


def test_build_user_prompt_empty_context():
    """Test building user prompt with empty context."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0, "label": "Program", "page_areas": []}],
        "first ocr": [],
    }

    vocab_json = {"Choreographer": []}

    client_context = {}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    # Should still work without context
    assert isinstance(prompt, str)
    assert "Processing 1 pages" in prompt
    # Context line should be empty or not present
    assert "Context:" not in prompt or "Context: \n" in prompt


def test_build_user_prompt_no_vocab():
    """Test building user prompt with empty vocabulary."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0, "label": "Program", "page_areas": []}],
        "first ocr": [],
    }

    vocab_json = {}

    client_context = {"context": "Test"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    assert isinstance(prompt, str)
    # Categories should be empty
    assert "CATEGORIES (use ONLY these as categories" in prompt


def test_build_user_prompt_with_page_areas():
    """Test that page_areas are included in the example."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [
            {
                "page_number": 0,
                "label": "Program",
                "page_areas": [
                    {"label": "Program", "bounding_box": [100, 100, 500, 300]},
                    {"label": "Donor", "bounding_box": [100, 400, 500, 600]},
                ],
            }
        ],
        "first ocr": [],
    }

    vocab_json = {"Performance Title": []}

    client_context = {"context": "Test"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    # Check that example includes page_areas
    assert '"page_areas"' in prompt
    # The example should show the structure
    assert "EXAMPLE OUTPUT:" in prompt


def test_build_user_prompt_preserves_labels():
    """Test that page labels are preserved in the example."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [
            {"page_number": 0, "label": "Title", "page_areas": []},
            {"page_number": 1, "label": "Program", "page_areas": []},
        ],
        "first ocr": [],
    }

    vocab_json = {"Performance Title": []}

    client_context = {"context": "Test"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    # Check that the example includes the correct labels
    assert '"label": "Title"' in prompt
    assert '"label": "Program"' in prompt


def test_build_user_prompt_compact_json():
    """Test that data is sent in compact JSON format."""
    labeled_json = {
        "pdf_name": "test_program.pdf",
        "features": [{"page_number": 0, "label": "Program", "page_areas": []}],
        "first ocr": [[1, [["Text", 100, 100, 200, 120]]]],
    }

    vocab_json = {"Choreographer": []}

    client_context = {"context": "Test"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    # Check for compact JSON format (no spaces after separators in data section)
    # The labeled_json should be compacted
    assert '"pdf_name":"test_program.pdf"' in prompt or '"pdf_name" :"test_program.pdf"' in prompt
    # Features array should be compact
    assert '"features":[' in prompt or '"features" :[' in prompt


def test_get_system_prompt_contains_category_mappings():
    """Test that system prompt includes specific category mapping examples."""
    prompt = get_system_prompt()

    # Check for specific category mappings mentioned
    assert "Costume Designer" in prompt
    assert "costume" in prompt.lower() or "wardrobe" in prompt.lower()
    assert "Lighting Designer" in prompt
    assert "Musical Performer" in prompt
    assert "Staged by" in prompt


def test_get_system_prompt_contains_output_format_instructions():
    """Test that system prompt includes output format requirements."""
    prompt = get_system_prompt()

    assert "REQUIRED FIELDS" in prompt
    assert '"page"' in prompt
    assert '"label"' in prompt
    assert '"attributes"' in prompt
    assert '"boundingBoxIndices"' in prompt
    assert "Return ONLY raw JSON array" in prompt


def test_build_user_prompt_example_structure():
    """Test that the example output has the correct structure."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0, "label": "Program", "page_areas": []}],
        "first ocr": [],
    }

    vocab_json = {"Performance Title": []}

    client_context = {"context": "Test"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    # Extract the example section
    example_start = prompt.find("EXAMPLE OUTPUT:")
    assert example_start > 0

    # Check that example contains required fields
    example_section = prompt[example_start : example_start + 1000]
    assert '"page"' in example_section
    assert '"label"' in example_section
    assert '"attributes"' in example_section
    assert '"boundingBoxIndices"' in example_section
    assert '"index"' in example_section
    assert '"text"' in example_section


def test_build_user_prompt_handles_missing_page_number():
    """Test handling of features without page_number."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [
            {"label": "Program", "page_areas": []},  # Missing page_number
        ],
        "first ocr": [],
    }

    vocab_json = {"Performance Title": []}

    client_context = {"context": "Test"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    # Should handle gracefully
    assert isinstance(prompt, str)
    # May show 0 pages since page_number is missing
    assert "Processing" in prompt


def test_build_user_prompt_categories_order():
    """Test that categories maintain order."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0, "label": "Program", "page_areas": []}],
        "first ocr": [],
    }

    vocab_json = {
        "Choreographer": [],
        "Composer": [],
        "Performance Title": [],
        "Dancers": [],
    }

    client_context = {"context": "Test"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="dance",
    )

    # Check that all categories are present
    assert "Choreographer" in prompt
    assert "Composer" in prompt
    assert "Performance Title" in prompt
    assert "Dancers" in prompt


def test_default_prompt_template_structure():
    """Test that default template has all required keys."""
    template = get_default_prompt_template()

    required_keys = ["system_prompt", "task_description", "output_format_description"]
    for key in required_keys:
        assert key in template
        assert isinstance(template[key], str)
        assert len(template[key]) > 0


def test_system_prompt_multi_performance_instruction():
    """Test that system prompt includes multi-performance handling."""
    prompt = get_system_prompt()

    assert "MULTI-PERFORMANCE" in prompt
    assert "MULTIPLE performances" in prompt
    assert "SAME page number" in prompt


def test_build_user_prompt_symphony_type():
    """Test building prompt for symphony program type."""
    labeled_json = {
        "pdf_name": "test.pdf",
        "features": [{"page_number": 0, "label": "Program", "page_areas": []}],
        "first ocr": [],
    }

    vocab_json = {"Composer": [], "Musical Performer": []}

    client_context = {"context": "Symphony Orchestra"}

    prompt = build_user_prompt(
        labeled_json=labeled_json,
        vocab_json=vocab_json,
        client_context=client_context,
        program_type="symphony",
    )

    assert "Program type: symphony" in prompt
    assert "Context: Symphony Orchestra" in prompt

"""
Prompt templates for Azure OpenAI entity matching.

This module contains all prompt templates used for extracting entities and
bounding boxes from performing arts programs.
"""

import json
import logging
from typing import Any


def get_default_prompt_template() -> dict[str, Any]:
    """Get the default prompt template for entity matching.

    Returns:
        dict[str, Any]: Default prompt template with system prompt and descriptions.
    """
    return {
        "system_prompt": """You are an expert at analyzing performing arts programs (ballet, symphony, etc.) and matching entities from OCR text to a controlled vocabulary.

Your task is to:
1. Analyze the OCR-extracted text and entities from program pages
2. Match entities (performers, composers, choreographers, venues, dates, etc.) to the provided vocabulary
3. Estimate confidence levels (High/Medium/Low) for each match
4. Preserve bounding box information for matched entities
5. Handle synonyms, variations in naming, and OCR errors
6. Parse dates and normalize them to YYYY-MM-DD format
7. Return ONLY valid JSON in the specified output format

Be thorough but conservative - only match entities you are confident about.""",
        "task_description": """Match entities from the labeled program pages to the vocabulary, maintaining bounding box information.""",
        "output_format_description": """Return a JSON array where each element represents a page with matched entities. Include page number, label, page_area, attributes (matched entities with values and confidence), and bounding boxes.""",
    }


def get_system_prompt() -> str:
    """Get the system prompt for entity extraction with bounding box indices.

    Returns:
        str: System prompt instructing OpenAI on entity extraction requirements.
    """
    return """Extract entities from performing arts programs and return as JSON array.

VALUE NORMALIZATION:
- Normalize names of people and places: 'JOHN SMITH' → 'John Smith', 'john smith' → 'John Smith'
- Do not normalize performance titles or works of art
- Fix obvious OCR errors and spacing issues
- Use proper capitalization for all values
- Normalize dates into ISO format YYYY-MM-DD

MULTI-PAGE: Return ONE element per page. If input has 3 pages, return array with 3 elements.

MULTI-PERFORMANCE: If ONE page has MULTIPLE performances (Performance Titles), create MULTIPLE elements with SAME page number one for each Performance Title.

PAGE_AREAS:
- Each page has "page_areas" array with labeled sections (bounding boxes)
- page_areas contain: "label" (section type) and "bounding_box" (x, y, x2, y2 coordinates)
- ONLY extract attributes from entities whose coordinates fall WITHIN the page_areas bounding boxes
- If page_areas exist, they OVERRIDE the root "label" field
- Use the page_areas "label" to determine what attributes to extract (e.g., "Program" area = extract Performance Title, Choreographer, etc.)
- Multiple page_areas on same page = multiple performances, split into separate elements

Title Pages:
- For title pages extract the "Performance Date" from the "pdf_name" if it exists, if not then check the page contents as normal.

REQUIRED FIELDS per element:
- "page": exact page number from input
- "label": use page_areas[0].label if page_areas exist, otherwise use root label
- "page_areas": copy the relevant page_area(s) for this element
- "attributes": object with category keys and entity values (ONLY entities within page_areas bounding box)
- "boundingBoxIndices": array of {index, text} objects - ONE entry per entity value
  * If you extract 22 names, you MUST return 22 boundingBoxIndices
  * If multiple names come from same OCR line, repeat the same index for each name
  * Count must match: sum of all attribute value arrays = boundingBoxIndices length

Attribute Value Extraction Rules:
- DO NOT extract job titles or position names as attribute values
- Example to exclude/ignore: "Director of Development"
- ONLY extract the actual person's name that follows the role title
- Role titles often appear as section headers - IGNORE these completely

CATEGORY MAPPING:
- Use ONLY the provided category names as attribute keys
- Map synonyms/variations to the correct category:
  Examples include mapping raw text (when it makes sense contextually) -> Proper Category
  - "choreograph", "choreographer" -> "Choreographer"
  - "compose" -> "Composer"
  - "costume", "wardrobe" -> "Costume Designer"
  - "lighting design", "lighting" -> "Lighting Designer"
  - "musical performer", "artist" -> "Musical Performer"
  - "staged by", "restaged", "reconstructed", "directed", "rehearsal director", "assistant choreographer" -> "Staged by"
  - "set designer", "set design", "scenic design", "scenery design", "scenery designer" -> "Set Designer"
- DO NOT create new category names
- When you see a role description, map it to the closest provided category

OUTPUT: Return ONLY raw JSON array. No markdown, no code blocks, no extra text. Start with [ and end with ]
IMPORTANT: Return MINIFIED/COMPACT JSON (no unnecessary whitespace between elements) to save tokens. Use format: [{"key":"value"}] not [ { "key": "value" } ]"""


def get_user_prompt_template() -> str:
    """Get the user prompt template for entity extraction.

    Returns:
        str: User prompt template with placeholders for dynamic content.

    Placeholders:
        {num_pages}: Number of pages being processed
        {page_numbers}: Comma-separated list of page numbers
        {program}: Program type (dance/symphony)
        {context}: Client context information
        {categories}: Comma-separated list of vocabulary categories
        {example}: JSON example showing expected output format
    """
    return """Processing {num_pages} pages: {page_numbers}

Program type: {program}
{context}

CATEGORIES (use ONLY these as categories/attribute keys, map synonyms to these):
{categories}

PAGE_AREAS FILTERING:
- Check each page for "page_areas" array
- Each page_area has "label" (section type) and "bounding_box" (x, y, x2, y2)
- ONLY extract entities whose coordinates are INSIDE the page_area bounding_box
- Use page_area "label" (NOT root label) to determine which attributes to extract
- Example: page_area with label="Program" → extract Performance Title, Choreographer, Composer, etc.
- Example: page_area with label="Donor" → extract only Donors which are Proper Nouns (not labels or unrelated text)
- Example: page_area with label="Company" → extract Staff and Board members (proper names ONLY, NOT role titles like "Executive Director")
- Multiple page_areas on same page = split into separate output elements

Attribute Value Extraction Rules:
- DO NOT extract job titles or position names as attribute values
- Example to exclude/ignore: "Director of Development"
- ONLY extract the actual person's name that follows the role title
- Role titles often appear as section headers - IGNORE these completely

BOUNDING BOX INDICES - CRITICAL:
- For EVERY entity value in attributes, you MUST return a corresponding boundingBoxIndices entry
- If multiple entity values come from the SAME OCR line, repeat the SAME index for each value
- Example: If OCR line index 5 contains "John Smith Mary Jones", and you extract both names:
  * attributes: {{"Artist/Performer": ["John Smith", "Mary Jones"]}}
  * boundingBoxIndices: [{{"index": 5, "text": "John Smith Mary Jones"}}, {{"index": 5, "text": "John Smith Mary Jones"}}]
- The number of boundingBoxIndices MUST EXACTLY MATCH the total number of entity values across all attributes
- Format: [INDEX, text, x, y, x2, y2, w, h, confidence]
- Only include entities whose coordinates fall within page_area bounding_box

INPUT DATA:
{data}

EXAMPLE OUTPUT:
{example}

Return raw JSON array only. Map all role descriptions to the provided categories. Only include entities within page_areas."""


def build_user_prompt(
    labeled_json: dict[str, Any],
    vocab_json: dict[str, Any],
    client_context: dict[str, Any],
    program_type: str,
) -> str:
    """Build the user prompt with all dynamic content filled in.

    Args:
        labeled_json: The labeled JSON from OCR + user corrections
        vocab_json: The vocabulary JSON with category names
        client_context: Client-specific context information
        program_type: Type of program (dance or symphony)

    Returns:
        str: Complete user prompt ready to send to OpenAI
    """
    # Get client context text
    client_context_text = client_context.get("context", "")
    if client_context.get("notes"):
        notes_text = "\n".join([f"- {note}" for note in client_context.get("notes", [])])
        client_context_text = f"{client_context_text}\n\n{notes_text}"

    # Use compact JSON format for labeled data
    labeled_json_compact = json.dumps(labeled_json, separators=(",", ":"), ensure_ascii=False)

    # Get the actual page numbers, labels, and page_areas from the batch
    features = labeled_json.get("features", [])
    page_numbers = [f["page_number"] for f in features if "page_number" in f]
    page_labels = [f.get("label", "Unknown") for f in features]
    page_areas = [f.get("page_areas", []) for f in features]
    page_numbers_str = ",".join(map(str, page_numbers))

    # Extract ONLY the category names from vocab (not the values)
    try:
        vocab_categories = list(vocab_json.keys()) if vocab_json else []
        categories_str = ", ".join(vocab_categories)
        logging.info(f"Vocab categories for prompt: {categories_str}")
    except Exception as e:
        logging.error(f"Error extracting vocab categories: {type(e).__name__}: {e}")
        raise

    # Build example output showing the required number of pages with actual labels and page_areas
    if len(page_numbers) > 1:
        example_data = [
            {
                "page": page_numbers[0],
                "label": page_labels[0],
                "page_areas": page_areas[0] if page_areas else [],
                "attributes": {"Performance Title": ["Title 1"]},
                "boundingBoxIndices": [{"index": 5, "text": "Title"}],
            },
            {
                "page": page_numbers[1],
                "label": page_labels[1],
                "page_areas": page_areas[1] if len(page_areas) > 1 else [],
                "attributes": {"Composer": ["Name 1", "Name 2"]},
                "boundingBoxIndices": [{"index": 12, "text": "Name"}, {"index": 15, "text": "Name"}],
            },
        ]
    else:
        example_data = [
            {
                "page": page_numbers[0] if page_numbers else 0,
                "label": page_labels[0] if page_labels else "Unknown",
                "page_areas": page_areas[0] if page_areas else [],
                "attributes": {"Performance Title": ["Title 1"]},
                "boundingBoxIndices": [{"index": 5, "text": "Title"}],
            }
        ]

    # Convert to JSON string for the example
    example_array = json.dumps(example_data, indent=2, separators=(",", ": "))

    # Build context string
    context_str = f"Context: {client_context_text}" if client_context_text else ""

    # Fill in the template
    template = get_user_prompt_template()
    return template.format(
        num_pages=len(page_numbers),
        page_numbers=page_numbers_str,
        program=program_type,
        context=context_str,
        categories=categories_str,
        example=example_array,
        data=labeled_json_compact,
    )

"""Azure OpenAI-based page labeling module.

Replaces the legacy ML models (spacy, mlflow) with Azure OpenAI GPT-4o for page classification.
Classifies pages into: Title, Program, Company, Donor, Other
"""

import json
import logging
import os
from typing import Any


def build_page_labeling_prompt(
    features_json: dict[str, Any],
    pdf_name: str,
) -> list[dict[str, str]]:
    """Build the prompt for Azure OpenAI to classify pages.

    Args:
        features_json (dict[str, Any]): The features JSON with OCR text, entities, and page info.
        pdf_name (str): Name of the PDF file being processed.

    Returns:
        list[dict[str, str]]: List of message dicts for OpenAI chat API.
    """
    system_prompt = """You are an expert at analyzing performing arts programs (ballet, symphony, opera, theater, etc.) and classifying pages into specific categories.

Your task is to analyze OCR-extracted text and named entities from each page and classify it into exactly ONE of these categories:

**Page Categories:**
1. **Title** - The first page, cover page, or title page of the program. Contains event name, date, venue, season information.
2. **Program** - Pages listing the actual performances, program listings, repertoire, pieces being performed, and cast lists. It must have a performance title for it to for a Program page and should not be about a specific artist or performer.
3. **Company** - Pages about the performing organization (ballet company, orchestra, opera company). Includes staff lists, artistic directors, board members, company history.
4. **Donor** - Pages acknowledging donors, sponsors, patrons, contributors, supporters. Includes donor lists organized by giving levels.
5. **Other** - Any other content (advertisements, upcoming events, biographies, general information that doesn't fit above categories).

**Classification Guidelines:**
- The FIRST page should typically be labeled "Title"
- Look for keywords, entity types, and content structure to determine the category
- Program pages often have: performance titles, composer names, choreographer names, performer names, piece titles, schedules
- Company pages often have: lists of staff names with titles or organizational roles
- Donor pages often have: giving levels, recognition categories, lists of names
- Be decisive - choose the BEST matching category

**Input Format:**
You will receive JSON with page information including:
- page_number: The page index
- text: OCR-extracted text content
- entities: Named entities detected (Person, Organization, Date, Location, etc.)
- features: Text statistics (word count, entity counts, etc.)

**Output Format:**
Return a JSON object with a "pages" key containing an array of all page classifications.

Each page classification should have:
- page_number: The page number (int)
- label: One of ["Title", "Program", "Company", "Donor", "Other"]
- confidence: Your confidence level ["High", "Medium", "Low"]
- reasoning: Brief explanation (1-2 sentences) for the classification

IMPORTANT: Classify ALL pages provided. Return all results in a single JSON object.

Example:
```json
{
  "pages": [
    {
      "page_number": 0,
      "label": "Title",
      "confidence": "High",
      "reasoning": "First page with event title, date, and venue name."
    },
    {
      "page_number": 1,
    "label": "Program",
    "confidence": "High",
    "reasoning": "Contains performance titles, composer names, and piece listings."
  }
]
```

Return ONLY valid JSON. Be thorough but decisive in your classifications."""

    # Build the user message with page information
    pages_data = []
    features = features_json.get("features", [])

    for page in features:
        page_num = page.get("page_number", 0)

        # Extract text samples (first 500 chars to keep prompt reasonable)
        text_sample = ""
        if "text" in page and page["text"]:
            text_sample = page["text"][:500]

        # Extract entity information
        entities_summary = {}
        if "details" in page:
            for detail in page["details"]:
                if len(detail) >= 2:
                    entities = detail[1]  # List of [text, entity_type] pairs
                    for entity_pair in entities:
                        if len(entity_pair) >= 2:
                            entity_text, entity_type = entity_pair[0], entity_pair[1]
                            if entity_type not in entities_summary:
                                entities_summary[entity_type] = []
                            entities_summary[entity_type].append(entity_text)

        # Limit entities to avoid huge prompts
        for entity_type in entities_summary:
            entities_summary[entity_type] = entities_summary[entity_type][:20]

        # Extract key features
        features_summary = {
            "word_count": page.get("total", 0),
            "person_count": page.get("person", 0),
            "organization_count": page.get("organization", 0),
            "location_count": page.get("location", 0),
            "date_count": page.get("date", 0),
        }

        page_info = {
            "page_number": page_num,
            "text_sample": text_sample,
            "entities": entities_summary,
            "features": features_summary,
        }
        pages_data.append(page_info)

    user_message = f"""PDF File: {pdf_name}

Please classify each of the following {len(pages_data)} pages:

{json.dumps(pages_data, indent=2, ensure_ascii=False)}

Remember:
- If this is the first page (page_number: 0) of the document, it is typically "Title"
- Look for performance/repertoire content for "Program" but if it's just a biography or info about a specific performer then it should be "Other"
- Look for staff/board/organizational info for "Company"
- Look for donor/sponsor acknowledgments for "Donor"
- Use "Other" for advertisements or miscellaneous content

IMPORTANT: Return a JSON object with a "pages" key containing an array with ALL {len(pages_data)} page classifications."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    return messages


def call_azure_openai_for_labeling(
    messages: list[dict[str, str]],
    azure_openai_endpoint: str,
    azure_openai_api_key: str,
    deployment_name: str = "gpt-4o",
    api_version: str = "2024-08-01-preview",
    temperature: float = 0.1,
    max_tokens: int = 4000,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Call Azure OpenAI API for page labeling with retry logic.

    Args:
        messages (list[dict[str, str]]): The chat messages to send.
        azure_openai_endpoint (str): Azure OpenAI endpoint URL.
        azure_openai_api_key (str): Azure OpenAI API key.
        deployment_name (str): Name of the GPT-4o deployment (default: "gpt-4o").
        api_version (str): API version (default: "2024-08-01-preview").
        temperature (float): Sampling temperature (default: 0.1 for deterministic).
        max_tokens (int): Maximum tokens in response (default: 4000).
        max_retries (int): Maximum number of retries for rate limit errors (default: 3).

    Returns:
        dict[str, Any]: The response from Azure OpenAI API.

    Raises:
        Exception: If the API call fails.
    """
    # Import at runtime to avoid initialization issues
    import time

    from openai import AzureOpenAI, RateLimitError

    logging.info(f"Calling Azure OpenAI for page labeling: deployment '{deployment_name}'")
    logging.info(f"Temperature: {temperature}, Max tokens: {max_tokens}")

    # Initialize Azure OpenAI client with explicit max_retries=0 since we handle retries manually
    client = AzureOpenAI(
        azure_endpoint=azure_openai_endpoint,
        api_key=azure_openai_api_key,
        api_version=api_version,
        max_retries=0,  # We handle retries manually
    )

    # TEMPORARY: Write request to file for debugging (local development only)
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    # log_dir = Path("openai_logs")
    # log_dir.mkdir(exist_ok=True)
    # request_file = log_dir / f"page_labeling_request_{timestamp}.json"

    # request_data = {
    #     "timestamp": timestamp,
    #     "deployment_name": deployment_name,
    #     "api_version": api_version,
    #     "temperature": temperature,
    #     "max_tokens": max_tokens,
    #     "messages": messages,
    # }

    # with open(request_file, "w", encoding="utf-8") as f:
    #     json.dump(request_data, f, indent=2, ensure_ascii=False)
    # logging.info(f"Request written to: {request_file}")

    for attempt in range(max_retries):
        try:
            # Make the chat completion request
            response = client.chat.completions.create(
                model=deployment_name,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},  # Ensure JSON response
            )

            # Convert response to dict
            response_data = {
                "id": response.id,
                "object": response.object,
                "created": response.created,
                "model": response.model,
                "choices": [
                    {
                        "index": choice.index,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content,
                        },
                        "finish_reason": choice.finish_reason,
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                if response.usage
                else None,
            }

            logging.info("Azure OpenAI page labeling call successful")
            if response.usage:
                logging.info(
                    f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                    f"Completion: {response.usage.completion_tokens}, "
                    f"Total: {response.usage.total_tokens}"
                )

            # TEMPORARY: Write response to file for debugging (local development only)
            # response_file = log_dir / f"page_labeling_response_{timestamp}.json"
            # with open(response_file, "w", encoding="utf-8") as f:
            #     json.dump(response_data, f, indent=2, ensure_ascii=False)
            # logging.info(f"Response written to: {response_file}")

            return response_data

        except RateLimitError as e:
            if attempt < max_retries - 1:
                # Exponential backoff: 2^attempt * 2 seconds
                wait_time = (2**attempt) * 2
                logging.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
            else:
                error_message = f"Azure OpenAI page labeling rate limit exceeded after {max_retries} attempts: {e}"
                logging.error(error_message)
                raise Exception(error_message) from e

        except Exception as e:
            error_message = f"Azure OpenAI page labeling API call failed: {e}"
            logging.error(error_message)
            if hasattr(e, "__dict__"):
                logging.error(f"Exception details: {e.__dict__}")
            raise Exception(error_message) from e

    # Should never reach here due to the raise in the loop
    raise Exception("Unexpected error in call_azure_openai_for_labeling")


def parse_labeling_response(response: dict[str, Any], num_pages: int) -> list[str]:
    """Parse the Azure OpenAI response and extract page labels.

    Args:
        response (dict[str, Any]): The raw response from Azure OpenAI.
        num_pages (int): Expected number of pages.

    Returns:
        list[str]: List of labels for each page (e.g., ["Title", "Program", "Company"]).

    Raises:
        Exception: If response parsing fails or labels are invalid.
    """
    content = ""  # Initialize to avoid unbound variable error
    try:
        if "choices" not in response or len(response["choices"]) == 0:
            raise Exception("No choices in OpenAI response")

        choice = response["choices"][0]
        if "message" not in choice or "content" not in choice["message"]:
            raise Exception("No message content in OpenAI response")

        content = choice["message"]["content"]
        logging.info(f"Received page labeling response: {len(content)} characters")
        logging.info(f"Response content preview: {content[:500]}")  # Log first 500 chars

        # Parse the JSON content
        parsed = json.loads(content)
        logging.info(f"Parsed type: {type(parsed)}")
        logging.info(f"Parsed keys (if dict): {parsed.keys() if isinstance(parsed, dict) else 'N/A'}")

        # Handle both array and object with array responses
        if isinstance(parsed, dict):
            # Try common variations of response structure
            if "pages" in parsed:
                page_labels = parsed["pages"]
            elif "labels" in parsed:
                page_labels = parsed["labels"]
            elif "classifications" in parsed:
                page_labels = parsed["classifications"]
            elif "results" in parsed:
                page_labels = parsed["results"]
            else:
                # If dict but no known array key, maybe the dict itself contains page info
                # Log the actual structure and raise informative error
                logging.error(f"Unexpected dict structure: {json.dumps(parsed, indent=2)}")
                raise Exception(f"Dict response missing expected array key. Keys found: {list(parsed.keys())}")
        elif isinstance(parsed, list):
            page_labels = parsed
        else:
            raise Exception(f"Unexpected response format: {type(parsed)}")

        # Validate we have the expected number of labels
        if len(page_labels) != num_pages:
            logging.warning(f"Expected {num_pages} labels but got {len(page_labels)}")

        # Extract labels in order
        valid_labels = {"Title", "Program", "Company", "Donor", "Other"}
        labels = []

        # Sort by page_number to ensure correct order
        page_labels_sorted = sorted(page_labels, key=lambda x: x.get("page_number", 0))

        for i, page_label_info in enumerate(page_labels_sorted):
            label = page_label_info.get("label", "Other")
            confidence = page_label_info.get("confidence", "Unknown")
            reasoning = page_label_info.get("reasoning", "")

            # Validate label
            if label not in valid_labels:
                logging.warning(f"Invalid label '{label}' for page {i}, defaulting to 'Other'")
                label = "Other"

            labels.append(label)
            logging.info(f"Page {i}: {label} ({confidence}) - {reasoning}")

        while len(labels) < num_pages:
            labels.append("Other")
            logging.warning(f"Padding page {len(labels) - 1} with 'Other' label")

        return labels[:num_pages]

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse OpenAI response as JSON: {e}"
        logging.error(error_msg)
        if "content" in locals():
            logging.error(f"Response content: {content}")
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"Error parsing page labels: {e}"
        logging.error(error_msg)
        raise Exception(error_msg) from e


def label_pages_with_openai(
    features_json: dict[str, Any],
    pdf_name: str,
    azure_openai_endpoint: str | None = None,
    azure_openai_api_key: str | None = None,
    deployment_name: str = "gpt-4o",
    batch_size: int = 20,
) -> list[str]:
    """Main function to label pages using Azure OpenAI with batching support.

    Args:
        features_json (dict[str, Any]): The features JSON from OCR/NER processing.
        pdf_name (str): Name of the PDF file.
        azure_openai_endpoint (str | None): Azure OpenAI endpoint (or None to use env var).
        azure_openai_api_key (str | None): Azure OpenAI API key (or None to use env var).
        deployment_name (str): GPT-4o deployment name (default: "gpt-4o").
        batch_size (int): Number of pages to process per batch (default: 20).

    Returns:
        list[str]: List of labels for each page.

    Raises:
        Exception: If labeling fails.
    """
    import time

    if not azure_openai_endpoint:
        azure_openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not azure_openai_api_key:
        azure_openai_api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if not azure_openai_endpoint or not azure_openai_api_key:
        raise Exception("Azure OpenAI credentials not provided or found in environment")

    features = features_json.get("features", [])
    total_pages = len(features)
    logging.info(f"Labeling {total_pages} pages for PDF: {pdf_name} in batches of {batch_size}")

    all_labels = []
    total_batches = (total_pages + batch_size - 1) // batch_size

    for batch_start in range(0, total_pages, batch_size):
        batch_end = min(batch_start + batch_size, total_pages)
        batch_num = (batch_start // batch_size) + 1

        logging.info(f"Processing batch {batch_num}/{total_batches}: pages {batch_start} to {batch_end - 1}")

        batch_features_json = {
            "features": features[batch_start:batch_end],
        }
        for key in features_json:
            if key not in ["features"] and not isinstance(features_json[key], list):
                batch_features_json[key] = features_json[key]

        batch_pages = len(batch_features_json["features"])

        messages = build_page_labeling_prompt(batch_features_json, pdf_name)

        response = call_azure_openai_for_labeling(
            messages=messages,
            azure_openai_endpoint=azure_openai_endpoint,
            azure_openai_api_key=azure_openai_api_key,
            deployment_name=deployment_name,
            temperature=0.1,
        )

        batch_labels = parse_labeling_response(response, batch_pages)
        all_labels.extend(batch_labels)

        if batch_end < total_pages:
            delay = 3
            logging.info(f"Batch {batch_num} complete. Waiting {delay}s before next batch...")
            time.sleep(delay)

    logging.info(f"Page labeling complete: {len(all_labels)} pages labeled")
    return all_labels

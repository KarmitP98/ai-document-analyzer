"""Azure OpenAI helper module for entity matching using GPT-4o."""

import json
import logging
import os
import time
from typing import Any

from azure.storage.blob import BlobServiceClient

from classes.src.prompts import build_user_prompt, get_default_prompt_template, get_system_prompt


def process_large_page_with_chunking(
    feature: dict[str, Any],
    first_ocr_page: list[Any],
    labeled_json: dict[str, Any],
    vocab_json: dict[str, Any],
    client_context: dict[str, Any],
    prompt_template: dict[str, Any],
    program_type: str,
    azure_openai_endpoint: str,
    azure_openai_api_key: str,
    chunk_size: int = 250,
) -> list[dict[str, Any]]:
    """Process a large page by chunking its OCR data and merging results.

    Args:
        feature: The feature dictionary for the page
        first_ocr_page: The OCR data for this page [page_num, [ocr_entries]] (already indexed)
        labeled_json: Original labeled JSON with full indexed OCR for validation
        vocab_json: Vocabulary JSON
        client_context: Client context
        prompt_template: Prompt template
        program_type: Program type
        azure_openai_endpoint: Azure OpenAI endpoint
        azure_openai_api_key: Azure OpenAI API key
        chunk_size: Maximum OCR entries per chunk

    Returns:
        list[dict[str, Any]]: Merged matched entities from all chunks
    """
    page_num = first_ocr_page[0]
    ocr_entries = first_ocr_page[1]
    total_entries = len(ocr_entries)
    num_chunks = (total_entries + chunk_size - 1) // chunk_size

    logging.info(f"Page {page_num}: Chunking {total_entries} OCR entries into {num_chunks} chunks of ~{chunk_size} entries")

    all_chunk_entities = []

    for chunk_idx in range(num_chunks):
        chunk_start = chunk_idx * chunk_size
        chunk_end = min(chunk_start + chunk_size, total_entries)
        ocr_chunk = ocr_entries[chunk_start:chunk_end]

        logging.info(f"Page {page_num}: Processing chunk {chunk_idx + 1}/{num_chunks} (OCR entries {chunk_start}-{chunk_end})")

        # Create chunk-specific labeled JSON with the chunk's OCR data
        # Note: OCR entries are already indexed, so we just use them as-is
        chunk_labeled_json = {
            "pdf_name": labeled_json.get("pdf_name", ""),
            "features": [feature],
            "first ocr": [[page_num, ocr_chunk]],
        }

        for key in labeled_json:
            if key not in ["features", "final ocr", "first ocr"] and not isinstance(labeled_json[key], list):
                chunk_labeled_json[key] = labeled_json[key]

        # Build prompt for chunk
        chunk_messages = build_openai_prompt(chunk_labeled_json, vocab_json, client_context, prompt_template, program_type)

        try:
            # Call OpenAI for this chunk
            chunk_response = call_azure_openai(
                messages=chunk_messages,
                azure_openai_endpoint=azure_openai_endpoint,
                azure_openai_api_key=azure_openai_api_key,
                deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            )

            chunk_entities = parse_openai_response(chunk_response)
            chunk_entities = filter_invalid_categories(chunk_entities, vocab_json)

            # Convert indices and validate using FULL indexed OCR data from labeled_json
            # No need to adjust indices - they're already correct from the original indexing
            chunk_entities = convert_indices_to_bounding_boxes(chunk_entities, labeled_json)
            chunk_entities = find_missing_bounding_boxes(chunk_entities, labeled_json, similarity_threshold=85.0)
            chunk_entities = validate_and_adjust_confidence(chunk_entities, vocab_json)
            chunk_entities = filter_bounding_boxes_by_page_areas(chunk_entities)

            all_chunk_entities.extend(chunk_entities)

        except Exception as e:
            error_msg = str(e)
            # If chunk still too large (truncated response OR malformed JSON), recursively split into smaller chunks
            if any(keyword in error_msg.lower() for keyword in ["truncated", "max_tokens", "expecting", "json", "delimiter"]):
                logging.warning(f"Page {page_num} chunk {chunk_idx + 1} too large or malformed JSON, splitting into smaller sub-chunks")

                # Recursively process with half the chunk size
                smaller_chunk_size = chunk_size // 2
                if smaller_chunk_size < 25:
                    logging.error(f"Page {page_num} chunk {chunk_idx + 1} cannot be split further (chunk_size={smaller_chunk_size})")
                    raise Exception(f"Chunk too large even at minimum size: {e}") from e

                # Create a mini feature for this chunk range
                chunk_feature = feature.copy()
                chunk_first_ocr = [page_num, ocr_chunk]

                # Recursively process with smaller chunks
                sub_chunk_entities = process_large_page_with_chunking(
                    feature=chunk_feature,
                    first_ocr_page=chunk_first_ocr,
                    labeled_json=chunk_labeled_json,
                    vocab_json=vocab_json,
                    client_context=client_context,
                    prompt_template=prompt_template,
                    program_type=program_type,
                    azure_openai_endpoint=azure_openai_endpoint,
                    azure_openai_api_key=azure_openai_api_key,
                    chunk_size=smaller_chunk_size,
                )

                all_chunk_entities.extend(sub_chunk_entities)
            else:
                # Other error, re-raise
                raise

    # Merge results from all chunks for this page
    if not all_chunk_entities:
        return []

    merged_entity = all_chunk_entities[0].copy()

    # Merge attributes and bounding boxes from all chunks
    for chunk_entity in all_chunk_entities[1:]:
        chunk_attributes = chunk_entity.get("attributes", {})
        for category, values in chunk_attributes.items():
            if category not in merged_entity["attributes"]:
                merged_entity["attributes"][category] = []
            merged_entity["attributes"][category].extend(values)

        chunk_bboxes = chunk_entity.get("boundingBoxes", [])
        merged_entity.setdefault("boundingBoxes", []).extend(chunk_bboxes)

    # Deduplicate values within each category
    for category in merged_entity["attributes"]:
        merged_entity["attributes"][category] = list(dict.fromkeys(merged_entity["attributes"][category]))

    logging.info(f"Page {page_num}: Merged {num_chunks} chunks into {len(merged_entity.get('boundingBoxes', []))} total bounding boxes")

    return [merged_entity]


def chunk_large_page_ocr(
    feature: dict[str, Any],
    first_ocr_entries: list[Any],
    max_ocr_entries: int = 200,
) -> list[tuple[dict[str, Any], list[Any]]]:
    """Split a large page into multiple chunks based on OCR entry count.

    Args:
        feature: The feature dictionary for the page
        first_ocr_entries: The OCR entries for the page
        max_ocr_entries: Maximum OCR entries per chunk (default: 200)

    Returns:
        list[tuple[dict[str, Any], list[Any]]]: List of (feature, ocr_chunk) tuples
    """
    if len(first_ocr_entries) <= max_ocr_entries:
        return [(feature, first_ocr_entries)]

    chunks = []
    num_chunks = (len(first_ocr_entries) + max_ocr_entries - 1) // max_ocr_entries

    for chunk_idx in range(num_chunks):
        chunk_start = chunk_idx * max_ocr_entries
        chunk_end = min(chunk_start + max_ocr_entries, len(first_ocr_entries))
        ocr_chunk = first_ocr_entries[chunk_start:chunk_end]

        feature_chunk = feature.copy()
        feature_chunk["chunk_info"] = {
            "chunk_number": chunk_idx + 1,
            "total_chunks": num_chunks,
            "ocr_range": [chunk_start, chunk_end],
        }

        chunks.append((feature_chunk, ocr_chunk))

    return chunks


def degrade_confidence(confidence: float | int | None) -> float:
    """Degrade confidence by one step: high (>0.8) -> medium (>0.5) -> low (≤0.5).

    Args:
        confidence: Current confidence score (0-1 range or percentage 0-100)

    Returns:
        float: Degraded confidence score
    """
    if confidence is None:
        return 0.5

    # Normalize to 0-1 range if it's in percentage form
    if confidence > 1:
        confidence = confidence / 100.0

    # Degrade by one confidence level
    if confidence > 0.8:  # High -> Medium
        return 0.8
    elif confidence > 0.5:  # Medium -> Low
        return 0.5

    return confidence


def get_vocab_value(category: str, value: str, vocab_json: dict[str, Any]) -> str | None:
    """Get the actual vocab value that matches the given value (case-insensitive).

    Args:
        category: The attribute category name
        value: The value to match
        vocab_json: Vocabulary dictionary

    Returns:
        str | None: The actual vocab value if found, None otherwise
    """
    if category not in vocab_json:
        return None

    vocab_values = vocab_json[category]

    # Handle both list format and dict with 'tags' key
    if isinstance(vocab_values, dict) and "tags" in vocab_values:
        vocab_values = vocab_values["tags"]

    if not isinstance(vocab_values, list):
        return None

    # Convert value to string for comparison
    value_str = str(value).lower().strip()

    # Find matching vocab item and return the actual vocab value
    for vocab_item in vocab_values:
        if str(vocab_item).lower().strip() == value_str:
            return str(vocab_item)

    return None


def is_value_in_vocab(category: str, value: str, vocab_json: dict[str, Any]) -> bool:
    """Check if a value exists in the vocabulary for a given category.

    Args:
        category: The attribute category name
        value: The value to check
        vocab_json: Vocabulary dictionary

    Returns:
        bool: True if value exists in vocab for this category, False otherwise
    """
    return get_vocab_value(category, value, vocab_json) is not None


def filter_invalid_categories(matched_entities: list[dict[str, Any]], vocab_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Filter out attribute categories that are not in the vocabulary.

    This is a safety filter in case OpenAI returns invalid categories despite
    being instructed to map synonyms to valid categories.

    Also filters corresponding boundingBoxIndices to maintain 1:1 mapping.

    Args:
        matched_entities: List of entity dictionaries with attributes
        vocab_json: Vocabulary dictionary with valid category keys

    Returns:
        list[dict[str, Any]]: Filtered matched_entities with only valid categories
    """
    valid_categories = set(vocab_json.keys())
    filtered_entities = []
    removed_categories = set()

    logging.info(f"Valid vocab categories: {sorted(valid_categories)}")

    for entity in matched_entities:
        filtered_entity = entity.copy()

        if "attributes" in filtered_entity:
            # Track which entity indices to keep
            entities_to_keep_indices = []
            filtered_attributes = {}
            entity_idx = 0

            logging.info(f"Page {entity.get('page', 'unknown')}: OpenAI returned categories: {list(filtered_entity['attributes'].keys())}")

            for category, values in filtered_entity["attributes"].items():
                if category in valid_categories:
                    filtered_attributes[category] = values
                    # Track indices of entities we're keeping
                    if isinstance(values, list):
                        for _ in values:
                            entities_to_keep_indices.append(entity_idx)
                            entity_idx += 1
                    else:
                        entity_idx += 1
                else:
                    removed_categories.add(category)
                    logging.warning(f"OpenAI returned invalid category '{category}' on page {entity.get('page', 'unknown')} - filtering out")
                    # Skip indices for removed entities
                    if isinstance(values, list):
                        entity_idx += len(values)
                    else:
                        entity_idx += 1

            filtered_entity["attributes"] = filtered_attributes

            # Filter boundingBoxIndices to match the filtered attributes
            if "boundingBoxIndices" in filtered_entity and entities_to_keep_indices:
                original_indices = filtered_entity["boundingBoxIndices"]
                filtered_indices = [original_indices[i] for i in entities_to_keep_indices if i < len(original_indices)]
                filtered_entity["boundingBoxIndices"] = filtered_indices

                removed_count = len(original_indices) - len(filtered_indices)
                if removed_count > 0:
                    logging.info(f"Page {entity.get('page', 'unknown')}: Removed {removed_count} boundingBoxIndices for invalid categories")

        filtered_entities.append(filtered_entity)

    if removed_categories:
        logging.warning(f"Filtered out {len(removed_categories)} invalid categories: {sorted(removed_categories)}")

    return filtered_entities


def download_prompt_template(blob_service_client: BlobServiceClient, client_path: str, temp_file_path: str) -> dict[str, Any]:
    """Download the prompt template from Azure Blob Storage.

    Args:
        blob_service_client (BlobServiceClient): Azure BlobServiceClient instance.
        client_path (str): Path to the client's container.
        temp_file_path (str): Temporary file path to store the prompt file.

    Returns:
        dict[str, Any]: The loaded prompt template as a dictionary.
    """
    try:
        prompt_client = blob_service_client.get_blob_client(container=f"data/{client_path}/prompts", blob="prompt.json")
        prompt_file_path = f"{temp_file_path}/prompt.json"
        logging.info(f"Downloading prompt template from {prompt_client.url} to {prompt_file_path}")
        with open(prompt_file_path, "wb") as download_file:
            blob_data = prompt_client.download_blob().readall()
            if isinstance(blob_data, str):
                blob_data = blob_data.encode("utf-8")
            download_file.write(blob_data)
        with open(prompt_file_path, "r", encoding="utf-8") as prompt_file:
            json_data = json.load(prompt_file)
            return json_data
    except Exception as e:
        error_message = f"Error downloading prompt template: {e}. Using default prompt."
        logging.warning(error_message)
        # Return a default prompt template if file not found
        return get_default_prompt_template()


def download_client_context(blob_service_client: BlobServiceClient, client_path: str, temp_file_path: str) -> dict[str, Any]:
    """Download the client-specific context from Azure Blob Storage.

    Args:
        blob_service_client (BlobServiceClient): Azure BlobServiceClient instance.
        client_path (str): Path to the client's container.
        temp_file_path (str): Temporary file path to store the context file.

    Returns:
        dict[str, Any]: The loaded client context as a dictionary.
    """
    try:
        context_client = blob_service_client.get_blob_client(container=f"data/{client_path}/prompts", blob="prompt_client_context.json")
        context_file_path = f"{temp_file_path}/prompt_client_context.json"
        logging.info(f"Downloading client context from {context_client.url} to {context_file_path}")
        with open(context_file_path, "wb") as download_file:
            blob_data = context_client.download_blob().readall()
            if isinstance(blob_data, str):
                blob_data = blob_data.encode("utf-8")
            download_file.write(blob_data)
        with open(context_file_path, "r", encoding="utf-8") as context_file:
            json_data = json.load(context_file)
            return json_data
    except Exception as e:
        error_message = f"Error downloading client context: {e}. Using empty context."
        logging.warning(error_message)
        return {"context": "", "notes": []}


# Note: get_default_prompt_template() is now imported from prompts.py


def build_openai_prompt(
    labeled_json: dict[str, Any],
    vocab_json: dict[str, Any],
    client_context: dict[str, Any],
    prompt_template: dict[str, Any],
    program_type: str,
) -> list[dict[str, str]]:
    """Build the complete prompt for Azure OpenAI including system and user messages.

    Uses compact JSON formatting (no indentation) to minimize token usage.
    Does NOT send vocabulary - OpenAI extracts entities, we match locally with fuzzy matching.

    Args:
        labeled_json (dict[str, Any]): The labeled JSON from OCR + user corrections.
        vocab_json (dict[str, Any]): The vocabulary JSON (not sent to OpenAI, only used for local matching).
        client_context (dict[str, Any]): Client-specific context information.
        prompt_template (dict[str, Any]): The prompt template with instructions.
        program_type (str): Type of program (dance or symphony).

    Returns:
        list[dict[str, str]]: List of messages for the OpenAI chat completion API.
    """
    # Strip unnecessary fields from labeled_json to reduce token usage
    # Only keep: pdf_name, features (with page_number, label, page_areas), first ocr
    stripped_json = {
        "pdf_name": labeled_json.get("pdf_name", ""),
        "features": [],
        "first ocr": [],
    }

    # Get all page numbers from features to determine which OCR data to include
    feature_page_numbers = set()

    # Strip features to only essential fields and collect page numbers
    for feature in labeled_json.get("features", []):
        stripped_feature = {
            "page_number": feature.get("page_number"),
            "label": feature.get("label", "Unknown"),
            "page_areas": feature.get("page_areas", []),
        }
        stripped_json["features"].append(stripped_feature)
        feature_page_numbers.add(feature.get("page_number"))

    # Only include OCR data for pages that are in the features batch
    # Remember: OCR pages are 1-indexed (page 1, 2, 3) while feature page_numbers are 0-indexed (0, 1, 2)
    all_first_ocr = labeled_json.get("first ocr", [])
    for ocr_entry in all_first_ocr:
        if isinstance(ocr_entry, list) and len(ocr_entry) >= 2:
            ocr_page_num = ocr_entry[0]
            # Convert OCR page number (1-indexed) to feature page number (0-indexed) for comparison
            feature_page_num = ocr_page_num - 1
            if feature_page_num in feature_page_numbers:
                stripped_json["first ocr"].append(ocr_entry)

    # Get prompts from the prompts module
    system_prompt = get_system_prompt()

    # Use compact JSON format for labeled data
    labeled_json_compact = json.dumps(stripped_json, separators=(",", ":"), ensure_ascii=False)
    logging.info(f"Prompt size - Data: {len(labeled_json_compact):,} chars (~{len(labeled_json_compact) // 4:,} tokens)")

    # Build user prompt using the prompts module (pass stripped json)
    user_prompt = build_user_prompt(stripped_json, vocab_json, client_context, program_type)

    # Extract vocabulary categories for logging
    vocab_categories = list(vocab_json.keys()) if vocab_json else []
    categories_str = ", ".join(vocab_categories)
    logging.info(f"Using {len(vocab_categories)} vocabulary categories: {categories_str}")

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    return messages


def call_azure_openai(
    messages: list[dict[str, str]],
    azure_openai_endpoint: str,
    azure_openai_api_key: str,
    deployment_name: str = "gpt-4o",
    api_version: str = "2025-01-01-preview",
    temperature: float = 0.1,
    max_tokens: int = 16000,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Call Azure OpenAI API for entity matching using the official OpenAI SDK.

    Args:
        messages (list[dict[str, str]]): List of chat messages (system, user).
        azure_openai_endpoint (str): Azure OpenAI endpoint URL.
        azure_openai_api_key (str): Azure OpenAI API key.
        deployment_name (str): Deployment name (default: gpt-4o).
        api_version (str): API version (default: 2025-01-01-preview).
        temperature (float): Temperature for generation (default: 0.1 for consistency).
        max_tokens (int): Maximum tokens in response (default: 16000).
        max_retries (int): Maximum number of retries for rate limit errors (default: 3).

    Returns:
        dict[str, Any]: The response from Azure OpenAI API.

    Raises:
        Exception: If the API call fails or returns an error.
    """
    # Import at runtime to avoid Azure Functions worker initialization issues

    from openai import AzureOpenAI, RateLimitError

    logging.info(f"Calling Azure OpenAI deployment '{deployment_name}' at {azure_openai_endpoint}")
    logging.info(f"Message count: {len(messages)}, Temperature: {temperature}, Max tokens: {max_tokens}")

    # Initialize Azure OpenAI client with explicit max_retries=0 since we handle retries manually
    client = AzureOpenAI(
        azure_endpoint=azure_openai_endpoint,
        api_key=azure_openai_api_key,
        api_version=api_version,
        max_retries=0,
    )

    # TEMPORARY: Write request to file for debugging (local development only)
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    # log_dir = Path("openai_logs")
    # log_dir.mkdir(exist_ok=True)
    # request_file = log_dir / f"entity_matching_request_{timestamp}.json"

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
            # Note: We DON'T use response_format={"type": "json_object"} because that forces
            # OpenAI to return a dict/object, not an array. We need an array for multi-page batches.
            response = client.chat.completions.create(
                model=deployment_name,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Convert the response to a dictionary format similar to the REST API
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

            logging.info("Azure OpenAI call successful")
            if response.usage:
                logging.info(
                    f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                    f"Completion: {response.usage.completion_tokens}, "
                    f"Total: {response.usage.total_tokens}"
                )

            # TEMPORARY: Write response to file for debugging (local development only)
            # response_file = log_dir / f"entity_matching_response_{timestamp}.json"
            # with open(response_file, "w", encoding="utf-8") as f:
            #     json.dump(response_data, f, indent=2, ensure_ascii=False)
            # logging.info(f"Response written to: {response_file}")

            return response_data

        except RateLimitError as e:
            if attempt < max_retries - 1:
                # Exponential backoff with longer waits for S0 tier: 60s, 90s, 120s
                # S0 tier has low tokens-per-minute limits, so we need substantial delays
                wait_time = 60 + (attempt * 30)  # 60s, 90s, 120s
                logging.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
            else:
                error_message = f"Azure OpenAI API rate limit exceeded after {max_retries} attempts: {e}"
                logging.error(error_message)
                raise Exception(error_message) from e

        except Exception as e:
            error_message = f"Azure OpenAI API call failed: {e}"
            logging.error(error_message)
            # OpenAI SDK exceptions may have additional details
            if hasattr(e, "__dict__"):
                logging.error(f"Exception details: {e.__dict__}")
            raise Exception(error_message) from e

    # Should never reach here due to the raise in the loop
    raise Exception("Unexpected error in call_azure_openai")


def parse_openai_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the Azure OpenAI response and extract matched entities.

    Args:
        response (dict[str, Any]): The raw response from Azure OpenAI.

    Returns:
        list[dict[str, Any]]: The parsed matched entities as a list of page dictionaries.

    Raises:
        Exception: If response parsing fails or required fields are missing.
    """
    content = ""  # Initialize to avoid unbound variable error
    try:
        if "choices" not in response or len(response["choices"]) == 0:
            raise Exception("No choices in OpenAI response")

        choice = response["choices"][0]
        if "message" not in choice or "content" not in choice["message"]:
            raise Exception("No message content in OpenAI response")

        content = choice["message"]["content"]
        finish_reason = choice.get("finish_reason", "unknown")

        logging.info(f"OpenAI response content length: {len(content)} characters")
        logging.info(f"Finish reason: {finish_reason}")

        # Check if response was truncated due to max_tokens limit
        if finish_reason == "length":
            error_message = (
                f"OpenAI response was truncated due to max_tokens limit. "
                f"Response length: {len(content)} characters. "
                f"This page is too large and needs chunking. "
                f"Try reducing the number of OCR entries or use a smaller chunk size."
            )
            logging.error(error_message)
            raise Exception(error_message)

        # Parse the JSON content
        matched_entities = json.loads(content)

        # Log the actual structure we received for debugging
        logging.info(f"OpenAI response type: {type(matched_entities)}")
        if isinstance(matched_entities, dict):
            logging.info(f"Response is dict with keys: {list(matched_entities.keys())}")
            # Show first 500 chars of response for debugging
            logging.info(f"Response preview: {json.dumps(matched_entities, indent=2)[:500]}")
        elif isinstance(matched_entities, list):
            logging.info(f"Response is array with {len(matched_entities)} elements")
            if matched_entities and isinstance(matched_entities[0], dict):
                logging.info(f"First element keys: {list(matched_entities[0].keys())}")

        # Validate the response structure
        if not isinstance(matched_entities, (list, dict)):
            raise Exception("OpenAI response is not a list or dict")

        # If it's a dict with a key like "pages" or "results", extract that
        if isinstance(matched_entities, dict):
            if "pages" in matched_entities:
                matched_entities = matched_entities["pages"]
            elif "results" in matched_entities:
                matched_entities = matched_entities["results"]
            else:
                # Try to convert single page response to list
                matched_entities = [matched_entities]

        # Validate each page has required fields
        for idx, page in enumerate(matched_entities):
            if not isinstance(page, dict):
                raise Exception(f"Page {idx} is not a dictionary")
            if "page" not in page:
                logging.warning(f"Page {idx} missing 'page' number, setting to {idx}")
                page["page"] = idx
            if "attributes" not in page:
                logging.warning(f"Page {idx} missing 'attributes', setting to empty dict")
                page["attributes"] = {}
            # Check for index-based format
            if "boundingBoxIndices" not in page:
                logging.warning(f"Page {idx} missing 'boundingBoxIndices', setting to empty list")
                page["boundingBoxIndices"] = []
            if "page_areas" not in page:
                logging.warning(f"Page {idx} missing 'page_areas', setting to empty list")
                page["page_areas"] = []

        logging.info(f"Successfully parsed {len(matched_entities)} pages from OpenAI response")
        return matched_entities

    except json.JSONDecodeError as e:
        content_preview = content[:500] if content else "Content not available"
        error_message = f"Failed to parse OpenAI response as JSON: {e}\nContent: {content_preview}..."
        logging.error(error_message)
        raise Exception(error_message) from e
    except Exception as e:
        error_message = f"Error parsing OpenAI response: {e}"
        logging.error(error_message)
        raise Exception(error_message) from e


def convert_indices_to_bounding_boxes(matched_entities: list[dict[str, Any]], labeled_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert boundingBoxIndices to full boundingBoxes using first ocr data.

    Takes OpenAI response with integer array of indices and looks up the actual
    coordinates from the "first ocr" array in labeled_json.

    Args:
        matched_entities: List of page dicts with boundingBoxIndices (array of integers)
        labeled_json: The full labeled JSON with "first ocr" data

    Returns:
        The same matched_entities list but with boundingBoxes populated
    """
    first_ocr = labeled_json.get("first ocr", [])

    # Create a lookup dict: page_number -> ocr_data_array
    first_ocr_by_page = {}
    for ocr_entry in first_ocr:
        if isinstance(ocr_entry, list) and len(ocr_entry) >= 2:
            page_num = ocr_entry[0]
            ocr_data = ocr_entry[1]
            first_ocr_by_page[page_num] = ocr_data

    for page in matched_entities:
        page_number = page.get("page", -1)
        bbox_indices = page.get("boundingBoxIndices", [])

        # Initialize boundingBoxes if not present
        if "boundingBoxes" not in page:
            page["boundingBoxes"] = []

        # Get the first ocr data for this page
        # NOTE: first_ocr uses 1-indexed pages, our page_numbers are 0-indexed
        # So page 0 needs to look up first_ocr[1], page 1 -> first_ocr[2], etc.
        ocr_lookup_page = page_number + 1
        ocr_data = first_ocr_by_page.get(ocr_lookup_page, [])

        if not ocr_data:
            logging.warning(f"No first ocr data found for page {page_number}")
            continue

        logging.info(f"Page {page_number}: Processing {len(bbox_indices)} boundingBoxIndices")

        # Collect all entities in order from attributes to match with indices
        entities_in_order = []
        attributes = page.get("attributes", {})
        for category, values in attributes.items():
            if isinstance(values, list):
                for value in values:
                    entities_in_order.append((value, category))

        logging.info(f"Page {page_number}: {len(entities_in_order)} entities extracted")

        # Convert each index to a full bounding box
        for idx, bbox_index_obj in enumerate(bbox_indices):
            # Format: {"index": 5, "text": "Amy"}
            if not isinstance(bbox_index_obj, dict):
                logging.warning(f"Page {page_number}: Invalid index type {type(bbox_index_obj)} at position {idx}, expected dict with 'index' and 'text'")
                continue

            ocr_index = bbox_index_obj.get("index")
            ocr_text = bbox_index_obj.get("text", "")

            # Get the entity value and category for this index position
            if idx < len(entities_in_order):
                value, category = entities_in_order[idx]
            else:
                logging.warning(f"Page {page_number}: Index position {idx} out of range for entities (only {len(entities_in_order)} entities)")
                continue

            # Look up the coordinates from first ocr
            # OCR indices are 0-based (we told OpenAI to use 0-based indexing)
            if ocr_index is None or not isinstance(ocr_index, int):
                logging.warning(f"Page {page_number}: Invalid ocr_index {ocr_index} for entity '{value}' (OpenAI returned: {bbox_index_obj})")
                continue

            if not (0 <= ocr_index < len(ocr_data)):
                logging.warning(
                    f"Page {page_number}: Index {ocr_index} out of range for OCR data (only {len(ocr_data)} entries). Entity: '{value}', OpenAI matched: '{ocr_text}'"
                )
                continue

            ocr_entry = ocr_data[ocr_index]

            # New format: [index, text, x, y, x2, y2, w, h, confidence]
            # Extract text from second element (index 1)
            actual_ocr_text = ocr_entry[1] if isinstance(ocr_entry, list) and len(ocr_entry) > 1 else ""

            # Verify OpenAI's index is correct by checking if entity appears in OCR text
            from rapidfuzz import fuzz

            # Convert value to string in case it's a number (e.g., year 2000.0)
            value_str = str(value) if not isinstance(value, str) else value
            actual_ocr_text_str = str(actual_ocr_text) if not isinstance(actual_ocr_text, str) else actual_ocr_text

            similarity = fuzz.partial_ratio(value_str.lower(), actual_ocr_text_str.lower()) if value_str and actual_ocr_text_str else 0

            if similarity < 80:
                # OpenAI gave us wrong index - search for correct one
                logging.warning(
                    f"Page {page_number}: OpenAI index {ocr_index} doesn't match entity '{value_str}' (similarity: {similarity}%). Searching for correct index..."
                )

                best_match_index = None
                best_match_score = 0
                best_match_text = ""

                for search_idx, search_entry in enumerate(ocr_data):
                    if isinstance(search_entry, list) and len(search_entry) > 1:
                        # Text is at index 1 in new format
                        search_text = search_entry[1]
                        search_text_str = str(search_text) if not isinstance(search_text, str) else search_text
                        search_score = fuzz.partial_ratio(value_str.lower(), search_text_str.lower()) if value_str and search_text_str else 0

                        if search_score > best_match_score and search_score >= 85:
                            best_match_index = search_idx
                            best_match_score = search_score
                            best_match_text = search_text

                if best_match_index is not None:
                    logging.info(
                        f"Page {page_number}: Found better match for '{value_str}' at index {best_match_index} (score: {best_match_score}%): '{best_match_text}'"
                    )
                    ocr_index = best_match_index
                    ocr_entry = ocr_data[ocr_index]
                    actual_ocr_text = best_match_text
                else:
                    logging.warning(f"Page {page_number}: Could not find match for '{value_str}' in OCR data. Skipping bounding box.")
                    continue
            else:
                logging.info(
                    f"Page {page_number}: Entity '{value}' ({category}) -> Index {ocr_index}, OpenAI matched: '{ocr_text}', Actual OCR: '{actual_ocr_text}' (similarity: {similarity}%)"
                )

            # Now extract coordinates from the verified OCR entry
            # New format: [index, text, x, y, x2, y2, w, h, confidence]
            # Skip index (element 0), extract from element 1 onwards
            if isinstance(ocr_entry, list) and len(ocr_entry) >= 8:
                index_val, text, x, y, x2, y2, w, h = ocr_entry[:8]
                confidence = ocr_entry[8] if len(ocr_entry) > 8 else None

                # Create the full bounding box using the vocab value (not OCR text)
                bbox = {
                    "value": value,
                    "attributes": [
                        {
                            "value": category,
                            "vocabName": value,
                        }
                    ],
                    "coordinates": {"x": x, "y": y, "x2": x2, "y2": y2, "w": w, "h": h},
                }

                if confidence is not None:
                    bbox["attributes"][0]["score"] = confidence

                page["boundingBoxes"].append(bbox)
            else:
                logging.warning(f"Invalid OCR entry format at index {ocr_index} for page {page_number} (expected at least 8 elements)")

        logging.info(f"Page {page_number}: Converted {len(bbox_indices)} indices to {len(page['boundingBoxes'])} bounding boxes")

    return matched_entities


def validate_and_adjust_confidence(matched_entities: list[dict[str, Any]], vocab_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate bounding box values against vocab and degrade confidence if not found.

    Relies on OpenAI to do the heavy lifting of normalization and matching.
    Only degrades confidence for values not in vocab - does NOT do expensive fuzzy matching
    on every value (would be too slow with large vocab files).

    Args:
        matched_entities: List of page dicts with boundingBoxes
        vocab_json: Vocabulary dictionary

    Returns:
        Updated matched_entities with adjusted confidence scores
    """
    for page in matched_entities:
        page_number = page.get("page", -1)
        attributes = page.get("attributes", {})
        bboxes = page.get("boundingBoxes", [])

        normalized_count = 0
        degraded_count = 0

        for bbox in bboxes:
            if "attributes" not in bbox or not bbox["attributes"]:
                continue

            attr = bbox["attributes"][0]
            category = attr.get("value", "")
            value = bbox.get("value", "")

            # Get the actual vocab value (case-insensitive match)
            vocab_value = get_vocab_value(category, value, vocab_json)

            if vocab_value:
                # Value found in vocab - replace with actual vocab value to preserve formatting
                if vocab_value != value:
                    bbox["value"] = vocab_value
                    attr["vocabName"] = vocab_value
                    # Change value in 'attributes' - just don't update if not present
                    try:
                        if attributes != {}:
                            attributes[category] = [vocab_value if ent == value else ent for ent in attributes[category]]
                    except Exception:
                        logging.debug(
                            f"Page {page_number}: Attempted to normalize '{value}' → '{vocab_value}' for category '{category}' in attributes but failed."
                        )
                    normalized_count += 1
                    logging.debug(f"Page {page_number}: Normalized '{value}' → '{vocab_value}' for category '{category}'")
            else:
                # Value not in vocab - degrade confidence
                current_confidence = attr.get("score", 0.5)
                new_confidence = degrade_confidence(current_confidence)
                attr["score"] = new_confidence
                degraded_count += 1

                logging.debug(
                    f"Page {page_number}: Value '{value}' not in vocab for category '{category}'. "
                    f"Confidence degraded: {current_confidence:.2f} → {new_confidence:.2f}"
                )

        if normalized_count > 0:
            logging.info(f"Page {page_number}: Normalized {normalized_count} values to match vocab formatting")
        if degraded_count > 0:
            logging.info(f"Page {page_number}: Degraded confidence for {degraded_count} bounding boxes (values not in vocab)")

    return matched_entities


def is_bbox_within_page_area(bbox_coords: dict[str, Any], page_area_coords: dict[str, Any]) -> bool:
    """Check if a bounding box is within a page area bounding box.

    Args:
        bbox_coords (dict[str, Any]): Bounding box with x, y, x2, y2 keys
        page_area_coords (dict[str, Any]): Page area bounding box with x, y, x2, y2 keys

    Returns:
        bool: True if bbox is within page_area, False otherwise
    """
    try:
        # Use or 0 to handle None, then convert to float for safe comparison
        bbox_x = float(bbox_coords.get("x") or 0)
        bbox_y = float(bbox_coords.get("y") or 0)
        bbox_x2 = float(bbox_coords.get("x2") or 0)
        bbox_y2 = float(bbox_coords.get("y2") or 0)

        area_x = float(page_area_coords.get("x") or 0)
        area_y = float(page_area_coords.get("y") or 0)
        area_x2 = float(page_area_coords.get("x2") or 0)
        area_y2 = float(page_area_coords.get("y2") or 0)

        return bbox_x >= area_x and bbox_y >= area_y and bbox_x2 <= area_x2 and bbox_y2 <= area_y2
    except (TypeError, ValueError) as e:
        # If conversion to float fails, treat as not within area
        logging.warning(f"Invalid coordinate in bbox comparison: {e}")
        return False


def filter_bounding_boxes_by_page_areas(matched_entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter bounding boxes to only include those within defined page areas.

    If page_areas exist on a page, only bounding boxes that fall completely
    within those areas are kept. Duplicates appearing both inside and outside
    page areas are filtered to keep only the ones inside.

    Args:
        matched_entities (list[dict[str, Any]]): List of page dicts with boundingBoxes and page_areas

    Returns:
        list[dict[str, Any]]: Updated matched_entities with filtered bounding boxes
    """
    for page in matched_entities:
        page_number = page.get("page", -1)
        page_areas = page.get("page_areas", [])
        bboxes = page.get("boundingBoxes", [])

        if not page_areas or len(page_areas) == 0:
            continue

        filtered_bboxes = []
        excluded_count = 0

        for bbox in bboxes:
            bbox_coords = bbox.get("coordinates", {})
            if not bbox_coords:
                continue

            within_any_area = False
            for page_area in page_areas:
                area_bbox = page_area.get("bounding_box", {})
                if is_bbox_within_page_area(bbox_coords, area_bbox):
                    within_any_area = True
                    break

            if within_any_area:
                filtered_bboxes.append(bbox)
            else:
                excluded_count += 1
                value = bbox.get("value", "")
                logging.debug(f"Page {page_number}: Excluding bbox '{value}' - outside page areas")

        page["boundingBoxes"] = filtered_bboxes

        if excluded_count > 0:
            logging.info(f"Page {page_number}: Excluded {excluded_count} bounding boxes outside page areas (kept {len(filtered_bboxes)})")

    return matched_entities


def add_default_attributes_for_empty_pages(matched_entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add default Extras attribute to pages with no attributes.

    This ensures labeled pages (except 'Other') are not lost even when they
    have no extracted attributes. Adds 'Extras': ['No Valid Attributes Detected'].

    Args:
        matched_entities (list[dict[str, Any]]): List of page dicts with attributes

    Returns:
        list[dict[str, Any]]: Updated matched_entities with default attributes added
    """
    for page in matched_entities:
        page_number = page.get("page", -1)
        page_label = page.get("label", "")
        attributes = page.get("attributes", {})

        if not attributes or len(attributes) == 0:
            if page_label and page_label != "Other":
                page["attributes"] = {"Extras": ["No Valid Attributes Detected"]}
                logging.info(f"Page {page_number} (label: {page_label}): Added default 'Extras' attribute (no attributes extracted)")

    return matched_entities


def find_missing_bounding_boxes(
    matched_entities: list[dict[str, Any]], labeled_json: dict[str, Any], similarity_threshold: float = 70.0
) -> list[dict[str, Any]]:
    """Find and add bounding boxes for entities that OpenAI missed.

    This function fuzzy matches entities that don't have bounding boxes yet
    against the OCR data to find their coordinates.

    Args:
        matched_entities: List of page dicts with attributes and boundingBoxes
        labeled_json: Original labeled JSON with "first ocr" data
        similarity_threshold: Minimum similarity score (0-100) for fuzzy matching

    Returns:
        Updated matched_entities with additional bounding boxes
    """
    from rapidfuzz import fuzz

    first_ocr = labeled_json.get("first ocr", [])

    for page in matched_entities:
        page_number = page.get("page", -1)

        # Get all entities that already have bboxes
        existing_bbox_values = set()
        for bbox in page.get("boundingBoxes", []):
            existing_bbox_values.add(bbox.get("value", ""))

        # Find entities missing bboxes
        missing_entities = []
        for category, values in page.get("attributes", {}).items():
            if isinstance(values, list):
                for value in values:
                    # Convert value to string if it's not (e.g., year as float)
                    value_str = str(value) if not isinstance(value, str) else value
                    if value_str and value_str not in existing_bbox_values:
                        missing_entities.append((category, value_str))

        if not missing_entities:
            continue

        logging.info(f"Page {page_number}: Searching for {len(missing_entities)} missing bounding boxes")

        # Get OCR data for this page (convert 0-indexed page to 1-indexed OCR lookup)
        ocr_lookup_page = page_number + 1
        ocr_data = None

        for ocr_entry in first_ocr:
            if isinstance(ocr_entry, list) and len(ocr_entry) >= 2:
                if ocr_entry[0] == ocr_lookup_page:
                    ocr_data = ocr_entry[1]
                    break

        if not ocr_data:
            logging.warning(f"Page {page_number}: No OCR data found for fuzzy matching")
            continue

        # Search OCR for each missing entity
        found_count = 0
        unmatched_count = 0
        for category, entity_value in missing_entities:
            best_match_index = None
            best_match_score = 0
            # best_match_text = None

            # Search through all OCR entries
            for idx, ocr_entry in enumerate(ocr_data):
                if not isinstance(ocr_entry, list) or len(ocr_entry) < 8:
                    continue

                # Extract OCR text (after preprocessing, index is first element)
                ocr_text = ocr_entry[1] if len(ocr_entry) > 8 else ocr_entry[0]

                # Convert to string if not already
                ocr_text_str = str(ocr_text) if not isinstance(ocr_text, str) else ocr_text

                if not ocr_text_str:
                    continue

                # Calculate similarity
                similarity = fuzz.partial_ratio(entity_value.lower(), ocr_text_str.lower()) if entity_value and ocr_text_str else 0

                if similarity > best_match_score and similarity >= similarity_threshold:
                    best_match_score = similarity
                    best_match_index = idx
                    # best_match_text = ocr_text

            # Create bbox - either with matched OCR or as low-confidence placeholder
            if best_match_index is not None:
                ocr_entry = ocr_data[best_match_index]

                # Handle both preprocessed ([index, text, x, y...]) and original ([text, x, y...]) formats
                if len(ocr_entry) > 8:
                    # Preprocessed format with index as first element
                    _, text, x, y, x2, y2, w, h = ocr_entry[:8]
                    confidence = ocr_entry[8] if len(ocr_entry) > 8 else None
                elif len(ocr_entry) >= 8:
                    # Original format without index
                    text, x, y, x2, y2, w, h = ocr_entry[:7]
                    confidence = ocr_entry[7] if len(ocr_entry) > 7 else None
                else:
                    continue

                # Skip if any coordinates are None
                if None in [x, y, x2, y2, w, h]:
                    logging.warning(f"Page {page_number}: OCR entry at index {best_match_index} has None coordinates - skipping")
                    continue

                # Create bounding box
                bbox = {
                    "value": entity_value,  # Use vocab value
                    "attributes": [
                        {
                            "value": category,
                            "vocabName": entity_value,  # Use vocab value
                            "score": confidence if confidence is not None else 0,
                        }
                    ],
                    "coordinates": {"x": x, "y": y, "x2": x2, "y2": y2, "w": w, "h": h},
                }

                page.setdefault("boundingBoxes", []).append(bbox)
                found_count += 1

                logging.debug(f"Page {page_number}: Found bbox for '{entity_value}' at OCR index {best_match_index} (score: {best_match_score:.1f}%)")
            else:
                # No match found - create placeholder bbox with low confidence
                bbox = {
                    "value": entity_value,
                    "attributes": [
                        {
                            "value": category,
                            "vocabName": entity_value,
                            "score": 0.45,  # Low confidence for unmatched
                        }
                    ],
                    "coordinates": {"x": 9999, "y": 9999, "x2": 9999, "y2": 9999, "w": 0, "h": 0},  # Placeholder coordinates
                }

                page.setdefault("boundingBoxes", []).append(bbox)
                unmatched_count += 1

                logging.debug(f"Page {page_number}: No OCR match for '{entity_value}' - added as low confidence placeholder")

        if found_count > 0:
            logging.info(f"Page {page_number}: Added {found_count} bounding boxes via fuzzy matching (total now: {len(page.get('boundingBoxes', []))})")
        if unmatched_count > 0:
            logging.info(
                f"Page {page_number}: Added {unmatched_count} unmatched entities as low confidence placeholders (total now: {len(page.get('boundingBoxes', []))})"
            )

    return matched_entities


def process_with_azure_openai(
    labeled_json: dict[str, Any],
    vocab_json: dict[str, Any],
    blob_service_client: BlobServiceClient,
    client_path: str,
    temp_file_path: str,
    program_type: str,
    batch_size: int = 3,
) -> list[dict[str, Any]]:
    """Main function to process entity matching using Azure OpenAI with batching.

    Processes pages in batches to stay within S0 tier rate limits.
    Each batch is processed separately with delays between batches.

    Args:
        labeled_json (dict[str, Any]): The labeled JSON from OCR + user corrections.
        vocab_json (dict[str, Any]): The vocabulary JSON for entity matching.
        blob_service_client (BlobServiceClient): Azure BlobServiceClient instance.
        client_path (str): Path to the client's container.
        temp_file_path (str): Temporary file path for downloads.
        program_type (str): Type of program (dance or symphony).
        batch_size (int): Number of pages to process per batch (default: 4 for S0 tier).

    Returns:
        list[dict[str, Any]]: The matched entities with attributes and bounding boxes.

    Raises:
        Exception: If processing fails at any stage.
    """

    logging.info("Starting Azure OpenAI entity matching process with batching")

    # Get Azure OpenAI credentials from environment
    azure_openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if not azure_openai_endpoint or not azure_openai_api_key:
        raise Exception("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in environment variables")

    # Download prompt template and client context
    logging.info("Downloading prompt template and client context")
    prompt_template = download_prompt_template(blob_service_client, client_path, temp_file_path)
    client_context = download_client_context(blob_service_client, client_path, temp_file_path)

    # Preprocess ALL first_ocr data ONCE at the start - add index to each OCR entry
    # This creates the canonical indexed OCR that will be used for all lookups and validation
    logging.info("Preprocessing OCR data: adding indexes to all OCR entries")
    indexed_first_ocr = []
    for ocr_page in labeled_json.get("first ocr", []):
        if isinstance(ocr_page, list) and len(ocr_page) >= 2:
            page_num = ocr_page[0]
            ocr_entries = ocr_page[1]
            indexed_entries = []
            for idx, entry in enumerate(ocr_entries):
                if isinstance(entry, list):
                    indexed_entry = [idx] + entry
                    indexed_entries.append(indexed_entry)
            indexed_first_ocr.append([page_num, indexed_entries])

    logging.info(f"Indexed {len(indexed_first_ocr)} pages of OCR data")

    # Create a full labeled_json with indexed OCR for validation
    # This will be used for ALL validation calls (find_missing_bounding_boxes, convert_indices_to_bounding_boxes)
    full_indexed_labeled_json = labeled_json.copy()
    full_indexed_labeled_json["first ocr"] = indexed_first_ocr

    # Extract pages from labeled_json, filtering out "Other" pages
    all_features = labeled_json.get("features", [])
    all_final_ocr = labeled_json.get("final ocr", [])

    # Filter features and corresponding OCR data, keeping only non-"Other" pages
    features = []
    final_ocr = []
    first_ocr = []
    skipped_count = 0

    for idx, feature in enumerate(all_features):
        effective_label = feature.get("label", "Other")
        page_areas = feature.get("page_areas", [])

        if page_areas and isinstance(page_areas, list) and len(page_areas) > 0:
            if "label" in page_areas[0]:
                effective_label = page_areas[0]["label"]

        if effective_label != "Other":
            features.append(feature)
            if idx < len(all_final_ocr):
                final_ocr.append(all_final_ocr[idx])
            if idx < len(indexed_first_ocr):
                first_ocr.append(indexed_first_ocr[idx])
        else:
            skipped_count += 1

    if skipped_count > 0:
        logging.info(f"Skipped {skipped_count} pages labeled as 'Other' (no vocab matching needed)")

    total_pages = len(features)

    if total_pages == 0:
        logging.warning("No pages found for vocab matching (all pages are 'Other' or no pages exist)")
        return []

    logging.info(f"Processing {total_pages} pages in batches of {batch_size}")

    all_matched_entities = []
    total_batches = (total_pages + batch_size - 1) // batch_size

    # Process pages in batches
    for batch_start in range(0, total_pages, batch_size):
        batch_end = min(batch_start + batch_size, total_pages)
        batch_num = (batch_start // batch_size) + 1

        logging.info(f"Processing batch {batch_num}/{total_batches}: pages {batch_start} to {batch_end - 1}")

        # FIRST: Check if any page in this batch is too large (>120 OCR entries)
        # Do this BEFORE building the batch to avoid wasting resources
        has_large_pages = False
        for page_idx in range(batch_start, batch_end):
            single_page_first_ocr_raw = first_ocr[page_idx] if page_idx < len(first_ocr) else None
            if single_page_first_ocr_raw and isinstance(single_page_first_ocr_raw, list) and len(single_page_first_ocr_raw) >= 2:
                ocr_entry_count = len(single_page_first_ocr_raw[1])
                if ocr_entry_count > 120:
                    has_large_pages = True
                    page_num = single_page_first_ocr_raw[0] if len(single_page_first_ocr_raw) > 0 else page_idx
                    logging.warning(
                        f"Batch {batch_num} contains large page {page_idx} (PDF page {page_num}) with {ocr_entry_count} OCR entries - will use chunking"
                    )
                    break

        # If batch contains large pages, process pages individually with chunking
        # This applies even to single-page batches (batch_end - batch_start == 1)
        if has_large_pages:
            logging.warning(f"Batch {batch_num} contains large pages. Splitting into individual pages for chunking...")

            # Process each page in this batch individually
            for page_idx in range(batch_start, batch_end):
                single_page_num = page_idx - batch_start + 1
                logging.info(f"Processing page {page_idx} individually (sub-batch {single_page_num}/{batch_end - batch_start})")

                # Check if this is a large page that needs chunking
                single_page_first_ocr_raw = first_ocr[page_idx] if page_idx < len(first_ocr) else None

                if single_page_first_ocr_raw and isinstance(single_page_first_ocr_raw, list) and len(single_page_first_ocr_raw) >= 2:
                    ocr_entry_count = len(single_page_first_ocr_raw[1])

                    if ocr_entry_count > 120:
                        logging.warning(f"Page {page_idx} has {ocr_entry_count} OCR entries - processing with chunking")

                        # Process with chunking - pass full_indexed_labeled_json for validation
                        page_entities = process_large_page_with_chunking(
                            feature=features[page_idx],
                            first_ocr_page=single_page_first_ocr_raw,
                            labeled_json=full_indexed_labeled_json,
                            vocab_json=vocab_json,
                            client_context=client_context,
                            prompt_template=prompt_template,
                            program_type=program_type,
                            azure_openai_endpoint=azure_openai_endpoint,
                            azure_openai_api_key=azure_openai_api_key,
                            chunk_size=80,
                        )

                        all_matched_entities.extend(page_entities)

                        continue

                # Normal single-page processing
                single_page_first_ocr = [single_page_first_ocr_raw] if single_page_first_ocr_raw else []

                single_page_labeled_json = {
                    "pdf_name": labeled_json.get("pdf_name", ""),
                    "features": [features[page_idx]],
                    "first ocr": single_page_first_ocr,
                }

                for key in labeled_json:
                    if key not in ["features", "final ocr", "first ocr"] and not isinstance(labeled_json[key], list):
                        single_page_labeled_json[key] = labeled_json[key]

                # Build prompt for single page
                single_messages = build_openai_prompt(single_page_labeled_json, vocab_json, client_context, prompt_template, program_type)
                single_prompt_length = sum(len(msg.get("content", "")) for msg in single_messages)
                logging.info(f"Page {page_idx} prompt size: ~{single_prompt_length:,} characters (~{single_prompt_length // 4:,} tokens)")

                try:
                    # Call OpenAI for single page
                    single_response = call_azure_openai(
                        messages=single_messages,
                        azure_openai_endpoint=azure_openai_endpoint,
                        azure_openai_api_key=azure_openai_api_key,
                        deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                    )

                    try:
                        single_matched_entities = parse_openai_response(single_response)
                        logging.info(f"Page {page_idx}: Parsed {len(single_matched_entities)} entities from OpenAI response")
                    except Exception as e:
                        logging.error(f"Page {page_idx}: Error in parse_openai_response: {type(e).__name__}: {e}")
                        raise

                    try:
                        single_matched_entities = filter_invalid_categories(single_matched_entities, vocab_json)
                        logging.info(f"Page {page_idx}: Filtered to {len(single_matched_entities)} entities")
                    except Exception as e:
                        logging.error(f"Page {page_idx}: Error in filter_invalid_categories: {type(e).__name__}: {e}")
                        raise

                    try:
                        single_matched_entities = convert_indices_to_bounding_boxes(single_matched_entities, full_indexed_labeled_json)
                        logging.info(f"Page {page_idx}: Converted indices to bounding boxes")
                    except Exception as e:
                        logging.error(f"Page {page_idx}: Error in convert_indices_to_bounding_boxes: {type(e).__name__}: {e}")
                        raise

                    try:
                        single_matched_entities = find_missing_bounding_boxes(single_matched_entities, full_indexed_labeled_json, similarity_threshold=85.0)
                        logging.info(f"Page {page_idx}: Found missing bounding boxes")
                    except Exception as e:
                        logging.error(f"Page {page_idx}: Error in find_missing_bounding_boxes: {type(e).__name__}: {e}")
                        raise

                    try:
                        single_matched_entities = validate_and_adjust_confidence(single_matched_entities, vocab_json)
                        logging.info(f"Page {page_idx}: Validated and adjusted confidence")
                    except Exception as e:
                        logging.error(f"Page {page_idx}: Error in validate_and_adjust_confidence: {type(e).__name__}: {e}")
                        raise

                    try:
                        single_matched_entities = filter_bounding_boxes_by_page_areas(single_matched_entities)
                        logging.info(f"Page {page_idx}: Filtered bounding boxes by page areas")
                    except Exception as e:
                        logging.error(f"Page {page_idx}: Error in filter_bounding_boxes_by_page_areas: {type(e).__name__}: {e}")
                        raise

                    all_matched_entities.extend(single_matched_entities)

                except Exception as e:
                    error_msg = str(e)
                    # If response truncated, this page needs chunking
                    if "truncated" in error_msg.lower() or "max_tokens" in error_msg.lower():
                        logging.warning(f"Page {page_idx} response truncated, switching to chunking approach")

                        # Make sure we have valid OCR data
                        if not single_page_first_ocr_raw:
                            logging.error(f"Page {page_idx} truncated but no OCR data available for chunking")
                            raise

                        # Reprocess this page with chunking
                        page_entities = process_large_page_with_chunking(
                            feature=features[page_idx],
                            first_ocr_page=single_page_first_ocr_raw,
                            labeled_json=full_indexed_labeled_json,
                            vocab_json=vocab_json,
                            client_context=client_context,
                            prompt_template=prompt_template,
                            program_type=program_type,
                            azure_openai_endpoint=azure_openai_endpoint,
                            azure_openai_api_key=azure_openai_api_key,
                            chunk_size=120,
                        )

                        all_matched_entities.extend(page_entities)
                    else:
                        # Other error, re-raise
                        raise

            logging.info(f"Batch {batch_num} completed via individual page processing")

        else:
            # Process batch normally - build the batch and send as single request
            logging.info(f"Processing batch {batch_num} as single request")

            # Create a subset of labeled_json for this batch using already-indexed OCR
            batch_first_ocr = first_ocr[batch_start:batch_end] if first_ocr else []

            batch_labeled_json = {
                "pdf_name": labeled_json.get("pdf_name", ""),
                "features": features[batch_start:batch_end],
                "first ocr": batch_first_ocr,
            }

            for key in labeled_json:
                if key not in ["features", "final ocr", "first ocr"] and not isinstance(labeled_json[key], list):
                    batch_labeled_json[key] = labeled_json[key]

            # Build the OpenAI prompt for this batch
            logging.info(f"Building OpenAI prompt for batch {batch_num}")
            messages = build_openai_prompt(batch_labeled_json, vocab_json, client_context, prompt_template, program_type)

            # Log the approximate prompt size for this batch
            prompt_length = sum(len(msg.get("content", "")) for msg in messages)
            estimated_tokens = prompt_length // 4
            logging.info(f"Batch {batch_num} prompt size: ~{prompt_length:,} characters (~{estimated_tokens:,} tokens)")

            try:
                response = call_azure_openai(
                    messages=messages,
                    azure_openai_endpoint=azure_openai_endpoint,
                    azure_openai_api_key=azure_openai_api_key,
                    deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
                )

                # Parse the response for this batch
                logging.info(f"Parsing OpenAI response for batch {batch_num}")
                batch_matched_entities = parse_openai_response(response)

                # Filter out invalid categories as safety measure
                logging.info(f"Validating categories for batch {batch_num}")
                batch_matched_entities = filter_invalid_categories(batch_matched_entities, vocab_json)

                # Convert boundingBoxIndices to full boundingBoxes using full indexed OCR data
                logging.info(f"Converting bounding box indices to coordinates for batch {batch_num}")
                batch_matched_entities = convert_indices_to_bounding_boxes(batch_matched_entities, full_indexed_labeled_json)

                # Find missing bounding boxes via fuzzy matching against full OCR data
                logging.info(f"Searching for missing bounding boxes in batch {batch_num}")
                batch_matched_entities = find_missing_bounding_boxes(batch_matched_entities, full_indexed_labeled_json, similarity_threshold=85.0)

                # Validate values against vocab and adjust confidence
                batch_matched_entities = validate_and_adjust_confidence(batch_matched_entities, vocab_json)

                # Filter bounding boxes to only keep those within page areas
                logging.info(f"Filtering bounding boxes by page areas for batch {batch_num}")
                batch_matched_entities = filter_bounding_boxes_by_page_areas(batch_matched_entities)

                # Add batch results to overall results
                all_matched_entities.extend(batch_matched_entities)

            except Exception as e:
                error_message = f"Batch {batch_num} failed: {e}"
                logging.error(error_message)
                raise Exception(error_message) from e

        # Add delay between batches to avoid rate limits (except for last batch)
        if batch_end < total_pages:
            delay = 3
            logging.info(f"Batch {batch_num} complete. Waiting {delay}s before next batch to avoid rate limits...")
            time.sleep(delay)

    # Add default attributes to pages with no extracted attributes
    logging.info("Adding default attributes to pages with no extracted attributes")
    all_matched_entities = add_default_attributes_for_empty_pages(all_matched_entities)

    logging.info(f"Successfully processed all {total_pages} pages in {total_batches} batches")
    return all_matched_entities

"""Package to use Vocab to tag and match entities."""

import copy
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from typing import Any

import azure.functions as func
from azure.data.tables import TableClient, TableServiceClient
from azure.storage.blob import BlobServiceClient

from classes.src.azure_openai_helper import process_with_azure_openai
from classes.src.cd_azure import (
    download_parsed_vocab,
    download_vocab,
    get_blob_service_client,
    get_client_program_type,
    get_table_service_client,
    update_entity_status,
    upload_to_blob,
)
from classes.src.constants import LOCAL_DEBUG, read_attribute_config_json


def fill_in_vocab(vocab: dict, parsed_vocab: dict | None, program_type: str):
    """Fill in missing keys in the vocabulary dictionary.

    Args:
        vocab (dict): The vocabulary dictionary.
        parsed_vocab (dict): The parsed vocabulary dictionary containing grouped attributes.
        program_type (str): The type of program (dance or symphony).

    Returns:
        dict: The updated vocabulary dictionary with missing keys filled in.
    """
    if program_type not in ["dance", "symphony"]:
        logging.warning(f"Invalid program_type provided of {program_type}.")
        program_type = "dance"

    expected_vocab_keys = read_attribute_config_json(program_type, parsed_vocab=parsed_vocab).get(program_type, {}).get("page_attributes", [])

    for i in expected_vocab_keys:
        if i not in vocab.keys():
            vocab[i] = []
    return vocab


def check_page_and_program(ent1: dict, ent2: dict, force_merge: bool = False):
    """Check if two entities belong to the same page and program.

    Args:
        ent1 (dict): The first entity.
        ent2 (dict): The second entity.
        force_merge (bool): Whether to force merge regardless of other conditions.

    Returns:
        bool: True if both entities belong to the same page and program or are explicitly told to be merged with compatible labels, False otherwise.
    """
    if force_merge:
        # When force merging due to page continuation, ensure labels are compatible
        ent1_label = ent1.get("page_area", {}).get("label", ent1.get("label", "")).lower()
        ent2_label = ent2.get("page_area", {}).get("label", ent2.get("label", "")).lower()
        return ent1_label == ent2_label

    # otherwise check both page number AND performance title must match
    page = ent1["page"] == ent2["page"]
    prog = ent1["attributes"]["Performance Title"][0] == ent2["attributes"]["Performance Title"][0]
    return page and prog


def is_valid_page_attribute(target_key: str, target_value: str, bounding_box: list):
    """
    Determines if a given bounding box contains the specified target value and is valid for the target key.

    Args:
        target_key (str): The attribute category (e.g., "Lighting Designer", "Composer").
        target_value (str): The entity value to validate (e.g., "Mock Lighting Designer").
        bounding_box (list): A bounding box structure with format:
            [entity_name, [[x, y, x2, y2, [attributes], entity_name, confidence],]

    Returns:
        bool: True if the bounding box contains the target value, False otherwise.

    """
    try:
        # Basic structure validation
        if not isinstance(bounding_box, (list, tuple)) or len(bounding_box) < 2:
            return False
        has_target_key = False
        # Check if target_value matches the entity name at bounding_box[0]
        has_target_value = bounding_box[0] == target_value
        for match_box in bounding_box[1]:
            # Check if target_key is in the categories list at index 4
            if len(match_box) > 4 and isinstance(match_box[4], list):
                has_target_key = has_target_key or (target_key in match_box[4])
        # Additional validation: check if target_value also appears in the coordinate tuple's entity_name
        # bounding_box[1] is a tuple of coordinate tuples
        # bounding_box[1][0] is the first coordinate tuple: (x, y, x2, y2, [attributes], entity_name, confidence)
        if (
            len(bounding_box) >= 2
            and isinstance(bounding_box[1], (list, tuple))
            and len(bounding_box[1]) > 0
            and isinstance(bounding_box[1][0], (list, tuple))
            and len(bounding_box[1][0]) >= 6
        ):  # Need at least 6 elements to access index 5
            coordinate_entity_name = bounding_box[1][0][5]  # entity_name is at index 5
            has_consistent_entity_name = coordinate_entity_name == target_value
            return has_target_key and has_target_value and has_consistent_entity_name

        # Fallback: just check the primary entity name match if structure is simpler
        return has_target_key and has_target_value

    except (IndexError, TypeError):
        # Handle malformed bounding box structures gracefully
        return False


def aggr_pages(asset_attributes: list, program_search_list: list) -> list:
    """
    Aggregate attributes of entities with the same page number and performance title,
    ensuring attributes like people are only included where they make sense.

    Args:
        asset_attributes (list): The list of asset attributes.
        program_search_list (list): The list of program search terms to validate attributes.

    Returns:
        list: The cleaned list of aggregated asset attributes.
    """

    if len(asset_attributes) == 1:
        return asset_attributes

    clean = {}

    merged_programs: dict = {}
    # Aggregate the pages together if they are matching performances
    for i, current_page in enumerate(asset_attributes):
        # print(f"Processing Page {i}: {current_page['page']}, Label: {current_page['label']}")
        # Initialize aggregation for the current page
        aggregated_page = copy.deepcopy(current_page)
        aggregated_attributes = aggregated_page["attributes"]
        aggregated_bounding_boxes = aggregated_page["boundingBoxes"]
        page_num = current_page["page"]
        current_page_label = current_page["label"]
        page_area: dict = current_page.get(
            "page_area", {"default": True, "page": page_num, "from_prev": False, "to_next": False, "label": current_page_label, "bounding_box": None}
        )
        from_prev_page = page_area["from_prev"]
        # print(f"page_area: {page_area}")
        label = page_area["label"]
        label_lower = label.lower()
        if label_lower != "program":
            # print("Not a program page, skipping aggregation")
            clean[f"{page_num}"] = aggregated_page
        elif label_lower == "program":
            # print("Processing program page for aggregation")
            # {current_page}")
            program_titles = current_page["attributes"].get("Performance Title", [None])
            # print(f"program_titles: {program_titles}")
            if len(program_titles) <= 0:
                program_titles = [None]
            program_title = program_titles[0]

            if from_prev_page and merged_programs and (program_title in [None, "Unknown"]):
                # Get the last program title from the merged_programs dictionary
                program_title = list(merged_programs.keys())[-1]
                # print(f"Using Previous Program Title: {program_title}")
            if program_title in [None, "Unknown"]:
                clean[f"{page_num}"] = aggregated_page
                continue
            # print(f"Program Title: {program_title}")
            # print(f"merged_programs: {merged_programs}")
            if program_title in merged_programs.keys():
                other_page = merged_programs[program_title]
            else:
                # print(f"Program title '{program_title}' is new so we will keep it as-is for now")
                # update our dictionary of programs with this program as-is since no merging is needed yet
                merged_programs[program_title] = aggregated_page
                clean[f"{page_num}-{program_title}"] = merged_programs[program_title]
                continue
            # otherwise it's already in the dictionary so we'll have to merge if they're valid
            other_page_num = other_page["page"]
            other_label = other_page["label"]
            # print(f"other_page: {other_page}")

            # force merge them if the two pages are linked AND have the same label type AND are consecutive
            other_page_area_label = other_page.get("page_area", {}).get("label", other_label).lower()
            current_page_area_label = page_area.get("label", current_page_label).lower()
            labels_compatible = other_page_area_label == current_page_area_label

            # Check if pages are consecutive for the same label type
            # Look at all pages processed so far to ensure no page of the SAME label came between them
            # Pages with different labels (like "Other" for ads) should be ignored
            pages_between_compatible = True
            if labels_compatible and from_prev_page and other_page.get("page_area", {}).get("to_next", False):
                other_page_num = other_page["page"]
                current_page_num = page_num

                # Check if there are any pages of the SAME label between the two pages
                for processed_page in asset_attributes[:i]:  # Check all pages processed before current
                    processed_page_num = processed_page["page"]
                    processed_page_area = processed_page.get("page_area", {})
                    processed_label = processed_page_area.get("label", processed_page.get("label", "")).lower()

                    # If there's a page between the two with the SAME label, don't allow merge
                    # (pages with different labels like "Other" are ignored)
                    if (
                        other_page_num < processed_page_num < current_page_num and processed_label == current_page_area_label and processed_label != "other"
                    ):  # Ignore "other" pages when checking for continuity
                        pages_between_compatible = False
                        # print(f"Found same-label page {processed_page_num} between {other_page_num} and {current_page_num}, preventing merge")
                        break

            force_merge: bool = other_page.get(("page_area"), {}).get("to_next", False) and from_prev_page and labels_compatible and pages_between_compatible
            # print(f"from_prev_page: {from_prev_page}")
            # print(f"labels_compatible: {labels_compatible}")
            # print(f"force_merge: {force_merge}")
            if force_merge:
                # print(f"Force merge {other_page['page']} with {page_num} so treat them as the same page")
                page_num = other_page["page"]
                program_title = other_page["attributes"]["Performance Title"][0]
                # print(f"program_title: {program_title}")
            if other_label.lower() == "program" and check_page_and_program(current_page, other_page, force_merge):
                # print(f"Possibly merge pages {page_num} and {other_page_num}")
                # merge all of the attributes together
                for key in aggregated_attributes:
                    if key != "Performance Title":
                        # Validate that the key makes sense for the page type
                        # must have a valid bounding box that has both the value and the key listed in it
                        for bounding_box in other_page["boundingBoxes"] + aggregated_bounding_boxes:
                            is_valid = True
                            try:
                                # all values must be valid
                                for target_value in other_page["attributes"][key]:
                                    is_valid = is_valid and (
                                        current_page.get("type", "dance") == "symphony"
                                        or is_valid_page_attribute(target_key=key, target_value=target_value, bounding_box=bounding_box)
                                    )
                            except Exception as e:
                                logging.error(f"Error validating page attribute {key} with value {other_page['attributes'][key]} on page {other_page_num}: {e}")
                                is_valid = False
                            if is_valid:
                                # if the attribute is not already in it then add it
                                for attribute_value in other_page["attributes"].get(key, []):
                                    if attribute_value not in aggregated_attributes[key]:
                                        aggregated_attributes[key].append(attribute_value)

                # print(f"aggregated_attributes: {aggregated_attributes}")
                # print(f"{page_num}-{program_title}")
                # Update the aggregated page
                aggregated_page["attributes"]["Performance Title"] = [program_title]
                aggregated_page["attributes"] = aggregated_attributes
                aggregated_page["boundingBoxes"] = aggregated_bounding_boxes
                # update our dictionary of programs
                merged_programs[program_title] = aggregated_page
                clean[f"{page_num}-{program_title}"] = merged_programs[program_title]
            else:
                # Pages cannot be merged, so treat current page as a separate entry
                # Use a unique key that includes page number to avoid conflicts
                clean[f"{page_num}-{program_title}"] = aggregated_page

    return [values for page, values in clean.items() if page is not None]


def reorder_labelled_json(json_body: dict) -> dict:
    """Reorder the labelled JSON data based on the bounding box coordinates.

    Args:
        json_body (dict): The labelled JSON data.

    Returns:
        dict: The reordered labelled JSON data.
    """
    # TODO(MT): Needs refactoring
    for page in json_body["features"]:
        page_num = page["page_number"]
        if page["label"] in (["Program", "Company", "Title"]):
            final_ocr_sorted = sorted(
                json_body["final ocr"][page_num][1], key=lambda x: x[2] if len(x) > 2 else 9999
            )  # Sort Text by Top Left Y-axis (Ascending, Top = 0)
            final_ocr_sorted_text = [
                re.sub("[^A-Za-z0-9]+", "", i[0]) for i in final_ocr_sorted
            ]  # Extract Sorted Text - remove everything other than Alphanumerics
            for feature_box in json_body["features"][page_num]["details"]:
                feature_text = re.sub("[^A-Za-z0-9]+", "", feature_box[0])  # Extract Feature Text - remove everything other than Alphanumerics
                try:  # Fails if Feature Text is not in Sorted Text
                    feature_details_content_index = final_ocr_sorted_text.index(
                        feature_text
                    )  # Look for Index of Feature Text in Sorted Text (get Order Number)
                    feature_box.append(feature_details_content_index)  # Append Order Number to Feature Box
                except Exception:
                    logging.warning(f"Feature text '{feature_text}' not found in sorted text.")
            features_sorted = sorted(json_body["features"][page_num]["details"], key=lambda x: x[2] if len(x) > 2 else 9999)  # Sort Features by Order Number
            features_sorted = [box[:2] for box in features_sorted]  # Remove Order Number from Feature List
            json_body["features"][page_num]["details"] = features_sorted
            json_body["final ocr"][page_num][1] = final_ocr_sorted  # Replace Final OCR with sorted Final OCR

    return json_body


def process_vocab_matching_with_openai(
    program_type: str,
    json_body: dict[str, Any],
    vocab: dict[str, Any],
    parsed_vocab: dict | None,
    temp_file_path: str,
    pdf_name: str,
    blob_service_client: BlobServiceClient,
    entity_blob_container: str,
    label_blob_container: str,
    client_path: str,
) -> str:
    """Perform vocab matching using Azure OpenAI, and upload results to Azure Blob Storage.

    Args:
        program_type (str): The type of program (e.g., "dance", "symphony").
        json_body (dict[str, Any]): JSON body containing the labeled input data.
        vocab (dict[str, Any]): Vocab dictionary.
        parsed_vocab (dict[str, Any]): Parsed Vocab dictionary with tag groupings.
        temp_file_path (str): Temporary file path for intermediate files.
        pdf_name (str): Name of the PDF file.
        blob_service_client (BlobServiceClient): Azure BlobServiceClient instance.
        entity_blob_container (str): Blob container for storing entities.
        label_blob_container (str): Blob container for storing updated labelled JSON.
        client_path (str): Path to the client's container.

    Returns:
        str: JSON string of matched entities.

    Raises:
        Exception: If OpenAI processing fails.
    """
    logging.info("Processing vocab matching with Azure OpenAI")

    # Fill in missing vocab entries
    logging.info("Filling in vocab")
    complete_vocab = fill_in_vocab(vocab, parsed_vocab, program_type)

    # Re-ordering labelled page boxes
    logging.info("Re-ordering labelled page boxes")
    ordered_json_body = reorder_labelled_json(json_body)

    # Save the ordered JSON to a temporary file
    json_str = json.dumps(ordered_json_body)
    labelled_file_path = f"{temp_file_path}/{pdf_name[:-4]}_label_corrections.json"
    with open(labelled_file_path, "w") as file:
        file.write(json_str)

    labelled_blob_name = pdf_name[: pdf_name.find(".pdf")] + "_labelled.json"

    # Upload the updated labelled JSON to Blob Storage
    logging.info(f"Uploading labeled JSON to blob storage: {labelled_blob_name}")
    upload_to_blob(blob_service_client, label_blob_container, labelled_blob_name, labelled_file_path)

    # Clean up the temporary file if it exists
    if os.path.exists(labelled_file_path):
        os.remove(labelled_file_path)

    # Process with Azure OpenAI
    logging.info("Calling Azure OpenAI for entity matching")
    try:
        matched_entities = process_with_azure_openai(
            labeled_json=ordered_json_body,
            vocab_json=complete_vocab,
            blob_service_client=blob_service_client,
            client_path=client_path,
            temp_file_path=temp_file_path,
            program_type=program_type,
        )
    except Exception as e:
        import traceback

        error_message = f"Azure OpenAI processing failed: {type(e).__name__}: {e}\nTraceback:\n{traceback.format_exc()}"
        logging.error(error_message)
        raise Exception(f"Azure OpenAI processing failed: {type(e).__name__}: {e}") from e

    # Aggregate pages (same as old method)
    logging.info("Aggregating matched pages")
    attribute_configs = read_attribute_config_json(program_type=program_type, parsed_vocab=parsed_vocab).get(program_type, {})
    program_search_list: list = attribute_configs.get("program", [])
    clean_matched = aggr_pages(asset_attributes=matched_entities, program_search_list=program_search_list)

    json_matched = json.dumps(clean_matched)

    # Save entities to a temporary file
    entities_file_path = f"{temp_file_path}/{pdf_name[:-4]}_entities.json"
    with open(entities_file_path, "w") as file:
        file.write(json_matched)

    # Upload the entities file to Blob Storage
    entities_blob_name = f"{pdf_name[:-4]}_entities.json"
    logging.info(f"Uploading entities JSON to blob storage: {entities_blob_name}")
    upload_to_blob(blob_service_client, entity_blob_container, entities_blob_name, entities_file_path)

    # Clean up the temporary file
    if os.path.exists(entities_file_path):
        os.remove(entities_file_path)

    logging.info("Azure OpenAI vocab matching completed successfully")
    return json_matched


def process_vocab_matching_request(json_body: Any) -> func.HttpResponse:
    """Azure Function entry point for vocab matching.

    Args:
        json_body (Any): JSON body containing the input data.

    Returns:
        func.HttpResponse: HTTP response object.
    """
    if LOCAL_DEBUG:
        with open("./test_results/request.json", "w") as file:
            json.dump(json_body, file, indent=4)
    logging.info("Processing vocab matching request")
    temp_file_path = tempfile.gettempdir().replace("\\", "/")
    pdf_name = json_body.get("pdf_name", None)
    if not pdf_name:
        logging.error("PDF name not provided in the request body.")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": "PDF name not provided."}),
            status_code=400,
            mimetype="application/json",
        )

    client_path = json_body.get("clientId", None)
    if not client_path:
        logging.error("Client ID not provided in the request body.")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": "Client ID not provided."}),
            status_code=400,
            mimetype="application/json",
        )
    label_blob_container = f"data/{client_path}/labelled"
    entity_blob_container = f"data/{client_path}/entities"

    # Initialize clients
    connection_string = os.environ.get("STORAGE_CONNECTION_STRING", None)
    if not connection_string:
        logging.error("Storage connection string not found in environment variables.")
        return func.HttpResponse(
            json.dumps({"status": "error", "message": "Storage connection string not found."}),
            status_code=500,
            mimetype="application/json",
        )
    blob_service_client: BlobServiceClient = get_blob_service_client(connection_string=connection_string)
    table_service_client: TableServiceClient = get_table_service_client(connection_string=connection_string)
    table_client: TableClient = table_service_client.create_table_if_not_exists(table_name="Programs")
    try:
        # get the client's program type to the json body
        program_type = get_client_program_type(table_service_client, client_id=client_path)
        # temp override
        if json_body.get("program_type_override", None):
            program_type = json_body["program_type_override"]

        # Download vocab
        vocab = download_vocab(blob_service_client, client_path, temp_file_path)
        parsed_vocab = download_parsed_vocab(blob_service_client, client_path, temp_file_path)

        # Update entity status to "In Progress"
        start_time = datetime.now()
        update_entity_status(table_client, pdf_name, "Entity Tagging In Progress", start_time=start_time, end_time=None, error_message="")

        # Use Azure OpenAI for vocab matching
        logging.info("Using Azure OpenAI method for vocab matching with batched processing")
        # Process vocab matching using Azure OpenAI (batched for rate limit management)
        json_matched = process_vocab_matching_with_openai(
            program_type=program_type,
            json_body=json_body,
            vocab=vocab,
            parsed_vocab=parsed_vocab,
            temp_file_path=temp_file_path,
            pdf_name=pdf_name,
            blob_service_client=blob_service_client,
            entity_blob_container=entity_blob_container,
            label_blob_container=label_blob_container,
            client_path=client_path,
        )

        # Update entity status to "Completed"
        end_time = datetime.now()
        update_entity_status(table_client, pdf_name, "Entity Tagging Completed", start_time=start_time, end_time=end_time, error_message="")

        return func.HttpResponse(json_matched, mimetype="application/json")
    except Exception as e:
        import traceback

        logging.error(f"Error: {e}")
        logging.error("Stack trace:\n" + traceback.format_exc())
        # Update entity status to "Error"
        update_entity_status(table_client, pdf_name, "Entity Tagging Error", start_time=None, end_time=None, error_message=str(e))
        return func.HttpResponse(json.dumps({"status": "error", "message": str(e)}), status_code=500, mimetype="application/json")

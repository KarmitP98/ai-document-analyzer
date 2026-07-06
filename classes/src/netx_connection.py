"""
NetX Connection helper module.

This module contains methods for connecting to NetX, listing, managing and uploading assets and folders.
"""

import json
import logging
import os
import tempfile
import traceback
from collections import OrderedDict
from datetime import datetime
from typing import Any

import azure.functions as func
import requests
from azure.data.tables import TableClient, TableServiceClient, UpdateMode
from azure.storage.blob import BlobServiceClient

from classes.src.constants import read_attribute_config_json


# Get NetX authentication key.
def get_auth_key(url, username, password):
    params = {"id": "null", "method": "authenticate", "params": [username, password], "dataContext": "json", "jsonrpc": "2.0"}
    timeout_seconds = 600
    login = requests.get(url, data=json.dumps(params), timeout=timeout_seconds)
    logging.info(f"Login response: {login}")
    logging.info(f"Raw response from NetX: {login.text}")
    logging.info(f"Json response from NetX: {login.json()}")
    authkey = login.json().get("result", {}).get("sessionKey", None)
    return authkey


def get_root_folder_list(folder_id, url, authkey):
    params = {
        "id": "null",
        "method": "getFoldersByParent",
        "params": [authkey, folder_id, {"page": {"startIndex": 0}, "data": ["folder.id", "folder.base", "folder.children"]}],
        "dataContext": "json",
        "jsonrpc": "2.0",
    }
    timeout_seconds = 600
    root_folders = requests.get(url, data=json.dumps(params), timeout=timeout_seconds).json()["result"]["results"]
    return root_folders


def get_number_of_assets(url, authkey, folder_id_containing_assets):
    params = {
        "id": "null",
        "method": "getFoldersByParent",
        "params": [authkey, folder_id_containing_assets, {"data": ["folder.id", "folder.base", "folder.children"]}],
        "dataContext": "json",
        "jsonrpc": "2.0",
    }
    timeout_seconds = 600
    folders_with_assets = requests.get(url, data=json.dumps(params), timeout=timeout_seconds).json()["result"]["results"]
    total_num_assets = sum([asset["children"]["assetCount"] for asset in folders_with_assets])
    return total_num_assets


def get_asset_ids(url, authkey, folder_id_containing_assets, number_of_assets):
    params = {
        "id": "null",
        "method": "getAssetsByFolder",
        "params": [authkey, folder_id_containing_assets, "true", {"page": {"startIndex": 0, "size": number_of_assets}, "data": ["asset.id", "asset.base"]}],
        "dataContext": "json",
        "jsonrpc": "2.0",
    }
    timeout_seconds = 600
    assets_in_folder = requests.get(url, data=json.dumps(params), timeout=timeout_seconds).json()["result"]["results"]
    id_list = [ids["id"] for ids in assets_in_folder]
    return id_list


def extract_asset_attributes(url, authkey, asset_id_list):
    params = {
        "dataContext": "json",
        "jsonrpc": "2.0",
        "id": "null",
        "method": "getAssets",
        "params": [authkey, asset_id_list, {"data": ["asset.base", "asset.attributes"]}],
    }
    timeout_seconds = 600
    req_results = requests.get(url, data=json.dumps(params), timeout=timeout_seconds).json()["result"]
    return req_results


def netx_api_get_assets(url, username, password, folder_id_containing_assets):
    authkey = get_auth_key(url=url, username=username, password=password)
    number_of_assets = get_number_of_assets(url=url, authkey=authkey, folder_id_containing_assets=folder_id_containing_assets)
    asset_id_list = get_asset_ids(url=url, authkey=authkey, folder_id_containing_assets=folder_id_containing_assets, number_of_assets=number_of_assets)
    asset_attributes = extract_asset_attributes(url=url, authkey=authkey, asset_id_list=asset_id_list)
    return asset_attributes


def clean_up_attributes(attributes, asset_type, remove_donor):
    """Clean up attributes dictionary so it integrates with NetX fields."""
    if remove_donor:
        keys_to_remove = ["Extras", "Donors"]
    else:
        keys_to_remove = ["Extras"]

    for key_remove in keys_to_remove:
        attributes.pop(key_remove, None)
    # Set Asset Type based on ENTIRE PDF or just PROGRAM PDF
    attributes["Asset Type"] = [asset_type]
    return attributes


def combine_attributes(asset_attributes: dict | list, client_prefix: str, performance_type: str = "dance", parsed_vocab: dict | None = None):
    """Combine and aggregate asset attributes across multiple pages, optionally prepending a client prefix to each attribute key.

    Args:
        asset_attributes (dict|list): A dictionary containing asset attributes for each page or a list of page asset dictionaries
        client_prefix (str): A string to prepend to each attribute key.
        performance_type (str): The type of performance, used to determine the attributes to send to netx.
        parsed_vocab (dict): The parsed vocabulary dictionary used to read attribute configuration.

    Returns:
        dict: A dictionary where each key is an attribute name (optionally prefixed) and each value is a list of unique, aggregated attribute values across all pages.
    """

    overall_attributes = read_attribute_config_json(performance_type, parsed_vocab)[performance_type]["page_attributes"]
    key_prefix: str = ""

    # Prepend client prefix to attributes
    if client_prefix and client_prefix != "":
        key_prefix = f"{client_prefix}-"
        overall_attributes = {f"{key_prefix}{key}": value for key, value in overall_attributes.items()}

    for page in asset_attributes:
        for attr in page["attributes"].keys():
            existing_attr_value = page["attributes"].get(attr, None)
            new_key = f"{key_prefix}{attr}"
            if existing_attr_value and new_key in overall_attributes:
                overall_attributes[new_key] += existing_attr_value

    for attr in overall_attributes.keys():
        attributes = extract_attribute_values(overall_attributes.get(attr, []))
        overall_attributes[attr] = list(OrderedDict.fromkeys(attributes))

    return overall_attributes


def create_asset_folder(url, session_key, root_folder, pdf_name):
    """NetX API to Create Folder to house asset."""
    param_create_folder = {
        "id": "null",
        "method": "createFolderFromPath",
        "params": [session_key, root_folder + "/" + pdf_name[: pdf_name.find(".pdf")], {"data": ["folder.id"]}],
        "dataContext": "json",
        "jsonrpc": "2.0",
    }

    timeout_seconds = 600
    create_folder = requests.post(url, data=json.dumps(param_create_folder), timeout=timeout_seconds)

    return create_folder


def create_folder_by_path(url, session_key, root_folder):
    """NetX API to Create Folder to house asset."""
    param_create_folder = {
        "id": "null",
        "method": "createFolderFromPath",
        "params": [session_key, root_folder, {"data": ["folder.id"]}],
        "dataContext": "json",
        "jsonrpc": "2.0",
    }
    timeout_seconds = 600
    create_folder = requests.post(url, data=json.dumps(param_create_folder), timeout=timeout_seconds)

    return create_folder


def get_folder_by_path(url, session_key, root_folder):
    """NetX API to Get Folder by path"""
    param_get_folder = {
        "id": "null",
        "method": "getFolderByPath",
        "params": [session_key, root_folder, {"data": ["folder.id"]}],
        "dataContext": "json",
        "jsonrpc": "2.0",
    }
    timeout_seconds = 600
    get_folder = requests.post(url, data=json.dumps(param_get_folder), timeout=timeout_seconds)

    return get_folder


def upload_pdf_file(upload_url, session_key, folder_id, path_to_pdf, pdf_name):
    """NetX API to Upload File."""
    param_upload_file = {"fileName": pdf_name, "sessionKey": session_key, "folderId": folder_id}
    files = {"Upload": open(path_to_pdf, "rb")}
    timeout_seconds = 600
    create_file = requests.post(upload_url, data=param_upload_file, files=files, timeout=timeout_seconds)

    return create_file


def create_asset(url, session_key, folder_id, pdf_name):
    """NetX API to Create Asset from uploaded File."""
    param_asset = {
        "id": "null",
        "method": "createAssetFromFile",
        "params": [session_key, pdf_name, folder_id, {"data": ["asset.id"]}],
        "dataContext": "json",
        "jsonrpc": "2.0",
    }
    timeout_seconds = 600
    asset = requests.post(url, data=json.dumps(param_asset), timeout=timeout_seconds)

    return asset


def set_asset_attributes(url, session_key, asset_id, attributes):
    """NetX API to set attributes for created asset."""
    asset_attributes = {
        "id": "null",
        "method": "setAssetAttributes",
        "params": [
            session_key,
            asset_id,
            attributes,
        ],
        "dataContext": "json",
        "jsonrpc": "2.0",
    }
    timeout_seconds = 600
    attach_attributes = requests.post(url, data=json.dumps(asset_attributes), timeout=timeout_seconds)

    return attach_attributes


def netx_upload_pipeline(upload_url, url, session_key, folder_id, path_to_pdf, pdf_name, attributes):
    """Pipeline NetX Uploading procedure: Upload file, create asset, attach attributes."""
    logging.info("netx_upload_pipeline")
    logging.info(f"-- upload_url: {upload_url}")
    logging.info(f"-- url: {url}")
    logging.info(f"-- session_key: {session_key}")
    logging.info(f"-- folder_id: {folder_id}")
    logging.info(f"-- path_to_pdf: {path_to_pdf}")
    logging.info(f"-- pdf_name: {pdf_name}")
    logging.info(f"-- attributes: {attributes}")

    create_file = upload_pdf_file(upload_url, session_key, folder_id, path_to_pdf, pdf_name)
    created_asset = create_asset(url, session_key, folder_id, pdf_name)
    asset_id = created_asset.json()["result"]["id"]
    attach_attributes = set_asset_attributes(url, session_key, asset_id, attributes)

    return create_file, created_asset, attach_attributes


def extract_attribute_values(attr_list: list, key: str = "value", default_value: str = "") -> list:
    """
    Extracts values from a list that may contain either strings or dicts with a given key.

    Args:
        attr_list (list): List of strings or list of dicts.
        key (str): Key to extract from dicts.
        default_value(str): Default value to return if key is not found.
    Returns:
        list: List of extracted values (strings).
    """
    result = []
    for item in attr_list:
        if isinstance(item, dict) and key in item:
            result.append(item[key])
        elif isinstance(item, str):
            result.append(item)
    if len(result) == 0:
        return [default_value]
    return result


def get_temp_file_path() -> str:
    """Get the system temporary directory path with forward slashes.

    Returns:
        str: Temporary directory path.
    """
    return tempfile.gettempdir().replace("\\", "/")


def get_entity_list(cd_table: TableClient, pdf_name: str) -> list[dict[str, Any]]:
    """Query the table for entities matching the given PDF name.

    Args:
        cd_table: Azure Table client.
        pdf_name (str): Name of the PDF.

    Returns:
        list[dict[str, Any]]: List of matching entities.
    """
    my_filter = "PartitionKey eq '{}'".format(pdf_name)
    pdf_query = cd_table.query_entities(my_filter)
    return [x for x in pdf_query]


def write_json_to_blob(blob_service_client: BlobServiceClient, container: str, blob_name: str, data: Any, temp_file_path: str) -> None:
    """Write JSON data to a temporary file and upload it to Azure Blob Storage.

    Args:
        blob_service_client (BlobServiceClient): Blob service client.
        container (str): Blob container name.
        blob_name (str): Name of the blob.
        data (Any): Data to write.
        temp_file_path (str): Path to the temp directory.
    """
    json_str = json.dumps(data)
    temp_json_path = f"{temp_file_path}/{blob_name}"
    with open(temp_json_path, "w") as file_object:
        file_object.write(json_str)
    output_blob_client = blob_service_client.get_blob_client(container=container, blob=blob_name)
    with open(temp_json_path, "rb") as file_object:
        output_blob_client.upload_blob(file_object, overwrite=True)
    os.remove(temp_json_path)
    logging.info(f"Removed temp file: {temp_json_path}")


def update_or_create_entity(
    cd_table: TableClient,
    entity_list: list[dict[str, Any]],
    pdf_name: str,
    status: str,
    error_message: str = "",
    extra_fields: dict[str, Any] | None = None,
) -> None:
    """Update or create an entity in the Azure Table in a generic way.

    Args:
        cd_table (TableClient): Azure Table client.
        entity_list (List[Dict[str, Any]]): List of entities.
        pdf_name (str): Name of the PDF.
        status (str): Status to set.
        error_message (str, optional): Error message. Defaults to "".
        extra_fields (Dict[str, Any], optional): Additional fields to update or create. Defaults to None.
    """
    entity_data = {
        "PartitionKey": pdf_name,
        "RowKey": "",
        "fileName": pdf_name,
        "status": status,
        "ErrorMessage": error_message,
    }
    if extra_fields:
        entity_data.update(extra_fields)

    if not entity_list:
        # Entity does not exist, create it
        cd_table.create_entity(entity=entity_data)
        logging.info(f"Created entity: {entity_data}")
    else:
        # Entity exists, update it
        entity = entity_list[0]
        entity.update(entity_data)
        cd_table.update_entity(mode=UpdateMode.REPLACE, entity=entity)
        logging.info(f"Updated entity: {entity}")


def authenticate_session(json_body: dict[str, Any]) -> tuple:
    """Authenticate with NetX and return the session key.

    Args:
        json_body (Dict[str, Any]): Request body.

    Returns:
        Tuple[Optional[str], bool, str]: session_key, connection_success, error_message
    """
    session_key = None
    auth_key = json_body.get("session_key", "")
    username = json_body.get("username", "")
    password = json_body.get("password", "")  # nosec B105
    url = json_body.get("url", "")
    connection_success = True
    error_message = ""
    try:
        if session_key != "" and (username == "" or password == ""):  # nosec B105
            logging.info("Authenticating Session via Session Key")
            session_key = auth_key
        else:
            logging.info("Authenticating Session via Username/Password")
            session_key = get_auth_key(url, username, password)
        if session_key is None:
            error_message = "Session key is None, authentication failed."
            connection_success = False
    except Exception as e:
        tb_str = traceback.format_exc()
        logging.error(f"Exception occurred during authentication: {e}\n{tb_str}")
        error_message = str(e)
        connection_success = False
    return session_key, connection_success, error_message


def download_pdf(blob_service_client: BlobServiceClient, container: str, pdf_name: str, temp_file_path: str) -> str:
    """Download a PDF from blob storage to a temporary file.

    Args:
        blob_service_client (BlobServiceClient): Blob service client.
        container (str): Blob container name.
        pdf_name (str): Name of the PDF.
        temp_file_path (str): Path to the temp directory.

    Returns:
        str: Path to the downloaded PDF.
    """
    input_blob_client = blob_service_client.get_blob_client(container=container, blob=pdf_name)
    path_to_pdf = f"{temp_file_path}/{pdf_name}"
    with open(path_to_pdf, "wb") as download_file:
        download_file.write(input_blob_client.download_blob().readall())
    logging.info(f"PDF Downloaded successfully to {path_to_pdf}")
    return path_to_pdf


def download_json_from_blob(blob_service_client: BlobServiceClient, container_path: str, file_name: str, temp_file_path: str) -> Any:
    """Download a json file from Azure Blob Storage.

    Args:
        blob_service_client (BlobServiceClient): Azure BlobServiceClient instance.
        container_path (str): The container that the blob is in. This can either be the name of the container, or an instance of ContainerProperties.
        file_name (str): Name of the file to download.
        temp_file_path (str): Temporary file path to store the file.

    Returns:
        Any: The json contents.
    """
    try:
        client = blob_service_client.get_blob_client(container=container_path, blob=file_name)
        file_path = f"{temp_file_path}/vocab.json"
        with open(file_path, "wb") as download_file:
            blob_data = client.download_blob().readall()
            if isinstance(blob_data, str):
                blob_data = blob_data.encode("utf-8")
            download_file.write(blob_data)
        with open(file_path, "r") as vocab_file:
            return json.load(vocab_file)
    except Exception as e:
        error_message = f"Error downloading file: {e}"
        raise Exception(error_message) from e


def update_program_status(program_id: str, program_status: str, error_message: str = "") -> None:
    """Update the status of a program in the Azure Table.

    Args:
        program_id (str): The ID of the program to update.
        program_status (str): The status to set for the program.
        error_message (str, optional): Error message to store with the status. Defaults to empty string.

    Returns:
        None
    """
    try:
        # Create table client
        table_service_client = TableServiceClient.from_connection_string(conn_str=os.environ["STORAGE_CONNECTION_STRING"])
        table_client = table_service_client.create_table_if_not_exists(table_name="Programs")

        # Query for the program entity
        entity_list = get_entity_list(table_client, program_id)

        if not entity_list:
            logging.error(f"Program with ID {program_id} not found")
            return

        # Update the entity
        entity = entity_list[0]
        entity.update({"status": program_status, "errorMessage": error_message, "updatedAt": datetime.now()})

        # Update the entity in the table
        table_client.update_entity(mode=UpdateMode.REPLACE, entity=entity)
        logging.info(f"Updated program {program_id} status to {program_status}")

    except Exception as e:
        tb_str = traceback.format_exc()
        logging.error(f"Error updating program status: {e}\n{tb_str}")
        raise


def validate_required_fields(data: dict) -> "tuple[bool, str]":
    """Validate that all required fields are present in the request data.

    Args:
        data (dict): The request data to validate

    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    required_fields = ["session_key", "client_id", "upload_url", "url", "pdf_names"]
    missing_fields = [field for field in required_fields if not data.get(field)]

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    # Validate pdf_names is a list and not empty
    if not isinstance(data["pdf_names"], list):
        return False, "pdf_names must be an array"
    if not data["pdf_names"]:
        return False, "pdf_names array cannot be empty"

    return True, ""


def process_batch_uploads(req: func.HttpRequest) -> func.HttpResponse:
    """Process multiple uploads in series.

    Args:
        req (func.HttpRequest): Azure Function HTTP request containing an array of upload requests.

    Returns:
        func.HttpResponse: Azure Function HTTP response with results of all uploads.
    """
    logging.info("Processing batch uploads to NetX")
    try:
        from azure.data.tables import TableClient, TableServiceClient

        from classes.src.cd_azure import generate_program_assets, get_entity_list

        request_data = req.get_json()
        results = []
        logging.info(f"PDF Names: {request_data['pdf_names']}")
        asset_data = generate_program_assets(request_data["client_id"], request_data["pdf_names"])
        logging.info(f"asset_data to send to netx: {asset_data}")
        table_service_client: TableServiceClient = TableServiceClient.from_connection_string(conn_str=os.environ["STORAGE_CONNECTION_STRING"])
        cd_table: TableClient = table_service_client.create_table_if_not_exists(table_name="Programs")
        for asset in asset_data:
            try:
                # Get entity_list for this asset
                entity_list = get_entity_list(cd_table, asset["pdf_name"])
                # Call netx_upload_pipeline directly with processed attributes
                create_sub_folder = request_data.get("create_sub_folder", False)
                root_folder = request_data.get("root_folder", "")
                upload_url = request_data["upload_url"]
                url = request_data["url"]
                session_key = request_data["session_key"]
                pdf_name = asset["pdf_name"]
                path_to_pdf = asset["path_to_pdf"]
                attributes = asset["attributes_json"]
                # Determine folder_id (simulate logic from netx_pipeline)
                folder_id = 1
                if create_sub_folder:
                    created_folder = create_asset_folder(url, session_key, root_folder, pdf_name)
                    folder_id = created_folder.json()["result"]["id"]
                else:
                    response = get_folder_by_path(url, session_key, root_folder).json()
                    if "error" in response:
                        created_folder = create_folder_by_path(url, session_key, root_folder)
                        folder_id = created_folder.json()["result"]["id"]
                    else:
                        folder_id = response["result"]["id"]
                # Upload PDF and attributes directly
                netx_upload_pipeline(
                    upload_url=upload_url,
                    url=url,
                    session_key=session_key,
                    folder_id=folder_id,
                    path_to_pdf=path_to_pdf,
                    pdf_name=pdf_name,
                    attributes=attributes,
                )
                update_or_create_entity(
                    cd_table,
                    entity_list,
                    pdf_name,
                    status="NetX Upload Completed",
                    error_message="",
                    extra_fields={"updatedAt": datetime.now(), "NetXEndTime": datetime.now(), "ErrorMessage": "", "readyToSubmit": False},
                )
                results.append({"pdf_name": pdf_name, "status_code": 200, "message": "Success"})
            except Exception as e:
                error_message = f"Error processing {asset['pdf_name']}: {str(e)}"
                logging.error(error_message)
                update_program_status(asset["pdf_name"], "NetX Upload Error", error_message=error_message)
                results.append({"pdf_name": asset["pdf_name"], "status_code": 500, "message": error_message})
        return func.HttpResponse(json.dumps({"status_code": 200, "message": "Batch processing completed", "results": results}), mimetype="application/json")
    except Exception as e:
        error_message = f"Error processing batch uploads: {str(e)}"
        logging.error(error_message)
        return func.HttpResponse(json.dumps({"status_code": 500, "message": error_message}), mimetype="application/json")

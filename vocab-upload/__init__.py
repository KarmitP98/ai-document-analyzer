"""Azure Function to process Vocab from CSV to JSON."""

import json
import logging
import os
import tempfile

import azure.functions as func
import pandas as pd
from azure.storage.blob import BlobServiceClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    tempFilePath = tempfile.gettempdir().replace("\\", "/")

    try:
        # Get inputs
        json_body = req.get_json()
        client_path = json_body["clientId"]
        vocab_filename = json_body["vocabFilename"]
    except Exception as e:
        return json.dumps({"status_code": 400, "error": "Invalid body", "message": str(e)})

    try:
        # Specify client containers
        vocab_blob_container = "data/" + client_path + "/vocabs"
        vocab_field = vocab_filename[: vocab_filename.find(".")].replace("_", "/")

        logging.info(f"-----Adding {vocab_field} to vocab.csv/vocab.json-----")
        blob_service_client = BlobServiceClient.from_connection_string(conn_str=os.environ["STORAGE_CONNECTION_STRING"])

        # Download vocab_field.netx.csv
        vocab_field_client = blob_service_client.get_blob_client(container=vocab_blob_container, blob=vocab_filename)  # noqa: E501
        downloaded_vocab_field_path = tempFilePath + "/" + str(client_path) + vocab_filename
        with open(downloaded_vocab_field_path, "wb") as download_file:
            download_file.write(vocab_field_client.download_blob().readall())

        # Read in and initialize vocab_field dataframe
        vocab_field_file = pd.read_csv(downloaded_vocab_field_path)
        vocab_field_file["field"] = vocab_field

        # Check if vocab.csv exists - if not create one
        vocab_csv_blob = blob_service_client.get_blob_client(container=vocab_blob_container, blob="vocab.csv")
        exists = vocab_csv_blob.exists()

        if exists:  # Download vocab.csv
            logging.info("-----Vocab file already exists-----")
            old_vocab_client = blob_service_client.get_blob_client(container=vocab_blob_container, blob="vocab.csv")  # noqa: E501
            downloaded_old_vocab_path = tempFilePath + "/" + str(client_path) + "old_vocab.csv"
            with open(downloaded_old_vocab_path, "wb") as download_file:
                download_file.write(old_vocab_client.download_blob().readall())
            vocab_file = pd.read_csv(downloaded_old_vocab_path)
            vocab_file = vocab_file.drop(vocab_file.loc[vocab_file["field"] == vocab_field].index, axis=0).reset_index(drop=True)
        else:  # vocab.csv does not exist - create template
            logging.info("-----Creating vocab file-----")
            vocab_file = pd.DataFrame({"field": [], "value": []})

        # Drop any Blank row in the Field we are adding
        final_csv = pd.concat([vocab_file, vocab_field_file], ignore_index=True)
        final_csv = final_csv.drop(final_csv.loc[final_csv["value"].isna()].index, axis=0).reset_index(drop=True)
        final_csv.drop_duplicates(inplace=True, ignore_index=True)

        # Create JSON file
        final_json = final_csv.groupby("field")["value"].apply(list).reset_index().set_index("field")["value"].to_json()

        logging.info("-----Writing vocab.json to blob-----")
        # Writing JSON to BlobStorage
        final_json_path = tempFilePath + "/" + str(client_path) + "vocab.json"
        with open(final_json_path, "w") as file_object:
            file_object.write(final_json)
        output_blob_client = blob_service_client.get_blob_client(container=vocab_blob_container, blob="vocab.json")  # noqa: E501
        with open(final_json_path, "rb") as file_object:
            output_blob_client.upload_blob(file_object, overwrite=True)

        logging.info("-----Writing vocab.csv to blob-----")
        # Writing CSV to BlobStorage
        final_csv_path = tempFilePath + "/" + str(client_path) + "vocab.csv"
        final_csv.to_csv(final_csv_path, index=False)
        output_blob_client = blob_service_client.get_blob_client(container=vocab_blob_container, blob="vocab.csv")  # noqa: E501
        with open(final_csv_path, "rb") as file_object:
            output_blob_client.upload_blob(file_object, overwrite=True)

        logging.info("-----Removing temporary files-----")
        # Clean up and remove temporary files
        os.remove(downloaded_vocab_field_path)
        logging.info(f"Removed temp file: {downloaded_vocab_field_path}")
        os.remove(final_json_path)
        logging.info(f"Removed temp file: {final_json_path}")
        os.remove(final_csv_path)
        logging.info(f"Removed temp file: {final_csv_path}")
        if exists:
            os.remove(downloaded_old_vocab_path)
            logging.info(f"Removed temp file: {downloaded_old_vocab_path}")
    except Exception as e:
        return json.dumps({"status_code": 409, "error": "Error during processing", "message": str(e)})

    return json.dumps({"status_code": 200, "error": "", "message": "Success"})

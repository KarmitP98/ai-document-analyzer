import logging
import os
from datetime import datetime, timedelta

import azure.functions as func
from azure.storage.blob import (
    AccountSasPermissions,
    BlobServiceClient,
    ResourceTypes,
    generate_account_sas,
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    log(message="Called Blob Storage Token Generation")
    log(message="Fetching BlobStorage accout name")

    blob_service_client = BlobServiceClient.from_connection_string(conn_str=os.environ["STORAGE_CONNECTION_STRING"])

    account_name = blob_service_client.account_name
    account_key = os.getenv("BlobStorageAccountKey")
    if account_key and account_name:
        log(message="Creating Blob Storage Token")
        sas_token = generate_account_sas(
            account_name=account_name,
            account_key=account_key,
            resource_types=ResourceTypes(
                object=True,
                container=True,
                service=True,
            ),
            permission=AccountSasPermissions(
                add=True, create=True, delete=True, delete_previous_version=True, list=True, process=True, read=True, update=True, write=True
            ),
            expiry=datetime.utcnow() + timedelta(hours=8),
        )

        if sas_token:
            log(message="Generated Blob SAS Token")
            return func.HttpResponse(body=sas_token, status_code=200)
        else:
            logging.error("SAS Token could not be generated!")
            return func.HttpResponse(body="SAS Token could not be generated!", status_code=500)
    else:
        logging.error("Account Name and Key not found!")
        return func.HttpResponse(body="Account Name and Key not found!", status_code=500)


def log(message: str):
    logging.info(message)

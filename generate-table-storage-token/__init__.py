import logging
import os
from datetime import datetime, timedelta

import azure.functions as func
from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import AccountSasPermissions, ResourceTypes, generate_account_sas
from azure.storage.blob import BlobServiceClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Creating Blob Storage SAS Token...")

    logging.info("Fetching Account Name and Key...")

    blob_service_client = BlobServiceClient.from_connection_string(conn_str=os.environ["STORAGE_CONNECTION_STRING"])

    account_name = blob_service_client.account_name
    account_key = os.getenv("BlobStorageAccountKey")
    # Need to pass Credential into Azure Tables' 'generate_account_sas'
    credential = AzureNamedKeyCredential(name=account_name, key=account_key)
    # if account_key and

    if account_name:
        logging.info("Creating SAS Token...")
        sas_token = generate_account_sas(
            credential=credential,
            resource_types=ResourceTypes(object=True, service=True),
            permission=AccountSasPermissions(read=True, add=True, create=True, delete=True, list=True, process=True, update=True, write=True),
            expiry=datetime.utcnow() + timedelta(hours=8),
        )

        if sas_token:
            logging.info("SAS Token Created.")
            return func.HttpResponse(body=sas_token, status_code=200)
        else:
            logging.warning("SAS Token could not be created!")
            return func.HttpResponse(
                body="SAS Token could not be created!",
                status_code=500,
            )
    else:
        logging.warning("Account and Key not found!")
        return func.HttpResponse(body="Account and Key not found!", statusCode=404)

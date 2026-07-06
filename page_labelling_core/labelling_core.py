import logging
import os
import tempfile
from datetime import datetime

from azure.data.tables import TableServiceClient, UpdateMode

from classes.chromadiverse import ChromaDiverse

cached_chroma_diverse: ChromaDiverse | None = None


def process_labelling(blob_path, chroma_diverse: ChromaDiverse | None = None):
    # lazy load the ChromaDiverse if not provided
    if not chroma_diverse:
        global cached_chroma_diverse
        if cached_chroma_diverse:
            logging.info("Using cached chroma_diverse instance")
            chroma_diverse = cached_chroma_diverse
        else:
            logging.info("Initialize chroma_diverse")
            chroma_diverse = ChromaDiverse()
            # No need to load models anymore - Azure OpenAI is used for classification
            logging.info("Using Azure OpenAI for page classification")
            cached_chroma_diverse = chroma_diverse

    tempFilePath = tempfile.gettempdir().replace("\\", "/")
    storage_connection_string = os.environ["STORAGE_CONNECTION_STRING"]
    # Extract PDF name
    pdf_name = blob_path[blob_path.find("/pdfs/") + 6 :]
    # Identify Client Folder
    client_path = blob_path[: blob_path.find("/pdfs")]
    chroma_diverse.feature_container = client_path + "/features"
    chroma_diverse.labelled_container = client_path + "/labelled"
    chroma_diverse.pdf_container = client_path + "/pdfs"

    table_service_client = TableServiceClient.from_connection_string(conn_str=storage_connection_string)
    chroma_diverseTable = table_service_client.create_table_if_not_exists(table_name="Programs")
    my_filter = "PartitionKey eq '" + pdf_name + "'"
    pdf_query = chroma_diverseTable.query_entities(my_filter)
    entity_list = [x for x in pdf_query]  # Should be of length 1

    if entity_list == []:  # Entity does not Exist - Create
        ent_list = {
            "PartitionKey": pdf_name,
            "RowKey": "",
            "fileName": pdf_name,
            "status": "Labelling In Progress",
            "updatedAt": datetime.now(),
            "LabellingStartTime": datetime.now(),
            "LabellingEndTime": "",
            "EntityTaggingStartTime": "",
            "EntityTaggingEndTime": "",
            "NetXStartTime": "",
            "NetXEndTime": "",
            "ErrorMessage": "",
        }
        chroma_diverseTable.create_entity(entity=ent_list)
        logging.info(ent_list)
        entity_list = [ent_list]
    else:  # Entity already Exists - update
        entity_list[0]["status"] = "Labelling In Progress"
        entity_list[0]["RowKey"] = ""
        entity_list[0]["updatedAt"] = datetime.now()
        entity_list[0]["LabellingStartTime"] = datetime.now()
        entity_list[0]["LabellingEndTime"] = ""
        entity_list[0]["EntityTaggingStartTime"] = ""
        entity_list[0]["EntityTaggingEndTime"] = ""
        entity_list[0]["NetXStartTime"] = ""
        entity_list[0]["NetXEndTime"] = ""
        entity_list[0]["ErrorMessage"] = ""
        chroma_diverseTable.update_entity(mode=UpdateMode.REPLACE, entity=entity_list[0])
        logging.info(entity_list)

    try:
        logging.info("---Feature Extraction---")
        chroma_diverse.pdf_name = pdf_name
        chroma_diverse.temp_blob_pdf = tempFilePath + "/" + pdf_name[:-4] + "_blob.pdf"
        chroma_diverse.temp_pdf = tempFilePath + "/"
        chroma_diverse.temp_json = tempFilePath + "/" + pdf_name[:-4] + "_features.json"
        chroma_diverse.prediction_json = tempFilePath + "/" + pdf_name[:-4] + "_predictions.json"

        logging.info("Download PDF")
        chroma_diverse.download_pdf(chroma_diverse.pdf_container)

        logging.info("Extract Features")
        chroma_diverse.extract_features()

        logging.info("---Classification---")
        chroma_diverse.make_predictions(drop_program_features=["other", "stopword"], drop_company_features=[], drop_donor_features=["other", "stopword"])

        os.remove(chroma_diverse.temp_blob_pdf)
        logging.info(f"-----Labelling: Removed temp file: {chroma_diverse.temp_blob_pdf}-----")
        os.remove(chroma_diverse.temp_json)
        logging.info(f"-----Labelling: Removed temp file: {chroma_diverse.temp_json}-----")
        os.remove(chroma_diverse.prediction_json)
        logging.info(f"-----Labelling: Removed temp file: {chroma_diverse.prediction_json}-----")
        os.remove(chroma_diverse.temp_pdf + chroma_diverse.pdf_name)
        logging.info(f"-----Labelling: Removed temp file: {chroma_diverse.temp_pdf + chroma_diverse.pdf_name}-----")

        logging.info("---Success - Updating Tables---")
        logging.info(entity_list)

        entity_list[0]["status"] = "Labelling Completed"
        entity_list[0]["RowKey"] = ""
        entity_list[0]["updatedAt"] = datetime.now()
        entity_list[0]["LabellingEndTime"] = datetime.now()
        chroma_diverseTable.update_entity(mode=UpdateMode.REPLACE, entity=entity_list[0])
        logging.info(entity_list)

        return {"status_code": 200, "error": "", "message": "Success"}
    except Exception as e:
        entity_list[0]["status"] = "Labelling Error"
        entity_list[0]["RowKey"] = ""
        entity_list[0]["updatedAt"] = ""
        entity_list[0]["ErrorMessage"] = str(e)
        chroma_diverseTable.update_entity(mode=UpdateMode.REPLACE, entity=entity_list[0])
        logging.info(entity_list)
        logging.error(f"Error labelling: {e}")
        return {"status_code": 400, "error": "Error during processing", "message": str(e)}

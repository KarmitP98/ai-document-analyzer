"""Azure Function to OCR, NER and Classify pages."""

import json
import logging

import azure.functions as func

from page_labelling_core.labelling_core import process_labelling


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        json_body = req.get_json()
        blob_path = json_body["filepath"]
    except Exception as e:
        logging.error(f"Error in request body: {e}")
        json_response = json.dumps({"status_code": 400, "error": "Invalid body", "message": str(e)})
        return func.HttpResponse(json_response, status_code=400, mimetype="application/json")

    result = process_labelling(blob_path)
    json_response = json.dumps(result)
    return func.HttpResponse(json_response, status_code=result.get("status_code", 500), mimetype="application/json")

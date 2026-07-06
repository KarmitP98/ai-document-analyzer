"""Azure Function create and send assets to NetX."""

import json
import logging

import azure.functions as func

from classes.src.netx_connection import process_batch_uploads, update_program_status, validate_required_fields


def main(req: func.HttpRequest) -> func.HttpResponse:
    """GET and POST request handler for Azure Function.

    Processes an array of PDF names in a single request.
    """
    logging.info("NetX Upload Function Triggered")

    # Get the request data
    request_data = req.get_json()
    logging.info(f"request_data: {request_data}")
    try:
        # Validate that request_data is a dictionary
        if not isinstance(request_data, dict):
            error_message = f"Request body must be a JSON object: {request_data}"
            logging.error(error_message)

            # Update all programs to error status
            for pdf_name in request_data.get("pdf_names", []):
                update_program_status(pdf_name, "NetX Upload Error", error_message="Request body must be a JSON object")

            return func.HttpResponse(
                json.dumps({"status_code": 400, "message": "Request body must be a JSON object"}), mimetype="application/json", status_code=400
            )

        # Validate required fields
        is_valid, error_message = validate_required_fields(request_data)
        if not is_valid:
            error_message = f"Validation error: {error_message}"
            logging.error(error_message)
            # Update all programs to error status
            for pdf_name in request_data.get("pdf_names", []):
                update_program_status(pdf_name, "NetX Upload Error", error_message=error_message)
            return func.HttpResponse(json.dumps({"status_code": 400, "message": error_message}), mimetype="application/json", status_code=400)

        return process_batch_uploads(req)

    except json.JSONDecodeError as e:
        error_message = f"Invalid JSON in request body: {str(e)}"
        logging.error(error_message)
        for pdf_name in request_data.get("pdf_names", []):
            update_program_status(pdf_name, "NetX Upload Error", error_message="Invalid JSON in request body")
        return func.HttpResponse(json.dumps({"status_code": 400, "message": "Invalid JSON in request body"}), mimetype="application/json", status_code=400)
    except Exception as e:
        logging.error(f"Error in main function: {str(e)}")

        for pdf_name in request_data.get("pdf_names", []):
            update_program_status(pdf_name, "NetX Upload Error", error_message=f"Error in main function: {str(e)}")

        return func.HttpResponse(json.dumps({"status_code": 500, "message": f"Internal server error: {str(e)}"}), mimetype="application/json", status_code=500)

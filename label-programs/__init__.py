import json
import logging

import azure.functions as func

from page_labelling_core.labelling_core import process_labelling


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Queue Trigger: Processes a queue message containing a list of files for a client.
    For each file, calls the labelling core logic synchronously. Returns error info on failure.
    """
    try:
        data = req.get_json()
        # Expecting: {type: 'program', files: [...], clientId}
        files = data.get("files", [])
        client_id = data.get("clientId")

        logging.info(f"Queue trigger received: client_id={client_id}, files={files}")
        # Only process if files are present
        if files:
            for file_name in files:
                blob_path = f"data/{client_id}/pdfs/{file_name}"
                try:
                    # Call the labelling logic for each file, wait for completion before next
                    result = process_labelling(blob_path)
                    logging.info(f"Labelling result for {file_name}: {result}")
                    if result.get("status_code", 500) != 200:
                        # Return error details if labelling fails
                        return func.HttpResponse(
                            json.dumps(
                                {
                                    "fileName": file_name,
                                    "status": "error",
                                    "clientId": client_id,
                                    "message": result.get("message", "Unknown error"),
                                    "status_code": result.get("status_code", 500),
                                }
                            ),
                            mimetype="application/json",
                            status_code=result.get("status_code", 500),
                        )
                except Exception as e:
                    # Return error details if an exception occurs
                    logging.error(f"Error calling process_labelling for {file_name}: {e}")
                    return func.HttpResponse(
                        json.dumps({"fileName": file_name, "status": "error", "clientId": client_id, "message": str(e), "status_code": 500}),
                        mimetype="application/json",
                        status_code=500,
                    )
        # All files processed successfully or no files to process
        return func.HttpResponse(json.dumps({"status": "success"}), mimetype="application/json", status_code=200)
    except Exception as e:
        logging.error(f"Error processing queue message: {e}")
        return func.HttpResponse(json.dumps({"status": "error", "message": str(e)}), mimetype="application/json", status_code=500)

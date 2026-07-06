"""
Download Program Data

Generates a full zip file that includes:
- The Program PDF
- All performance PDF files
- JSON files of the Program and each performance (named so the PDF file name matches the JSON file name) of the program attributes and names

Inputs:
    JSON body with:
    - client_id (str): The client ID for the program
    - pdf_names (list): List of PDF names to include in the download

    {
        "client_id": "client123",
        "pdf_names": ["program1.pdf", "program2.pdf", "program3.pdf"]
    }
Returns:
    bytes: The binary content of the zip file containing the program data.
"""

import logging

import azure.functions as func

from classes.src.cd_azure import download_program_data


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Download Program Data endpoint triggered")
    try:
        json_body = req.get_json()
        logging.info(f"Received JSON body: {json_body}")

        client_id: str | None = json_body.get("client_id", None)
        pdf_names: list = json_body.get("pdf_names", [])

        logging.info(f"Parsed client_id: {client_id}")
        logging.info(f"Parsed pdf_names: {pdf_names}")

        if not client_id or not pdf_names or len(pdf_names) <= 0:
            return func.HttpResponse(body="Missing required fields: client_id, or pdf_names", status_code=400)

        logging.info("About to call download_program_data function")
        body: bytes = download_program_data(client_id, pdf_names)
        logging.info(f"Successfully generated zip file with {len(body)} bytes")

        return func.HttpResponse(body=body, status_code=200)
    except Exception as e:
        logging.error(f"Error in download program data endpoint: {str(e)}")
        logging.error(f"Exception type: {type(e).__name__}")
        import traceback

        logging.error(f"Traceback: {traceback.format_exc()}")
        return func.HttpResponse(body=f"Internal server error: {str(e)}", status_code=500)

"""Azure Function to match entities with Vocab."""

import json
import logging

import azure.functions as func

from classes.vocab_matching import process_vocab_matching_request


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function entry point for vocab matching.

    Args:
        req (func.HttpRequest): HTTP request object.

    Returns:
        func.HttpResponse: HTTP response object.
    """
    try:
        print("Received request for vocab matching.")
        return process_vocab_matching_request(json_body=req.get_json())
    except Exception as e:
        import traceback

        logging.error(f"Error: {e}")
        logging.error("Stack trace:\n" + traceback.format_exc())

        return func.HttpResponse(json.dumps({"status": "error", "message": str(e)}), status_code=500, mimetype="application/json")

import json
import logging
import traceback

import azure.functions as func

from classes.src.netx_connection import get_auth_key


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Netx Login Function Triggered!")
    try:
        json_body = req.get_json()
        url = json_body["url"]
        username = json_body["username"]
        password = json_body["password"]
        authkey = get_auth_key(url=url, username=username, password=password)
    except Exception as e:
        tb_str = traceback.format_exc()
        logging.error(f"Exception occurred during authentication: {e}\n{tb_str}")
        final_json = json.dumps({"statusCode": 501, "message": "Authentication Error: " + str(e), "authKey": None})
        return func.HttpResponse(final_json, mimetype="application/json", status_code=501)

    # If authKey is None, return an error response
    if not authkey:
        logging.error("Authentication failed, authkey is None")
        final_json = json.dumps({"statusCode": 501, "message": "Authentication failed, Please check your credentials!", "authKey": None})
        return func.HttpResponse(final_json, mimetype="application/json", status_code=501)

    final_json = json.dumps({"authKey": authkey, "statusCode": 200, "message": "Authentication Successful!"})
    return func.HttpResponse(final_json, mimetype="application/json", status_code=200)

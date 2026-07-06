"""Azure Function create and send assets to NetX."""

import json
import logging

import azure.functions as func

from classes.src.netx_connection import get_auth_key, get_root_folder_list


# GET and POST request
# Input will be of form: {"username": XX, "password": XX, "url": XX}
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Checking New Client Authorization")
    json_body = req.get_json()

    url = json_body["url"]
    folder_id = json_body["folderId"]

    try:
        # If AuthKey is provided use that or fetch the authkey using NetX Login function
        if "authKey" in json_body:
            authkey = json_body["authKey"]
        else:
            username = json_body["username"]
            password = json_body["password"]
            authkey = get_auth_key(url=url, username=username, password=password)

        root_folder_response = get_root_folder_list(folder_id=folder_id, url=url, authkey=authkey)
    except Exception as e:
        final_json = json.dumps({"status_code": 501, "error": "Authentication Error: " + str(e), "body": ""})
        return func.HttpResponse(final_json, mimetype="application/json", status_code=501)

    logging.info("Success")
    final_json = json.dumps({"status_code": 200, "message": "Success", "body": root_folder_response})
    return func.HttpResponse(final_json, mimetype="application/json", status_code=200)

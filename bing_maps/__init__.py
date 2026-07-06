"""Azure Function create and send Bing Maps API Results."""

import json
import logging

import azure.functions as func

from classes.bing_maps import bing_maps_fetch_matches, create_final_json
from classes.src.config_settings import get_bing_key


def main(req: func.HttpRequest) -> func.HttpResponse:
    """GET and POST request.

    Input is the vocab_matching.json passed from the frontend
    """
    json_matched = req.get_json()
    key = get_bing_key()
    logging.info("Fetching relevant addresses using Bing Maps API")
    bing_maps_results = bing_maps_fetch_matches(json_matched, key)
    json_combined = create_final_json(bing_maps_results, json_matched)

    try:
        if len(json_combined["bing_maps"]) > 0:  # type: ignore
            logging.info("Results fetched")

    except Exception:
        if json_combined["bing_maps"] == []:
            logging.info("No relevant matches")
            empty_details = {
                "countryRegion": "",
                "formattedAddress": "",
                "locality": "",
                "countryRegionIso2": "",
            }
            json_combined["bing_maps"] = empty_details
    json_return = json.dumps(json_combined)
    return func.HttpResponse(json_return, mimetype="application/json")

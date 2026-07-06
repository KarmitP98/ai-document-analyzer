"""Bing Maps API Class."""

import itertools

from classes.locations import LocationByQuery
from classes.src.config_settings import (
    get_bing_map_confidence,
    get_bing_map_max_results,
)


def bing_maps_fetch_matches(json_matched, key):
    """Fetch the top 5 Bing Maps results corresponding to different address queries in the pdf"""
    """Input for bing_maps_fetch_matches : vocab_matching.json and functional bing maps API key"""
    """LocationByQuery :Input will be of form: {'q': xx, 'key': xx, 'maxResults': 5, 'confidence': 'High'}. """
    query_list = []
    bing_maps_addresses = []

    keys = ["Venue", "City", "State/Province", "Country"]
    for item in json_matched:
        current_loc_list = []

        for location_key in keys:
            if location_key in item["attributes"]:
                current_loc_list.append(item["attributes"][location_key])
            else:
                continue
        current_loc_list = list(filter(None, current_loc_list))
        current_loc_list = list(itertools.product(*current_loc_list))
        updated_current_loc_list = []
        for pair in current_loc_list:
            updated_current_loc_list.append(" ".join(pair))
        query_list.extend(updated_current_loc_list)

    for i in range(len(query_list)):
        query_to_search = query_list[i]
        if query_to_search != "":
            data = {"q": query_to_search, "key": key, "maxResults": get_bing_map_max_results(), "confidence": get_bing_map_confidence}
            loc_by_query = LocationByQuery(data)
            bing_maps_addresses.extend(loc_by_query.get_address)

    # Remove duplicates while maintaining order
    bing_maps_addresses_set = []
    seen = set()
    for d in bing_maps_addresses:
        item_tuple = tuple(d.items())

        if item_tuple not in seen:
            seen.add(item_tuple)
            bing_maps_addresses_set.append(d)

    # Return top 5 relevant bing maps matches
    bing_maps_addresses_return = bing_maps_addresses_set[: get_bing_map_max_results()]

    return bing_maps_addresses_return


def create_final_json(bing_maps_addresses_return, json_matched):
    """Append Bing Maps results as a separate key in the vocab_matching json and return the final combined json"""
    """Input for create_final_json: top 5 results provided by bing_maps_fetch_matches(), the original vocab_matching.json"""
    final_json = dict.fromkeys(["bing_maps", "vocab_matching"])
    final_json["bing_maps"] = bing_maps_addresses_return
    final_json["vocab_matching"] = json_matched

    return final_json

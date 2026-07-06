"""Config settings."""

import os


def get_bing_key():
    """Returns bing maps key."""
    try:
        key = os.getenv("BingMapsKey")
        return key
    except KeyError as exc:
        print(exc)


def get_bing_map_max_results():
    """Returns the value of maximum results for bing maps query."""
    max_results = 5
    return max_results


def get_bing_map_confidence():
    """Returns the confidence level value for bin maps query."""
    confidence = "High"
    return confidence

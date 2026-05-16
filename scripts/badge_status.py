"""Check deployment status of the Streamlit app and return shields.io badge URLs."""

import requests

APP_URL = "https://brand-aeo.streamlit.app/"

_BADGE_COLORS = {
    "online": "green",
    "offline": "red",
    "unknown": "grey",
}


def get_app_status(url: str) -> str:
    """Return 'online', 'offline', or 'unknown' based on HTTP response from url."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return "online"
        if response.status_code >= 500:
            return "offline"
        return "unknown"
    except requests.exceptions.ConnectionError:
        return "offline"
    except requests.exceptions.Timeout:
        return "unknown"
    except Exception:
        return "unknown"


def get_badge_url(status: str) -> str:
    """Return a shields.io badge URL for the given status string."""
    color = _BADGE_COLORS.get(status, "grey")
    return f"https://img.shields.io/badge/app-{status}-{color}"

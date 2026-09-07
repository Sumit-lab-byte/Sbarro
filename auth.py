import requests
from config import SOURCES


def get_access_token(source_key):
    source = SOURCES[source_key]

    missing = [
        name
        for name, value in {
            "client_id": source["client_id"],
            "client_secret": source["client_secret"],
            "token_url": source["token_url"],
        }.items()
        if not value
    ]

    if missing:
        raise ValueError(
            f"Missing {', '.join(missing)} for source: {source['name']}"
        )

    payload = {
        "grant_type": "client_credentials",
        "client_id": source["client_id"],
        "client_secret": source["client_secret"],
    }

    if source["token_format"] == "basic":
        response = requests.post(
            source["token_url"],
            data={
                "grant_type": "client_credentials",
            },
            auth=(
                source["client_id"],
                source["client_secret"],
            ),
            timeout=60,
        )
    elif source["token_format"] == "form":
        response = requests.post(
            source["token_url"],
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            timeout=60,
        )
    else:
        response = requests.post(
            source["token_url"],
            json=payload,
            timeout=60,
        )

    response.raise_for_status()

    access_token = response.json().get("access_token")

    if not access_token:
        raise ValueError(
            f"No access token returned for {source['name']}: {response.text}"
        )

    return access_token
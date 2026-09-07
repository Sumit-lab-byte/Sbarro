import os
from dotenv import load_dotenv

load_dotenv(override=True)


def get_api_base_url(token_url):
    if not token_url:
        return None

    return token_url.rstrip("/").removesuffix("/token")


SOURCES = {
    "national": {
        "token_format": "json",
        "name": "Sbarro National",
        "survey_id": os.getenv("NATIONAL_SURVEY_ID"),
        "api_base_url": get_api_base_url(os.getenv("NATIONAL_TOKEN_URL")),
        "client_id": os.getenv("NATIONAL_CLIENT_ID"),
        "client_secret": os.getenv("NATIONAL_CLIENT_SECRET"),
        "token_url": os.getenv("NATIONAL_TOKEN_URL"),
    },
}
import json
import os

import requests

from auth import get_access_token
from config import SOURCES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "survey.json")

SOURCE_KEY = "national"
source = SOURCES[SOURCE_KEY]

token = get_access_token(SOURCE_KEY)

headers = {
    "Authorization": f"Bearer {token}",
}

url = f"{source['api_base_url']}/surveys"

params = {
    "filterby": f"survey_id,eq,{source['survey_id']}",
    "relatives": "questions,questions.answer_options",
}

print(f"Fetching survey {source['survey_id']}...")

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=60,
)

response.raise_for_status()

data = response.json()

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4)

surveys = data.get("surveys", {}).get("survey", [])

if isinstance(surveys, dict):
    surveys = [surveys]

if not surveys:
    raise ValueError("No survey was returned by the API.")

survey = surveys[0]

questions = survey.get("questions", [])

if isinstance(questions, dict):
    questions = questions.get("question", [])

if not isinstance(questions, list):
    questions = []

answer_option_count = 0

for question in questions:
    if not isinstance(question, dict):
        continue

    answer_options = question.get("answer_options", [])

    if isinstance(answer_options, dict):
        answer_options = answer_options.get("answer_option", [])

    if isinstance(answer_options, list):
        answer_option_count += len(answer_options)

print("\n" + "=" * 60)
print("SURVEY DOWNLOAD COMPLETED")
print("=" * 60)
print(f"Survey ID           : {survey.get('survey_id', '')}")
print(f"Survey Name         : {survey.get('survey_name', '')}")
print(f"Questions found     : {len(questions)}")
print(f"Answer options found: {answer_option_count}")
print(f"Saved to            : {OUTPUT_FILE}")

if answer_option_count == 0:
    print("\nWARNING:")
    print(
        "The API did not include answer options in survey.json. "
        "Run this script first, then we will use the Sbarro workbook "
        "to create the required question-by-question label mapping."
    )
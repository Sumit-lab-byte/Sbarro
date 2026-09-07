import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SURVEY_FILE = os.path.join(BASE_DIR, "survey.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "question_list.txt")


def as_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return value.get("question", [value])
    return []


with open(SURVEY_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

surveys = data.get("surveys", {}).get("survey", [])

if isinstance(surveys, dict):
    surveys = [surveys]

survey = surveys[0]

questions_data = survey.get("questions", [])
questions = as_list(questions_data)

lines = []

for question in questions:
    question_id = question.get("question_id", "")
    question_text = question.get("question_text", "")

    lines.append(f"{question_id} | {question_text}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    file.write("\n".join(lines))

print(f"Questions found: {len(questions)}")
print(f"Saved question list to: {OUTPUT_FILE}")
import json
import os
import re
from difflib import SequenceMatcher

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

JOBS_FILE = os.path.join(BASE_DIR, "jobs.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "dataset.xlsx")
FORM_DEFINITION_FILE = os.path.join(
    BASE_DIR,
    "Sbarro Mystery Shop 2026.xlsx",
)

CLIENT_SURVEY_NAME = "Mystery Shop 2026"

STATUS_MAP = {
    "0": "Created",
    "1": "New",
    "2": "Incomplete",
    "3": "Complete",
    "4": "Collaboration Shop",
    "5": "Excluded",
    "6": "Hold A",
    "7": "Hold B",
    "8": "Reviewed",
    "9": "Finalized",
    "10": "Emailed",
    "12": "Client Finalized",
    "15": "Locked",
}

BASE_COLUMNS = [
    "Evaluation_ID",
    "Client_Survey_Name",
    "Evaluation_Date",
    "Reporting_Date",
    "Location_ID",
    "Location_Name",
    "Location_Address1",
    "Location_Address2",
    "Location_City",
    "Location_State",
    "Location_Country",
    "LocationZip",
    "Evaluation_Status",
    "Link_to_Evaluation",
    "WaveName",
]

QUESTION_COLUMNS = [
    ("Date of Visit:", "9819:729874"),
    ("Date shop performed", None),
    ("Day of visit:", "9819:729875"),
    ("Time of Visit:", "9819:729877"),
    ("Was this location open for business?", "9819:729876"),
    ("...if no, please give details:", "9819:729878"),
    ("...if no, please upload picture of closed store front:", "9819:729879"),
    ("Expense Amount:", "9819:729880"),
    ("Receipt upload:", "9819:729885"),
    ("Photo upload of overall store:", "9819:729886"),
    (
        "Guest Engagement - 1. If the employees are not already engaging with "
        "existing customers, is a warm, friendly greeting given to each "
        "potential customer who walks by?",
        "9819:729924",
    ),
    ("...Please Explain:", "9819:729925"),
    (
        "Guest Engagement - 2. Did the employees appearance or lack of uniform "
        "detract from your overall experience?",
        "9819:729926",
    ),
    (
        "Guest Engagement - 2a. ...if yes, What detracted from the visit?",
        "9819:729952",
    ),
    ("Guest Engagement - 2b. ...if other", "9819:729928"),
    (
        "Guest Engagement - 3. Were the staff members friendly, upbeat and "
        "happy you were there?",
        "9819:729929",
    ),
    (
        "Guest Engagement - 4. Did anyone suggest a Combo, a beverage "
        "(or larger size beverage), dipping cup, or other item?",
        "9819:729930",
    ),
    (
        "Guest Engagement - 4a. ...if yes, what did they suggest?",
        "9819:729953",
    ),
    (
        "Guest Engagement - 4b. ...if other, please mention here",
        "9819:729932",
    ),
    (
        "Guest Engagement - 5. Which option best reflects how quickly you "
        "were served?",
        "9819:729933",
    ),
    (
        "Guest Engagement - 6. Did the cashier thank you for coming to "
        "Sbarro and give you a warm send off?",
        "9819:729934",
    ),
    (
        "Guest Engagement - 7. Were you given a receipt without asking for it?",
        "9819:729935",
    ),
    ("Time order placed:", "9819:729936"),
    ("Time payment process is completed:", "9819:729937"),
    (
        "Guest Engagement - 8. How long was your experience from placing your "
        "order to cashing out at the register?",
        "9819:729938",
    ),
    ("Guest Engagement Comments:", "9819:729939"),
    (
        "Merchandising - 1. How many trays of pizzas were available for you "
        "to choose from in the display area?",
        "9819:729888",
    ),
    (
        "Merchandising - 2. What flavors (or types) of pizzas were displayed?",
        "9819:729899",
    ),
    (
        "Merchandising - 3. How many trays of strombolis were available for "
        "you to choose from in the display area?",
        "9819:729900",
    ),
    (
        "Merchandising - 4. What types of strombolis were displayed?",
        "9819:729901",
    ),
    (
        "Merchandising - 5. After 11:00 AM, did the display area have at "
        "least one tray of breadsticks available for purchase?",
        "9819:729902",
    ),
    (
        "Merchandising - 6. Were professional looking labels visible in "
        "front of every product?",
        "9819:729903",
    ),
    (
        "Merchandising - 7. Were there at least 3 pieces on each pizza and "
        "stromboli tray, and were the breadstick trays at least half full?",
        "9819:729904",
    ),
    (
        "Merchandising - 8. Did the other food offerings displayed "
        "(pasta, potatoes, meatballs, salads, etc.) look appetizing?",
        "9819:729905",
    ),
    ("Photo of display area", "9819:729906"),
    ("Photo of display area", "9819:729907"),
    (
        "Merchandising - 9. Was the restaurant clean and in good condition?",
        "9819:729908",
    ),
    (
        "Merchandising - 9a. ...if no, what needs improvement?",
        "9819:729909",
    ),
    (
        "Merchandising - 9b. ...if other, please mention here",
        "9819:729910",
    ),
    (
        "Merchandising - 10. If you weren't a mystery shopper, would the "
        "restaurant appearance / design have prompted you to eat at Sbarro?",
        "9819:729911",
    ),
    (
        "Merchandising - 10a. ...if no, what would have dissuaded you?",
        "9819:729912",
    ),
    (
        "Merchandising - 11. Was there a hot grab-n-go section on the "
        "premises intended for Sbarro products?",
        "9819:729916",
    ),
    (
        "Merchandising - 11a. If yes, was there any Sbarro product in the "
        "grab-n-go?",
        "9819:729917",
    ),
    (
        "Merchandising - 11b. If so, what was there?",
        "9819:729918",
    ),
    (
        "Merchandising - 11c. If yes, were any of the displayed products in "
        "the grab-n-go expired?",
        "9819:729919",
    ),
    ("Expired Products", "9819:729920"),
    ("Expired Products", "9819:729921"),
    ("Merchandising Comments:", "9819:729922"),
    (
        "Delivered Product Quality - 1. Were the portion sizes and amount of "
        "toppings acceptable?",
        "9819:729941",
    ),
    (
        "Delivered Product Quality - 2. Did your food taste fresh?",
        "9819:729942",
    ),
    (
        "Delivered Product Quality - 3. Did the temperature of the food meet "
        "your expectations?",
        "9819:729943",
    ),
    (
        "Delivered Product Quality - 4. How many Pepperonis does the pizza "
        "slice have?",
        "9819:729944",
    ),
    (
        "Delivered Product Quality - 5. Did your pizza slice have bubbles "
        "that affected the overall food quality?",
        "9819:729945",
    ),
    ("Picture of food from top", "9819:729946"),
    ("Picture of food from side", "9819:729947"),
    ("Picture of food from bottom", "9819:729948"),
    ("Food Quality Comments:", "9819:729949"),
    (
        "Overall Experience - 1. What is your likelihood to return? Scale 1-10",
        "9819:729913",
    ),
    (
        "Overall Experience - 2. What was the key driver of your response above?",
        "9819:729951",
    ),
    (
        "Overall Experience - 2a. ...if other, please mention here",
        "9819:729915",
    ),
]

OUTPUT_COLUMNS = BASE_COLUMNS + [
    column_name for column_name, _ in QUESTION_COLUMNS
]

IMAGE_QUESTION_IDS = {
    "9819:729879",
    "9819:729885",
    "9819:729886",
    "9819:729906",
    "9819:729907",
    "9819:729920",
    "9819:729921",
    "9819:729946",
    "9819:729947",
    "9819:729948",
}


def to_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value)


def normalize_question_text(value):
    value = to_text(value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = value.replace(" - ", "-")
    return value


def get_location(job):
    location = job.get("location") or {}

    if not isinstance(location, dict):
        location = {}

    return {
        "id": (
            location.get("client_location_id")
            or job.get("client_location_id")
            or location.get("location_id")
            or job.get("location_id")
            or ""
        ),
        "name": (
            location.get("client_location_name")
            or job.get("client_location_name")
            or location.get("location_name")
            or location.get("name")
            or job.get("location_name")
            or ""
        ),
        "address1": (
            location.get("address1")
            or location.get("address_1")
            or location.get("location_address1")
            or job.get("location_address1")
            or ""
        ),
        "address2": (
            location.get("address2")
            or location.get("address_2")
            or location.get("location_address2")
            or job.get("location_address2")
            or ""
        ),
        "city": location.get("city") or job.get("location_city") or "",
        "state": location.get("state") or job.get("location_state") or "",
        "country": (
            location.get("country_code")
            or location.get("country")
            or job.get("location_country")
            or job.get("country_code")
            or ""
        ),
        "zip": (
            location.get("zip")
            or location.get("zipcode")
            or location.get("postal_code")
            or location.get("location_zip")
            or job.get("location_zip")
            or ""
        ),
    }


def load_choice_labels():
    if not os.path.exists(FORM_DEFINITION_FILE):
        raise FileNotFoundError(
            "Missing form definition file:\n"
            f"{FORM_DEFINITION_FILE}\n\n"
            "Copy 'Sbarro Mystery Shop 2026.xlsx' into the Sbarro folder."
        )

    form = pd.read_excel(
        FORM_DEFINITION_FILE,
        header=None,
        dtype=object,
    )

    labels_by_question_text = {}
    current_question = None

    for _, row in form.iterrows():
        question_text = to_text(row.iloc[0]).strip()
        option_text = to_text(row.iloc[2]).strip()

        if question_text:
            current_question = normalize_question_text(question_text)
            labels_by_question_text.setdefault(current_question, [])

        if current_question and option_text:
            label = re.sub(r"\(\d+\)\s*$", "", option_text).strip()

            if label:
                labels_by_question_text[current_question].append(label)

    return labels_by_question_text


def get_choice_labels_by_question_id():
    labels_by_question_text = load_choice_labels()
    choice_labels_by_question_id = {}

    for column_name, question_id in QUESTION_COLUMNS:
        if not question_id:
            continue

        expected_text = normalize_question_text(column_name)

        if expected_text in labels_by_question_text:
            labels = labels_by_question_text[expected_text]

            if labels:
                choice_labels_by_question_id[question_id] = labels

            continue

        best_match = ""
        best_score = 0

        for form_question in labels_by_question_text:
            score = SequenceMatcher(
                None,
                expected_text,
                form_question,
            ).ratio()

            if score > best_score:
                best_score = score
                best_match = form_question

        if best_score >= 0.82:
            labels = labels_by_question_text[best_match]

            if labels:
                choice_labels_by_question_id[question_id] = labels

    return choice_labels_by_question_id


def get_choice_value(response, option_labels):
    answer_option_ids = response.get("answer_option_ids") or []

    if isinstance(answer_option_ids, str):
        answer_option_ids = [answer_option_ids]

    if not isinstance(answer_option_ids, list):
        return ""

    selected_labels = []

    for option_id in answer_option_ids:
        option_number = to_text(option_id).rsplit(":", 1)[-1]

        if not option_number.isdigit():
            continue

        option_number = int(option_number)

        if 1 <= option_number <= len(option_labels):
            selected_labels.append(option_labels[option_number - 1])

        elif 0 <= option_number < len(option_labels):
            selected_labels.append(option_labels[option_number])

    return " | ".join(dict.fromkeys(selected_labels))


def get_response_values(job, choice_labels_by_question_id):
    answers = {}

    responses = job.get("responses") or []

    if isinstance(responses, dict):
        responses = responses.get("response", [responses])

    if not isinstance(responses, list):
        return answers

    for response in responses:
        if not isinstance(response, dict):
            continue

        question_id = to_text(response.get("question_id")).strip()

        if not question_id:
            continue

        option_labels = choice_labels_by_question_id.get(question_id, [])

        value = ""

        if option_labels:
            value = get_choice_value(response, option_labels)

        if not value:
            response_text = to_text(response.get("response_text")).strip()
            response_url = to_text(response.get("response_url")).strip()

            if question_id in IMAGE_QUESTION_IDS:
                value = response_url or response_text
            else:
                value = response_text or response_url

        if value:
            answers.setdefault(question_id, []).append(value)

    return {
        question_id: " | ".join(dict.fromkeys(values))
        for question_id, values in answers.items()
    }


print("Loading jobs.json...")

with open(JOBS_FILE, "r", encoding="utf-8") as file:
    jobs = json.load(file).get("jobs", {}).get("job", [])

if isinstance(jobs, dict):
    jobs = [jobs]

if not jobs:
    raise ValueError("jobs.json contains no jobs. Run s2_fetch_jobs.py first.")

choice_labels_by_question_id = get_choice_labels_by_question_id()

print(
    "Multiple-choice question mappings loaded: "
    f"{len(choice_labels_by_question_id)}"
)

rows = []

for job in jobs:
    location = get_location(job)
    answers = get_response_values(job, choice_labels_by_question_id)
    job_status = to_text(job.get("job_status")).strip()

    row_values = [
        to_text(job.get("job_id")),
        CLIENT_SURVEY_NAME,
        to_text(job.get("job_date")),
        to_text(job.get("report_date")),
        to_text(location["id"]),
        to_text(location["name"]),
        to_text(location["address1"]),
        to_text(location["address2"]),
        to_text(location["city"]),
        to_text(location["state"]),
        to_text(location["country"]),
        to_text(location["zip"]),
        STATUS_MAP.get(job_status, job_status),
        to_text(job.get("shop_view_url")),
        to_text(job.get("wave_name")),
    ]

    for _, question_id in QUESTION_COLUMNS:
        if question_id is None:
            row_values.append(to_text(job.get("job_date")))
        else:
            row_values.append(answers.get(question_id, ""))

    rows.append(row_values)

df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

df.to_excel(OUTPUT_FILE, index=False)

print("\n" + "=" * 60)
print("SBARRO DATASET CREATED SUCCESSFULLY")
print("=" * 60)
print(f"Rows exported    : {len(df)}")
print(f"Columns exported : {len(df.columns)}")
print(f"Output file      : {OUTPUT_FILE}")
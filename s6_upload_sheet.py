import os
from datetime import date, datetime

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EXCEL_FILE = os.path.join(BASE_DIR, "dataset.xlsx")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")

SHEET_ID = "1EqW35dTmOGvWg0r71YqsexFuQKgPwzMWYn-zJz4Chk0"
WORKSHEET_NAME = "Sheet1"

EXPECTED_COLUMN_COUNT = 75
BATCH_SIZE = 500

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def google_safe_value(value):
    if pd.isna(value):
        return ""

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.strftime("%Y-%m-%d")

    return str(value)


print("Reading dataset.xlsx...")

# header=None preserves duplicate headers exactly, such as duplicate photo columns.
raw_data = pd.read_excel(EXCEL_FILE, header=None)

headers = [
    google_safe_value(value)
    for value in raw_data.iloc[0].tolist()
]

data_rows = [
    [google_safe_value(value) for value in row]
    for row in raw_data.iloc[1:].values.tolist()
]

if len(headers) != EXPECTED_COLUMN_COUNT:
    raise ValueError(
        f"dataset.xlsx has {len(headers)} columns; "
        f"expected {EXPECTED_COLUMN_COUNT}."
    )

print(f"Rows    : {len(data_rows)}")
print(f"Columns : {len(headers)}")

print("\nConnecting to Google Sheets...")

credentials = Credentials.from_service_account_file(
    CREDENTIALS_FILE,
    scopes=SCOPES,
)

client = gspread.authorize(credentials)
spreadsheet = client.open_by_key(SHEET_ID)
worksheet = spreadsheet.worksheet(WORKSHEET_NAME)

print(f"Spreadsheet : {spreadsheet.title}")
print(f"Worksheet   : {worksheet.title}")

all_values = [headers] + data_rows

required_rows = len(all_values)
required_columns = len(headers)

if worksheet.row_count < required_rows:
    worksheet.add_rows(required_rows - worksheet.row_count)

if worksheet.col_count < required_columns:
    worksheet.add_cols(required_columns - worksheet.col_count)

print("\nRemoving old sheet data...")
worksheet.clear()

print("Uploading data...")

for start in range(0, len(all_values), BATCH_SIZE):
    batch = all_values[start:start + BATCH_SIZE]
    start_row = start + 1

    worksheet.update(
        range_name=f"A{start_row}",
        values=batch,
        value_input_option="RAW",
    )

    uploaded_data_rows = min(
        max(start + BATCH_SIZE - 1, 0),
        len(data_rows),
    )

    print(f"Uploaded {uploaded_data_rows}/{len(data_rows)} data rows")

print("\n" + "=" * 60)
print("GOOGLE SHEETS EXPORT COMPLETED SUCCESSFULLY")
print("=" * 60)
print(f"Data rows uploaded : {len(data_rows)}")
print(f"Columns uploaded   : {len(headers)}")
print(f"Worksheet          : {worksheet.title}")
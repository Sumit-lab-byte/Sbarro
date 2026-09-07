import json
import os
import requests

from auth import get_access_token
from config import SOURCES


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "jobs.json")

all_jobs = []

for source_key, source in SOURCES.items():
    print("\n" + "=" * 60)
    print(f"Fetching {source['name']} | Survey ID: {source['survey_id']}")
    print("=" * 60)

    token = get_access_token(source_key)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = f"{source['api_base_url']}/jobs"

    params = {
        "filterby": f"survey_id,eq,{source['survey_id']}",
        "relatives": "location,responses",
    }

    source_job_count = 0

    while url:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Could not fetch {source['name']} jobs. "
                f"Status {response.status_code}: {response.text}"
            )

        data = response.json()

        jobs = data.get("jobs", {}).get("job", [])

        if isinstance(jobs, dict):
            jobs = [jobs]

        for job in jobs:
            job["_source"] = source_key
            job["_source_name"] = source["name"]
            all_jobs.append(job)

        source_job_count += len(jobs)

        print(
            f"{source['name']}: {source_job_count} jobs | "
            f"Combined total: {len(all_jobs)}"
        )

        url = data.get("jobs", {}).get("next")
        params = None  # Only needed for the first page

output = {
    "jobs": {
        "job": all_jobs
    }
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(output, file, indent=4)

print("\n" + "=" * 60)
print("JOB DOWNLOAD COMPLETED")
print("=" * 60)
print(f"Combined jobs downloaded: {len(all_jobs)}")
print(f"Saved to: {OUTPUT_FILE}")
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

print("Current Working Directory:", os.getcwd())
print("Script Directory:", BASE_DIR)

scripts = [
    "s2_fetch_jobs.py",
    "s5_transform.py",
    "s6_upload_sheet.py"
]

print("=" * 50)
print("Starting Daily API Refresh")
print("=" * 50)

for script in scripts:

    script_path = os.path.join(BASE_DIR, script)

    print(f"\nRunning {script}...\n")

    result = subprocess.run([sys.executable, script_path])

    if result.returncode != 0:
        print(f"\nError while running {script}")
        sys.exit(1)

print("\n" + "=" * 50)
print("Daily Refresh Completed Successfully!")
print("Final_Client_Output.xlsx has been updated.")
print("=" * 50)
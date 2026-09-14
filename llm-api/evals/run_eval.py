import json
import requests
from pathlib import Path

CASES_PATH = Path(__file__).parent / "cases.json"
ENDPOINT = "http://127.0.0.1:8000/enrich"

with open(CASES_PATH, "r", encoding="utf-8") as f:
    cases = json.load(f)

correct = 0
failures = []

for i, case in enumerate(cases, start=1):
    response = requests.post(ENDPOINT, json=case["input"], timeout=60)

    if response.status_code != 200:
        print(f"Case {i}: FAILED (status {response.status_code}) - {case['input']['title']}")
        failures.append({"case": i, "title": case["input"]["title"], "reason": f"status {response.status_code}"})
        continue

    result = response.json()
    actual_category = result.get("category")
    expected_category = case["expected_category"]

    if actual_category == expected_category:
        correct += 1
        print(f"Case {i}: PASS - {case['input']['title']} -> {actual_category}")
    else:
        print(f"Case {i}: FAIL - {case['input']['title']} -> got '{actual_category}', expected '{expected_category}'")
        failures.append({
            "case": i,
            "title": case["input"]["title"],
            "expected": expected_category,
            "actual": actual_category,
        })

print(f"\n--- EVAL RESULT: {correct}/{len(cases)} correct ---")
if failures:
    print("\nFailed cases:")
    for f in failures:
        print(f"  Case {f['case']} ({f['title']}): {f}")
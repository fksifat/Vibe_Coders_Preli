"""
Run all 10 public sample cases against the live /analyze-ticket endpoint.
Usage:
    python tests/sample_cases.py [--url http://localhost:8000]
"""
import re
import json
import sys
import argparse
from pathlib import Path

import httpx

SAMPLE_FILE = Path(__file__).parent.parent / "SUST_Preli_Sample_Cases.json"
REQUIRED_OUTPUT_FIELDS = [
    "ticket_id",
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "severity",
    "department",
    "agent_summary",
    "recommended_next_action",
    "customer_reply",
    "human_review_required",
]
# These are ASKING patterns (violations). The safety reminder "do not share your PIN" is fine.
SAFETY_FORBIDDEN = [
    r"please\s+share\s+your\s+(pin|otp|password)",
    r"kindly\s+share\s+your\s+(pin|otp|password)",
    r"provide\s+your\s+(pin|otp|password)",
    r"enter\s+your\s+(pin|otp|password)",
    r"send\s+(?:us\s+)?your\s+(pin|otp|password)",
    r"we\s+will\s+refund\s+you",
    r"you\s+will\s+(?:get|receive)\s+(?:a\s+)?refund",
]


def check_safety(reply: str) -> list[str]:
    violations = []
    lower = reply.lower()
    for pattern in SAFETY_FORBIDDEN:
        if re.search(pattern, lower):
            violations.append(f"SAFETY VIOLATION: pattern '{pattern}' found in customer_reply")
    return violations


def run_tests(base_url: str):
    data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    cases = data["cases"]

    print(f"\n{'='*70}")
    print(f"QueueStorm Sample Case Tests — {base_url}")
    print(f"{'='*70}\n")

    passed = 0
    failed = 0

    for case in cases:
        cid = case["id"]
        label = case["label"]
        inp = case["input"]
        expected = case["expected_output"]

        print(f"[{cid}] {label}")

        try:
            resp = httpx.post(
                f"{base_url}/analyze-ticket",
                json=inp,
                timeout=35.0,
            )
        except Exception as e:
            print(f"  ❌ REQUEST FAILED: {e}\n")
            failed += 1
            continue

        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}: {resp.text[:200]}\n")
            failed += 1
            continue

        out = resp.json()
        errors = []

        # Check all required fields present
        for field in REQUIRED_OUTPUT_FIELDS:
            if field not in out:
                errors.append(f"Missing field: {field}")

        # Check critical field values match expected
        for field in ("ticket_id", "relevant_transaction_id", "evidence_verdict",
                      "case_type", "department", "human_review_required"):
            got = out.get(field)
            want = expected.get(field)
            if got != want:
                errors.append(f"{field}: got={got!r}, want={want!r}")

        # Safety check
        reply = out.get("customer_reply", "")
        errors.extend(check_safety(reply))

        if errors:
            failed += 1
            print(f"  ❌ FAILED:")
            for e in errors:
                print(f"     • {e}")
        else:
            passed += 1
            print(f"  ✅ PASSED  (case_type={out.get('case_type')}, severity={out.get('severity')})")

        # Show reply snippet
        print(f"     customer_reply: {reply[:100]}...")
        print()

    print(f"{'='*70}")
    print(f"Results: {passed}/{len(cases)} passed, {failed}/{len(cases)} failed")
    print(f"{'='*70}\n")
    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the service")
    args = parser.parse_args()

    success = run_tests(args.url)
    sys.exit(0 if success else 1)

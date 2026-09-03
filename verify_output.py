#!/usr/bin/env python3
"""
Checks the consolidated CSV the workflow produces.

This exists because of a specific failure that happened twice during build-out.
n8n's Structured Output Parser validates the model's reply against a schema
wrapped in an "output" key. When the reply does not match that shape, the parser
does NOT raise - it strips the unrecognised keys and returns an empty object.
That empty object flows through the rest of the graph quite happily: every node
goes green, the execution reports "success", the CSV is written with the right
number of rows, and every generated column is blank.

An execution status is therefore not evidence. This is.

Usage:
    python3 verify_output.py output/shopnest_ticket_output.csv [--rows 30]
Exit code 0 = all checks pass, 1 = something is wrong.
"""

import argparse
import csv
import sys

REQUIRED_COLUMNS = [
    "support_ticket_id",
    "support_ticket_desc",
    "summarisation",
    "response_generation",
    "information_extraction_score",
    "information_extraction_reasoning",
    "field_coverage_score",
    "field_coverage_reasoning",
    "issue_addressal_score",
    "issue_addressal_reasoning",
    "resolution_clarity_score",
    "resolution_clarity_reasoning",
    "overall_score",
    "overall_reasoning",
]

# The 1-3 scale comes from the course's own reference notebook.
SCORE_RANGES = {
    "information_extraction_score": (1, 3),
    "field_coverage_score": (1, 3),
    "issue_addressal_score": (1, 3),
    "resolution_clarity_score": (1, 3),
    "overall_score": (2, 6),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--rows", type=int, default=30)
    a = ap.parse_args()

    failures = []
    notes = []

    with open(a.csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("FAIL: the file has no data rows at all")
        return 1

    # 1. Row count.
    if len(rows) != a.rows:
        failures.append(f"expected {a.rows} rows, found {len(rows)}")
    else:
        notes.append(f"row count {len(rows)}")

    # 2. Every required column present.
    cols = list(rows[0])
    missing = [c for c in REQUIRED_COLUMNS if c not in cols]
    if missing:
        failures.append("missing columns: " + ", ".join(missing))
    else:
        notes.append(f"all {len(REQUIRED_COLUMNS)} required columns present")

    # 3. No column blank across every row. This is the check that catches the
    #    silent-parser failure - the one that looks like a successful run.
    always_blank = [c for c in cols
                    if all(not str(r.get(c, "")).strip() for r in rows)]
    if always_blank:
        failures.append("columns blank in EVERY row: " + ", ".join(always_blank))

    # 4. No individual blank cell in a required column.
    for c in REQUIRED_COLUMNS:
        if c not in cols or c in always_blank:
            continue
        blanks = [r[REQUIRED_COLUMNS[0]] for r in rows
                  if not str(r.get(c, "")).strip()]
        if blanks:
            failures.append(f"{c} is blank on ticket id(s): {', '.join(map(str, blanks[:10]))}")

    # 5. Scores are numeric and inside their declared range.
    for c, (lo, hi) in SCORE_RANGES.items():
        if c not in cols or c in always_blank:
            continue
        bad = []
        for r in rows:
            raw = str(r.get(c, "")).strip()
            try:
                v = float(raw)
            except ValueError:
                bad.append(f"{r[REQUIRED_COLUMNS[0]]}={raw!r}")
                continue
            if not (lo <= v <= hi):
                bad.append(f"{r[REQUIRED_COLUMNS[0]]}={raw}")
        if bad:
            failures.append(f"{c} outside {lo}-{hi} or non-numeric: {', '.join(bad[:10])}")
        else:
            notes.append(f"{c} all within {lo}-{hi}")

    # 6. overall_score must actually be the sum of its two parts, not a guess.
    if all(c in cols and c not in always_blank for c in
           ("issue_addressal_score", "resolution_clarity_score", "overall_score")):
        mismatched = []
        for r in rows:
            try:
                a_, b_, o_ = (float(r["issue_addressal_score"]),
                              float(r["resolution_clarity_score"]),
                              float(r["overall_score"]))
            except ValueError:
                continue
            if a_ + b_ != o_:
                mismatched.append(f"{r[REQUIRED_COLUMNS[0]]}: {a_}+{b_}!={o_}")
        if mismatched:
            failures.append("overall_score is not the sum of its parts: "
                            + ", ".join(mismatched[:10]))
        else:
            notes.append("overall_score == issue + clarity on every row")

    # 7. Say plainly whether this run used the mock. A file full of [MOCK] text
    #    must never be presented as a real result.
    mock_hits = sum(1 for r in rows
                    if "[MOCK" in str(r.get("summarisation", ""))
                    or "[MOCK" in str(r.get("response_generation", "")))
    if mock_hits:
        notes.append(f"MOCK OUTPUT: {mock_hits}/{len(rows)} rows are mock text, "
                     "not real LLM output")

    for n in notes:
        print(f"  ok   {n}")
    for f_ in failures:
        print(f"  FAIL {f_}")

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

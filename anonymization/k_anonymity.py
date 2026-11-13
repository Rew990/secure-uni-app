"""k-anonymity pipeline (owner: Privacy & DevOps).

Usage (planned):
    python -m anonymization.k_anonymity --input students.csv --k 3 \
        --output anonymization/output/anonymised.csv

Method from Week 3 (k-anonymity) and Lab 8 (worked example):
  1. Classify columns. Direct identifiers (full_name, student_number,
     national_id) are removed. Quasi-identifiers: age (from birth_year),
     zip_code, gender, department. Sensitive attribute: gpa (left untouched).
  2. Generalization hierarchy per quasi-identifier, e.g.
       age: exact -> 5-year band -> 10-year band -> 20-year band -> *
       zip: full -> 4-digit prefix -> 3-digit prefix -> 1-digit prefix -> *
  3. Bottom-up full-domain generalization: climb one level at a time until
     every equivalence class has >= k rows; suppress leftover outlier rows.
  4. Report the Discernibility Metric: DM = sum(class size^2) + total_rows * suppressed_rows.
  5. verify_k() must pass before the CSV is written.

TODO(privacy):
  - generalize(): climb the hierarchies until k is reached -> age_range, zip_prefix
  - suppress(): drop rows whose QI group has fewer than k members
  - verify_k(): every QI group has size >= k
  - discernibility_metric(): print it after each level (as in Lab 8)
  - write CSV with columns matching app.models.AnonymizedRecord
"""
import argparse

import pandas as pd

QUASI_IDENTIFIERS = ["age_range", "gender", "zip_prefix", "department"]
DIRECT_IDENTIFIERS = ["full_name", "student_number", "national_id", "national_id_enc"]


def generalize(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def suppress(df: pd.DataFrame, k: int) -> pd.DataFrame:
    raise NotImplementedError


def verify_k(df: pd.DataFrame, k: int) -> bool:
    raise NotImplementedError


def discernibility_metric(df: pd.DataFrame, total_rows: int, suppressed: int) -> int:
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="anonymization/output/anonymised.csv")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    df = pd.read_csv(args.input).drop(columns=DIRECT_IDENTIFIERS, errors="ignore")
    out = suppress(generalize(df), args.k)
    assert verify_k(out, args.k), "k-anonymity check failed"
    out.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()

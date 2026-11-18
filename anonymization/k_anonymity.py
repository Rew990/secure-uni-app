"""k-anonymity pipeline (owner: Privacy & DevOps).

Usage:
    python -m anonymization.k_anonymity --k 3

Method from Week 3 (k-anonymity) and Lab 8 (worked example):
  1. Classify columns: direct identifiers removed, quasi-identifiers
     generalized/suppressed, sensitive attribute (gpa) untouched.
  2. A generalization hierarchy ("ladder") per quasi-identifier.
  3. Bottom-up full-domain search: climb one rung at a time until every
     equivalence class has >= k rows, suppressing a few outlier rows if allowed.
  4. Discernibility Metric after every level.
  5. verify_k() must pass before the CSV is written.
  6. Report what k does not protect: l-diversity, naive confidence,
     t-closeness, homogeneity (Lab 8, Lectures 4 and 5).
"""
import argparse
from datetime import date
from pathlib import Path

import pandas as pd

# ---------- Step 1: classify the columns ----------
DIRECT_IDENTIFIERS = ["full_name", "student_number", "national_id_enc"]   # removed
QUASI_IDENTIFIERS = ["age", "zip_code", "gender", "department"]          # generalized
SENSITIVE = "gpa"                                                         # untouched
# Which ladders to climb, in turn. Department stays exact (researchers need it);
# add "department" here if k can't be reached without it.
CLIMB_ORDER = ["age", "zip_code", "gender"]

OUTPUT = Path("anonymization/output/anonymised.csv")

# ---------- Step 3: generalization hierarchies ----------
# Each ladder is a list of rungs. Rung 0 = the exact value, the last rung = "*".
AGE_LADDER = [None, 5, 10, 20, "*"]          # exact -> 5-year -> 10-year -> 20-year band -> *
ZIP_LADDER = [None, 4, 3, 1, "*"]            # full -> 4-digit -> 3-digit -> 1-digit prefix -> *
VALUE_LADDER = [None, "*"]                   # gender, department: value -> *


def generalize_age(age: int, rung) -> str:
    if rung is None:
        return str(age)
    if rung == "*":
        return "*"
    if isinstance(rung, list):               # custom band edges, e.g. Lab 8's [20, 30, 40, 60]
        for lo, hi in zip(rung, rung[1:]):
            if lo <= age < hi:
                return f"{lo}-{hi - 1}"
        return "*"
    lo = age // rung * rung                  # 34 with 5-year bands -> 30
    return f"{lo}-{lo + rung - 1}"           # "30-34"


def generalize_zip(zip_code: str, rung) -> str:
    zip_code = str(zip_code)
    if rung is None:
        return zip_code
    if rung == "*":
        return "*"
    return zip_code[:rung] + "*" * (len(zip_code) - rung)   # 47602 at 3 -> "476**"


def generalize_value(value: str, rung) -> str:
    return str(value) if rung is None else "*"


LADDERS = {
    "age": (AGE_LADDER, generalize_age),
    "zip_code": (ZIP_LADDER, generalize_zip),
    "gender": (VALUE_LADDER, generalize_value),
    "department": (VALUE_LADDER, generalize_value),
}


def apply_levels(df: pd.DataFrame, levels: dict, ladders: dict = LADDERS) -> pd.DataFrame:
    """Full-domain generalization: every row of a column moves to the same rung."""
    out = df.copy()
    for col, level in levels.items():
        ladder, fn = ladders[col]
        out[col] = df[col].map(lambda v: fn(v, ladder[level]))
    return out


# ---------- Step 4 and 6: classes, k, DM ----------
def class_sizes(df: pd.DataFrame, qis: list) -> pd.Series:
    """Size of every equivalence class (rows with identical quasi-identifiers)."""
    return df.groupby(qis).size()


def discernibility_metric(sizes: pd.Series, total_rows: int, suppressed: int) -> int:
    """DM = sum(class size^2) + total_rows * suppressed_rows  (Week 3)."""
    return int((sizes ** 2).sum()) + total_rows * suppressed


def verify_k(df: pd.DataFrame, qis: list, k: int) -> bool:
    """Every equivalence class has at least k rows."""
    return len(df) > 0 and int(class_sizes(df, qis).min()) >= k


# ---------- Step 4 and 5: bottom-up search with suppression ----------
def anonymize(df: pd.DataFrame, k: int, qis: list = QUASI_IDENTIFIERS, ladders: dict = LADDERS,
              order: list | None = None, max_suppress: int = 0, verbose: bool = True):
    """Climb one rung at a time (in `order`, round robin) until k is reached.

    At each level, rows in classes smaller than k may be suppressed instead, if there
    are at most `max_suppress` of them. Returns (table, levels, history).
    """
    order = order or qis
    levels = {q: 0 for q in qis}
    total = len(df)
    history = []
    step = 0          # position in the climb order
    while True:
        table = apply_levels(df, levels, ladders)
        sizes = class_sizes(table, qis)
        small = sizes[sizes < k]
        to_drop = int(small.sum())
        dm = discernibility_metric(sizes, total, 0)
        history.append({"levels": dict(levels), "min_class": int(sizes.min()), "dm": dm})
        if verbose:
            print(f"level {len(history) - 1}: {levels}  smallest class = {sizes.min()}  DM = {dm}")

        if to_drop == 0:
            return table, levels, history
        if to_drop <= max_suppress:
            # Suppression (Week 3): drop the outlier rows instead of blurring everyone
            keys = set(small.index)
            keep = ~table.set_index(qis).index.isin(keys)
            kept = table[keep]
            dm_s = discernibility_metric(class_sizes(kept, qis), total, to_drop)
            history[-1]["suppressed"] = to_drop
            history[-1]["dm"] = dm_s
            if verbose:
                print(f"         suppress {to_drop} row(s) -> DM = {dm_s}")
            return kept, levels, history

        # climb one rung on the next attribute that can still climb
        for _ in range(len(order)):
            col = order[step % len(order)]
            step += 1
            if levels[col] < len(ladders[col][0]) - 1:
                levels[col] += 1
                break
        else:
            raise RuntimeError("Every ladder in the climb order is at the top and k is still not reached")


# ---------- Step 8: what k does not protect ----------
def gpa_band(gpa: float) -> str:
    gpa = float(gpa)
    if gpa < 2:
        return "0-2"
    if gpa < 3:
        return "2-3"
    return "3-4"


GPA_ORDER = ["0-2", "2-3", "3-4"]


def tvd(p: pd.Series, q: pd.Series) -> float:
    """Total variation distance, Lab 8: (1/2) * sum |P - Q|."""
    cats = p.index.union(q.index)
    return 0.5 * float(sum(abs(p.get(c, 0) - q.get(c, 0)) for c in cats))


def emd_ordered(p: pd.Series, q: pd.Series, order: list) -> float:
    """Earth Mover's Distance for ordered values, Lecture 5: sum |CDF_P - CDF_Q| over every cut but the last."""
    cp = cq = total = 0.0
    for c in order[:-1]:
        cp += p.get(c, 0)
        cq += q.get(c, 0)
        total += abs(cp - cq)
    return total


def privacy_report(table: pd.DataFrame, qis: list, sensitive: str, order: list | None = None) -> pd.DataFrame:
    """One row per class: size, distinct l, naive confidence, t-closeness, homogeneous?"""
    overall = table[sensitive].value_counts(normalize=True)
    rows = []
    for key, group in table.groupby(qis):
        dist = group[sensitive].value_counts(normalize=True)
        rows.append({
            "class": key,
            "size": len(group),
            "l_distinct": group[sensitive].nunique(),
            "naive_confidence": round(float(dist.max()), 3),
            "t_tvd": round(tvd(dist, overall), 3),
            "t_emd": round(emd_ordered(dist, overall, order), 3) if order else None,
            "homogeneous": group[sensitive].nunique() == 1,
        })
    return pd.DataFrame(rows)


# ---------- Step 2: read the data ----------
def load_students(year: int) -> pd.DataFrame:
    from app.database import get_engine          # Rawan's engine, same SQLite file as the app
    df = pd.read_sql("SELECT birth_year, gender, zip_code, department, gpa FROM students", get_engine())
    df["age"] = year - df["birth_year"]
    return df.drop(columns=["birth_year"])


def main() -> None:
    parser = argparse.ArgumentParser(description="k-anonymise the students table")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--max-suppress", type=int, default=2, help="outlier rows that may be dropped")
    parser.add_argument("--year", type=int, default=date.today().year, help="year used to turn birth_year into age")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()

    df = load_students(args.year)
    print(f"{len(df)} rows read, k = {args.k}")
    table, levels, history = anonymize(df, args.k, order=CLIMB_ORDER, max_suppress=args.max_suppress)

    # Step 7: verify, then write
    assert verify_k(table, QUASI_IDENTIFIERS, args.k), "k-anonymity check failed, nothing written"

    table = table.assign(gpa_band=table[SENSITIVE].map(gpa_band))
    report = privacy_report(table, QUASI_IDENTIFIERS, "gpa_band", GPA_ORDER)
    print("\nPer-class report (GPA grouped into bands 0-2, 2-3, 3-4):")
    print(report.to_string(index=False))
    print(f"\nTable is {args.k}-anonymous and {report['l_distinct'].min()}-diverse (distinct).")
    print(f"Highest naive confidence: {report['naive_confidence'].max():.0%}")
    print(f"t-closeness (max EMD): {report['t_emd'].max():.3f}")
    for _, r in report[report["homogeneous"]].iterrows():
        print(f"WARNING homogeneity attack: every row in class {r['class']} has GPA band "
              f"{table.set_index(QUASI_IDENTIFIERS).loc[r['class'], 'gpa_band'].iloc[0]}")

    out = table.rename(columns={"age": "age_range", "zip_code": "zip_prefix"})
    out = out[["age_range", "gender", "zip_prefix", "department", "gpa"]]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"\nWrote {len(out)} rows to {args.output}")


if __name__ == "__main__":
    main()

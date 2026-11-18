"""Checks the k-anonymity functions against Lab 8's worked example (9 rows, k = 3)."""
import pandas as pd
import pytest

from anonymization.k_anonymity import (
    anonymize, generalize_age, generalize_zip, privacy_report, verify_k, discernibility_metric,
    class_sizes,
)

LAB8 = pd.DataFrame({
    "age": [22, 27, 29, 30, 32, 36, 43, 47, 57],
    "zip_code": ["47602", "47678", "47677", "47605", "47607", "47673", "47905", "47906", "47909"],
    "gender": ["M", "F", "M", "F", "M", "F", "M", "F", "M"],
    "disease": ["Heart Disease", "Heart Disease", "Flu", "Heart Disease", "Cancer",
                "Cancer", "Flu", "Cancer", "Heart Disease"],
})
QIS = ["age", "zip_code", "gender"]
# Lab 8's ladders: age into 20-30 / 30-40 / 40-60, ZIP to 3 digits, then gender suppressed
LAB8_LADDERS = {
    "age": ([None, [20, 30, 40, 60]], generalize_age),
    "zip_code": ([None, 3], generalize_zip),
    "gender": ([None, "*"], lambda v, r: v if r is None else "*"),
}


@pytest.fixture(scope="module")
def result():
    return anonymize(LAB8, k=3, qis=QIS, ladders=LAB8_LADDERS, verbose=False)


def test_ladders():
    assert generalize_age(34, 5) == "30-34"
    assert generalize_age(34, 10) == "30-39"
    assert generalize_age(34, 20) == "20-39"
    assert generalize_zip("47602", 3) == "476**"


def test_raw_table_is_only_1_anonymous():
    assert not verify_k(LAB8, QIS, 2)


def test_dm_matches_lab8(result):
    _, _, history = result
    assert [h["dm"] for h in history] == [9, 9, 15, 27]


def test_reaches_k3(result):
    table, _, _ = result
    assert verify_k(table, QIS, 3)
    assert sorted(class_sizes(table, QIS)) == [3, 3, 3]


def test_l_diversity_and_naive_confidence(result):
    table, _, _ = result
    report = privacy_report(table, QIS, "disease")
    assert report["l_distinct"].min() == 2                     # Lab 8: min(2, 2, 3) = 2
    assert sorted(report["naive_confidence"]) == [0.333, 0.667, 0.667]
    assert not report["homogeneous"].any()                     # Lab 8: no homogeneity attack


def test_t_closeness(result):
    table, _, _ = result
    report = privacy_report(table, QIS, "disease")
    assert report["t_tvd"].max() == pytest.approx(0.333, abs=0.001)   # Lab 8: Dmax = 0.3335 > T = 0.25


def test_suppression_costs_n_per_row():
    sizes = pd.Series([4])
    assert discernibility_metric(sizes, total_rows=5, suppressed=1) == 21   # Week 3, R5 example


def test_import_is_admin_only(client, headers, tmp_path, monkeypatch):
    from app.routers import anonymized
    csv_file = tmp_path / "anonymised.csv"
    csv_file.write_text("age_range,gender,zip_prefix,department,gpa\n20-29,*,115**,CS,3.4\n")
    monkeypatch.setattr(anonymized, "CSV_PATH", csv_file)

    assert client.post("/anonymized/import", headers=headers["instructor"]).status_code == 403
    assert client.post("/anonymized/import", headers=headers["student"]).status_code == 403
    r = client.post("/anonymized/import", headers=headers["admin"])
    assert r.status_code == 200 and r.json() == {"imported": 1}
    rows = client.get("/anonymized", headers=headers["instructor"]).json()
    assert rows == [{"age_range": "20-29", "gender": "*", "zip_prefix": "115**", "department": "CS", "gpa": 3.4}]

import json
import unittest
from decimal import Decimal
from pathlib import Path

from comex_pipeline.transform import transform_response, validate_rows

FIXTURE = Path(__file__).parent / "fixtures" / "comexstat_sample.json"


def sample_payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TransformTests(unittest.TestCase):
    def test_transforms_real_api_field_names_and_decimal_metrics(self):
        rows = transform_response(sample_payload(), "2022-01", "2022-02")

        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0].section_code, "V")
        self.assertEqual(rows[0].section_name, "Produtos minerais")
        self.assertEqual(rows[0].fob_usd, Decimal("5219955882"))
        self.assertEqual(rows[0].net_kg, Decimal("31603110281"))
        validate_rows(rows, "2022-01", "2022-02")

    def test_rejects_record_missing_required_field(self):
        payload = sample_payload()
        del payload["data"]["list"][0]["metricKG"]

        with self.assertRaisesRegex(ValueError, "campos obrigatórios"):
            transform_response(payload, "2022-01", "2022-02")

    def test_rejects_negative_metric(self):
        payload = sample_payload()
        payload["data"]["list"][0]["metricFOB"] = "-1"

        with self.assertRaisesRegex(ValueError, "não negativo"):
            transform_response(payload, "2022-01", "2022-02")

    def test_rejects_duplicate_month_section_key(self):
        payload = sample_payload()
        payload["data"]["list"].append(payload["data"]["list"][0].copy())
        rows = transform_response(payload, "2022-01", "2022-02")

        with self.assertRaisesRegex(ValueError, "duplicada"):
            validate_rows(rows, "2022-01", "2022-02")

    def test_rejects_missing_requested_month(self):
        payload = sample_payload()
        payload["data"]["list"] = [
            row for row in payload["data"]["list"] if row["monthNumber"] == "01"
        ]
        rows = transform_response(payload, "2022-01", "2022-02")

        with self.assertRaisesRegex(ValueError, "meses esperados"):
            validate_rows(rows, "2022-01", "2022-02")

    def test_rejects_out_of_range_month(self):
        payload = sample_payload()

        with self.assertRaisesRegex(ValueError, "fora do intervalo"):
            transform_response(payload, "2022-02", "2022-02")

    def test_rejects_inconsistent_section_description(self):
        payload = sample_payload()
        payload["data"]["list"][2]["section"] = "Nome divergente"
        rows = transform_response(payload, "2022-01", "2022-02")

        with self.assertRaisesRegex(ValueError, "Descrição divergente"):
            validate_rows(rows, "2022-01", "2022-02")


if __name__ == "__main__":
    unittest.main()

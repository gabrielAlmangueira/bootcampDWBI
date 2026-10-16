import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from comex_pipeline.extract import (
    build_query,
    extract_exports,
    fetch_source_update,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.headers = {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class ExtractTests(unittest.TestCase):
    def test_query_is_limited_to_monthly_section_exports(self):
        query = build_query("2022-01", "2025-12")

        self.assertEqual(query["flow"], "export")
        self.assertTrue(query["monthDetail"])
        self.assertEqual(query["details"], ["section"])
        self.assertEqual(query["metrics"], ["metricFOB", "metricKG"])
        self.assertEqual(query["period"], {"from": "2022-01", "to": "2025-12"})

    def test_extract_archives_response_and_query_metadata(self):
        response = FakeResponse(
            {"success": True, "data": {"list": [{"year": "2022"}]}}
        )
        session = FakeSession([response])
        with tempfile.TemporaryDirectory() as temporary_directory:
            raw_path = extract_exports(
                "https://example.test/general",
                "2022-01",
                "2022-12",
                Path(temporary_directory),
                "2026-10-06",
                session=session,
            )

            self.assertEqual(json.loads(raw_path.read_text())["success"], True)
            metadata = json.loads(raw_path.with_suffix(".metadata.json").read_text())
            self.assertEqual(metadata["source_updated"], "2026-10-06")
            self.assertEqual(metadata["row_count"], 1)
            self.assertEqual(session.calls[0][0], "POST")
            self.assertEqual(session.calls[0][2]["json"]["details"], ["section"])

    def test_fetch_update_rejects_invalid_api_response(self):
        session = FakeSession([FakeResponse({"success": False, "data": {}})])

        with self.assertRaisesRegex(ValueError, "Resposta inválida"):
            fetch_source_update("https://example.test/updated", session=session)

    def test_retries_transient_server_error(self):
        session = FakeSession(
            [
                FakeResponse({"error": True}, status_code=503),
                FakeResponse({"success": True, "data": {"updated": "2026-10-06"}}),
            ]
        )
        with patch("comex_pipeline.extract.time.sleep"):
            result = fetch_source_update(
                "https://example.test/updated", session=session
            )

        self.assertEqual(result, "2026-10-06")
        self.assertEqual(len(session.calls), 2)

    def test_rate_limit_waits_at_least_ten_seconds(self):
        session = FakeSession(
            [
                FakeResponse({"error": True}, status_code=429),
                FakeResponse({"success": True, "data": {"updated": "2026-10-06"}}),
            ]
        )
        with patch("comex_pipeline.extract.time.sleep") as sleep:
            fetch_source_update("https://example.test/updated", session=session)

        sleep.assert_called_once_with(10)


if __name__ == "__main__":
    unittest.main()

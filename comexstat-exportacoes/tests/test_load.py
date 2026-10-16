import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from comex_pipeline.load import load_rows
from comex_pipeline.transform import ExportFactRow


class FakeCursor:
    def __init__(self):
        self.statements = []
        self.next_id = 1

    def execute(self, statement, parameters=None):
        self.statements.append((statement, parameters))

    def fetchone(self):
        self.next_id += 1
        return (self.next_id,)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def cursor(self):
        return self.fake_cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class LoadTests(unittest.TestCase):
    def test_load_applies_schema_upserts_dimensions_fact_and_audit(self):
        row = ExportFactRow(
            month_start=date(2022, 1, 1),
            year=2022,
            month=1,
            section_code="V",
            section_name="Produtos minerais",
            fob_usd=Decimal("1000"),
            net_kg=Decimal("25"),
        )
        cursor = FakeCursor()
        connection = FakeConnection(cursor)
        fake_psycopg = SimpleNamespace(connect=lambda dsn: connection)
        with tempfile.TemporaryDirectory() as temporary_directory:
            schema = Path(temporary_directory) / "schema.sql"
            schema.write_text("CREATE TABLE test_table (id integer);", encoding="utf-8")
            with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
                loaded = load_rows(
                    [row],
                    "postgresql://example",
                    schema,
                    "2022-01",
                    "2022-12",
                    "2026-10-06",
                    Path("sample.json"),
                )

        sql = "\n".join(statement for statement, _ in cursor.statements)
        self.assertEqual(loaded, 1)
        self.assertIn("CREATE TABLE test_table", sql)
        self.assertEqual(sql.count("ON CONFLICT"), 365 + 2)
        self.assertIn("INSERT INTO etl_execucao", sql)
        audit_parameters = cursor.statements[-1][1]
        self.assertEqual(audit_parameters[1], date(2022, 1, 1))
        self.assertEqual(audit_parameters[2], date(2022, 12, 31))
        self.assertEqual(audit_parameters[4], 1)

    def test_load_rejects_empty_batch_before_connecting(self):
        fake_psycopg = SimpleNamespace(connect=lambda dsn: self.fail("unexpected DB connection"))

        with patch.dict("sys.modules", {"psycopg": fake_psycopg}):
            with self.assertRaisesRegex(ValueError, "carga vazia"):
                load_rows(
                    [],
                    "postgresql://example",
                    Path("unused.sql"),
                    "2022-01",
                    "2022-12",
                    "2026-10-06",
                    Path("unused.json"),
                )

    def test_calendar_dates_are_contiguous_and_cover_full_months(self):
        from comex_pipeline.load import _calendar_dates

        dates = _calendar_dates("2024-02", "2024-02")

        self.assertEqual(len(dates), 29)
        self.assertEqual(dates[0], date(2024, 2, 1))
        self.assertEqual(dates[-1], date(2024, 2, 29))
        self.assertEqual(
            dates,
            [date(2024, 2, day) for day in range(1, 30)],
        )


if __name__ == "__main__":
    unittest.main()

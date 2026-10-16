from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .config import Settings
from .extract import (
    extract_exports,
    fetch_source_update,
    read_raw_response,
)
from .load import load_rows
from .transform import transform_response, validate_rows

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "001_create_dw.sql"


def _metadata_for(raw_path: Path) -> dict:
    metadata_path = raw_path.with_suffix(".metadata.json")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadados da extração não encontrados: {metadata_path}")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def run_pipeline(settings: Settings) -> Path:
    if not settings.pg_dsn:
        raise ValueError("PG_DSN é obrigatório para executar a carga.")
    source_updated = fetch_source_update(settings.updated_url)
    raw_path = extract_exports(
        settings.api_url,
        settings.period_start,
        settings.period_end,
        RAW_DIR,
        source_updated,
    )
    payload = read_raw_response(raw_path)
    rows = transform_response(payload, settings.period_start, settings.period_end)
    validate_rows(rows, settings.period_start, settings.period_end)
    count = load_rows(
        rows,
        settings.pg_dsn,
        SCHEMA_PATH,
        settings.period_start,
        settings.period_end,
        source_updated,
        raw_path,
    )
    logging.info("Pipeline concluído: %s linhas carregadas no PostgreSQL.", count)
    return raw_path


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    parser = argparse.ArgumentParser(description="Pipeline ComexStat para PostgreSQL.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="Executa extração, transformação, validação e carga.")
    commands.add_parser("extract", help="Extrai e arquiva o JSON bruto.")
    load_parser = commands.add_parser("load", help="Carrega um JSON bruto já extraído.")
    load_parser.add_argument("--raw-file", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "run":
        settings = Settings.from_environment(require_database=True)
        run_pipeline(settings)
        return

    settings = Settings.from_environment(
        require_database=args.command == "load"
    )
    if args.command == "extract":
        source_updated = fetch_source_update(settings.updated_url)
        extract_exports(
            settings.api_url,
            settings.period_start,
            settings.period_end,
            RAW_DIR,
            source_updated,
        )
        return

    raw_path = args.raw_file.resolve()
    metadata = _metadata_for(raw_path)
    period = metadata.get("query", {}).get("period", {})
    period_start = period.get("from")
    period_end = period.get("to")
    if not period_start or not period_end:
        raise ValueError("Metadados não contêm o período original da extração.")
    rows = transform_response(
        read_raw_response(raw_path),
        period_start,
        period_end,
    )
    validate_rows(rows, period_start, period_end)
    load_rows(
        rows,
        settings.pg_dsn,
        SCHEMA_PATH,
        period_start,
        period_end,
        metadata["source_updated"],
        raw_path,
    )


if __name__ == "__main__":
    main()

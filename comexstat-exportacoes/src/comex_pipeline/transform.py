from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class ExportFactRow:
    month_start: date
    year: int
    month: int
    section_code: str
    section_name: str
    fob_usd: Decimal
    net_kg: Decimal


REQUIRED_FIELDS = {
    "year",
    "monthNumber",
    "coNcmSecrom",
    "section",
    "metricFOB",
    "metricKG",
}


def _as_decimal(value: Any, field: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Campo {field} não é numérico: {value!r}") from None
    if not number.is_finite() or number < 0:
        raise ValueError(f"Campo {field} precisa ser finito e não negativo: {value!r}")
    return number


def transform_response(
    payload: dict[str, Any], period_start: str, period_end: str
) -> list[ExportFactRow]:
    if not payload.get("success"):
        raise ValueError("A resposta do ComexStat indica falha.")
    records = payload.get("data", {}).get("list")
    if not isinstance(records, list) or not records:
        raise ValueError("Resposta do ComexStat sem lista de registros.")

    transformed: list[ExportFactRow] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Registro {index} não é um objeto.")
        missing = REQUIRED_FIELDS.difference(record)
        if missing:
            raise ValueError(
                f"Registro {index} não contém campos obrigatórios: {sorted(missing)}"
            )
        try:
            year = int(record["year"])
            month = int(record["monthNumber"])
            month_start = date(year, month, 1)
        except (TypeError, ValueError):
            raise ValueError(f"Período inválido no registro {index}.") from None
        month_key = f"{year:04d}-{month:02d}"
        if month_key < period_start or month_key > period_end:
            raise ValueError(
                f"Registro {index} fora do intervalo {period_start} a {period_end}."
            )
        section_code = str(record["coNcmSecrom"]).strip()
        section_name = str(record["section"]).strip()
        if not section_code or not section_name:
            raise ValueError(f"Registro {index} sem código ou nome de seção.")
        transformed.append(
            ExportFactRow(
                month_start=month_start,
                year=year,
                month=month,
                section_code=section_code,
                section_name=section_name,
                fob_usd=_as_decimal(record["metricFOB"], "metricFOB"),
                net_kg=_as_decimal(record["metricKG"], "metricKG"),
            )
        )
    return transformed


def validate_rows(
    rows: list[ExportFactRow], period_start: str, period_end: str
) -> None:
    if not rows:
        raise ValueError("Não há linhas transformadas para validar.")

    seen_keys: set[tuple[date, str]] = set()
    section_names: dict[str, str] = {}
    found_months: set[str] = set()
    for row in rows:
        key = (row.month_start, row.section_code)
        if key in seen_keys:
            raise ValueError(
                f"Chave duplicada na granularidade mensal-seção: {key}."
            )
        seen_keys.add(key)
        existing_name = section_names.setdefault(row.section_code, row.section_name)
        if existing_name != row.section_name:
            raise ValueError(
                f"Descrição divergente para seção {row.section_code!r}: "
                f"{existing_name!r} e {row.section_name!r}."
            )
        found_months.add(row.month_start.strftime("%Y-%m"))

    expected_months: set[str] = set()
    year, month = map(int, period_start.split("-"))
    end_year, end_month = map(int, period_end.split("-"))
    while (year, month) <= (end_year, end_month):
        expected_months.add(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    missing_months = expected_months.difference(found_months)
    if missing_months:
        raise ValueError(
            f"Não há registros para os meses esperados: {sorted(missing_months)}."
        )

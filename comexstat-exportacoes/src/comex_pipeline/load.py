from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from .transform import ExportFactRow

MONTH_NAMES_PT = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def _calendar_dates(period_start: str, period_end: str) -> list[date]:
    start = date.fromisoformat(f"{period_start}-01")
    end_year, end_month = map(int, period_end.split("-"))
    if end_month == 12:
        end = date(end_year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(end_year, end_month + 1, 1) - timedelta(days=1)
    dates: list[date] = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def _apply_schema(cursor, schema_path: Path) -> None:
    statements = [
        statement.strip()
        for statement in schema_path.read_text(encoding="utf-8").split(";")
        if statement.strip()
    ]
    for statement in statements:
        cursor.execute(statement)


def load_rows(
    rows: list[ExportFactRow],
    dsn: str,
    schema_path: Path,
    period_start: str,
    period_end: str,
    source_updated: str,
    raw_file: Path,
) -> int:
    import psycopg

    if not rows:
        raise ValueError("Recusando carga vazia no DW.")
    source_updated_date = date.fromisoformat(source_updated)
    calendar_dates = _calendar_dates(period_start, period_end)
    period_start_date = calendar_dates[0]
    period_end_date = calendar_dates[-1]

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            _apply_schema(cursor, schema_path)
            for calendar_date in calendar_dates:
                cursor.execute(
                    """
                    INSERT INTO dim_tempo
                        (data_calendario, ano, numero_mes, nome_mes, trimestre,
                         numero_dia, dia_semana_numero)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (data_calendario) DO UPDATE SET
                        ano = EXCLUDED.ano,
                        numero_mes = EXCLUDED.numero_mes,
                        nome_mes = EXCLUDED.nome_mes,
                        trimestre = EXCLUDED.trimestre,
                        numero_dia = EXCLUDED.numero_dia,
                        dia_semana_numero = EXCLUDED.dia_semana_numero
                    """,
                    (
                        calendar_date,
                        calendar_date.year,
                        calendar_date.month,
                        MONTH_NAMES_PT[calendar_date.month - 1],
                        (calendar_date.month - 1) // 3 + 1,
                        calendar_date.day,
                        calendar_date.isoweekday(),
                    ),
                )
            for row in rows:
                cursor.execute(
                    "SELECT tempo_id FROM dim_tempo WHERE data_calendario = %s",
                    (row.month_start,),
                )
                tempo_result = cursor.fetchone()
                if tempo_result is None:
                    raise RuntimeError(
                        f"Data de calendário não carregada: {row.month_start}."
                    )
                tempo_id = tempo_result[0]
                cursor.execute(
                    """
                    INSERT INTO dim_secao_produto (codigo_secao, nome_secao)
                    VALUES (%s, %s)
                    ON CONFLICT (codigo_secao) DO UPDATE SET
                        nome_secao = EXCLUDED.nome_secao
                    RETURNING secao_id
                    """,
                    (row.section_code, row.section_name),
                )
                secao_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO fato_exportacao_mensal
                        (tempo_id, secao_id, valor_fob_usd, quilograma_liquido)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (tempo_id, secao_id) DO UPDATE SET
                        valor_fob_usd = EXCLUDED.valor_fob_usd,
                        quilograma_liquido = EXCLUDED.quilograma_liquido
                    """,
                    (tempo_id, secao_id, row.fob_usd, row.net_kg),
                )
            cursor.execute(
                """
                INSERT INTO etl_execucao
                    (fonte_atualizada_em, periodo_inicio, periodo_fim,
                     arquivo_bruto, linhas_carregadas)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    source_updated_date,
                    period_start_date,
                    period_end_date,
                    str(raw_file),
                    len(rows),
                ),
            )
    return len(rows)

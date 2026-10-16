from __future__ import annotations

import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv


_PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@dataclass(frozen=True)
class Settings:
    api_url: str
    updated_url: str
    period_start: str
    period_end: str
    pg_dsn: str | None

    @classmethod
    def from_environment(cls, require_database: bool = False) -> "Settings":
        load_dotenv()
        period_start = os.getenv("COMEXSTAT_START", "2022-01")
        period_end = os.getenv("COMEXSTAT_END", "2025-12")
        if not _PERIOD_PATTERN.fullmatch(period_start):
            raise ValueError("COMEXSTAT_START deve estar no formato YYYY-MM.")
        if not _PERIOD_PATTERN.fullmatch(period_end):
            raise ValueError("COMEXSTAT_END deve estar no formato YYYY-MM.")
        if period_start > period_end:
            raise ValueError("COMEXSTAT_START deve ser anterior ou igual a COMEXSTAT_END.")

        pg_dsn = os.getenv("PG_DSN")
        if require_database and not pg_dsn:
            raise ValueError("Defina PG_DSN no ambiente para carregar no PostgreSQL.")

        return cls(
            api_url=os.getenv(
                "COMEXSTAT_API_URL", "https://api-comexstat.mdic.gov.br/general"
            ),
            updated_url=os.getenv(
                "COMEXSTAT_UPDATED_URL",
                "https://api-comexstat.mdic.gov.br/general/dates/updated",
            ),
            period_start=period_start,
            period_end=period_end,
            pg_dsn=pg_dsn,
        )

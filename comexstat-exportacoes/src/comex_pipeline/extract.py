from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _request_with_retries(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: float,
    json_body: dict[str, Any] | None = None,
    attempts: int = 3,
) -> requests.Response:
    for attempt in range(attempts):
        try:
            response = session.request(
                method, url, json=json_body, timeout=timeout
            )
        except (requests.ConnectionError, requests.Timeout):
            if attempt == attempts - 1:
                raise
            LOGGER.warning("Falha transitória de conexão; tentativa %s/%s", attempt + 2, attempts)
            time.sleep(2**attempt)
            continue

        if response.status_code in RETRYABLE_STATUS_CODES and attempt < attempts - 1:
            retry_delay = 2**attempt
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        retry_delay = max(retry_delay, float(retry_after))
                    except ValueError:
                        LOGGER.warning("Ignorando Retry-After inválido: %r", retry_after)
                retry_delay = max(retry_delay, 10)
            LOGGER.warning(
                "API respondeu HTTP %s; aguardando %s s, tentativa %s/%s",
                response.status_code,
                retry_delay,
                attempt + 2,
                attempts,
            )
            time.sleep(retry_delay)
            continue
        response.raise_for_status()
        return response

    raise RuntimeError("A requisição terminou sem resposta.")


def fetch_source_update(
    updated_url: str, session: requests.Session | None = None
) -> str:
    client = session or requests.Session()
    response = _request_with_retries(client, "GET", updated_url, timeout=30)
    payload = response.json()
    if not payload.get("success") or not payload.get("data", {}).get("updated"):
        raise ValueError("Resposta inválida ao consultar a atualização do ComexStat.")
    return str(payload["data"]["updated"])


def build_query(period_start: str, period_end: str) -> dict[str, Any]:
    return {
        "flow": "export",
        "monthDetail": True,
        "period": {"from": period_start, "to": period_end},
        "filters": [],
        "details": ["section"],
        "metrics": ["metricFOB", "metricKG"],
    }


def extract_exports(
    api_url: str,
    period_start: str,
    period_end: str,
    raw_dir: Path,
    source_updated: str,
    session: requests.Session | None = None,
) -> Path:
    client = session or requests.Session()
    query = build_query(period_start, period_end)
    response = _request_with_retries(
        client, "POST", api_url, json_body=query, timeout=60
    )
    payload = response.json()
    if not payload.get("success") or not isinstance(
        payload.get("data", {}).get("list"), list
    ):
        raise ValueError("Resposta inválida ao consultar dados do ComexStat.")
    if not payload["data"]["list"]:
        raise ValueError("A API retornou zero registros para o período solicitado.")

    raw_dir.mkdir(parents=True, exist_ok=True)
    extracted_at = datetime.now(timezone.utc)
    file_stamp = extracted_at.strftime("%Y%m%dT%H%M%SZ")
    raw_path = raw_dir / f"comexstat_exports_{period_start}_{period_end}_{file_stamp}.json"
    metadata_path = raw_path.with_suffix(".metadata.json")
    raw_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata = {
        "source": "ComexStat / MDIC",
        "endpoint": api_url,
        "query": query,
        "source_updated": source_updated,
        "extracted_at": extracted_at.isoformat(),
        "row_count": len(payload["data"]["list"]),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    LOGGER.info("Extraídos %s registros para %s", metadata["row_count"], raw_path)
    return raw_path


def read_raw_response(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as raw_file:
        payload = json.load(raw_file)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON bruto precisa conter um objeto: {path}")
    return payload

from __future__ import annotations

import csv
import io
import json
from typing import Any

from fastapi import APIRouter, Query, Response

from app.repositories.trading_repository import trading_repository

router = APIRouter()


def _normalise(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if value is None:
        return ''
    return str(value)


def _to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ''
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _normalise(row.get(key)) for key in fieldnames})
    return buffer.getvalue()


@router.get('/csv/{dataset}')
def export_csv(dataset: str, limit: int = Query(default=5000, ge=1, le=50000)):
    rows = trading_repository.export_table_rows(dataset, limit=limit) if trading_repository.available else []
    csv_text = _to_csv(rows)
    return Response(
        content=csv_text,
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="trading-cockpit-{dataset}.csv"'},
    )


@router.get('/datasets')
def export_datasets():
    return {
        'datasets': ['orders', 'signals', 'predictions', 'decision_audits', 'backtests', 'data_quality'],
        'format': 'csv',
        'endpoint_template': '/api/export/csv/{dataset}?limit=5000',
    }

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.validation_monitoring_service import validation_monitoring_service

router = APIRouter()


@router.get('/validation-gates')
def validation_gates(
    strategy_name: str | None = None,
    decision_mode: str | None = None,
):
    return validation_monitoring_service.validation_gates(strategy_name=strategy_name, decision_mode=decision_mode)


@router.get('/daily-report')
def daily_report(lookback_hours: int = Query(default=24, ge=1, le=24 * 30)):
    return validation_monitoring_service.daily_report(lookback_hours=lookback_hours)


@router.get('/alerts')
def alerts(
    strategy_name: str | None = None,
    decision_mode: str | None = None,
):
    return validation_monitoring_service.alerts(strategy_name=strategy_name, decision_mode=decision_mode)


@router.get('/strategy-matrix')
def strategy_matrix():
    return validation_monitoring_service.strategy_matrix()


@router.get('/system-report')
def system_report():
    return validation_monitoring_service.system_report()

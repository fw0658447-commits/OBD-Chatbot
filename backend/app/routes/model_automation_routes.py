from fastapi import APIRouter, Query

from app.schemas.model_automation_schema import ModelAutomationConfigPatch, ModelAutomationRunRequest
from app.services.model_automation_service import model_automation_service

router = APIRouter()


@router.get('/status')
def automation_status():
    return model_automation_service.status()


@router.patch('/config')
def update_automation_config(request: ModelAutomationConfigPatch):
    model_automation_service.update_config(request.model_dump(exclude_unset=True))
    return model_automation_service.status()


@router.post('/start')
def start_automation():
    return model_automation_service.start()


@router.post('/stop')
def stop_automation():
    return model_automation_service.stop()


@router.post('/cancel')
def cancel_automation_run():
    return model_automation_service.cancel_current_run()


@router.post('/run-once')
def run_automation_once(request: ModelAutomationRunRequest | None = None):
    return model_automation_service.run_once(source='manual', config_patch=(request.config_patch if request else None))


@router.post('/run-background')
def run_automation_background(request: ModelAutomationRunRequest | None = None):
    return model_automation_service.run_background(source='manual', config_patch=(request.config_patch if request else None))


@router.get('/runs')
def automation_runs(limit: int = Query(default=25, ge=1, le=100)):
    return model_automation_service.list_runs(limit=limit)

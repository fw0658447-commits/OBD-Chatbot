import time

from app.services.bot_runtime_service import bot_runtime_service
from app.services.bot_scheduler_service import bot_scheduler_service


def run_worker() -> None:
    """Optional process worker.

    The in-app scheduler can be controlled from the frontend. This worker is a
    conservative companion: it only runs when `scheduler_enabled` is true in the
    shared bot runtime config and it always stays paper-only.
    """

    while True:
        config = bot_runtime_service.get_config()
        interval_seconds = max(10, int(config.get('scheduler_interval_seconds') or 60))
        try:
            if config.get('kill_switch_active'):
                print({'event': 'worker_skip', 'reason': 'kill_switch_active'})
            elif config.get('scheduler_enabled') and config.get('bot_enabled'):
                result = bot_scheduler_service.run_once(source='worker')
                print({'event': 'worker_run_once', 'status': result.get('status'), 'results': len(result.get('results', []))})
            else:
                print({'event': 'worker_idle', 'scheduler_enabled': config.get('scheduler_enabled'), 'bot_enabled': config.get('bot_enabled')})
        except Exception as exc:
            print({'event': 'worker_error', 'error': str(exc)})
        time.sleep(interval_seconds)


if __name__ == '__main__':
    run_worker()

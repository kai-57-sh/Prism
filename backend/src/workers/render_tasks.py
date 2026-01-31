"""
RQ task definitions for long-running render jobs.
"""

import asyncio

from src.models import SessionLocal
from src.services.job_manager import JobManager
from src.services.observability import logger


def run_render_job(job_id: str, client_ip: str) -> None:
    logger.info("render_worker_start", job_id=job_id, client_ip=client_ip)
    db = SessionLocal()
    try:
        job_manager = JobManager()
        asyncio.run(
            job_manager.execute_generation_from_job(
                db=db,
                job_id=job_id,
                client_ip=client_ip,
                skip_rate_limit=True,
            )
        )
    except Exception as exc:
        logger.error("render_worker_failed", job_id=job_id, error=str(exc))
        raise
    finally:
        db.close()

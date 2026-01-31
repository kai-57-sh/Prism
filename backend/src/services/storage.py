"""
Storage Service - Database operations for Templates and Jobs
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json

from src.models.job import JobModel
from src.models.template import TemplateModel


class TemplateDB:
    """Template database operations"""

    @staticmethod
    def create_template(
        db: Session,
        template_id: Union[TemplateModel, str],
        version: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        shot_skeletons: Optional[List[Dict[str, Any]]] = None,
        negative_prompt_base: Optional[str] = None,
    ) -> TemplateModel:
        """Create a new template"""
        if isinstance(template_id, TemplateModel):
            template = template_id
            if template.negative_prompt_base is None:
                template.negative_prompt_base = ""
            if template.tags is None:
                template.tags = {}
            if template.constraints is None:
                template.constraints = {}
            if template.shot_skeletons is None:
                template.shot_skeletons = []
        else:
            template = TemplateModel(
                template_id=template_id,
                version=version or "1.0",
                tags=tags or {},
                constraints=constraints or {},
                shot_skeletons=shot_skeletons or [],
                negative_prompt_base=negative_prompt_base or "",
            )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def get_template(db: Session, template_id: str, version: str) -> Optional[TemplateModel]:
        """Get template by ID and version"""
        return (
            db.query(TemplateModel)
            .filter(TemplateModel.template_id == template_id, TemplateModel.version == version)
            .first()
        )

    @staticmethod
    def list_templates(db: Session, skip: int = 0, limit: int = 100) -> List[TemplateModel]:
        """List all templates"""
        return db.query(TemplateModel).offset(skip).limit(limit).all()

    @staticmethod
    def update_template(
        db: Session,
        template_id: str,
        version: str,
        **kwargs,
    ) -> Optional[TemplateModel]:
        """Update template fields"""
        template = TemplateDB.get_template(db, template_id, version)
        if template:
            for key, value in kwargs.items():
                setattr(template, key, value)
            template.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(template)
        return template

    @staticmethod
    def delete_template(db: Session, template_id: str, version: str) -> bool:
        """Delete a template"""
        template = TemplateDB.get_template(db, template_id, version)
        if template:
            db.delete(template)
            db.commit()
            return True
        return False


class JobDB:
    """Job database operations"""

    @staticmethod
    def create_job(
        db: Session,
        user_input_redacted: Union[JobModel, str],
        user_input_hash: Optional[str] = None,
        pii_flags: Optional[List[str]] = None,
        template_id: Optional[str] = None,
        template_version: Optional[str] = None,
        quality_mode: Optional[str] = None,
        ir: Optional[Dict[str, Any]] = None,
        shot_plan: Optional[Dict[str, Any]] = None,
        shot_requests: Optional[List[Dict[str, Any]]] = None,
        external_task_ids: Optional[List[str]] = None,
        total_duration_s: Optional[int] = None,
        resolution: Optional[str] = None,
    ) -> JobModel:
        """Create a new job"""
        if isinstance(user_input_redacted, JobModel):
            job = user_input_redacted
            if not getattr(job, "user_input_hash", None):
                job.user_input_hash = ""
            if not getattr(job, "template_id", None):
                job.template_id = "unknown"
            if not getattr(job, "template_version", None):
                job.template_version = "1.0"
            if not getattr(job, "quality_mode", None):
                job.quality_mode = "balanced"
            if not getattr(job, "state", None):
                job.state = "CREATED"
            if not getattr(job, "ir", None):
                job.ir = {}
            if not getattr(job, "shot_plan", None):
                job.shot_plan = {}
            if not getattr(job, "shot_requests", None):
                job.shot_requests = []
            if not getattr(job, "external_task_ids", None):
                job.external_task_ids = []
            if getattr(job, "total_duration_s", None) is None:
                job.total_duration_s = 0
            if not getattr(job, "resolution", None):
                job.resolution = "1280*720"
            if not getattr(job, "state_transitions", None):
                state_value = job.state.value if hasattr(job.state, "value") else job.state
                job.state_transitions = [
                    {
                        "state": state_value,
                        "timestamp": datetime.utcnow().isoformat(),
                        "event": "job_created",
                    }
                ]
            if getattr(job, "retry_count", None) is None:
                job.retry_count = 0
            if getattr(job, "retry_exhausted", None) is None:
                job.retry_exhausted = False
        else:
            job = JobModel(
                job_id=JobModel.generate_job_id(),
                user_input_redacted=user_input_redacted,
                user_input_hash=user_input_hash or "",
                pii_flags=pii_flags or [],
                template_id=template_id or "unknown",
                template_version=template_version or "1.0",
                quality_mode=quality_mode or "balanced",
                state="CREATED",
                ir=ir or {},
                shot_plan=shot_plan or {},
                shot_requests=shot_requests or [],
                shot_assets=None,
                preview_shot_assets=None,
                selected_seeds=None,
                external_task_ids=external_task_ids or [],
                total_duration_s=total_duration_s or 0,
                resolution=resolution or "1280*720",
                state_transitions=[
                    {
                        "state": "CREATED",
                        "timestamp": datetime.utcnow().isoformat(),
                        "event": "job_created",
                    }
                ],
                retry_count=0,
                retry_exhausted=False,
            )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[JobModel]:
        """Get job by ID"""
        return db.query(JobModel).filter(JobModel.job_id == job_id).first()

    @staticmethod
    def update_job_state(
        db: Session,
        job_id: str,
        new_state: Union[str, Any],
        event: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> Optional[JobModel]:
        """Update job state and record transition"""
        job = JobDB.get_job(db, job_id)
        if job:
            state_value = new_state.value if hasattr(new_state, "value") else new_state
            job.state = state_value
            ts = timestamp or datetime.utcnow()
            transitions = list(job.state_transitions or [])
            transitions.append(
                {
                    "state": state_value,
                    "timestamp": ts.isoformat(),
                    "event": event or "state_updated",
                }
            )
            job.state_transitions = transitions

            # Update timestamp fields based on state
            if new_state == "SUBMITTED":
                job.submitted_at = ts
            elif new_state == "RUNNING":
                job.running_at = ts
            elif new_state == "SUCCEEDED":
                job.succeeded_at = ts
            elif new_state == "FAILED":
                job.failed_at = ts

            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def update_job_shot_plan(
        db: Session,
        job_id: str,
        shot_plan: Dict[str, Any],
    ) -> Optional[JobModel]:
        """Update job with shot plan."""
        job = JobDB.get_job(db, job_id)
        if job:
            job.shot_plan = shot_plan
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def update_job_shot_assets(
        db: Session,
        job_id: str,
        shot_assets: List[Dict[str, Any]],
    ) -> Optional[JobModel]:
        """Update job with shot assets."""
        return JobDB.update_job_assets(db, job_id, shot_assets)

    @staticmethod
    def get_jobs_by_state(
        db: Session,
        state: Union[str, Any],
    ) -> List[JobModel]:
        """Get jobs filtered by state."""
        state_value = state.value if hasattr(state, "value") else state
        return JobDB.list_jobs(db, state=state_value)

    @staticmethod
    def delete_job(db: Session, job_id: str) -> bool:
        """Delete a job."""
        job = JobDB.get_job(db, job_id)
        if job:
            db.delete(job)
            db.commit()
            return True
        return False

    @staticmethod
    def update_job_assets(
        db: Session,
        job_id: str,
        shot_assets: List[Dict[str, Any]],
    ) -> Optional[JobModel]:
        """Update job with shot assets"""
        job = JobDB.get_job(db, job_id)
        if job:
            job.shot_assets = shot_assets
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def update_job_preview_assets(
        db: Session,
        job_id: str,
        preview_shot_assets: List[Dict[str, Any]],
    ) -> Optional[JobModel]:
        """Update job with preview shot assets"""
        job = JobDB.get_job(db, job_id)
        if job:
            job.preview_shot_assets = preview_shot_assets
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def update_job_selected_seeds(
        db: Session,
        job_id: str,
        selected_seeds: Dict[int, int],
    ) -> Optional[JobModel]:
        """Update job with selected seeds"""
        job = JobDB.get_job(db, job_id)
        if job:
            job.selected_seeds = selected_seeds
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def update_job_error(
        db: Session,
        job_id: str,
        error_details: Dict[str, Any],
    ) -> Optional[JobModel]:
        """Update job with error details"""
        job = JobDB.get_job(db, job_id)
        if job:
            job.error_details = error_details
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def update_job_retry(
        db: Session,
        job_id: str,
        retry_count: int,
        last_retry_error: Dict[str, Any],
        retry_exhausted: bool,
    ) -> Optional[JobModel]:
        """Update job retry information"""
        job = JobDB.get_job(db, job_id)
        if job:
            job.retry_count = retry_count
            job.last_retry_error = last_retry_error
            job.retry_exhausted = retry_exhausted
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def list_jobs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        state: Optional[str] = None,
    ) -> List[JobModel]:
        """List jobs with optional state filter"""
        query = db.query(JobModel)
        if state:
            query = query.filter(JobModel.state == state)
        return query.order_by(JobModel.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def delete_old_jobs(db: Session, days: int = 30) -> int:
        """Delete jobs older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = (
            db.query(JobModel)
            .filter(JobModel.created_at < cutoff_date)
            .delete()
        )
        db.commit()
        return deleted


def init_db(db: Session) -> None:
    """
    Initialize database with default data
    """
    # Create tables
    from src.models import Base
    Base.metadata.create_all(bind=db.get_bind())

    # Load templates from file system
    load_templates(db)


def load_templates(db: Session) -> None:
    """
    Load templates from backend/src/templates/medical_scenes directory
    """
    import os
    from src.config.settings import settings

    template_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "medical_scenes"
    )

    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        return

    for filename in os.listdir(template_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(template_dir, filename)
            with open(filepath, "r") as f:
                template_data = json.load(f)

            # Check if template already exists
            existing = TemplateDB.get_template(
                db,
                template_data["template_id"],
                template_data["version"]
            )

            if not existing:
                TemplateDB.create_template(
                    db=db,
                    template_id=template_data["template_id"],
                    version=template_data["version"],
                    tags=template_data["tags"],
                    constraints=template_data["constraints"],
                    shot_skeletons=template_data["shot_skeletons"],
                    negative_prompt_base=template_data["negative_prompt_base"],
                )

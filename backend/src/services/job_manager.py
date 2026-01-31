"""
Job Manager - Orchestrate per-shot generation workflow
"""

import asyncio
import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from src.models.job import JobModel
from src.services.job_state import transition_state, is_terminal_state
from src.services.storage import JobDB
from src.services.rate_limiter import RateLimiter
from src.services.asset_storage import AssetStorage
from src.services.observability import (
    logger,
    log_template_hit,
    log_generation_duration,
    log_failure_classification,
)
from src.core.input_processor import InputProcessor
from src.core.llm_orchestrator import LLMOrchestrator
from src.core.template_router import TemplateRouter
from src.core.validator import Validator
from src.core.prompt_compiler import PromptCompiler
from src.core.wan26_adapter import Wan26RetryAdapter
from src.services.wan26_downloader import Wan26Downloader
from src.services.ffmpeg_splitter import FFmpegSplitter, FFmpegError
from src.config.constants import (
    QUALITY_MODES,
    JOB_TIMEOUT_MINUTES,
    MAX_RETRY_ATTEMPTS,
)


class JobManager:
    """
    Orchestrate end-to-end per-shot generation workflow
    """

    def __init__(self):
        """Initialize job manager"""
        self.input_processor = InputProcessor()
        self.llm_orchestrator = LLMOrchestrator()
        self.template_router = TemplateRouter()
        self.validator = Validator()
        self.prompt_compiler = PromptCompiler()
        self.wan26_adapter = Wan26RetryAdapter()
        self.downloader = Wan26Downloader()
        self.ffmpeg_splitter = FFmpegSplitter()
        self.asset_storage = AssetStorage()
        self.rate_limiter = RateLimiter()

    async def execute_generation_workflow(
        self,
        db: Session,
        user_input: str,
        quality_mode: str,
        client_ip: str,
        resolution: str = "1280x720",
    ) -> JobModel:
        """
        Execute complete generation workflow

        Args:
            db: Database session
            user_input: Raw user input
            quality_mode: Quality mode (fast, balanced, high)
            client_ip: Client IP address for rate limiting
            resolution: Video resolution

        Returns:
            JobModel with final status

        Raises:
            ValueError: If validation fails
            Exception: If workflow fails
        """
        start_time = datetime.utcnow()

        # Check rate limits
        rate_limit_result = self.rate_limiter.check_rate_limit(client_ip)
        if not rate_limit_result["allowed"]:
            raise ValueError(f"Rate limit exceeded. Try again at {rate_limit_result['reset_at']}")

        concurrent_result = self.rate_limiter.check_concurrent_jobs(client_ip)
        if not concurrent_result["allowed"]:
            raise ValueError(f"Concurrent job limit reached. Current: {concurrent_result['current']}, Max: {concurrent_result['max']}")

        # Step 1: Process input (redaction, language detection)
        logger.info("workflow_step_1", step="input_processing")
        processed = self.input_processor.process_input(
            user_input,
            auto_translate=False,  # TODO: Use AUTO_TRANSLATE constant
            align_bilingual=True,
            align_target_language="en-US",
        )

        # Step 2: Parse IR
        logger.info("workflow_step_2", step="ir_parsing")
        ir_input = processed.get("aligned_text") or processed["redacted_text"]
        ir = self.llm_orchestrator.parse_ir(
            ir_input,
            quality_mode,
        )
        ir_dict = ir.dict()

        # Step 3: Match template
        logger.info("workflow_step_3", step="template_matching")
        template_match = self.template_router.match_template(
            ir_dict,
            db,
        )

        if not template_match:
            # Trigger clarification
            logger.warning("template_match_failed", trigger_clarification=True)
            # TODO: Create clarification job
            raise ValueError("No matching template found. Please provide more details.")

        template = template_match.template

        # Log template hit
        log_template_hit(
            template_id=template["template_id"],
            confidence=template_match.confidence,
            confidence_components=template_match.confidence_components,
        )

        # Step 4: Instantiate template
        logger.info("workflow_step_4", step="template_instantiation")
        shot_plan = self.llm_orchestrator.instantiate_template(
            ir,
            template,
        )
        shot_plan_dict = shot_plan.dict()
        shot_plan_dict = self._normalize_shot_plan(shot_plan_dict, template)

        # Step 5: Validate parameters
        logger.info("workflow_step_5", step="validation")
        is_valid, suggestions = self.validator.validate_parameters(
            ir_dict,
            shot_plan_dict,
            quality_mode,
        )

        if not is_valid:
            logger.warning("validation_failed", suggestions=suggestions)
            # TODO: Apply auto-fix or trigger clarification
            raise ValueError(f"Validation failed: {suggestions}")

        # Step 6: Compile prompts per shot
        logger.info("workflow_step_6", step="prompt_compilation")
        shot_requests = []
        external_task_ids = []

        for shot in shot_plan_dict["shots"]:
            compiled = self.prompt_compiler.compile_shot_prompt(
                shot=shot,
                shot_plan=shot_plan_dict,
                ir=ir_dict,
                negative_prompt_base=template["negative_prompt_base"],
                prompt_extend=False,  # Default to false
            )

            shot_request = {
                "shot_id": shot["shot_id"],
                "compiled_prompt": compiled.compiled_prompt,
                "compiled_negative_prompt": compiled.compiled_negative_prompt,
                "params": compiled.params,
            }
            shot_requests.append(shot_request)

        # Step 7: Create job record
        logger.info("workflow_step_7", step="job_creation")
        job = JobDB.create_job(
            db=db,
            user_input_redacted=processed["redacted_text"],
            user_input_hash=processed["input_hash"],
            pii_flags=processed["pii_flags"],
            template_id=template["template_id"],
            template_version=template["version"],
            quality_mode=quality_mode,
            ir=ir_dict,
            shot_plan=shot_plan_dict,
            shot_requests=shot_requests,
            external_task_ids=[],
            total_duration_s=shot_plan_dict["duration_s"],
            resolution=resolution,
        )

        # Step 8: Submit to RUNNING state
        transition_state(db, job.job_id, "SUBMITTED", "workflow_submitted")
        transition_state(db, job.job_id, "RUNNING", "generation_started")

        # Increment concurrent job counter
        self.rate_limiter.increment_concurrent_jobs(client_ip)

        try:
            # Step 9: Generate per-shot videos
            logger.info("workflow_step_9", step="shot_generation")
            shot_assets = await self._generate_shots(
                db=db,
                job=job,
                shot_requests=shot_requests,
            )

            # Step 10: Update job with assets
            logger.info("workflow_step_10", step="update_assets")
            JobDB.update_job_assets(db, job.job_id, shot_assets)

            # Step 11: Write metadata
            logger.info("workflow_step_11", step="write_metadata")
            self._write_job_metadata(job, shot_assets)

            # Step 12: Transition to SUCCEEDED
            transition_state(db, job.job_id, "SUCCEEDED", "generation_complete")

            duration_s = (datetime.utcnow() - start_time).total_seconds()
            log_generation_duration(
                job_id=job.job_id,
                duration_s=duration_s,
                shot_count=len(shot_requests),
                quality_mode=quality_mode,
            )

            return job

        except Exception as e:
            # Handle failure
            logger.error("workflow_failed", job_id=job.job_id, error=str(e))
            transition_state(db, job.job_id, "FAILED", "generation_failed")

            # Classify error
            error_classification = self._classify_error(e)
            log_failure_classification(
                error_code=error_classification["code"],
                classification=error_classification["classification"],
                retryable=error_classification["retryable"],
                job_id=job.job_id,
            )

            # Update job with error details
            JobDB.update_job_error(
                db=db,
                job_id=job.job_id,
                error_details=error_classification,
            )

            raise

        finally:
            # Decrement concurrent job counter
            self.rate_limiter.decrement_concurrent_jobs(client_ip)

    async def execute_planning_workflow(
        self,
        db: Session,
        user_input: str,
        quality_mode: str,
        client_ip: str,
        resolution: str = "1280x720",
    ) -> JobModel:
        """
        Execute planning workflow (script + shot plan only, no video generation).

        Args:
            db: Database session
            user_input: Raw user input
            quality_mode: Quality mode (fast, balanced, high)
            client_ip: Client IP address for rate limiting
            resolution: Video resolution

        Returns:
            JobModel with planning results (shot_plan/shot_requests)
        """
        # Check rate limits
        rate_limit_result = self.rate_limiter.check_rate_limit(client_ip)
        if not rate_limit_result["allowed"]:
            raise ValueError(f"Rate limit exceeded. Try again at {rate_limit_result['reset_at']}")

        concurrent_result = self.rate_limiter.check_concurrent_jobs(client_ip)
        if not concurrent_result["allowed"]:
            raise ValueError(
                f"Concurrent job limit reached. Current: {concurrent_result['current']}, "
                f"Max: {concurrent_result['max']}"
            )

        # Step 1: Process input (redaction, language detection)
        logger.info("planning_step_1", step="input_processing")
        processed = self.input_processor.process_input(
            user_input,
            auto_translate=False,  # TODO: Use AUTO_TRANSLATE constant
            align_bilingual=True,
            align_target_language="en-US",
        )

        # Step 2: Parse IR
        logger.info("planning_step_2", step="ir_parsing")
        ir_input = processed.get("aligned_text") or processed["redacted_text"]
        ir = self.llm_orchestrator.parse_ir(
            ir_input,
            quality_mode,
        )
        ir_dict = ir.dict()

        # Step 3: Match template
        logger.info("planning_step_3", step="template_matching")
        template_match = self.template_router.match_template(
            ir_dict,
            db,
        )

        if not template_match:
            logger.warning("template_match_failed", trigger_clarification=True)
            raise ValueError("No matching template found. Please provide more details.")

        template = template_match.template

        # Log template hit
        log_template_hit(
            template_id=template["template_id"],
            confidence=template_match.confidence,
            confidence_components=template_match.confidence_components,
        )

        # Step 4: Instantiate template
        logger.info("planning_step_4", step="template_instantiation")
        shot_plan = self.llm_orchestrator.instantiate_template(
            ir,
            template,
        )
        shot_plan_dict = shot_plan.dict()
        shot_plan_dict = self._normalize_shot_plan(shot_plan_dict, template)

        # Step 5: Validate parameters
        logger.info("planning_step_5", step="validation")
        is_valid, suggestions = self.validator.validate_parameters(
            ir_dict,
            shot_plan_dict,
            quality_mode,
        )

        if not is_valid:
            logger.warning("planning_validation_failed", suggestions=suggestions)
            raise ValueError(f"Validation failed: {suggestions}")

        # Step 6: Compile prompts per shot
        logger.info("planning_step_6", step="prompt_compilation")
        shot_requests = []

        for shot in shot_plan_dict["shots"]:
            compiled = self.prompt_compiler.compile_shot_prompt(
                shot=shot,
                shot_plan=shot_plan_dict,
                ir=ir_dict,
                negative_prompt_base=template["negative_prompt_base"],
                prompt_extend=False,
            )

            shot_request = {
                "shot_id": shot["shot_id"],
                "compiled_prompt": compiled.compiled_prompt,
                "compiled_negative_prompt": compiled.compiled_negative_prompt,
                "params": compiled.params,
            }
            shot_requests.append(shot_request)

        # Step 7: Create job record
        logger.info("planning_step_7", step="job_creation")
        job = JobDB.create_job(
            db=db,
            user_input_redacted=processed["redacted_text"],
            user_input_hash=processed["input_hash"],
            pii_flags=processed["pii_flags"],
            template_id=template["template_id"],
            template_version=template["version"],
            quality_mode=quality_mode,
            ir=ir_dict,
            shot_plan=shot_plan_dict,
            shot_requests=shot_requests,
            external_task_ids=[],
            total_duration_s=shot_plan_dict["duration_s"],
            resolution=resolution,
        )

        # Step 8: Transition through planning states
        transition_state(db, job.job_id, "SUBMITTED", "planning_submitted")
        transition_state(db, job.job_id, "RUNNING", "planning_started")

        try:
            # Step 9: Write metadata (no assets yet)
            logger.info("planning_step_9", step="write_metadata")
            self._write_job_metadata(job, [])

            # Step 10: Mark planning complete
            transition_state(db, job.job_id, "SUCCEEDED", "planning_complete")

            return job
        except Exception as e:
            logger.error("planning_failed", job_id=job.job_id, error=str(e))
            transition_state(db, job.job_id, "FAILED", "planning_failed")

            error_classification = self._classify_error(e)
            log_failure_classification(
                error_code=error_classification["code"],
                classification=error_classification["classification"],
                retryable=error_classification["retryable"],
                job_id=job.job_id,
            )
            JobDB.update_job_error(
                db=db,
                job_id=job.job_id,
                error_details=error_classification,
            )
            raise

    async def execute_generation_from_job(
        self,
        db: Session,
        job_id: str,
        client_ip: str,
    ) -> JobModel:
        """
        Execute video generation workflow for an existing planned job.

        Args:
            db: Database session
            job_id: Job identifier
            client_ip: Client IP address for rate limiting

        Returns:
            JobModel with final status
        """
        job = JobDB.get_job(db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.state == "RUNNING":
            raise ValueError("Job is already running")
        if job.state == "FAILED":
            raise ValueError("Job is in FAILED state")
        if not job.shot_requests:
            raise ValueError("Job is missing shot requests")
        if job.shot_assets:
            raise ValueError("Job already has generated assets")

        rate_limit_result = self.rate_limiter.check_rate_limit(client_ip)
        if not rate_limit_result["allowed"]:
            raise ValueError(f"Rate limit exceeded. Try again at {rate_limit_result['reset_at']}")

        concurrent_result = self.rate_limiter.check_concurrent_jobs(client_ip)
        if not concurrent_result["allowed"]:
            raise ValueError(
                f"Concurrent job limit reached. Current: {concurrent_result['current']}, "
                f"Max: {concurrent_result['max']}"
            )

        # Transition to RUNNING
        if job.state == "CREATED":
            transition_state(db, job.job_id, "SUBMITTED", "generation_submitted")
            transition_state(db, job.job_id, "RUNNING", "generation_started")
        else:
            transition_state(db, job.job_id, "RUNNING", "generation_started")

        # Increment concurrent job counter
        self.rate_limiter.increment_concurrent_jobs(client_ip)

        start_time = datetime.utcnow()

        try:
            shot_assets = await self._generate_shots(
                db=db,
                job=job,
                shot_requests=job.shot_requests,
            )

            JobDB.update_job_assets(db, job.job_id, shot_assets)
            self._write_job_metadata(job, shot_assets)

            transition_state(db, job.job_id, "SUCCEEDED", "generation_complete")

            duration_s = (datetime.utcnow() - start_time).total_seconds()
            log_generation_duration(
                job_id=job.job_id,
                duration_s=duration_s,
                shot_count=len(job.shot_requests),
                quality_mode=job.quality_mode,
            )

            return job
        except Exception as e:
            logger.error("workflow_failed", job_id=job.job_id, error=str(e))
            transition_state(db, job.job_id, "FAILED", "generation_failed")

            error_classification = self._classify_error(e)
            log_failure_classification(
                error_code=error_classification["code"],
                classification=error_classification["classification"],
                retryable=error_classification["retryable"],
                job_id=job.job_id,
            )
            JobDB.update_job_error(
                db=db,
                job_id=job.job_id,
                error_details=error_classification,
            )
            raise
        finally:
            self.rate_limiter.decrement_concurrent_jobs(client_ip)

    async def _generate_shots(
        self,
        db: Session,
        job: JobModel,
        shot_requests: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Generate all shots concurrently

        Args:
            db: Database session
            job: Job model
            shot_requests: List of shot request dicts

        Returns:
            List of shot asset dicts
        """
        shot_assets = []
        external_task_ids: List[str] = []
        quality_mode = job.quality_mode

        # Get number of preview seeds based on quality mode
        default_preview_seeds = QUALITY_MODES[quality_mode]["preview_seeds"]

        async def _generate_shot_candidates(
            shot_request: Dict[str, Any],
        ) -> Tuple[List[Dict[str, Any]], List[str]]:
            shot_id = shot_request["shot_id"]
            output_suffix = shot_request.get("output_suffix")
            shot_candidates: List[Dict[str, Any]] = []
            task_ids: List[str] = []
            preview_seeds = shot_request.get("preview_seeds", default_preview_seeds)

            # Generate multiple preview candidates
            for _ in range(preview_seeds):
                try:
                    # Submit shot request
                    from src.core.wan26_adapter import ShotGenerationRequest

                    gen_request = ShotGenerationRequest(
                        prompt=shot_request["compiled_prompt"],
                        negative_prompt=shot_request["compiled_negative_prompt"],
                        size=shot_request["params"]["size"],
                        duration=shot_request["params"]["duration"],
                        seed=shot_request["params"]["seed"],
                        prompt_extend=shot_request["params"]["prompt_extend"],
                        watermark=shot_request["params"]["watermark"],
                    )

                    submit_response = await self.wan26_adapter.submit_shot_request_with_retry(
                        gen_request,
                    )
                    task_ids.append(submit_response.task_id)

                    # Poll for completion
                    status_response = await self.wan26_adapter.poll_task_status(
                        submit_response.task_id,
                    )

                    if status_response.status == "succeeded" and status_response.video_url:
                        # Download video
                        temp_video_path = await self.downloader.download_video(
                            status_response.video_url,
                        )

                        # Split video/audio
                        video_path = self.asset_storage.get_video_storage_path(
                            job.job_id,
                            shot_id,
                            suffix=output_suffix,
                        )
                        audio_path = self.asset_storage.get_audio_storage_path(
                            job.job_id,
                            shot_id,
                            suffix=output_suffix,
                        )

                        try:
                            split_result = await asyncio.to_thread(
                                self.ffmpeg_splitter.split_video_audio,
                                temp_video_path,
                                video_path,
                                audio_path,
                            )

                            audio_url = self.asset_storage.get_audio_url(
                                job.job_id,
                                shot_id,
                                suffix=output_suffix,
                            )
                            duration_s = split_result["duration_s"]

                            # Clean up temp file
                            os.remove(temp_video_path)
                        except FFmpegError as exc:
                            logger.warning(
                                "ffmpeg_fallback_video_only",
                                shot_id=shot_id,
                                error=str(exc),
                            )
                            # Store raw video when ffmpeg isn't available.
                            shutil.move(temp_video_path, video_path)
                            audio_path = ""
                            audio_url = ""
                            duration_s = int(shot_request["params"]["duration"])

                        # Create asset record
                        asset = {
                            "shot_id": shot_id,
                            "seed": shot_request["params"]["seed"],
                            "model_task_id": status_response.task_id,
                            "raw_video_url": status_response.video_url,
                            "video_url": self.asset_storage.get_video_url(
                                job.job_id,
                                shot_id,
                                suffix=output_suffix,
                            ),
                            "audio_url": audio_url,
                            "video_path": video_path,
                            "audio_path": audio_path,
                            "duration_s": duration_s,
                            "resolution": job.resolution,
                        }

                        shot_candidates.append(asset)

                    else:
                        # Generation failed
                        logger.error(
                            "shot_generation_failed",
                            shot_id=shot_id,
                            task_id=status_response.task_id,
                            error=status_response.error,
                        )

                except Exception as e:
                    logger.error(
                        "shot_workflow_error",
                        shot_id=shot_id,
                        error=str(e),
                    )
                    # Continue with next shot
                    continue

            return shot_candidates, task_ids

        tasks = [asyncio.create_task(_generate_shot_candidates(req)) for req in shot_requests]
        results = await asyncio.gather(*tasks) if tasks else []

        for candidates, task_ids in results:
            if candidates:
                shot_assets.extend(candidates)
            external_task_ids.extend(task_ids)

        if external_task_ids:
            job.external_task_ids = external_task_ids
            db.commit()
            db.refresh(job)

        return shot_assets

    def _write_job_metadata(
        self,
        job: JobModel,
        shot_assets: List[Dict[str, Any]],
    ) -> None:
        """
        Write job metadata to JSON file

        Args:
            job: Job model
            shot_assets: List of shot assets
        """
        metadata = {
            "job_id": job.job_id,
            "user_input_redacted": job.user_input_redacted,
            "user_input_hash": job.user_input_hash,
            "pii_flags": job.pii_flags,
            "template_id": job.template_id,
            "template_version": job.template_version,
            "quality_mode": job.quality_mode,
            "ir": job.ir,
            "shot_plan": job.shot_plan,
            "shot_requests": job.shot_requests,
            "shot_assets": shot_assets,
            "total_duration_s": job.total_duration_s,
            "resolution": job.resolution,
            "state_transitions": job.state_transitions,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }

        self.asset_storage.write_job_metadata(job.job_id, metadata)

    def _coerce_duration(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"(\d+)", value)
            if match:
                return int(match.group(1))
        return None

    def _normalize_shot_plan(
        self,
        shot_plan: Dict[str, Any],
        template: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not shot_plan:
            return shot_plan

        shots = shot_plan.get("shots", [])
        if not isinstance(shots, list):
            return shot_plan

        skeletons = template.get("shot_skeletons", []) or []
        skeleton_by_id: Dict[str, Dict[str, Any]] = {}
        for skeleton in skeletons:
            if isinstance(skeleton, dict) and skeleton.get("shot_id") is not None:
                skeleton_by_id[str(skeleton["shot_id"])] = skeleton

        normalized_shots: List[Dict[str, Any]] = []
        for idx, shot in enumerate(shots):
            if not isinstance(shot, dict):
                normalized_shots.append(shot)
                continue

            normalized = dict(shot)
            shot_id = normalized.get("shot_id")
            if shot_id is None and idx < len(skeletons):
                skeleton_id = skeletons[idx].get("shot_id")
                if skeleton_id is not None:
                    normalized["shot_id"] = skeleton_id
                    shot_id = skeleton_id

            duration = self._coerce_duration(normalized.get("duration_s"))
            if duration is None:
                duration = self._coerce_duration(normalized.get("duration"))
            if duration is None:
                duration = self._coerce_duration(normalized.get("length_s"))
            if duration is None:
                skeleton = None
                if shot_id is not None:
                    skeleton = skeleton_by_id.get(str(shot_id))
                if skeleton is None and idx < len(skeletons):
                    skeleton = skeletons[idx]
                if isinstance(skeleton, dict):
                    duration = self._coerce_duration(skeleton.get("duration_s"))
            if duration is not None:
                normalized["duration_s"] = duration

            normalized_shots.append(normalized)

        shot_plan["shots"] = normalized_shots

        total_duration = self._coerce_duration(shot_plan.get("duration_s"))
        if total_duration is None:
            total_duration = self._coerce_duration(shot_plan.get("duration"))
        if total_duration is None:
            computed_duration = sum(
                shot.get("duration_s", 0)
                for shot in normalized_shots
                if isinstance(shot, dict) and isinstance(shot.get("duration_s"), (int, float))
            )
            if computed_duration:
                shot_plan["duration_s"] = int(computed_duration)

        if not shot_plan.get("subtitle_policy"):
            subtitle_policy = (
                template.get("constraints", {}).get("subtitle_policy")
                or template.get("tags", {}).get("subtitle_policy")
            )
            if subtitle_policy:
                shot_plan["subtitle_policy"] = subtitle_policy

        if not shot_plan.get("template_id"):
            template_id = template.get("template_id")
            if template_id:
                shot_plan["template_id"] = template_id

        if not shot_plan.get("template_version"):
            template_version = template.get("version")
            if template_version:
                shot_plan["template_version"] = template_version

        return shot_plan

    async def execute_finalization_workflow(
        self,
        db: Session,
        job_id: str,
        selected_seeds: Dict[int, int],
        target_resolution: str = "1920x1080",
    ) -> JobModel:
        """
        Execute finalization workflow: regenerate selected shots at target resolution

        Args:
            db: Database session
            job_id: Job ID to finalize
            selected_seeds: Dict mapping shot_id to selected seed
            target_resolution: Target resolution (default 1920x1080)

        Returns:
            Updated JobModel with final shot assets
        """
        # Get job
        job = JobDB.get_job(db, job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Update selected seeds
        JobDB.update_job_selected_seeds(db, job_id, selected_seeds)

        # Transition to RUNNING
        transition_state(db, job_id, "RUNNING", "finalization_started")

        try:
            # Get shot requests from original job
            shot_requests = job.shot_requests

            # Generate final shots at target resolution using selected seeds
            logger.info(
                "finalization_start",
                job_id=job_id,
                selected_seeds=selected_seeds,
                target_resolution=target_resolution,
            )

            final_shot_assets = await self._generate_final_shots(
                db=db,
                job=job,
                selected_seeds=selected_seeds,
                target_resolution=target_resolution,
            )

            # Update job with final assets
            JobDB.update_job_assets(db, job_id, final_shot_assets)

            # Write metadata
            self._write_job_metadata(job, final_shot_assets)

            # Transition to SUCCEEDED
            transition_state(db, job_id, "SUCCEEDED", "finalization_complete")

            logger.info(
                "finalization_complete",
                job_id=job_id,
                shot_count=len(final_shot_assets),
            )

            # Refresh job from database
            job = JobDB.get_job(db, job_id)
            return job

        except Exception as e:
            logger.error(
                "finalization_failed",
                job_id=job_id,
                error=str(e),
            )
            transition_state(db, job_id, "FAILED", "finalization_failed")

            # Classify error
            error_classification = self._classify_error(e)
            log_failure_classification(
                error_code=error_classification["code"],
                classification=error_classification["classification"],
                retryable=error_classification["retryable"],
                job_id=job_id,
            )

            # Update job with error details
            JobDB.update_job_error(
                db=db,
                job_id=job_id,
                error_details=error_classification,
            )

            raise

    async def _generate_final_shots(
        self,
        db: Session,
        job: JobModel,
        selected_seeds: Dict[int, int],
        target_resolution: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate final shots at target resolution using selected seeds

        Args:
            db: Database session
            job: Job model
            selected_seeds: Dict mapping shot_id to selected seed
            target_resolution: Target resolution (e.g., "1920x1080")

        Returns:
            List of final shot asset dicts
        """
        final_shot_assets: List[Dict[str, Any]] = []
        shot_requests = job.shot_requests

        async def _generate_final_shot(
            shot_request: Dict[str, Any],
        ) -> Optional[Dict[str, Any]]:
            shot_id = shot_request["shot_id"]

            # Skip if shot not in selected seeds
            if shot_id not in selected_seeds:
                return None

            selected_seed = selected_seeds[shot_id]

            try:
                # Submit shot request with selected seed at target resolution
                from src.core.wan26_adapter import ShotGenerationRequest

                # Convert resolution format (1280x720 -> 1280*720)
                size = target_resolution.replace("x", "*")

                gen_request = ShotGenerationRequest(
                    prompt=shot_request["compiled_prompt"],
                    negative_prompt=shot_request["compiled_negative_prompt"],
                    size=size,
                    duration=shot_request["params"]["duration"],
                    seed=selected_seed,  # Use selected seed
                    prompt_extend=shot_request["params"]["prompt_extend"],
                    watermark=shot_request["params"]["watermark"],
                )

                submit_response = await self.wan26_adapter.submit_shot_request_with_retry(
                    gen_request,
                )

                # Poll for completion
                status_response = await self.wan26_adapter.poll_task_status(
                    submit_response.task_id,
                )

                if status_response.status == "succeeded" and status_response.video_url:
                    # Download video
                    temp_video_path = await self.downloader.download_video(
                        status_response.video_url,
                    )

                    # Split video/audio
                    video_path = self.asset_storage.get_video_storage_path(
                        job.job_id,
                        f"{shot_id}_final",
                    )
                    audio_path = self.asset_storage.get_audio_storage_path(
                        job.job_id,
                        f"{shot_id}_final",
                    )

                    try:
                        split_result = await asyncio.to_thread(
                            self.ffmpeg_splitter.split_video_audio,
                            temp_video_path,
                            video_path,
                            audio_path,
                        )

                        audio_url = self.asset_storage.get_audio_url(
                            job.job_id,
                            f"{shot_id}_final",
                        )
                        duration_s = split_result["duration_s"]

                        # Clean up temp file
                        os.remove(temp_video_path)
                    except FFmpegError as exc:
                        logger.warning(
                            "ffmpeg_fallback_video_only",
                            job_id=job.job_id,
                            shot_id=shot_id,
                            error=str(exc),
                        )
                        # Store raw video when ffmpeg isn't available.
                        shutil.move(temp_video_path, video_path)
                        audio_path = ""
                        audio_url = ""
                        duration_s = int(shot_request["params"]["duration"])

                    # Create final asset record
                    asset = {
                        "shot_id": shot_id,
                        "seed": selected_seed,
                        "model_task_id": status_response.task_id,
                        "raw_video_url": status_response.video_url,
                        "video_url": self.asset_storage.get_video_url(
                            job.job_id,
                            f"{shot_id}_final",
                        ),
                        "audio_url": audio_url,
                        "video_path": video_path,
                        "audio_path": audio_path,
                        "duration_s": duration_s,
                        "resolution": target_resolution,
                    }

                    final_shot_assets.append(asset)

                    logger.info(
                        "final_shot_generated",
                        job_id=job.job_id,
                        shot_id=shot_id,
                        seed=selected_seed,
                        resolution=target_resolution,
                    )

                    return asset
                else:
                    logger.error(
                        "final_shot_generation_failed",
                        job_id=job.job_id,
                        shot_id=shot_id,
                        task_id=status_response.task_id,
                        error=status_response.error,
                    )

            except Exception as e:
                logger.error(
                    "final_shot_workflow_error",
                    job_id=job.job_id,
                    shot_id=shot_id,
                    error=str(e),
                )
                # Continue with next shot
                return None

            return None

        tasks = [
            asyncio.create_task(_generate_final_shot(req))
            for req in shot_requests
            if req.get("shot_id") in selected_seeds
        ]
        results = await asyncio.gather(*tasks) if tasks else []

        for asset in results:
            if asset:
                final_shot_assets.append(asset)

        return final_shot_assets

    async def execute_revision_workflow(
        self,
        db: Session,
        parent_job_id: str,
        feedback: str,
        targeted_fields: List[str],
        suggested_modifications: Dict[str, Any],
        client_ip: Optional[str] = None,
    ) -> JobModel:
        """
        Execute revision workflow: create new job with targeted modifications

        Args:
            db: Database session
            parent_job_id: Parent job ID to revise
            feedback: User's revision feedback
            targeted_fields: Fields to modify (e.g., camera, narration, lighting)
            suggested_modifications: Suggested changes from feedback parser
            client_ip: Client IP address (optional)

        Returns:
            New JobModel with revision tracking
        """
        # Get parent job
        parent_job = JobDB.get_job(db, parent_job_id)
        if not parent_job:
            raise ValueError(f"Parent job not found: {parent_job_id}")

        logger.info(
            "revision_workflow_start",
            parent_job_id=parent_job_id,
            targeted_fields=targeted_fields,
        )

        # Step 1: Apply suggested modifications to IR
        modified_ir = self._apply_feedback_to_ir(
            ir=parent_job.ir,
            targeted_fields=targeted_fields,
            suggested_modifications=suggested_modifications,
        )

        # Step 2: Re-use same template
        template_id = parent_job.template_id
        template_version = parent_job.template_version
        quality_mode = parent_job.quality_mode

        # Step 3: Re-instantiate template with modified IR
        logger.info("revision_template_instantiation", parent_job_id=parent_job_id)
        from src.services.storage import TemplateDB
        template_model = TemplateDB.get_template(db, template_id, template_version)
        if not template_model:
            raise ValueError(f"Template not found: {template_id}:{template_version}")
        template_dict = template_model.to_dict()

        from src.core.llm_orchestrator import IR as IRModel
        ir_model = modified_ir
        if isinstance(modified_ir, dict):
            if not modified_ir.get("optimized_prompt"):
                modified_ir["optimized_prompt"] = parent_job.user_input_redacted or ""
            ir_model = IRModel(**modified_ir)

        shot_plan = self.llm_orchestrator.instantiate_template(
            ir_model,
            template_dict,
        )
        shot_plan_dict = shot_plan.dict()
        shot_plan_dict = self._normalize_shot_plan(shot_plan_dict, template_dict)

        # Step 4: Re-validate parameters
        logger.info("revision_validation", parent_job_id=parent_job_id)
        is_valid, suggestions = self.validator.validate_parameters(
            modified_ir,
            shot_plan_dict,
            quality_mode,
        )

        if not is_valid:
            logger.warning("revision_validation_failed", suggestions=suggestions)
            # Apply auto-fixes if possible
            # TODO: Implement auto-fix logic

        # Step 5: Re-compile prompts (only for targeted shots if possible)
        logger.info("revision_prompt_compilation", parent_job_id=parent_job_id)
        shot_requests = []

        for shot in shot_plan_dict["shots"]:
            # Check if this shot should be modified based on targeted_fields
            if self._should_modify_shot(shot, targeted_fields):
                # Compile new prompt for modified shot
                # Get template from DB
                from src.services.storage import TemplateDB
                template = TemplateDB.get_template(db, template_id, template_version)
                template_dict = template.to_dict() if template else {}

                compiled = self.prompt_compiler.compile_shot_prompt(
                    shot=shot,
                    shot_plan=shot_plan_dict,
                    ir=modified_ir,
                    negative_prompt_base=template_dict.get("negative_prompt_base", ""),
                    prompt_extend=False,
                )

                shot_request = {
                    "shot_id": shot["shot_id"],
                    "compiled_prompt": compiled.compiled_prompt,
                    "compiled_negative_prompt": compiled.compiled_negative_prompt,
                    "params": compiled.params,
                }
            else:
                # Re-use original shot request
                original_shot = next(
                    (s for s in parent_job.shot_requests if s["shot_id"] == shot["shot_id"]),
                    None,
                )
                if original_shot:
                    shot_request = original_shot
                else:
                    # Fallback: compile anyway
                    from src.services.storage import TemplateDB
                    template = TemplateDB.get_template(db, template_id, template_version)
                    template_dict = template.to_dict() if template else {}

                    compiled = self.prompt_compiler.compile_shot_prompt(
                        shot=shot,
                        shot_plan=shot_plan_dict,
                        ir=modified_ir,
                        negative_prompt_base=template_dict.get("negative_prompt_base", ""),
                        prompt_extend=False,
                    )

                    shot_request = {
                        "shot_id": shot["shot_id"],
                        "compiled_prompt": compiled.compiled_prompt,
                        "compiled_negative_prompt": compiled.compiled_negative_prompt,
                        "params": compiled.params,
                    }

            shot_requests.append(shot_request)

        # Step 6: Create new job with revision tracking
        logger.info("revision_job_creation", parent_job_id=parent_job_id)
        job = JobDB.create_job(
            db=db,
            user_input_redacted=parent_job.user_input_redacted,
            user_input_hash=parent_job.user_input_hash,
            pii_flags=parent_job.pii_flags,
            template_id=template_id,
            template_version=template_version,
            quality_mode=quality_mode,
            ir=modified_ir,
            shot_plan=shot_plan_dict,
            shot_requests=shot_requests,
            external_task_ids=[],
            total_duration_s=shot_plan_dict["duration_s"],
            resolution=parent_job.resolution,
        )

        # Add revision tracking
        from sqlalchemy import update
        from src.models.job import JobModel as JobModelTable

        stmt = (
            update(JobModelTable)
            .where(JobModelTable.job_id == job.job_id)
            .values(
                revision_of=parent_job_id,
                targeted_fields=targeted_fields,
            )
        )
        db.execute(stmt)
        db.commit()
        db.refresh(job)

        # Step 7: Submit to RUNNING state
        transition_state(db, job.job_id, "SUBMITTED", "revision_submitted")
        transition_state(db, job.job_id, "RUNNING", "revision_started")

        # Step 8: Generate shots
        logger.info("revision_shot_generation", parent_job_id=parent_job_id)
        shot_assets = await self._generate_shots(
            db=db,
            job=job,
            shot_requests=shot_requests,
        )

        # Step 9: Update job with assets
        JobDB.update_job_assets(db, job.job_id, shot_assets)

        # Step 10: Write metadata
        self._write_job_metadata(job, shot_assets)

        # Step 11: Transition to SUCCEEDED
        transition_state(db, job.job_id, "SUCCEEDED", "revision_complete")

        # Log revision event
        from src.services.observability import log_revision_event
        log_revision_event(
            job_id=job.job_id,
            parent_job_id=parent_job_id,
            targeted_fields=targeted_fields,
        )

        logger.info(
            "revision_complete",
            parent_job_id=parent_job_id,
            revision_job_id=job.job_id,
            shot_count=len(shot_assets),
        )

        return job

    def _apply_feedback_to_ir(
        self,
        ir: Dict[str, Any],
        targeted_fields: List[str],
        suggested_modifications: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply feedback modifications to IR

        Args:
            ir: Original IR
            targeted_fields: Fields to modify
            suggested_modifications: Suggested changes

        Returns:
            Modified IR
        """
        import copy
        modified_ir = copy.deepcopy(ir)

        # Apply modifications based on targeted fields
        for field in targeted_fields:
            if field == "camera":
                # Modify camera motion in scene or style
                if "camera_motion" in suggested_modifications:
                    modified_ir["scene"]["camera_motion"] = suggested_modifications["camera_motion"]

            elif field == "narration":
                # Modify narration in audio
                if "narration" in suggested_modifications:
                    modified_ir["audio"]["narration_tone"] = suggested_modifications.get("narration_tone", "calm")

            elif field == "lighting":
                # Modify lighting in style
                if "lighting" in suggested_modifications:
                    modified_ir["style"]["lighting"] = suggested_modifications["lighting"]

            elif field == "emotion":
                # Modify emotion curve
                if "emotion" in suggested_modifications:
                    modified_ir["emotion_curve"] = suggested_modifications["emotion"]

            elif field == "pacing":
                # Modify pacing (duration)
                if "duration" in suggested_modifications:
                    modified_ir["duration_preference_s"] = suggested_modifications["duration"]

        return modified_ir

    def _should_modify_shot(
        self,
        shot: Dict[str, Any],
        targeted_fields: List[str],
    ) -> bool:
        """
        Determine if a shot should be modified based on targeted fields

        Args:
            shot: Shot dictionary
            targeted_fields: Fields being modified

        Returns:
            True if shot should be modified
        """
        # For simplicity, modify all shots if any field is targeted
        # In production, could be more selective
        return len(targeted_fields) > 0

    def _classify_error(self, error: Exception) -> Dict[str, Any]:
        """
        Classify error for retry determination

        Args:
            error: Exception to classify

        Returns:
            Dict with code, classification, retryable flag
        """
        if isinstance(error, FFmpegError):
            return {
                "code": error.code,
                "message": error.message,
                "classification": "non_retryable",
                "retryable": False,
            }
        elif isinstance(error, asyncio.TimeoutError):
            return {
                "code": "TIMEOUT",
                "message": "Operation timed out",
                "classification": "retryable",
                "retryable": True,
            }
        else:
            return {
                "code": "UNKNOWN_ERROR",
                "message": str(error),
                "classification": "non_retryable",
                "retryable": False,
            }

    async def finalize_job(
        self,
        db: Session,
        job_id: str,
        selected_seeds: Dict[int, int],
    ) -> JobModel:
        """
        Finalize job by regenerating selected shots at 1080P

        Args:
            db: Database session
            job_id: Job ID to finalize
            selected_seeds: Dict mapping shot_id to selected seed

        Returns:
            Updated JobModel
        """
        # Get job
        job = JobDB.get_job(db, job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Update selected seeds
        JobDB.update_job_selected_seeds(db, job_id, selected_seeds)

        # Regenerate shots at 1080P
        # TODO: Implement finalization workflow

        return job

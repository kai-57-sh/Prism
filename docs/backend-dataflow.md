# Backend Data Flow (Input to Output)

This document describes the current backend data flow based on the FastAPI service
implementation. It includes sequence diagrams, flowcharts, data stores, external
dependencies, and error branches.

## Scope

- Primary flows:
  - `POST /v1/t2v/generate` (synchronous full generation)
  - `POST /v1/t2v/plan` + `POST /v1/t2v/jobs/{job_id}/render` (recommended async path)
- Support flows: `GET /v1/t2v/jobs/{job_id}`, `POST /v1/t2v/jobs/{job_id}/revise`,
  `POST /v1/t2v/jobs/{job_id}/finalize`, shot update/regenerate
- Data stores: `jobs` and `templates` tables, filesystem static assets
- External services: LLM, embeddings, DashScope video, Redis, ffmpeg, RQ worker

Note: `POST /v1/t2v/generate` executes the full workflow inside the request and
returns after generation completes (still with HTTP 202).

## Data Stores

- SQLite database (default `sqlite:///./data/jobs.db`)
  - `jobs` table (see `backend/src/models/job.py`)
    - Inputs: `user_input_redacted`, `user_input_hash`, `pii_flags`
    - Pipeline: `ir`, `shot_plan`, `shot_requests`
    - Outputs: `shot_assets` (may include multiple candidates per shot),
      `preview_shot_assets` (currently not written), `selected_seeds`,
      `resolution`, `total_duration_s`
    - Lifecycle: `state`, `state_transitions`, timestamps
    - Errors: `error_details`, retry fields
  - `templates` table (see `backend/src/models/template.py`)
    - `template_id`, `version`, `tags`, `constraints`, `shot_skeletons`,
      `negative_prompt_base`
- Filesystem static storage
  - Default: `/var/lib/prism/static`, fallback to `backend/data`
  - Subdirs: `vedios/`, `audio/`, `metadata/` (note spelling `vedios`)

## External Dependencies

- ModelScope Qwen LLM (IR parsing, template instantiation, feedback parsing)
  - `LLMOrchestrator` and `FeedbackParser`
- DashScope embeddings (template semantic search)
  - `TemplateRouter` + FAISS index
- DashScope Wan2.6 text-to-video API
  - `Wan26RetryAdapter` submit/poll
- Redis
  - Rate limiting and concurrent job tracking
  - RQ queue for `/render` async jobs
- HTTP download (httpx)
  - Download generated videos from DashScope URL
- ffmpeg/ffprobe
  - Split video into video-only and audio-only outputs

## State Transitions

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> SUBMITTED : job_created / planning_submitted
    CREATED --> FAILED : generation_failed
    SUBMITTED --> RUNNING : generation_started / planning_started
    SUBMITTED --> FAILED : generation_failed
    RUNNING --> SUCCEEDED : generation_complete / planning_complete
    RUNNING --> FAILED : generation_failed
    SUCCEEDED --> RUNNING : finalization_started / revision_started
```

## Sequence Diagram: Generate Flow (Sync)

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/generate
    participant RL as RateLimiter (Redis)
    participant JM as JobManager
    participant IP as InputProcessor
    participant LLM as LLMOrchestrator (ModelScope)
    participant TR as TemplateRouter (FAISS + Embeddings)
    participant V as Validator
    participant PC as PromptCompiler
    participant DB as SQLite (jobs/templates)
    participant W26 as Wan26Adapter (DashScope)
    participant DL as Wan26Downloader (HTTPX)
    participant FF as FFmpeg
    participant FS as AssetStorage (Filesystem)

    Client->>API: POST /v1/t2v/generate
    API->>RL: check_rate_limit + check_concurrent_jobs
    alt rate limited or concurrent limit
        RL-->>API: not allowed
        API-->>Client: 400 (VALIDATION_ERROR)
    else allowed
        API->>JM: execute_generation_workflow(...)
        JM->>IP: process_input(user_input)
        IP-->>JM: redacted_text, input_hash, pii_flags
        JM->>LLM: parse_ir(aligned_text or redacted_text)
        LLM-->>JM: IR
        JM->>TR: match_template(IR)
        TR-->>JM: TemplateMatch or None
        alt no template match
            JM-->>API: ValueError
            API-->>Client: 400 (CLARIFICATION_REQUIRED / VALIDATION_ERROR)
        else match
            JM->>LLM: instantiate_template(IR, template)
            LLM-->>JM: ShotPlan
            JM->>JM: normalize_shot_plan
            JM->>V: validate_parameters(IR, ShotPlan, quality_mode)
            alt validation fails
                V-->>JM: suggestions
                JM-->>API: ValueError
                API-->>Client: 400 (VALIDATION_ERROR)
            else validation ok
                JM->>PC: compile_shot_prompt per shot
                PC-->>JM: shot_requests
                JM->>DB: JobDB.create_job(...) -> jobs
                JM->>DB: transition_state SUBMITTED -> RUNNING
                loop per shot (preview seeds by quality mode)
                    JM->>W26: submit_shot_request_with_retry
                    W26-->>JM: task_id
                    JM->>W26: poll_task_status
                    alt generation succeeded
                        W26-->>JM: video_url
                        JM->>DL: download(video_url)
                        DL-->>JM: temp_video_path
                        JM->>FF: split_video_audio(temp)
                        alt ffmpeg ok
                            FF-->>JM: video_path, audio_path, duration
                        else ffmpeg error
                            FF-->>JM: error
                            JM->>JM: fallback store video only
                        end
                        JM->>FS: paths/urls + write metadata
                        JM->>DB: update_job_assets (incremental)
                    else generation failed
                        W26-->>JM: error
                        JM->>JM: log error and continue
                    end
                end
                JM->>DB: update_job_assets
                JM->>FS: write_job_metadata(job_id)
                JM->>DB: transition_state RUNNING -> SUCCEEDED/FAILED
                API-->>Client: 202 (job_id, status)
            end
        end
    end
```

## Sequence Diagram: Plan + Render (Async)

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/plan
    participant JM as JobManager
    participant LLM as LLMOrchestrator
    participant TR as TemplateRouter
    participant DB as SQLite

    Client->>API: POST /v1/t2v/plan
    API->>JM: execute_planning_workflow(...)
    JM->>LLM: parse_ir
    JM->>TR: match_template
    JM->>LLM: instantiate_template
    JM->>DB: create job (shot_plan + shot_requests)
    JM->>DB: transition SUBMITTED -> RUNNING -> SUCCEEDED
    API-->>Client: 202 (job_id)
```

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/jobs/{job_id}/render
    participant RL as RateLimiter (Redis)
    participant RQ as RQ Queue
    participant Worker as rq worker
    participant JM as JobManager
    participant DB as SQLite

    Client->>API: POST /render
    API->>RL: check_rate_limit + check_concurrent_jobs
    alt blocked
        API-->>Client: 400 (RENDER_ERROR)
    else allowed
        API->>RQ: enqueue run_render_job(job_id)
        API-->>Client: 202 (queued)
        RQ->>Worker: run_render_job
        Worker->>JM: execute_generation_from_job(...)
        JM->>DB: transition SUBMITTED -> RUNNING
        JM->>DB: update assets incrementally
        JM->>DB: transition RUNNING -> SUCCEEDED/FAILED
    end
```

## Sequence Diagram: Job Status Query

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/jobs/{job_id}
    participant DB as SQLite (jobs)

    Client->>API: GET /v1/t2v/jobs/{job_id}
    API->>DB: JobDB.get_job(job_id)
    alt job not found
        API-->>Client: 404 JOB_NOT_FOUND
    else found
        API-->>Client: 200 with status + shot_plan + assets
    end
```

## Sequence Diagram: Revision Flow (Sync)

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/jobs/{job_id}/revise
    participant DB as SQLite
    participant FP as FeedbackParser
    participant V as Validator
    participant JM as JobManager

    Client->>API: POST /revise {feedback}
    API->>DB: JobDB.get_job(parent_job_id)
    alt not found or not SUCCEEDED
        API-->>Client: 404 or 400 INVALID_JOB_STATE
    else ok
        API->>FP: parse_feedback(feedback, previous_ir)
        API->>V: validate_refinement
        alt invalid
            API-->>Client: 400 INVALID_REFINEMENT
        else ok
            API->>JM: execute_revision_workflow(...)
            JM->>DB: create new job
            JM->>DB: generate shots (sync in request)
            JM->>DB: update assets + transition SUCCEEDED/FAILED
            API-->>Client: 202 (new job_id)
        end
    end
```

## Sequence Diagram: Shot Update / Regenerate

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/jobs/{job_id}/shots/{shot_id}
    participant DB as SQLite
    participant JM as JobManager

    Client->>API: PATCH /shots/{shot_id}
    API->>DB: update shot_plan
    API-->>Client: updated shot

    Client->>API: POST /shots/{shot_id}/regenerate
    API->>DB: check job state SUCCEEDED
    API->>JM: compile_shot_prompt + generate single shot
    JM->>DB: update assets
    API-->>Client: new asset
```

## Sequence Diagram: Finalization Flow

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/jobs/{job_id}/finalize
    participant DB as SQLite
    participant JM as JobManager

    Client->>API: POST /finalize {selected_seeds}
    API->>DB: JobDB.get_job(job_id)
    alt not found or not SUCCEEDED
        API-->>Client: 404 or 400 INVALID_JOB_STATE
    else ok
        API->>API: validate preview_shot_assets
        alt no preview assets
            API-->>Client: 400 NO_PREVIEW_ASSETS
        else ok
            API->>JM: execute_finalization_workflow
            JM->>DB: transition RUNNING -> SUCCEEDED/FAILED
            API-->>Client: 202 (job_id)
        end
    end
```

## Asset Outputs

- Video URL: `/<static_prefix>/<video_subdir>/YYYY/MM/DD/{job_id}_shot_{shot_id}.mp4`
- Audio URL: `/<static_prefix>/<audio_subdir>/YYYY/MM/DD/{job_id}_shot_{shot_id}.mp3`
- Metadata URL: `/<static_prefix>/<metadata_subdir>/{job_id}.json`

Paths are generated by `AssetStorage` in `backend/src/services/asset_storage.py`.

## Error Handling (API Layer)

- Request validation failures are returned as 400 with `VALIDATION_ERROR`.
- `ValueError` can be mapped to 400 with `INVALID_VALUE` by the global handler,
  but most route handlers convert `ValueError` to `VALIDATION_ERROR` explicitly.
- Any unhandled exception becomes 500 with `INTERNAL_ERROR`.

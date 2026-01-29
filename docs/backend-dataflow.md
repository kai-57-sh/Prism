# Backend Data Flow (Input to Output)

This document describes the current backend data flow based on the FastAPI service
implementation. It includes sequence diagrams, flowcharts, data stores, external
dependencies, and error branches.

## Scope

- Primary flow: `POST /v1/t2v/generate` (text to video generation)
- Support flows: `GET /v1/t2v/jobs/{job_id}`, `POST /v1/t2v/jobs/{job_id}/revise`,
  `POST /v1/t2v/jobs/{job_id}/finalize`
- Data stores: `jobs` and `templates` tables, filesystem static assets
- External services: LLM, embeddings, DashScope video, Redis, ffmpeg

Note: `POST /v1/t2v/generate` executes the full workflow synchronously and returns
after generation completes, even though it returns HTTP 202.

## Data Stores

- SQLite database (default `sqlite:///./data/jobs.db`)
  - `jobs` table (see `backend/src/models/job.py`)
    - Inputs: `user_input_redacted`, `user_input_hash`, `pii_flags`
    - Pipeline: `ir`, `shot_plan`, `shot_requests`
    - Outputs: `shot_assets`, `preview_shot_assets`, `selected_seeds`, `resolution`,
      `total_duration_s`
    - Lifecycle: `state`, `state_transitions`, timestamps
    - Errors: `error_details`, retry fields
  - `templates` table (see `backend/src/models/template.py`)
    - `template_id`, `version`, `tags`, `constraints`, `shot_skeletons`,
      `negative_prompt_base`
- Filesystem static storage (default `/var/lib/prism/static`, fallback `./data`)
  - `videos/`, `audio/`, `metadata/` subdirs via `AssetStorage`

## External Dependencies

- ModelScope Qwen LLM (IR parsing, template instantiation, feedback parsing)
  - `LLMOrchestrator` and `FeedbackParser`
- DashScope embeddings (template semantic search)
  - `TemplateRouter` + FAISS index
- DashScope Wan2.6 text-to-video API
  - `Wan26RetryAdapter` submit/poll
- Redis
  - Rate limiting and concurrent job tracking
- HTTP download (httpx)
  - Download generated videos from DashScope URL
- ffmpeg/ffprobe
  - Split video into video-only and audio-only outputs

## State Transitions

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> SUBMITTED : job_created
    CREATED --> FAILED : generation_failed
    SUBMITTED --> RUNNING : generation_started
    SUBMITTED --> FAILED : generation_failed
    RUNNING --> SUCCEEDED : generation_complete
    RUNNING --> FAILED : generation_failed
    SUCCEEDED --> RUNNING : finalization_started / revision_started
```

## Sequence Diagram: Generate Flow

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
        JM->>TR: match_template(IR, templates)
        TR->>DB: list templates if index empty
        alt no template match
            TR-->>JM: None
            JM-->>API: ValueError (clarification or validation)
            API-->>Client: 400 (CLARIFICATION_REQUIRED / VALIDATION_ERROR)
        else match
            TR-->>JM: TemplateMatch
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
                loop per shot (and per preview seed)
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
                        JM->>FS: get paths/urls + write metadata
                    else generation failed
                        W26-->>JM: error
                        JM->>JM: log error and continue
                    end
                end
                JM->>DB: update_job_assets or update_job_error
                JM->>FS: write_job_metadata(job_id)
                JM->>DB: transition_state RUNNING -> SUCCEEDED/FAILED
                API-->>Client: 202 (job_id, status)
            end
        end
    end
```

## Flowchart: Generate Pipeline (with Error Branches)

```mermaid
flowchart TD
    A[HTTP POST /v1/t2v/generate] --> B[Validate request fields]
    B --> C[Rate limit + concurrent limit (Redis)]
    C -->|blocked| C1[Return 400 VALIDATION_ERROR]
    C -->|allowed| D[InputProcessor: redact + detect + align]
    D --> E[LLM: parse IR]
    E --> F[TemplateRouter: match template]
    F -->|no match| F1[Return 400 CLARIFICATION_REQUIRED]
    F -->|match| G[LLM: instantiate template -> ShotPlan]
    G --> H[Validator: validate parameters]
    H -->|invalid| H1[Return 400 VALIDATION_ERROR]
    H -->|ok| I[PromptCompiler: compile per-shot prompts]
    I --> J[JobDB.create_job -> jobs table]
    J --> K[Transition SUBMITTED -> RUNNING]
    K --> L[Wan2.6: submit + poll]
    L -->|failed| L1[Log error, continue]
    L -->|succeeded| M[Download video (HTTPX)]
    M --> N[FFmpeg split video/audio]
    N -->|ffmpeg failed| N1[Store video only]
    N -->|ok| O[Store video+audio]
    N1 --> O
    O --> P[AssetStorage: URLs + metadata JSON]
    P --> Q[Update job assets + write metadata]
    Q --> R[Transition RUNNING -> SUCCEEDED/FAILED]
    R --> S[Return 202 + job_id]
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
        DB-->>API: None
        API-->>Client: 404 JOB_NOT_FOUND
    else found
        DB-->>API: JobModel
        API-->>Client: 200 with status + assets (if SUCCEEDED)
    end
```

## Sequence Diagram: Revision Flow

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/jobs/{job_id}/revise
    participant DB as SQLite (jobs/templates)
    participant FP as FeedbackParser (ModelScope)
    participant V as Validator
    participant JM as JobManager
    participant LLM as LLMOrchestrator
    participant PC as PromptCompiler
    participant W26 as Wan26Adapter
    participant DL as Wan26Downloader
    participant FF as FFmpeg
    participant FS as AssetStorage

    Client->>API: POST /revise {feedback}
    API->>DB: JobDB.get_job(parent_job_id)
    alt not found or not SUCCEEDED
        API-->>Client: 404 or 400 INVALID_JOB_STATE
    else ok
        API->>FP: parse_feedback(feedback, previous_ir)
        FP-->>API: targeted_fields + suggested_modifications
        API->>V: validate_refinement(feedback, targeted_fields)
        alt invalid refinement
            API-->>Client: 400 INVALID_REFINEMENT
        else ok
            API->>JM: execute_revision_workflow(...)
            JM->>DB: load template
            JM->>LLM: instantiate_template(modified IR)
            JM->>PC: compile prompts for targeted shots
            JM->>DB: create new job (revision_of=parent)
            JM->>W26: generate per shot (submit/poll)
            JM->>DL: download
            JM->>FF: split
            JM->>FS: write metadata
            JM->>DB: update assets + transition SUCCEEDED/FAILED
            API-->>Client: 202 (new job_id)
        end
    end
```

## Sequence Diagram: Finalization Flow

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant API as FastAPI /v1/t2v/jobs/{job_id}/finalize
    participant DB as SQLite (jobs)
    participant JM as JobManager
    participant W26 as Wan26Adapter
    participant DL as Wan26Downloader
    participant FF as FFmpeg
    participant FS as AssetStorage

    Client->>API: POST /finalize {selected_seeds}
    API->>DB: JobDB.get_job(job_id)
    alt not found or not SUCCEEDED
        API-->>Client: 404 or 400 INVALID_JOB_STATE
    else ok
        API->>API: validate seeds against preview_shot_assets
        alt no preview assets or invalid seeds
            API-->>Client: 400 NO_PREVIEW_ASSETS / INVALID_SEEDS
        else ok
            API->>JM: execute_finalization_workflow(...)
            JM->>DB: update selected_seeds + transition RUNNING
            JM->>W26: generate selected shots at 1920x1080
            JM->>DL: download
            JM->>FF: split
            JM->>FS: write metadata
            JM->>DB: update assets + transition SUCCEEDED/FAILED
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

- Request validation failures are returned as 400 with `VALIDATION_ERROR`
  (`backend/src/api/main.py`).
- `ValueError` is mapped to 400 with `INVALID_VALUE`.
- Any unhandled exception becomes 500 with `INTERNAL_ERROR`.

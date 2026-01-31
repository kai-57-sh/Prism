# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Prism is a medical text-to-video agent that generates emotional and storytelling videos from natural language input. The system uses two external APIs:
- **DashScope Wan2.6-t2v** for text-to-video generation
- **ModelScope Qwen3-235B-A22B-Instruct-2507** for LLM-based orchestration

## Development Commands

### Environment Setup
```bash
./scripts/setup.sh          # Create venv and install dependencies
```

### Running the Application
```bash
cd backend
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
./scripts/test.sh           # Run all tests (unit, integration, contract)
pytest tests/unit/ -v       # Run only unit tests
pytest tests/integration/ -v  # Run only integration tests
pytest tests/contract/ -v   # Run only contract tests
```

### Code Quality
```bash
ruff check .                # Lint code
black .                     # Format code
mypy backend/src/           # Type checking
```

### API Testing
```bash
python docs/reference-pre/wan2.6.py                           # Test Wan2.6-t2v video generation
python docs/reference-pre/Qwen3-235B-A22B-Instruct-2507.py    # Test LLM integration
```

## Architecture

### Directory Structure
```
backend/
├── src/
│   ├── api/              # FastAPI routes (generation, jobs, finalize, revise)
│   ├── core/             # Core business logic
│   │   ├── wan26_adapter.py          # DashScope video generation wrapper
│   │   ├── llm_orchestrator.py       # LangChain chains for IR parsing & template instantiation
│   │   ├── template_router.py        # FAISS-based semantic template matching
│   │   ├── input_processor.py        # Input validation & preprocessing
│   │   ├── validator.py              # Business logic validation
│   │   └── prompt_compiler.py        # Jinja2-based prompt rendering
│   ├── models/           # SQLAlchemy data models (job, shot_plan, template, etc.)
│   ├── services/         # Service layer (job_manager, storage, ffmpeg_splitter, etc.)
│   ├── config/           # Configuration (settings.py with pydantic-settings)
│   └── utils/            # Utility functions
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── contract/         # OpenAPI contract tests
└── requirements.txt      # Python dependencies
```

### Key Architectural Patterns

**Request Flow:**
1. User input → API route (`/v1/t2v/generate`)
2. `InputProcessor` validates and preprocesses input
3. `LLMOrchestrator` parses intent into structured IR (Intermediate Representation)
4. `TemplateRouter` uses FAISS semantic search to match appropriate template
5. `LLMOrchestrator` instantiates template with shot-level details
6. `Wan26Adapter` submits shot requests to DashScope API
7. `JobManager` tracks job state and coordinates async video generation
8. `FFmpegSplitter` post-processes and concatenates shots
9. Final video delivered to user

**Dual LLM Usage:**
- **ModelScope Qwen3-235B**: Accessed via OpenAI-compatible API for intent parsing and template instantiation
- **LangChain integration**: Uses `ChatOpenAI` with ModelScope base URL

**Template System:**
- Templates stored in database, loaded via `TemplateDB`
- FAISS vector index enables semantic matching based on user input
- Jinja2-based prompt compilation for structured outputs

**State Management:**
- SQLAlchemy ORM with SQLite (configurable to PostgreSQL)
- Job state machine tracked in `JobManager`
- Redis for rate limiting

### API Endpoints

All routes under `/v1/t2v/`:
- `POST /generate` - Submit new video generation job
- `GET /jobs/{job_id}` - Get job status and details
- `POST /finalize/{job_id}` - Trigger ffmpeg post-processing
- `POST /revise/{job_id}` - Submit revision request

## Environment Configuration

Required environment variables (see `.env.example`):

```bash
# DashScope (Wan2.6-t2v video generation)
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx

# ModelScope (Qwen3-235B LLM)
MODELSCOPE_API_KEY=ms-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1
QWEN_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507

# Database & Storage
DATABASE_URL=sqlite:///./data/jobs.db
REDIS_URL=redis://localhost:6379/0
STATIC_ROOT=/var/lib/prism/static

# FFmpeg
FFMPEG_PATH=ffmpeg

# Application
LOG_LEVEL=INFO
```

## Code Style

- Python 3.11+
- Line length: 100 characters (ruff, black)
- Type hints required (mypy strict mode)
- Structlog for structured logging
- Pydantic v2 for data validation

## Key Dependencies

- `fastapi==0.104.1` - Web framework
- `langchain==0.1.0` - LLM orchestration
- `dashscope==1.17.0` - DashScope SDK for video generation
- `openai>=1.0.0` - OpenAI SDK (for ModelScope compatibility)
- `sqlalchemy==2.0.23` - ORM
- `pydantic==2.5.2` - Data validation
- `redis==5.0.1` - Rate limiting
- `faiss-cpu==1.7.4` - Vector search for template matching
- `jinja2==3.1.2` - Template rendering

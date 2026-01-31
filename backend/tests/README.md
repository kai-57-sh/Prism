# Prism Backend Test Suite

Complete test suite for the Prism Medical Text-to-Video backend system.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_input_processor.py       # Input processing tests
│   ├── test_template_router.py       # Template routing tests
│   ├── test_validator.py              # Validation tests
│   ├── test_prompt_compiler.py        # Prompt compilation tests
│   ├── test_wan26_adapter.py          # Wan2.6 adapter tests
│   ├── test_rate_limiter.py           # Rate limiting tests
│   └── test_models.py                 # Data model tests
├── integration/             # Integration tests
│   ├── test_qwen_integration.py       # Qwen LLM integration
│   ├── test_wan26_integration.py      # Wan2.6 video generation
│   ├── test_storage.py                # Database operations
│   ├── test_workflows.py              # End-to-end workflows
│   └── test_api_e2e.py                # API endpoint tests
├── contract/                # Contract tests
│   └── test_openapi.py              # OpenAPI spec validation
└── fixtures/                # Test fixtures and data
```

## Test Categories

### 1. Unit Tests

Test individual components in isolation with mocked dependencies.

- **Input Processor**: PII redaction, language detection, translation
- **Template Router**: Template matching and similarity scoring
- **Validator**: Shot plan validation, medical compliance
- **Prompt Compiler**: Prompt generation and enhancement
- **Wan26 Adapter**: Video generation API interaction
- **Rate Limiter**: Request throttling and concurrency limits
- **Data Models**: Job, IR, Shot Plan, Template models

### 2. Integration Tests

Test component interactions and real API calls.

- **Qwen Integration**: Real LLM calls for IR parsing and template instantiation
- **Wan26 Integration**: Real video generation with DashScope
- **Storage**: Database CRUD operations
- **Workflows**: Complete generation, finalization, and revision workflows
- **API E2E**: FastAPI endpoint testing

### 3. Contract Tests

Validate API specifications and compliance.

- **OpenAPI Spec**: Schema validation and endpoint verification

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Install pytest (if not in requirements):
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Run All Tests

```bash
cd backend
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Contract tests only
pytest tests/contract/ -v
```

### Run Specific Test Files

```bash
# Test input processor
pytest tests/unit/test_input_processor.py -v

# Test Qwen integration
pytest tests/integration/test_qwen_integration.py -v

# Test with output
pytest tests/unit/test_input_processor.py -v -s
```

### Using Test Runner Script

```bash
cd backend
chmod +x run_tests.sh

# Run unit tests
./run_tests.sh unit

# Run integration tests
./run_tests.sh integration

# Run all tests
./run_tests.sh all

# Run with coverage
./run_tests.sh all --coverage

# Verbose output
./run_tests.sh all -v

# Skip integration tests (for quick CI)
./run_tests.sh all --skip-integration
```

### Test Coverage

Generate coverage report:

```bash
# Terminal output
pytest tests/ --cov=src --cov-report=term

# HTML report
pytest tests/ --cov=src --cov-report=html

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Fixtures

### Available Fixtures (in `conftest.py`)

#### Database Fixtures
- `test_db_path`: Temporary database file
- `test_db_engine`: SQLAlchemy test engine
- `test_db_session`: Database session for tests

#### Mock Fixtures
- `mock_qwen_llm`: Mocked Qwen LLM
- `mock_dashscope_client`: Mocked DashScope client
- `mock_redis`: Mocked Redis client
- `async_mock_client`: Async HTTP client mock

#### Data Fixtures
- `sample_ir`: Sample intermediate representation
- `sample_template`: Sample medical scene template
- `sample_shot_plan`: Sample shot plan
- `sample_job`: Sample job model

#### Environment Fixtures
- `mock_env_vars`: Mock environment variables for testing
- `test_settings`: Test configuration overrides

### Using Fixtures in Tests

```python
import pytest

class TestMyComponent:
    @pytest.fixture
    def my_component(self, test_db_session):
        """Create component with database session"""
        from src.core.my_component import MyComponent
        return MyComponent(db_session=test_db_session)

    def test_component(self, my_component, sample_ir):
        """Test using component and sample data"""
        result = my_component.process(sample_ir)
        assert result is not None
```

## Writing Tests

### Unit Test Example

```python
import pytest
from src.core.my_component import MyComponent

class TestMyComponent:
    @pytest.fixture
    def component(self):
        return MyComponent()

    def test_functionality(self, component):
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = component.process(input_data)

        # Assert
        assert result.expected_field == "expected_value"
```

### Integration Test Example

```python
import pytest
from unittest.mock import patch

@pytest.mark.skipif(
    not os.getenv("API_KEY"),
    reason="API_KEY not set"
)
class TestAPIIntegration:
    @pytest.mark.asyncio
    async def test_api_call(self):
        # Make real API call
        response = await api_client.call()

        assert response.status_code == 200
        assert response.data
```

### Async Test Example

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

## Test Markers

Skip tests conditionally:

```python
# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("API_KEY"),
    reason="API_KEY not set"
)

# Skip slow tests
@pytest.mark.slow
def test_slow_operation():
    pass

# Skip manual test
@pytest.mark.skip(reason="Manual test")
def test_manual():
    pass

# Run specific markers
pytest tests/ -m "not slow"
```

## Mocking

### Using unittest.mock

```python
from unittest.mock import Mock, patch, AsyncMock

def test_with_mock():
    # Create mock
    mock_llm = Mock()
    mock_llm.invoke.return_value = Mock(content="Test response")

    # Patch
    with patch('src.core.llm_orchestrator.ChatOpenAI', return_value=mock_llm):
        result = function_that_uses_llm()

    assert result == "expected"
```

### Async Mocking

```python
@pytest.mark.asyncio
async def test_async_mock():
    mock_adapter = AsyncMock()
    mock_adapter.submit.return_value = Mock(task_id="123")

    result = await async_function(mock_adapter)

    assert result == "123"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run unit tests
        run: |
          cd backend
          pytest tests/unit/ -v --cov=src

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Debugging Tests

### Run with PDB

```bash
# Drop into debugger on failure
pytest tests/unit/test_input_processor.py -v --pdb

# Drop into debugger on error
pytest tests/unit/test_input_processor.py -v --pdb-trace
```

### Print Debugging

```bash
# Show print statements
pytest tests/unit/test_input_processor.py -v -s
```

### Stop on First Failure

```bash
pytest tests/ -v -x
```

## Troubleshooting

### Import Errors

Ensure `src/` is in Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Database Locks

Use temporary databases for tests:
```python
@pytest.fixture
def test_db_path():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        yield f.name
    os.unlink(f.name)
```

### AsyncIO Errors

Install pytest-asyncio:
```bash
pip install pytest-asyncio
```

Add to `conftest.py`:
```python
pytest_plugins = ['pytest_asyncio']
```

### API Key Errors

Create `.env` file with test keys:
```bash
MODELSCOPE_API_KEY=ms-test-key
DASHSCOPE_API_KEY=test-key
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Reuse test data through fixtures
3. **Mocking**: Mock external dependencies (APIs, databases)
4. **Async**: Use `@pytest.mark.asyncio` for async tests
5. **Cleanup**: Clean up resources in fixtures
6. **Documentation**: Add docstrings to test classes and methods
7. **Coverage**: Aim for >80% code coverage
8. **Speed**: Unit tests should be fast (<1s each)
9. **Clarity**: Use descriptive test names

## Contributing

When adding new features:

1. Write unit tests first (TDD)
2. Add integration tests for workflows
3. Update fixtures if needed
4. Ensure all tests pass before committing
5. Add docstrings to tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Asyncio](https://pytest-asyncio.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

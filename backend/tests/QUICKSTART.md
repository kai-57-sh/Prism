# Prism Backend Test Suite - 快速开始

## 测试套件概览

已为 Prism 后端创建完整的测试套件，包含 **99+ 个测试**，覆盖所有核心组件。

### 测试文件统计

- **总文件数**: 17 个
- **单元测试**: 7 个文件，62+ 个测试
- **集成测试**: 5 个文件，31+ 个测试
- **契约测试**: 1 个文件（已存在）
- **配置文件**: 4 个文件

## 文件结构

```
tests/
├── __init__.py                      # 测试包初始化
├── conftest.py                      # Pytest 配置和共享 fixtures
├── README.md                        # 详细文档
├── TEST_SUMMARY.md                  # 测试总结
├── QUICKSTART.md                    # 本文件
├── fixtures/                        # 测试数据
│   ├── __init__.py
│   └── sample_data.py               # 示例 IR、模板、shot plan
├── unit/                            # 单元测试
│   ├── test_input_processor.py      # 输入处理器测试
│   ├── test_template_router.py      # 模板路由测试
│   ├── test_validator.py            # 验证器测试
│   ├── test_prompt_compiler.py      # 提示词编译测试
│   ├── test_wan26_adapter.py        # Wan2.6 适配器测试
│   ├── test_rate_limiter.py         # 速率限制测试
│   └── test_models.py               # 数据模型测试
├── integration/                     # 集成测试
│   ├── test_qwen_integration.py     # Qwen LLM 集成
│   ├── test_wan26_integration.py    # Wan2.6 视频生成
│   ├── test_storage.py              # 数据库操作
│   ├── test_workflows.py            # 工作流测试
│   └── test_api_e2e.py              # API 端到端测试
└── contract/                        # 契约测试
    └── test_openapi.py              # OpenAPI 规范验证
```

## 快速开始

### 1. 安装测试依赖

```bash
cd backend
pip install -r requirements.txt
```

测试依赖包括：
- `pytest==7.4.3` - 测试框架
- `pytest-asyncio==0.21.1` - 异步测试支持
- `pytest-cov==4.1.0` - 代码覆盖率
- `pytest-mock==3.12.0` - Mock 支持
- `python-dotenv==1.0.0` - 环境变量

### 2. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，添加 API 密钥
# DASHSCOPE_API_KEY=your_key_here
# MODELSCOPE_API_KEY=ms-your_key_here
```

### 3. 验证设置

```bash
python test_setup.py
```

这将检查：
- ✓ 模块导入
- ✓ 环境配置
- ✓ 数据库连接
- ✓ 测试 fixtures

## 运行测试

### 使用测试脚本（推荐）

```bash
# 运行单元测试
./run_tests.sh unit

# 运行集成测试（需要 API 密钥）
./run_tests.sh integration

# 运行所有测试
./run_tests.sh all

# 生成覆盖率报告
./run_tests.sh all --coverage

# 详细输出
./run_tests.sh all -v

# 跳过集成测试（快速 CI）
./run_tests.sh all --skip-integration
```

### 手动运行

```bash
# 只运行单元测试
pytest tests/unit/ -v

# 只运行集成测试
pytest tests/integration/ -v

# 运行特定文件
pytest tests/unit/test_input_processor.py -v

# 显示输出
pytest tests/unit/test_input_processor.py -v -s

# 生成覆盖率
pytest tests/ --cov=src --cov-report=html

# 打开覆盖率报告
open htmlcov/index.html  # macOS
```

## 测试分类

### 单元测试 (Unit Tests)

**特点**:
- 快速执行（每个 < 1 秒）
- 不需要外部依赖
- 使用 mocked 组件

**覆盖组件**:
- 输入处理器 (PII 脱敏、语言检测)
- 模板路由器（匹配、相似度）
- LLM 编排器（IR 解析、模板实例化）
- 验证器（验证规则、医疗合规）
- 提示词编译器（提示词生成）
- Wan2.6 适配器（API 交互）
- 速率限制器（请求限制）
- 数据模型（Job, IR, ShotPlan）

**示例**:
```bash
pytest tests/unit/ -v
# 62+ tests, < 1 minute
```

### 集成测试 (Integration Tests)

**特点**:
- 真实 API 调用
- 需要有效的 API 密钥
- 执行时间较长（1-60 秒）

**测试内容**:
- Qwen LLM 集成（IR 解析、模板填充）
- Wan2.6 视频生成（真实调用）
- 数据库操作（CRUD）
- 完整工作流（生成、定稿、修订）
- API 端点测试

**示例**:
```bash
pytest tests/integration/test_qwen_integration.py -v
# 6 tests, real LLM calls
```

### 契约测试 (Contract Tests)

**特点**:
- 验证 API 规范
- 不需要 API 密钥
- 快速执行

**测试内容**:
- OpenAPI 规范验证
- 端点可用性
- 参数验证

**示例**:
```bash
pytest tests/contract/ -v
# 6 tests
```

## 测试 Fixtures

### 数据 Fixtures

```python
# 使用示例 IR
from tests.fixtures.sample_data import SAMPLE_IR

def test_with_ir():
    ir = SAMPLE_IR
    assert ir['topic'] == '失眠'
```

### 数据库 Fixtures

```python
def test_with_db(test_db_session):
    # 自动创建临时数据库
    from src.services.storage import JobDB
    job = JobModel(...)
    JobDB.create_job(test_db_session, job)
```

### Mock Fixtures

```python
def test_with_mock(mock_qwen_llm):
    # 自动 mock LLM
    mock_qwen_llm.invoke.return_value = Mock(content="测试回复")
```

## 覆盖率报告

### 生成覆盖率

```bash
# HTML 报告
pytest tests/ --cov=src --cov-report=html

# 终端报告
pytest tests/ --cov=src --cov-report=term

# 两者都有
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### 查看结果

```bash
# 在浏览器中打开
open htmlcov/index.html

# 查看终端输出
# 查看每个文件的覆盖率百分比
```

### 预期覆盖率

- **核心组件**: 100%
- **服务层**: 100%
- **数据模型**: 100%
- **API 端点**: 100%

## 编写新测试

### 单元测试模板

```python
import pytest
from src.core.my_component import MyComponent

class TestMyComponent:
    @pytest.fixture
    def component(self):
        return MyComponent()

    def test_basic_functionality(self, component):
        # Arrange
        input_data = {"key": "value"}

        # Act
        result = component.process(input_data)

        # Assert
        assert result.expected == "value"
```

### 集成测试模板

```python
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("API_KEY"),
    reason="API_KEY not set"
)
class TestMyIntegration:
    @pytest.mark.asyncio
    async def test_api_call(self):
        # 真实 API 调用
        response = await api_client.call()
        assert response.status_code == 200
```

## 故障排查

### 导入错误

```bash
# 确保 src 在 Python 路径中
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# 或者在测试目录运行
cd tests && pytest ../
```

### 数据库锁定

```bash
# 测试使用临时数据库，自动清理
# 如果出现锁定，删除测试数据库
rm -f test*.db
```

### API 密钥错误

```bash
# 检查环境变量
echo $DASHSCOPE_API_KEY
echo $MODELSCOPE_API_KEY

# 或在 .env 文件中设置
cat .env
```

### 异步测试错误

```bash
# 确保安装 pytest-asyncio
pip install pytest-asyncio
```

## CI/CD 集成

### GitHub Actions

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
      - name: Run tests
        run: |
          cd backend
          pytest tests/unit/ -v --cov=src
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 最佳实践

1. **测试隔离**: 每个测试独立运行
2. **使用 Fixtures**: 复用测试数据
3. **Mock 外部依赖**: API、数据库
4. **清晰命名**: 使用描述性测试名称
5. **快速反馈**: 单元测试应该快
6. **高覆盖率**: 目标 >80% 覆盖率
7. **文档化**: 为测试添加 docstring

## 参考文档

- **详细文档**: `tests/README.md`
- **测试总结**: `tests/TEST_SUMMARY.md`
- **示例数据**: `tests/fixtures/sample_data.py`
- **Pytest 文档**: https://docs.pytest.org/
- **FastAPI 测试**: https://fastapi.tiangolo.com/tutorial/testing/

## 支持

遇到问题？查看：
1. `tests/README.md` - 详细文档
2. `test_setup.py` - 设置验证
3. `conftest.py` - 可用的 fixtures
4. Pytest 文档 - 官方文档

---

**现在就开始测试！**

```bash
cd backend
python test_setup.py  # 验证设置
./run_tests.sh unit    # 运行单元测试
```

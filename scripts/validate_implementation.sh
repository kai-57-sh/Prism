#!/bin/bash
set -e

echo "=========================================="
echo "Prism Implementation Validation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VALIDATION_PASSED=0
VALIDATION_FAILED=0

# Function to check and report
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    VALIDATION_FAILED=$((VALIDATION_FAILED + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Checking Project Structure..."
echo "-----------------------------------"

# Check backend structure
for dir in backend/src/{api,core,models,services,templates,utils}; do
    if [ -d "/AII-wuqi/AII_home/fq_775/project-dev/Prism/$dir" ]; then
        check_pass "Directory exists: $dir"
    else
        check_fail "Missing directory: $dir"
    fi
done

# Check frontend structure
for dir in frontend/src/{client,ui,components,pages,services}; do
    if [ -d "/AII-wuqi/AII_home/fq_775/project-dev/Prism/$dir" ]; then
        check_pass "Directory exists: $dir"
    else
        check_fail "Missing directory: $dir"
    fi
done

# Check templates
if [ -f "/AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/templates/medical_scenes/insomnia_v1.json" ]; then
    check_pass "Template exists: insomnia_v1.json"
else
    check_fail "Missing template: insomnia_v1.json"
fi

echo ""
echo "2. Checking Configuration Files..."
echo "-----------------------------------"

# Check config files
for file in backend/requirements.txt backend/pyproject.toml frontend/requirements.txt .env.example .gitignore; do
    if [ -f "/AII-wuqi/AII_home/fq_775/project-dev/Prism/$file" ]; then
        check_pass "File exists: $file"
    else
        check_fail "Missing file: $file"
    fi
done

echo ""
echo "3. Checking Docker Configuration..."
echo "-----------------------------------"

# Check Docker files
for file in backend/Dockerfile frontend/Dockerfile docker/docker-compose.yml docker/nginx.conf; do
    if [ -f "/AII-wuqi/AII_home/fq_775/project-dev/Prism/$file" ]; then
        check_pass "Docker file exists: $file"
    else
        check_fail "Missing Docker file: $file"
    fi
done

echo ""
echo "4. Validating Python Syntax..."
echo "-----------------------------------"

# Check Python files for syntax errors
python_files=(
    "backend/src/config/settings.py"
    "backend/src/config/constants.py"
    "backend/src/models/__init__.py"
    "backend/src/models/job.py"
    "backend/src/services/storage.py"
    "backend/src/services/job_manager.py"
    "backend/src/core/input_processor.py"
    "backend/src/core/llm_orchestrator.py"
    "backend/src/core/template_router.py"
    "backend/src/core/validator.py"
    "backend/src/core/prompt_compiler.py"
    "backend/src/core/wan26_adapter.py"
    "backend/src/api/main.py"
    "backend/src/api/routes/generation.py"
    "backend/src/api/routes/jobs.py"
    "backend/src/api/routes/finalize.py"
)

for file in "${python_files[@]}"; do
    filepath="/AII-wuqi/AII_home/fq_775/project-dev/Prism/$file"
    if [ -f "$filepath" ]; then
        if python3 -m py_compile "$filepath" 2>/dev/null; then
            check_pass "Valid Python: $file"
        else
            check_fail "Syntax error in: $file"
        fi
    else
        check_fail "File not found: $file"
    fi
done

echo ""
echo "5. Validating JSON Templates..."
echo "-----------------------------------"

# Check template JSON validity
for template in backend/src/templates/medical_scenes/*.json; do
    filepath="/AII-wuqi/AII_home/fq_775/project-dev/Prism/$template"
    if [ -f "$filepath" ]; then
        if python3 -c "import json; json.load(open('$filepath'))" 2>/dev/null; then
            check_pass "Valid JSON: $template"
        else
            check_fail "Invalid JSON: $template"
        fi
    fi
done

echo ""
echo "6. Validating OpenAPI Specification..."
echo "-----------------------------------"

OPENAPI_FILE="/AII-wuqi/AII_home/fq_775/project-dev/Prism/specs/001-medical-t2v-agent/contracts/openapi.yaml"

if [ -f "$OPENAPI_FILE" ]; then
    check_pass "OpenAPI spec exists"

    # Check if YAML is valid
    if python3 -c "import yaml; yaml.safe_load(open('$OPENAPI_FILE'))" 2>/dev/null; then
        check_pass "OpenAPI YAML is valid"
    else
        check_warn "OpenAPI YAML has formatting issues (may need manual review)"
    fi

    # Check for required endpoints
    if grep -q "/v1/t2v/generate" "$OPENAPI_FILE"; then
        check_pass "Generate endpoint documented"
    else
        check_fail "Generate endpoint missing from spec"
    fi

    if grep -q "/v1/t2v/jobs/{job_id}" "$OPENAPI_FILE"; then
        check_pass "Jobs endpoint documented"
    else
        check_fail "Jobs endpoint missing from spec"
    fi

    if grep -q "/v1/t2v/jobs/{job_id}/finalize" "$OPENAPI_FILE"; then
        check_pass "Finalize endpoint documented"
    else
        check_fail "Finalize endpoint missing from spec"
    fi

    # Check for required schemas
    if grep -q "GenerateRequest" "$OPENAPI_FILE"; then
        check_pass "GenerateRequest schema exists"
    else
        check_fail "GenerateRequest schema missing"
    fi

    if grep -q "FinalizeRequest" "$OPENAPI_FILE"; then
        check_pass "FinalizeRequest schema exists"
    else
        check_fail "FinalizeRequest schema missing"
    fi
else
    check_fail "OpenAPI spec not found"
fi

echo ""
echo "7. Checking Import Dependencies..."
echo "-----------------------------------"

# Check if key imports are present in Python files
if grep -q "from fastapi import FastAPI" /AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/api/main.py; then
    check_pass "FastAPI import present"
else
    check_fail "FastAPI import missing"
fi

if grep -q "from sqlalchemy import" /AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/models/__init__.py; then
    check_pass "SQLAlchemy import present"
else
    check_fail "SQLAlchemy import missing"
fi

if grep -q "from langchain" /AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/core/llm_orchestrator.py; then
    check_pass "LangChain import present"
else
    check_fail "LangChain import missing"
fi

echo ""
echo "8. Verifying Data Models..."
echo "-----------------------------------"

# Check if model classes are defined
model_classes=(
    "JobModel"
    "TemplateModel"
    "IRModel"
    "ShotPlanModel"
)

for model in "${model_classes[@]}"; do
    if grep -r "class $model" /AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/models/ > /dev/null; then
        check_pass "Model defined: $model"
    else
        check_fail "Model missing: $model"
    fi
done

echo ""
echo "9. Checking API Route Registration..."
echo "-----------------------------------"

# Check if routes are registered in main.py
MAIN_FILE="/AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/api/main.py"

if grep -q "generation.router" "$MAIN_FILE"; then
    check_pass "Generation router registered"
else
    check_fail "Generation router not registered"
fi

if grep -q "jobs.router" "$MAIN_FILE"; then
    check_pass "Jobs router registered"
else
    check_fail "Jobs router not registered"
fi

if grep -q "finalize.router" "$MAIN_FILE"; then
    check_pass "Finalize router registered"
else
    check_fail "Finalize router not registered"
fi

echo ""
echo "10. Verifying Core Services..."
echo "-----------------------------------"

# Check if key service methods exist
if grep -q "def execute_generation_workflow" /AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/services/job_manager.py; then
    check_pass "Generation workflow method exists"
else
    check_fail "Generation workflow method missing"
fi

if grep -q "def execute_finalization_workflow" /AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/services/job_manager.py; then
    check_pass "Finalization workflow method exists"
else
    check_fail "Finalization workflow method missing"
fi

if grep -q "def parse_ir" /AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/core/llm_orchestrator.py; then
    check_pass "IR parser method exists"
else
    check_fail "IR parser method missing"
fi

if grep -q "def match_template" /AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/src/core/template_router.py; then
    check_pass "Template matcher method exists"
else
    check_fail "Template matcher method missing"
fi

echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $VALIDATION_PASSED${NC}"
echo -e "${RED}Failed: $VALIDATION_FAILED${NC}"
echo ""

if [ $VALIDATION_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All validations passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some validations failed. Please review the errors above.${NC}"
    exit 1
fi

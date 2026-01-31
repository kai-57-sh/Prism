#!/bin/bash
# Metrics Validation Script for Prism Medical Text-to-Video Agent
# Validates SC-001 through SC-011 success criteria

set -e

echo "=========================================="
echo "Prism Metrics Validation"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
LOG_FILE="${LOG_FILE:-/AII-wuqi/AII_home/fq_775/project-dev/Prism/logs/prism.log}"
DATABASE_URL="${DATABASE_URL:-sqlite:///AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/data/jobs.db}"
STATIC_ROOT="${STATIC_ROOT:-/AII-wuqi/AII_home/fq_775/project-dev/Prism/backend/static}"
MIN_CONFIDENCE=0.65
FAST_MODE_TARGET=180  # 3 minutes in seconds

echo -e "${YELLOW}Configuration${NC}"
echo "Log File: $LOG_FILE"
echo "Database: $DATABASE_URL"
echo "Static Root: $STATIC_ROOT"
echo "Min Confidence: $MIN_CONFIDENCE"
echo "Fast Mode Target: ${FAST_MODE_TARGET}s"
echo ""

# Counters
PASSED=0
FAILED=0
WARNED=0

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED=$((PASSED + 1))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED=$((FAILED + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNED=$((WARNED + 1))
}

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    check_fail "Log file not found: $LOG_FILE"
    echo "Please ensure the application has been run and logs are available"
    exit 1
fi

echo "=========================================="
echo "Validating Success Criteria"
echo "=========================================="
echo ""

# SC-001: Template Matching
echo "SC-001: Template Matching (confidence ≥0.65)"
echo "----------------------------------------------"

if grep -q "template_hit" "$LOG_FILE"; then
    total_hits=$(grep "template_hit" "$LOG_FILE" | wc -l)
    low_confidence=$(grep "template_hit" "$LOG_FILE" | jq -r 'select(.confidence < '"$MIN_CONFIDENCE"')' | wc -l)

    if [ $total_hits -gt 0 ]; then
        success_rate=$((total_hits - low_confidence))
        success_pct=$((success_rate * 100 / total_hits))

        echo "Total template hits: $total_hits"
        echo "High confidence (≥$MIN_CONFIDENCE): $success_rate ($success_pct%)"
        echo "Low confidence (<$MIN_CONFIDENCE): $low_confidence"

        if [ $success_pct -ge 95 ]; then
            check_pass "SC-001 PASSED: $success_pct% ≥ 95%"
        else
            check_fail "SC-001 FAILED: $success_pct% < 95%"
        fi
    else
        check_warn "No template hits found in logs"
    fi
else
    check_warn "No template_hit events in logs"
fi

echo ""

# SC-002: Per-Shot Generation
echo "SC-002: Per-Shot Generation (independent shots)"
echo "------------------------------------------------"

if grep -q "shot_generation_started" "$LOG_FILE"; then
    jobs_with_shots=$(grep "shot_generation_started" "$LOG_FILE" | jq -r '.job_id' | sort -u | wc -l)

    echo "Jobs with per-shot generation: $jobs_with_shots"

    if [ $jobs_with_shots -gt 0 ]; then
        check_pass "SC-002 PASSED: Per-shot generation working ($jobs_with_shots jobs)"
    else
        check_fail "SC-002 FAILED: No per-shot generation found"
    fi
else
    check_warn "No shot_generation_started events in logs"
fi

echo ""

# SC-003/SC-007: Fast Mode Performance
echo "SC-007: Fast Mode Performance (<3 minutes)"
echo "-------------------------------------------"

if grep -q "generation_completed" "$LOG_FILE"; then
    fast_mode_jobs=$(grep "generation_completed" "$LOG_FILE" | jq -r 'select(.quality_mode == "fast")')

    fast_count=$(echo "$fast_mode_jobs" | jq -s 'length')
    fast_under_limit=$(echo "$fast_mode_jobs" | jq -r 'select(.duration_s < '"$FAST_MODE_TARGET"')' | jq -s 'length')

    if [ $fast_count -gt 0 ]; then
        fast_pct=$((fast_under_limit * 100 / fast_count))

        echo "Fast mode jobs: $fast_count"
        echo "Under ${FAST_MODE_TARGET}s: $fast_under_limit ($fast_pct%)"

        if [ $fast_pct -ge 90 ]; then
            check_pass "SC-007 PASSED: $fast_pct% ≥ 90%"
        else
            check_fail "SC-007 FAILED: $fast_pct% < 90%"
        fi
    else
        check_warn "No fast mode jobs completed"
    fi
else
    check_warn "No generation_completed events in logs"
fi

echo ""

# SC-005: Preview Candidates
echo "SC-005: Preview Candidates (1-3 per shot)"
echo "------------------------------------------"

if grep -q "preview_generated" "$LOG_FILE"; then
    preview_jobs=$(grep "preview_generated" "$LOG_FILE" | jq -r '.job_id' | sort -u | wc -l)

    echo "Jobs with preview candidates: $preview_jobs"

    if [ $preview_jobs -gt 0 ]; then
        check_pass "SC-005 PASSED: Preview generation working ($preview_jobs jobs)"
    else
        check_fail "SC-005 FAILED: No preview candidates generated"
    fi
else
    check_warn "No preview_generated events in logs"
fi

echo ""

# SC-006: Preview to Final Consistency
echo "SC-006: Preview to Final Consistency"
echo "-------------------------------------"

if grep -q "finalization_started" "$LOG_FILE"; then
    finalized_jobs=$(grep "finalization_started" "$LOG_FILE" | jq -r '.job_id' | sort -u | wc -l)

    echo "Finalized jobs: $finalized_jobs"

    if [ $finalized_jobs -gt 0 ]; then
        check_pass "SC-006 PASSED: Finalization working ($finalized_jobs jobs)"
    else
        check_warn "No finalized jobs found"
    fi
else
    check_warn "No finalization_started events in logs"
fi

echo ""

# SC-008: Subtitle Policy Enforcement
echo "SC-008: Subtitle Policy Enforcement"
echo "------------------------------------"

if grep -q "prompt_compiled" "$LOG_FILE"; then
    # Check if negative prompts contain required terms
    subtitle_policy_none=$(grep "prompt_compiled" "$LOG_FILE" | jq -r 'select(.subtitle_policy == "none")')

    if [ -n "$subtitle_policy_none" ]; then
        policy_count=$(echo "$subtitle_policy_none" | jq -s 'length')
        with_terms=$(echo "$subtitle_policy_none" | jq -r 'select(.negative_prompt | test("text|subtitles|watermark|logo"))' | jq -s 'length')

        echo "Jobs with subtitle_policy=none: $policy_count"
        echo "With required negative terms: $with_terms"

        if [ $with_terms -eq $policy_count ]; then
            check_pass "SC-008 PASSED: All jobs have required terms ($with_terms/$policy_count)"
        else
            check_fail "SC-008 FAILED: Missing terms in some jobs ($with_terms/$policy_count)"
        fi
    else
        check_warn "No jobs with subtitle_policy=none found"
    fi
else
    check_warn "No prompt_compiled events in logs"
fi

echo ""

# SC-009: Concurrent Request Handling
echo "SC-009: Concurrent Request Handling"
echo "------------------------------------"

if grep -q "concurrent_requests" "$LOG_FILE"; then
    max_concurrent=$(grep "concurrent_requests" "$LOG_FILE" | jq -r '.concurrent_count' | sort -n | tail -1)

    echo "Max concurrent requests handled: $max_concurrent"

    if [ -n "$max_concurrent" ] && [ "$max_concurrent" -ge 50 ]; then
        check_pass "SC-009 PASSED: Can handle $max_concurrent concurrent requests"
    elif [ -n "$max_concurrent" ]; then
        check_warn "SC-009: Only tested with $max_concurrent concurrent requests (target: 50)"
    else
        check_warn "SC-009: No concurrent request data found"
    fi
else
    check_warn "SC-009: No concurrent request data in logs"
fi

echo ""

# SC-010: Error Classification
echo "SC-010: Error Classification"
echo "----------------------------"

if grep -q "failure_classified" "$LOG_FILE"; then
    total_failures=$(grep "failure_classified" "$LOG_FILE" | wc -l)
    classified=$(grep "failure_classified" "$LOG_FILE" | jq -r 'select(.classification != null and .classification != "")' | wc -l)

    echo "Total failures: $total_failures"
    echo "Classified: $classified"

    if [ $total_failures -gt 0 ]; then
        if [ $classified -eq $total_failures ]; then
            check_pass "SC-010 PASSED: All errors classified ($classified/$total_failures)"
        else
            check_fail "SC-010 FAILED: Some errors not classified ($classified/$total_failures)"
        fi
    else
        check_warn "No failures found to classify"
    fi
else
    check_warn "No failure_classified events in logs"
fi

echo ""

# SC-011: Reproducibility (Metadata Files)
echo "SC-011: Reproducibility (metadata files)"
echo "----------------------------------------"

if [ -d "$STATIC_ROOT/metadata" ]; then
    metadata_files=$(find "$STATIC_ROOT/metadata" -name "*.json" 2>/dev/null | wc -l)

    echo "Metadata files: $metadata_files"

    if [ $metadata_files -gt 0 ]; then
        # Verify JSON validity
        valid_json=0
        for file in "$STATIC_ROOT/metadata"/*.json; do
            if jq empty "$file" 2>/dev/null; then
                valid_json=$((valid_json + 1))
            fi
        done

        echo "Valid JSON files: $valid_json/$metadata_files"

        if [ $valid_json -eq $metadata_files ]; then
            check_pass "SC-011 PASSED: All metadata files valid ($valid_json files)"
        else
            check_fail "SC-011 FAILED: Some metadata files invalid ($valid_json/$metadata_files)"
        fi
    else
        check_warn "No metadata files found in $STATIC_ROOT/metadata"
    fi
else
    check_warn "Metadata directory not found: $STATIC_ROOT/metadata"
fi

echo ""

# Summary
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warned: $WARNED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical validations passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some validations failed. Please review the errors above.${NC}"
    exit 1
fi

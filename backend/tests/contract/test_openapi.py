"""
OpenAPI Contract Tests
"""

import pytest
from openapi_spec_validator import validate_spec


def test_openapi_spec_exists():
    """Test that OpenAPI spec file exists"""
    import os
    spec_path = "/AII-wuqi/AII_home/fq_775/project-dev/Prism/specs/001-medical-t2v-agent/contracts/openapi.yaml"
    assert os.path.exists(spec_path), "OpenAPI spec file not found"


def test_openapi_spec_valid():
    """Test that OpenAPI spec is valid"""
    import yaml

    spec_path = "/AII-wuqi/AII_home/fq_775/project-dev/Prism/specs/001-medical-t2v-agent/contracts/openapi.yaml"

    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)

    # Validate spec
    validate_spec(spec)


def test_openapi_has_required_endpoints():
    """Test that OpenAPI spec has required endpoints"""
    import yaml

    spec_path = "/AII-wuqi/AII_home/fq_775/project-dev/Prism/specs/001-medical-t2v-agent/contracts/openapi.yaml"

    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)

    paths = spec.get("paths", {})

    # Check required endpoints exist
    assert "/v1/t2v/generate" in paths, "Missing POST /v1/t2v/generate endpoint"
    assert "/v1/t2v/jobs/{job_id}" in paths, "Missing GET /v1/t2v/jobs/{job_id} endpoint"
    assert "/v1/t2v/jobs/{job_id}/finalize" in paths, "Missing POST /v1/t2v/jobs/{job_id}/finalize endpoint"


def test_openapi_schemas_valid():
    """Test that OpenAPI schemas match implementation"""
    import yaml

    spec_path = "/AII-wuqi/AII_home/fq_775/project-dev/Prism/specs/001-medical-t2v-agent/contracts/openapi.yaml"

    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)

    schemas = spec.get("components", {}).get("schemas", {})

    # Check required schemas exist
    assert "GenerationRequest" in schemas, "Missing GenerationRequest schema"
    assert "GenerationResponse" in schemas, "Missing GenerationResponse schema"
    assert "JobStatusResponse" in schemas, "Missing JobStatusResponse schema"
    assert "FinalizeRequest" in schemas, "Missing FinalizeRequest schema"
    assert "FinalizeResponse" in schemas, "Missing FinalizeResponse schema"


def test_generate_endpoint_parameters():
    """Test that generate endpoint has correct parameters"""
    import yaml

    spec_path = "/AII-wuqi/AII_home/fq_775/project-dev/Prism/specs/001-medical-t2v-agent/contracts/openapi.yaml"

    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)

    generate_path = spec["paths"]["/v1/t2v/generate"]
    post_spec = generate_path.get("post", {})

    # Check request body
    request_body = post_spec.get("requestBody", {})
    assert request_body, "Missing request body"

    # Check response
    responses = post_spec.get("responses", {})
    assert "202" in responses, "Missing 202 response"

    # Check response schema
    response_202 = responses["202"]
    content = response_202.get("content", {})
    assert "application/json" in content, "Missing JSON response content"


def test_finalize_endpoint_parameters():
    """Test that finalize endpoint has correct parameters"""
    import yaml

    spec_path = "/AII-wuqi/AII_home/fq_775/project-dev/Prism/specs/001-medical-t2v-agent/contracts/openapi.yaml"

    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)

    finalize_path = spec["paths"]["/v1/t2v/jobs/{job_id}/finalize"]
    post_spec = finalize_path.get("post", {})

    # Check path parameter
    parameters = post_spec.get("parameters", [])
    job_id_param = [p for p in parameters if p.get("name") == "job_id"]
    assert len(job_id_param) > 0, "Missing job_id path parameter"

    # Check request body
    request_body = post_spec.get("requestBody", {})
    assert request_body, "Missing request body"

    # Check response
    responses = post_spec.get("responses", {})
    assert "202" in responses, "Missing 202 response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

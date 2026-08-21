"""
File: backend/tests/test_ci_config.py
Purpose: Automated tests validating GitHub Actions CI/CD workflow YAML definitions.
"""

import os
import yaml
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CI_WORKFLOW = os.path.join(ROOT_DIR, ".github", "workflows", "ci.yml")
CD_WORKFLOW = os.path.join(ROOT_DIR, ".github", "workflows", "cd.yml")


def test_ci_workflow_structure():
    """Verify ci.yml exists, is valid YAML, and contains all required test jobs."""
    assert os.path.exists(CI_WORKFLOW), "ci.yml workflow file is missing!"
    
    with open(CI_WORKFLOW, "r", encoding="utf-8") as f:
        ci_config = yaml.safe_load(f)

    assert "name" in ci_config
    triggers = ci_config.get("on") or ci_config.get(True, {})
    assert "push" in triggers
    assert "pull_request" in triggers

    # Check jobs
    jobs = ci_config.get("jobs", {})
    required_jobs = {"backend-tests", "frontend-tests", "docker-validation"}
    assert required_jobs.issubset(jobs.keys()), f"Missing jobs in ci.yml: {required_jobs - set(jobs.keys())}"


def test_cd_workflow_structure():
    """Verify cd.yml exists, is valid YAML, and configures Docker build-and-push to GHCR."""
    assert os.path.exists(CD_WORKFLOW), "cd.yml workflow file is missing!"
    
    with open(CD_WORKFLOW, "r", encoding="utf-8") as f:
        cd_config = yaml.safe_load(f)

    assert "name" in cd_config
    jobs = cd_config.get("jobs", {})
    assert "build-and-push" in jobs

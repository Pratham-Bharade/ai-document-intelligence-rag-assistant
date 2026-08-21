"""
File: backend/tests/test_docker_config.py
Purpose: Automated tests validating Dockerfiles and Docker Compose configuration.
"""

import os
import yaml
import pytest


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
BACKEND_DOCKERFILE = os.path.join(ROOT_DIR, "backend", "Dockerfile")
FRONTEND_DOCKERFILE = os.path.join(ROOT_DIR, "frontend", "Dockerfile")
COMPOSE_FILE = os.path.join(ROOT_DIR, "docker-compose.yml")


def test_docker_compose_structure():
    """Verify docker-compose.yml has valid syntax, all 4 services, volumes, and healthchecks."""
    assert os.path.exists(COMPOSE_FILE), "docker-compose.yml is missing!"
    
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    services = config.get("services", {})
    required_services = {"postgres", "redis", "backend", "frontend"}
    assert required_services.issubset(services.keys()), f"Missing services in compose: {required_services - set(services.keys())}"

    # Verify healthchecks are defined
    for s_name in required_services:
        assert "healthcheck" in services[s_name], f"Service {s_name} is missing a healthcheck!"

    # Verify volumes
    volumes = config.get("volumes", {})
    assert "postgres_data" in volumes
    assert "redis_data" in volumes
    assert "document_uploads" in volumes

    # Verify network
    networks = config.get("networks", {})
    assert "rag_network" in networks


def test_backend_dockerfile_best_practices():
    """Verify backend Dockerfile uses multi-stage build, non-root user, and healthcheck."""
    assert os.path.exists(BACKEND_DOCKERFILE), "backend/Dockerfile is missing!"
    
    with open(BACKEND_DOCKERFILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert "AS builder" in content, "Backend Dockerfile must have builder stage"
    assert "AS runner" in content, "Backend Dockerfile must have runner stage"
    assert "USER appuser" in content, "Backend Dockerfile must run as non-root user appuser"
    assert "HEALTHCHECK" in content, "Backend Dockerfile must have HEALTHCHECK directive"
    assert "EXPOSE 8000" in content, "Backend Dockerfile must expose port 8000"


def test_frontend_dockerfile_best_practices():
    """Verify frontend Dockerfile uses multi-stage build, Nginx, and healthcheck."""
    assert os.path.exists(FRONTEND_DOCKERFILE), "frontend/Dockerfile is missing!"
    
    with open(FRONTEND_DOCKERFILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert "AS builder" in content, "Frontend Dockerfile must have builder stage"
    assert "AS runner" in content, "Frontend Dockerfile must have runner stage"
    assert "nginx:alpine" in content, "Frontend runner stage must use nginx:alpine"
    assert "HEALTHCHECK" in content, "Frontend Dockerfile must have HEALTHCHECK directive"
    assert "EXPOSE 80" in content, "Frontend Dockerfile must expose port 80"

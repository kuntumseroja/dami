import os

# Tests run against in-memory adapters and dev auth by default; the same
# suite runs against Postgres/MinIO by flipping these env vars (CI job).
os.environ.setdefault("REPO_BACKEND", "memory")
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("AUTH_MODE", "dev")
os.environ.setdefault("DAM_ENV", "test")
os.environ.setdefault("LOCAL_STORAGE_PATH", "./.test-data/objects")
os.environ.setdefault("DAM_AUDIT_LOG_PATH", "./.test-data/audit")

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.container import get_container
from app.main import app


@pytest.fixture()
def client():
    get_container.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_container.cache_clear()


# Role header helpers — DAM_ENV=test means no default dev admin shortcut in
# assertions; identity must be explicit.
DRAFTER = {"X-User-Id": "user-drafter", "X-User-Roles": "drafter"}
REVIEWER = {"X-User-Id": "user-reviewer", "X-User-Roles": "reviewer"}
APPROVER = {"X-User-Id": "user-approver", "X-User-Roles": "approver"}

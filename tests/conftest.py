import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "testsecret")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture(scope="session")
def app_client() -> TestClient:
    import app.core.config as config
    import app.core.dependencies as dependencies
    import app.main as main

    importlib.reload(config)
    importlib.reload(dependencies)
    importlib.reload(main)

    return TestClient(main.app)

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import app.core.config as config

@pytest.fixture
def temp_collections_root(tmp_path: Path) -> Path:
    """
    Create temporary collections root directory.
    
    Returns:
        Path to temporary data directory
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

@pytest.fixture
def test_app(temp_collections_root: Path, monkeypatch):
    """
    Override COLLECTIONS_ROOT and return FastAPI app.
    
    Args:
        temp_collections_root: Temporary collections directory
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        FastAPI app instance with overridden config
    """
    # Monkeypatch COLLECTIONS_ROOT BEFORE importing app
    monkeypatch.setattr(config, 'COLLECTIONS_ROOT', temp_collections_root)
    
    # NOW import the app (routes will use the patched value)
    from app.main import app
    
    return app

@pytest.fixture
def client(test_app) -> TestClient:
    """
    Returns TestClient for the app.
    
    Args:
        test_app: FastAPI app instance
        
    Returns:
        TestClient instance
    """
    return TestClient(test_app)

@pytest.fixture
def company_id() -> str:
    """
    Returns fixed company ID for tests.
    
    Returns:
        Company identifier
    """
    return "acme"
import pytest
from pathlib import Path
from tests.helpers.zip_factory import make_zip_with_files, make_invalid_zip, make_empty_zip
from tests.helpers.sample_texts import RESUME_TEXT_MATCH, RESUME_TEXT_PARTIAL
import app.core.config as config

def test_create_collection_success(client, tmp_path, company_id):
    """Test successful collection creation with valid ZIP."""
    # Arrange
    files = {
        "resume1.txt": RESUME_TEXT_MATCH.encode('utf-8'),
        "resume2.txt": RESUME_TEXT_PARTIAL.encode('utf-8')
    }
    zip_path = make_zip_with_files(tmp_path, files)
    
    # Act
    with open(zip_path, 'rb') as f:
        response = client.post(
            "/collections/create",
            data={"company_id": company_id},
            files={"zip_file": ("test.zip", f, "application/zip")}
        )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "collection_id" in data
    assert data["status"] == "uploaded"
    
    collection_id = data["collection_id"]
    
    # Verify filesystem
    collection_root = config.COLLECTIONS_ROOT / company_id / collection_id
    assert collection_root.exists()
    
    raw_dir = collection_root / "input" / "raw"
    assert raw_dir.exists()
    assert len(list(raw_dir.glob("*"))) > 0
    
    meta_file = collection_root / "collection_meta.json"
    assert meta_file.exists()

def test_create_collection_invalid_zip_returns_400(client, tmp_path, company_id):
    """Test that invalid ZIP returns 400 and cleans up."""
    # Arrange
    invalid_zip = make_invalid_zip(tmp_path)
    
    # Act
    with open(invalid_zip, 'rb') as f:
        response = client.post(
            "/collections/create",
            data={"company_id": company_id},
            files={"zip_file": ("test.zip", f, "application/zip")}
        )
    
    # Assert
    assert response.status_code == 400

def test_create_collection_empty_zip_returns_400(client, tmp_path, company_id):
    """Test that empty ZIP returns 400."""
    # Arrange
    empty_zip = make_empty_zip(tmp_path)
    
    # Act
    with open(empty_zip, 'rb') as f:
        response = client.post(
            "/collections/create",
            data={"company_id": company_id},
            files={"zip_file": ("test.zip", f, "application/zip")}
        )
    
    # Assert
    assert response.status_code == 400


import pytest
import json
from tests.helpers.zip_factory import make_zip_with_files
from tests.helpers.sample_texts import (
    RESUME_TEXT_MATCH, 
    RESUME_TEXT_PARTIAL, 
    RESUME_TEXT_EMPTY,
    RESUME_TEXT_DUPLICATE
)
import app.core.config as config

@pytest.fixture
def created_collection_id(client, tmp_path, company_id):
    """Create a collection and return its ID."""
    files = {
        "resume1.txt": RESUME_TEXT_MATCH.encode('utf-8'),
        "resume2.txt": RESUME_TEXT_PARTIAL.encode('utf-8')
    }
    zip_path = make_zip_with_files(tmp_path, files)
    
    with open(zip_path, 'rb') as f:
        response = client.post(
            "/collections/create",
            data={"company_id": company_id},
            files={"zip_file": ("test.zip", f, "application/zip")}
        )
    
    return response.json()["collection_id"]

def test_process_collection_success(client, created_collection_id, company_id):
    """Test successful collection processing."""
    # Act
    response = client.post(
        f"/collections/{created_collection_id}/process",
        json={"company_id": company_id}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    
    assert "details" in data
    details = data["details"]
    assert "stats" in details
    
    stats = details["stats"]
    assert "total_files" in stats
    assert "ok" in stats
    assert "failed" in stats
    assert "empty" in stats
    assert "duplicate" in stats
    
    # Verify filesystem
    collection_root = config.COLLECTIONS_ROOT / company_id / created_collection_id
    
    validation_report = collection_root / "reports" / "validation_report.json"
    assert validation_report.exists()
    
    duplicate_report = collection_root / "reports" / "duplicate_report.json"
    assert duplicate_report.exists()
    
    processed_dir = collection_root / "processed"
    assert processed_dir.exists()
    assert len(list(processed_dir.glob("*.txt"))) > 0
    
    # Verify meta updated
    meta_file = collection_root / "collection_meta.json"
    meta = json.loads(meta_file.read_text())
    assert meta["processing_status"] == "completed"

def test_process_collection_marks_empty_not_reject(client, tmp_path, company_id):
    """Test that empty resume is marked EMPTY but doesn't fail processing."""
    # Arrange - create collection with one empty resume
    files = {
        "resume1.txt": RESUME_TEXT_MATCH.encode('utf-8'),
        "resume_empty.txt": RESUME_TEXT_EMPTY.encode('utf-8')
    }
    zip_path = make_zip_with_files(tmp_path, files)
    
    with open(zip_path, 'rb') as f:
        create_response = client.post(
            "/collections/create",
            data={"company_id": company_id},
            files={"zip_file": ("test.zip", f, "application/zip")}
        )
    
    collection_id = create_response.json()["collection_id"]
    
    # Act
    response = client.post(
        f"/collections/{collection_id}/process",
        json={"company_id": company_id}
    )
    
    # Assert
    assert response.status_code == 200
    
    # Check validation report
    collection_root = config.COLLECTIONS_ROOT / company_id / collection_id
    validation_report = collection_root / "reports" / "validation_report.json"
    report = json.loads(validation_report.read_text())
    
    # At least one EMPTY status
    assert report["empty"] >= 1
    
    # Overall processing completed
    empty_files = [f for f in report["files"] if f["status"] == "EMPTY"]
    assert len(empty_files) >= 1

def test_process_collection_duplicate_detection(client, tmp_path, company_id):
    """Test that duplicate resumes are detected."""
    # Arrange - create collection with duplicate content
    files = {
        "resume1.txt": RESUME_TEXT_MATCH.encode('utf-8'),
        "resume2.txt": RESUME_TEXT_DUPLICATE.encode('utf-8')
    }
    zip_path = make_zip_with_files(tmp_path, files)
    
    with open(zip_path, 'rb') as f:
        create_response = client.post(
            "/collections/create",
            data={"company_id": company_id},
            files={"zip_file": ("test.zip", f, "application/zip")}
        )
    
    collection_id = create_response.json()["collection_id"]
    
    # Act
    response = client.post(
        f"/collections/{collection_id}/process",
        json={"company_id": company_id}
    )
    
    # Assert
    assert response.status_code == 200
    
    collection_root = config.COLLECTIONS_ROOT / company_id / collection_id
    
    # Check validation report
    validation_report = collection_root / "reports" / "validation_report.json"
    report = json.loads(validation_report.read_text())
    assert report["ok"] == 1
    assert report["duplicate"] == 1
    
    # Check duplicate report
    duplicate_report = collection_root / "reports" / "duplicate_report.json"
    dup_report = json.loads(duplicate_report.read_text())
    assert len(dup_report["duplicates"]) == 1

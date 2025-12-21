"""
Phase 1 Integration Test

Test that collection creation:
- Creates folder structure
- Saves ZIP file
- Extracts contents
- Creates metadata
"""
import io
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_test_zip():
    """Create a simple test ZIP in memory"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr("resume1.txt", "John Doe - Software Engineer")
        zf.writestr("resume2.txt", "Jane Smith - Data Scientist")
    buffer.seek(0)
    return buffer


def test_create_collection():
    # Create test ZIP
    test_zip = create_test_zip()
    
    # Upload to API
    response = client.post(
        "/collections/create",
        data={"company_id": "test_company"},
        files={"zip_file": ("resumes.zip", test_zip, "application/zip")}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "collection_id" in data
    assert data["status"] == "uploaded"
    
    collection_id = data["collection_id"]
    
    # Verify folder structure
    base = Path("storage/companies/test_company") / collection_id
    assert base.exists()
    assert (base / "input" / "raw").exists()
    assert (base / "input" / "manifest").exists()
    assert (base / "processed").exists()
    assert (base / "artifacts").exists()
    assert (base / "outputs").exists()
    assert (base / "reports").exists()
    
    # Verify ZIP saved
    assert (base / "input" / "resumes.zip").exists()
    
    # Verify extraction
    assert (base / "input" / "raw" / "resume1.txt").exists()
    assert (base / "input" / "raw" / "resume2.txt").exists()
    
    # Verify metadata
    meta_path = base / "collection_meta.json"
    assert meta_path.exists()
    
    import json
    with open(meta_path) as f:
        meta = json.load(f)
    
    assert meta["collection_id"] == collection_id
    assert meta["company_id"] == "test_company"
    assert meta["status"] == "uploaded"
    assert meta["format"] == "zip_only"
    
    print(f"✓ Test passed: Collection {collection_id} created successfully")


if __name__ == "__main__":
    test_create_collection()
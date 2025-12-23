import pytest
import json
from tests.helpers.zip_factory import make_zip_with_files
from tests.helpers.sample_texts import RESUME_TEXT_MATCH, RESUME_TEXT_PARTIAL, JD_TEXT_1
import app.core.config as config

@pytest.fixture
def processed_collection_id(client, tmp_path, company_id):
    """Create and process a collection, return its ID."""
    # Create
    files = {
        "resume1.txt": RESUME_TEXT_MATCH.encode('utf-8'),
        "resume2.txt": RESUME_TEXT_PARTIAL.encode('utf-8')
    }
    zip_path = make_zip_with_files(tmp_path, files)
    
    with open(zip_path, 'rb') as f:
        create_response = client.post(
            "/collections/create",
            data={"company_id": company_id},
            files={"zip_file": ("test.zip", f, "application/zip")}
        )
    
    collection_id = create_response.json()["collection_id"]
    
    # Process
    client.post(
        f"/collections/{collection_id}/process",
        json={"company_id": company_id}
    )
    
    return collection_id

def test_rank_success_returns_outputs(client, processed_collection_id, company_id):
    """Test successful ranking returns outputs."""
    # Act
    response = client.post(
        f"/collections/{processed_collection_id}/rank",
        json={
            "company_id": company_id,
            "jd_text": JD_TEXT_1
        }
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    
    assert "details" in data
    details = data["details"]
    assert "outputs_generated" in details
    assert "resume_count" in details
    assert "ranked_count" in details
    
    # Verify filesystem
    collection_root = config.COLLECTIONS_ROOT / company_id / processed_collection_id
    
    # Outputs
    ranking_json = collection_root / "outputs" / "ranking_results.json"
    assert ranking_json.exists()
    
    ranking_csv = collection_root / "outputs" / "ranking_results.csv"
    assert ranking_csv.exists()
    
    # Reports
    ranking_summary = collection_root / "reports" / "ranking_summary.json"
    assert ranking_summary.exists()
    
    # Artifacts
    vectorizer = collection_root / "artifacts" / "tfidf_vectorizer.pkl"
    assert vectorizer.exists()
    
    matrix = collection_root / "artifacts" / "resume_matrix.npz"
    assert matrix.exists()
    
    index = collection_root / "artifacts" / "resume_index.json"
    assert index.exists()

def test_rank_without_processing_returns_400(client, tmp_path, company_id):
    """Test that ranking without processing returns 400."""
    # Arrange - create collection but don't process
    files = {
        "resume1.txt": RESUME_TEXT_MATCH.encode('utf-8')
    }
    zip_path = make_zip_with_files(tmp_path, files)
    
    with open(zip_path, 'rb') as f:
        create_response = client.post(
            "/collections/create",
            data={"company_id": company_id},
            files={"zip_file": ("test.zip", f, "application/zip")}
        )
    
    collection_id = create_response.json()["collection_id"]
    
    # Act - try to rank without processing
    response = client.post(
        f"/collections/{collection_id}/rank",
        json={
            "company_id": company_id,
            "jd_text": JD_TEXT_1
        }
    )
    
    # Assert
    assert response.status_code == 400
    assert "processing first" in response.json()["detail"].lower()

def test_rank_top_k_limits_results(client, processed_collection_id, company_id):
    """Test that top_k limits returned results."""
    # Act
    response = client.post(
        f"/collections/{processed_collection_id}/rank",
        json={
            "company_id": company_id,
            "jd_text": JD_TEXT_1,
            "top_k": 1
        }
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    
    assert data["details"]["ranked_count"] == 1
    
    # Verify JSON output file
    collection_root = config.COLLECTIONS_ROOT / company_id / processed_collection_id
    ranking_json = collection_root / "outputs" / "ranking_results.json"
    results = json.loads(ranking_json.read_text())
    
    assert len(results) == 1

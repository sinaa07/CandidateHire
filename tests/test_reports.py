import pytest
import json
from tests.helpers.zip_factory import make_zip_with_files
from tests.helpers.sample_texts import RESUME_TEXT_MATCH, RESUME_TEXT_PARTIAL, JD_TEXT_1
import app.core.config as config

@pytest.fixture
def ranked_collection_id(client, tmp_path, company_id):
    """Create, process, and rank a collection."""
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
    
    # Rank
    client.post(
        f"/collections/{collection_id}/rank",
        json={
            "company_id": company_id,
            "jd_text": JD_TEXT_1
        }
    )
    
    return collection_id

def test_report_endpoint_returns_aggregated_reports(client, ranked_collection_id, company_id):
    """Test that report endpoint returns aggregated reports."""
    # Act
    response = client.get(
        f"/collections/{ranked_collection_id}/report",
        params={"company_id": company_id}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    
    assert "meta" in data
    assert "phase2" in data
    assert "phase3" in data
    
    assert data["phase2"]["validation_report"] is not None
    assert data["phase3"]["ranking_summary"] is not None

def test_report_include_results_true(client, ranked_collection_id, company_id):
    """Test that include_results=true includes ranking results."""
    # Act
    response = client.get(
        f"/collections/{ranked_collection_id}/report",
        params={
            "company_id": company_id,
            "include_results": True
        }
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    
    assert "ranking_results" in data["phase3"]
    assert isinstance(data["phase3"]["ranking_results"], list)
    assert len(data["phase3"]["ranking_results"]) > 0

def test_outputs_endpoint_flags_files(client, ranked_collection_id, company_id):
    """Test that outputs endpoint shows file availability."""
    # Act
    response = client.get(
        f"/collections/{ranked_collection_id}/outputs",
        params={"company_id": company_id}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    
    assert "outputs" in data
    assert data["outputs"]["ranking_results.json"] is True
    assert data["outputs"]["ranking_results.csv"] is True

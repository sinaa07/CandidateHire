import pytest
import json
from tests.helpers.zip_factory import make_zip_with_files
from tests.helpers.sample_texts import RESUME_TEXT_MATCH, RESUME_TEXT_PARTIAL, JD_TEXT_1
import app.core.config as config

def test_full_pipeline_happy_path(client, tmp_path, company_id):
    """Test complete end-to-end pipeline: create -> process -> rank -> report."""
    # 1. Create collection
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
    
    assert create_response.status_code == 200
    collection_id = create_response.json()["collection_id"]
    
    # 2. Process collection
    process_response = client.post(
        f"/collections/{collection_id}/process",
        json={"company_id": company_id}
    )
    
    assert process_response.status_code == 200
    
    # 3. Rank collection
    rank_response = client.post(
        f"/collections/{collection_id}/rank",
        json={
            "company_id": company_id,
            "jd_text": JD_TEXT_1
        }
    )
    
    assert rank_response.status_code == 200
    
    # 4. Get report with results
    report_response = client.get(
        f"/collections/{collection_id}/report",
        params={
            "company_id": company_id,
            "include_results": True
        }
    )
    
    assert report_response.status_code == 200
    report_data = report_response.json()
    
    # Verify structure
    assert "meta" in report_data
    assert "phase2" in report_data
    assert "phase3" in report_data
    
    # Verify ranking results
    ranking_results = report_data["phase3"]["ranking_results"]
    assert isinstance(ranking_results, list)
    assert len(ranking_results) > 0
    
    # Verify sorting (descending by final_score)
    scores = [r["final_score"] for r in ranking_results]
    assert scores == sorted(scores, reverse=True)
    
    # Verify explainability
    for result in ranking_results:
        assert "explainability" in result
        assert "matched_skills" in result["explainability"]
        assert "missing_skills" in result["explainability"]
    
    # Verify meta has both processing and ranking fields
    meta = report_data["meta"]
    assert "processing_status" in meta
    assert "ranking_status" in meta
    
    # 5. Get outputs
    outputs_response = client.get(
        f"/collections/{collection_id}/outputs",
        params={"company_id": company_id}
    )
    
    assert outputs_response.status_code == 200
    assert outputs_response.json()["outputs"]["ranking_results.json"] is True
    assert outputs_response.json()["outputs"]["ranking_results.csv"] is True
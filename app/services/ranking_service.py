from pathlib import Path
from datetime import datetime, UTC
import json
import csv
import logging
import app.core.config as config
from app.utils.jd_io import save_jd_text, load_jd_text
from app.utils.vectorization import (
    build_tfidf_vectorizer,
    fit_resume_matrix,
    transform_text,
    cosine_similarities
)
from app.utils.skills import SKILLS, extract_skills, skill_overlap_score
from app.utils.scoring import combine_scores, build_explainability
from app.utils.artifacts import (
    ensure_artifacts_dir,
    save_vectorizer,
    save_sparse_matrix,
    save_resume_index,
    save_rank_config
)

logger = logging.getLogger(__name__)

def rank_collection(company_id: str, collection_id: str, jd_text: str, top_k: int | None = None) -> dict:
    """Core Phase-3 ranking orchestration."""
    logger.info(f"Ranking collection {collection_id}")
    
    collection_root = config.COLLECTIONS_ROOT / company_id / collection_id
    processed_dir = collection_root / "processed"
    outputs_dir = collection_root / "outputs"
    reports_dir = collection_root / "reports"
    
    outputs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    if not jd_text or not jd_text.strip():
        raise ValueError("JD is required")
    
    save_jd_text(collection_root, jd_text)
    
    resume_files = sorted(processed_dir.glob("*.txt"))
    
    if not resume_files:
        raise ValueError("No processed resumes found")
    
    resume_texts = []
    resume_filenames = []
    
    for resume_file in resume_files:
        text = resume_file.read_text(encoding='utf-8', errors='ignore')
        resume_texts.append(text)
        resume_filenames.append(resume_file.name)
    
    skills_vocab = SKILLS
    jd_skills = extract_skills(jd_text, skills_vocab)
    jd_skills_set = set(jd_skills)
    
    vectorizer = build_tfidf_vectorizer()
    resume_matrix = fit_resume_matrix(vectorizer, resume_texts)
    jd_vector = transform_text(vectorizer, jd_text)
    tfidf_scores = cosine_similarities(resume_matrix, jd_vector)
    
    results = []
    
    for idx, (filename, resume_text, tfidf_score) in enumerate(zip(resume_filenames, resume_texts, tfidf_scores)):
        resume_skills = extract_skills(resume_text, skills_vocab)
        resume_skills_set = set(resume_skills)
        
        skill_score = skill_overlap_score(jd_skills_set, resume_skills_set)
        final_score = combine_scores(tfidf_score, skill_score)
        explainability = build_explainability(jd_skills, resume_skills)
        
        results.append({
            "filename": filename,
            "tfidf_score_raw": tfidf_score,
            "skill_score_raw": skill_score,
            "final_score_raw": final_score,
            "explainability": {
                "matched_skills": explainability["matched_skills"],
                "missing_skills": explainability["missing_skills"]
            }
        })
    
    results.sort(key=lambda x: (x["final_score_raw"], x["tfidf_score_raw"]), reverse=True)
    
    for rank, result in enumerate(results, start=1):
        result["rank"] = rank
        result["tfidf_score"] = round(result["tfidf_score_raw"], 4)
        result["skill_score"] = round(result["skill_score_raw"], 4)
        result["final_score"] = round(result["final_score_raw"], 4)
        del result["tfidf_score_raw"]
        del result["skill_score_raw"]
        del result["final_score_raw"]
    
    if top_k is not None:
        results = results[:top_k]
    
    ranking_json = outputs_dir / "ranking_results.json"
    ranking_json.write_text(json.dumps(results, indent=2), encoding='utf-8')
    
    ranking_csv = outputs_dir / "ranking_results.csv"
    with open(ranking_csv, 'w', newline='', encoding='utf-8') as f:
        if results:
            fieldnames = ["rank", "filename", "tfidf_score", "skill_score", "final_score"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow({
                    "rank": result["rank"],
                    "filename": result["filename"],
                    "tfidf_score": result["tfidf_score"],
                    "skill_score": result["skill_score"],
                    "final_score": result["final_score"]
                })
    
    ranking_summary = {
        "collection_id": collection_id,
        "company_id": company_id,
        "ranked_at": datetime.now(UTC).isoformat(),
        "resume_count": len(resume_filenames),
        "ranked_count": len(results),
        "weights": {"tfidf": 0.7, "skill": 0.3},
        "top_k": top_k
    }
    
    summary_file = reports_dir / "ranking_summary.json"
    summary_file.write_text(json.dumps(ranking_summary, indent=2), encoding='utf-8')
    
    artifacts_dir = ensure_artifacts_dir(collection_root)
    
    save_vectorizer(artifacts_dir, vectorizer)
    save_sparse_matrix(artifacts_dir, resume_matrix)
    save_resume_index(artifacts_dir, resume_filenames)
    
    rank_config = {
        "weights": {"tfidf": 0.7, "skill": 0.3},
        "skills_vocab_version": "v1",
        "created_at": datetime.now(UTC).isoformat()
    }
    save_rank_config(artifacts_dir, rank_config)
    
    meta_file = collection_root / "collection_meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    meta.update({
        "ranking_status": "completed",
        "ranked_at": datetime.now(UTC).isoformat()
    })
    meta_file.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    
    logger.info("Phase-3 ranking completed")
    
    return {
        "status": "completed",
        "resume_count": len(resume_filenames),
        "ranked_count": len(results),
        "top_k": top_k,
        "outputs_generated": [
            "ranking_results.json",
            "ranking_results.csv",
            "ranking_summary.json"
        ]
    }
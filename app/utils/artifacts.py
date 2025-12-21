from pathlib import Path
import pickle
import json
import scipy.sparse

def ensure_artifacts_dir(collection_root: Path) -> Path:
    """
    Creates artifacts directory.
    
    Args:
        collection_root: Collection root directory
        
    Returns:
        Path to artifacts directory
    """
    artifacts_dir = collection_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir

def save_vectorizer(artifacts_dir: Path, vectorizer) -> Path:
    """
    Saves vectorizer using pickle.
    
    Args:
        artifacts_dir: Artifacts directory
        vectorizer: TF-IDF vectorizer
        
    Returns:
        Path to saved vectorizer
    """
    vectorizer_file = artifacts_dir / "tfidf_vectorizer.pkl"
    with open(vectorizer_file, 'wb') as f:
        pickle.dump(vectorizer, f, protocol=pickle.HIGHEST_PROTOCOL)
    return vectorizer_file

def save_sparse_matrix(artifacts_dir: Path, matrix: scipy.sparse.csr_matrix) -> Path:
    """
    Saves sparse matrix.
    
    Args:
        artifacts_dir: Artifacts directory
        matrix: Sparse matrix
        
    Returns:
        Path to saved matrix
    """
    matrix_file = artifacts_dir / "resume_matrix.npz"
    scipy.sparse.save_npz(matrix_file, matrix)
    return matrix_file

def save_resume_index(artifacts_dir: Path, filenames: list[str]) -> Path:
    """
    Saves resume index mapping row to filename.
    
    Args:
        artifacts_dir: Artifacts directory
        filenames: List of resume filenames
        
    Returns:
        Path to saved index
    """
    index_file = artifacts_dir / "resume_index.json"
    index_file.write_text(json.dumps(filenames, indent=2), encoding='utf-8')
    return index_file

def save_rank_config(artifacts_dir: Path, config: dict) -> Path:
    """
    Saves ranking configuration.
    
    Args:
        artifacts_dir: Artifacts directory
        config: Configuration dictionary
        
    Returns:
        Path to saved config
    """
    config_file = artifacts_dir / "rank_config.json"
    config_file.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return config_file
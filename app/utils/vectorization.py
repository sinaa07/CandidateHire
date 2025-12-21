from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import scipy.sparse

def build_tfidf_vectorizer() -> TfidfVectorizer:
    """
    Creates and returns a configured TF-IDF vectorizer.
    
    Returns:
        Configured TfidfVectorizer
    """
    return TfidfVectorizer(
        lowercase=True,
        stop_words='english',
        ngram_range=(1, 2)
    )

def fit_resume_matrix(vectorizer: TfidfVectorizer, resume_texts: list[str]) -> scipy.sparse.csr_matrix:
    """
    Fits vectorizer on resume texts and returns sparse matrix.
    
    Args:
        vectorizer: TF-IDF vectorizer
        resume_texts: List of resume text contents
        
    Returns:
        Sparse matrix for resumes
    """
    return vectorizer.fit_transform(resume_texts)

def transform_text(vectorizer: TfidfVectorizer, text: str) -> scipy.sparse.csr_matrix:
    """
    Transforms a single text using already-fit vectorizer.
    
    Args:
        vectorizer: Fitted TF-IDF vectorizer
        text: Text to transform (JD)
        
    Returns:
        Sparse vector
    """
    return vectorizer.transform([text])

def cosine_similarities(resume_matrix: scipy.sparse.csr_matrix, jd_vector: scipy.sparse.csr_matrix) -> list[float]:
    """
    Returns cosine similarity per resume.
    
    Args:
        resume_matrix: Sparse matrix of resume vectors
        jd_vector: Sparse vector of JD
        
    Returns:
        List of cosine similarities (same order as matrix rows)
    """
    similarities = cosine_similarity(jd_vector, resume_matrix)
    return similarities[0].tolist()
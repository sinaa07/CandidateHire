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
    # Filter out empty texts
    non_empty_texts = [text for text in resume_texts if text and text.strip()]
    
    if not non_empty_texts:
        raise ValueError("No non-empty resume texts provided")
    
    try:
        matrix = vectorizer.fit_transform(non_empty_texts)
        
        # Check if vocabulary is empty
        if len(vectorizer.vocabulary_) == 0:
            raise ValueError("Empty vocabulary: all documents contain only stop words")
        
        return matrix
    except ValueError as e:
        if "empty vocabulary" in str(e).lower() or "only contain stop words" in str(e).lower():
            raise ValueError("Empty vocabulary: perhaps the documents only contain stop words. Please provide more substantial text content.")
        raise

def transform_text(vectorizer: TfidfVectorizer, text: str) -> scipy.sparse.csr_matrix:
    """
    Transforms a single text using already-fit vectorizer.
    
    Args:
        vectorizer: Fitted TF-IDF vectorizer
        text: Text to transform (JD)
        
    Returns:
        Sparse vector
    """
    if not text or not text.strip():
        # Return empty vector matching vocabulary size
        return scipy.sparse.csr_matrix((1, len(vectorizer.vocabulary_)))
    
    try:
        return vectorizer.transform([text])
    except Exception as e:
        # If transformation fails, return empty vector
        return scipy.sparse.csr_matrix((1, len(vectorizer.vocabulary_)))

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
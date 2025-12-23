from fastapi import HTTPException

def to_http_error(exc: Exception) -> HTTPException:
    """
    Convert internal exceptions to safe HTTP responses.
    
    Args:
        exc: Internal exception
        
    Returns:
        HTTPException with appropriate status code
    """
    if isinstance(exc, ValueError):
        error_msg = str(exc)
        
        # Map specific error messages to 404
        if "collection not found" in error_msg.lower():
            return HTTPException(status_code=404, detail=error_msg)
        if "report not found" in error_msg.lower():
            return HTTPException(status_code=404, detail=error_msg)
        
        # All other ValueErrors are 400
        return HTTPException(status_code=400, detail=error_msg)
    
    # Generic server error (no stack trace leak)
    return HTTPException(status_code=500, detail="Internal server error")

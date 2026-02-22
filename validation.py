"""Listing validation using fuzzy matching for GPU correctness."""

from rapidfuzz import fuzz
from main import GPU_LIST


def find_best_gpu_match(title: str) -> tuple[str, float]:
    """
    Find the GPU that best matches the listing title using fuzzy matching.
    
    Args:
        title: The listing title to match against GPU search queries
        
    Returns:
        Tuple of (gpu_name, match_score) where score is 0-100
    """
    if not title:
        return None, 0
    
    title_upper = title.upper()
    best_match = None
    best_score = 0
    
    for gpu in GPU_LIST:
        # Try matching against all search queries for this GPU
        for query in gpu.search_queries:
            score = fuzz.token_set_ratio(title_upper, query.upper())
            
            if score > best_score:
                best_score = score
                best_match = gpu.name
    
    return best_match, best_score


def validate_listing(gpu_name: str, title: str, threshold: int = 60) -> tuple[bool, str | None, float]:
    """
    Validate if a listing matches the expected GPU using fuzzy matching.
    
    Args:
        gpu_name: The GPU name the listing was found under
        title: The listing title to validate
        threshold: Minimum match score (0-100) to accept the listing for the original GPU
        
    Returns:
        Tuple of (is_valid, corrected_gpu_name, match_score)
        - is_valid: True if listing should be saved
        - corrected_gpu_name: The correct GPU name if different from original, None if original is correct
        - match_score: The best match score found
    """
    if not title:
        return False, None, 0
    
    # Find best match for the listing
    best_match, best_score = find_best_gpu_match(title)
    
    if best_match is None:
        return False, None, 0
    
    # If best match equals the original GPU and score is acceptable
    if best_match == gpu_name and best_score >= threshold:
        return True, None, best_score
    
    # If best match is different GPU and significantly better match
    if best_match != gpu_name and best_score >= threshold:
        # Check if the original GPU had a much worse score
        original_gpu = next((gpu for gpu in GPU_LIST if gpu.name == gpu_name), None)
        if original_gpu:
            title_upper = title.upper()
            original_score = max(
                fuzz.token_set_ratio(title_upper, query.upper())
                for query in original_gpu.search_queries
            )
        else:
            original_score = best_score  # Fallback if GPU not found
        
        # If best match is at least 15 points better, correct it
        if best_score - original_score >= 15:
            return True, best_match, best_score
        # Otherwise, if original is still acceptable, keep it
        elif original_score >= threshold:
            return True, None, original_score
        # If both are poor, reject
        else:
            return False, None, best_score
    
    # If we have a match but below threshold for original GPU
    if best_score >= threshold and best_match != gpu_name:
        return True, best_match, best_score
    
    # Threshold not met
    return False, None, best_score

"""Listing validation using fuzzy matching for GPU correctness."""

from rapidfuzz import fuzz
from main import GPU_LIST


def find_best_gpu_match(title: str) -> tuple[str, float]:
    """
    Find the GPU that best matches the listing title using fuzzy matching.
    
    Handles ambiguous matches by preferring:
    1. More specific GPU variants (e.g., "3070 Ti" over "3070" for a Ti title)
    2. Longer search queries when scores are tied
    
    Args:
        title: The listing title to match against GPU search queries
        
    Returns:
        Tuple of (gpu_name, match_score) where score is 0-100
    """
    if not title:
        return None, 0
    
    title_upper = title.upper()
    title_has_ti = "TI" in title_upper
    
    # Collect all potential matches with scores
    matches = []  # List of (gpu_name, query, score, query_length, gpu_has_ti)
    
    for gpu in GPU_LIST:
        gpu_has_ti = any("ti" in q.lower() for q in gpu.search_queries)
        for query in gpu.search_queries:
            score = fuzz.token_set_ratio(title_upper, query.upper())
            matches.append({
                "gpu_name": gpu.name,
                "query": query,
                "score": score,
                "query_length": len(query),
                "gpu_has_ti": gpu_has_ti,
            })
    
    if not matches:
        return None, 0
    
    # Sort by:
    # 1. Score (desc)
    # 2. If title has "Ti", prefer GPUs with Ti variants (Ti match bonus)
    # 3. Query length (desc) - prefer longer/more specific queries
    # 4. Query alphabetically
    def sort_key(m):
        score = -m["score"]
        # If title has Ti, heavily penalize non-Ti GPUs to prefer Ti variants
        ti_bonus = 0 if (title_has_ti and m["gpu_has_ti"]) else (1 if title_has_ti else 0)
        query_len = -m["query_length"]
        query_name = m["query"]
        return (score, ti_bonus, query_len, query_name)
    
    matches.sort(key=sort_key)
    
    best_match = matches[0]
    return best_match["gpu_name"], best_match["score"]


def validate_listing(gpu_name: str, title: str, threshold: int = 70) -> tuple[bool, str | None, float]:
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
    
    # If best match is different GPU, need to check if it's a valid correction
    if best_match != gpu_name:
        if best_score < threshold:
            # Best match doesn't meet threshold, reject
            return False, None, best_score
        
        # Best match is above threshold, check original score
        original_gpu = next((gpu for gpu in GPU_LIST if gpu.name == gpu_name), None)
        if original_gpu:
            title_upper = title.upper()
            original_score = max(
                fuzz.token_set_ratio(title_upper, query.upper())
                for query in original_gpu.search_queries
            )
        else:
            original_score = 0  # Fallback if GPU not found
        
        # Correction logic:
        # 1. If best match is clearly better (15+ points), correct it
        if best_score - original_score >= 15:
            return True, best_match, best_score
        
        # 2. If they're tied or very close (within 5 points), prefer more specific match
        if abs(best_score - original_score) <= 5:
            # Check if best match is more specific (e.g., "3070 Ti" vs "3070" when title has "Ti")
            best_gpu_obj = next((gpu for gpu in GPU_LIST if gpu.name == best_match), None)
            if best_gpu_obj and any("ti" in q.lower() for q in best_gpu_obj.search_queries):
                # Best match has a Ti variant and title contains Ti - correct it
                if "TI" in title_upper:
                    return True, best_match, best_score
        
        # 3. Otherwise, keep original if it meets threshold
        if original_score >= threshold:
            return True, None, original_score
        
        # 4. If neither meets threshold, reject
        return False, None, best_score
    
    # Threshold not met
    return False, None, best_score

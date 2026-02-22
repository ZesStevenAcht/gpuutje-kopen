"""
Test and demonstration script for GPU listing validation with fuzzy matching.

This script shows how the validation module correctly identifies mismatched listings
and corrects them using fuzzy matching.
"""

from validation import validate_listing


def test_validation():
    """Run validation tests with realistic examples."""
    
    test_cases = [
        {
            "name": "Listing mismatch: 3080 Ti found for RTX 3080 search",
            "gpu_searched": "RTX 3080 10GB",
            "listing_title": "Good condition, RTX 3080 Ti 12GB barely used",
            "expected": "Should correct to RTX 3080 Ti 12GB",
        },
        {
            "name": "Correct match: RTX 3090 found for RTX 3090 search",
            "gpu_searched": "RTX 3090 24GB",
            "listing_title": "Excellent RTX 3090 24GB, excellent condition",
            "expected": "Should keep as RTX 3090 24GB",
        },
        {
            "name": "4090 found for RTX 4080 search",
            "gpu_searched": "RTX 4080 16GB",
            "listing_title": "New sealed RTX 4090 24GB unopened box",
            "expected": "Should correct to RTX 4090 24GB",
        },
        {
            "name": "Generic description without clear GPU model",
            "gpu_searched": "RTX 4080 16GB",
            "listing_title": "GPU graphics card for sale, good condition",
            "expected": "Should reject (low match score)",
        },
        {
            "name": "A6000 mistakenly found for 4090 search",
            "gpu_searched": "RTX 4090 24GB",
            "listing_title": "Professional RTX A6000 48GB workstation card",
            "expected": "Should correct to RTX A6000 48GB",
        },
    ]
    
    print("=" * 80)
    print("GPU Listing Validation Tests")
    print("=" * 80)
    print()
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"  Searched for: {test['gpu_searched']}")
        print(f"  Listing title: {test['listing_title']}")
        print(f"  Expected: {test['expected']}")
        
        is_valid, corrected, score = validate_listing(
            test['gpu_searched'],
            test['listing_title']
        )
        
        status = "✓ VALID" if is_valid else "✗ REJECTED"
        correction = f" → Corrected to {corrected}" if corrected else " → No correction needed"
        
        print(f"  Result: {status}{correction} (Match score: {score:.1f}/100)")
        print()


if __name__ == "__main__":
    test_validation()

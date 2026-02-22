# Project Structure Documentation

This document explains the organization of the gpuutje-kopen project following standard Python project conventions.

## Directory Layout

```
project_root/
├── app.py                              # Flask application entry point
├── src/gpuutje_kopen/                 # Main package
│   ├── __init__.py                     # Package initialization
│   ├── gpu_list.py                     # GPU specifications and list
│   ├── storage.py                      # Data persistence layer
│   ├── analytics.py                    # Price analysis and statistics
│   ├── validation.py                   # GPU listing validation
│   └── search_worker.py                # Background search worker
├── templates/                          # Jinja2 HTML templates
│   └── index.html                      # Main web interface
├── tests/                              # Test suite
│   └── test_validation.py              # Validation module tests
├── docs/                               # Project documentation
│   ├── DOCKER.md                       # Docker deployment guide
│   ├── VALIDATION.md                   # Validation implementation details
│   └── STRUCTURE.md                    # This file
├── data/                               # Data directory (created at runtime)
│   └── results.json                    # Accumulated search results
├── .venv/                              # Python virtual environment
├── docker-compose.yml                  # Docker Compose configuration
├── Dockerfile                          # Docker image definition
├── pyproject.toml                      # Python project configuration
├── README.md                           # Project overview
├── .gitignore                          # Git ignore rules
└── .python-version                     # Python version specification
```

## Module Descriptions

### src/gpuutje_kopen/

This directory contains the main application package.

#### `__init__.py`
- Package initialization
- Defines `__version__` for version management

#### `gpu_list.py`
- Defines the `GPU` dataclass with fields:
  - `name`: GPU model name
  - `vram`: Memory in GB
  - `tokens_sec`: Tokens per second theoretical spec
  - `search_queries`: Alternative search terms
  - `tokens_tested`: Whether tokens_sec is tested vs estimated
- Contains `GPU_LIST`: comprehensive list of all tracked GPU models

#### `storage.py`
- `save_result()`: Persists search results to JSON with thread-safe locking
- `load_results()`: Loads historical results from JSON
- `get_results_by_gpu()`: Filters results by GPU model
- `mark_active_listings()`: Updates active/inactive status of listings based on search results
- Thread-safe file operations using file locks

#### `analytics.py`
- `calc_price_history()`: Calculates price history with span-based binning:
  - '14d': Daily bins over 14 days
  - '30d': Daily bins over 30 days
  - '1y': Weekly bins over 1 year
- Prefers `listing.date` (when posted) over timestamp (when scraped)
- `get_avg_price_period()`: Gets average price for a specific day range

#### `validation.py`
- `find_best_gpu_match()`: Uses fuzzy token_set_ratio matching to find GPU
- `validate_listing()`: Validates if a listing title matches the searched GPU
  - Returns `(is_valid, corrected_gpu, match_score)`
  - Implements Ti-aware tie-breaking (e.g., "3060 Ti" preferred over "3060")
  - Configurable threshold (default 70/100)

#### `search_worker.py`
- `search_gpu()`: Performs a search for a single GPU using marktplaats API
- `run_search_cycle()`: Iterates through all GPUs in GPU_LIST
- `worker_loop()`: Infinite loop running search cycles at 8-hour intervals
- `start_worker_thread()`: Creates background daemon thread for search worker
- Collects listing IDs and calls `mark_active_listings()` after each search

### app.py

Flask web application entry point:
- Adds `src/` to Python path for imports
- Imports from `gpuutje_kopen` package
- Defines Flask routes:
  - `/`: Main web interface
  - `/api/gpus`: Returns GPU list with stats
  - `/api/price-history/<gpu>`: Returns price history for span parameter
  - `/api/scatter-data`: Returns GPU specs with price for scatter plots
  - `/api/results`: Returns raw search results
  - `/api/stats`: Returns application statistics
- Starts background search worker thread on startup
- Returns `tokens_tested` flag and `active` flag in API responses

### templates/index.html

Frontend web interface with Plotly.js charts:
- **Scatter Plot**: 
  - X-axis: VRAM or Tokens/s
  - Y-axis: Average Price
  - Differentiates tested vs estimated specs with colors
  - Supports 14, 30, and 365-day time periods (default: 30)
- **Price History Graph**:
  - Line chart showing price trends
  - Supports 14d (daily), 30d (daily), 1y (weekly) spans
  - X-axis formatted as DD/MM
  - Default span: 30 days
- **Results Table**:
  - Searchable by GPU title
  - Filterable by VRAM, tokens/s, price
  - Shows active/inactive status
  - Links to Marktplaats listings (prefers active listings)

### tests/

Automated test suite.

#### `test_validation.py`
- Tests GPU listing validation with fuzzy matching
- Demonstrates:
  - Correct matching (e.g., "RTX 3090" → "RTX 3090")
  - Ti tie-breaking (e.g., "RTX 3080 Ti" found but searched "RTX 3080")
  - Cross-generation corrections (e.g., "RTX 4090" found but searched "RTX 4080")
  - Rejection of low-quality matches
- Run with: `python -m pytest tests/` or directly: `python tests/test_validation.py`

### docs/

Project documentation.

- **DOCKER.md**: Docker and Docker Compose deployment guide
- **VALIDATION.md**: Detailed validation implementation documentation
- **STRUCTURE.md**: This file

## Import Patterns

### Within Package (src/gpuutje_kopen/)

Modules use relative imports for cleaner dependencies:

```python
# In search_worker.py
from .gpu_list import GPU_LIST
from .storage import save_result, mark_active_listings
from .validation import validate_listing
```

### From app.py (Root Level)

```python
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import from package
from gpuutje_kopen.storage import save_result, load_results
from gpuutje_kopen.analytics import calc_price_history
from gpuutje_kopen.search_worker import start_worker_thread
```

### From Tests

```python
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import from package
from gpuutje_kopen.validation import validate_listing
```

## Data Persistence

**File**: `data/results.json`

Structure:
```json
{
  "results": [
    {
      "gpu": "RTX 3090 24GB",
      "date": "2024-02-22T10:30:45",
      "timestamp": 1708586445.0,
      "price": 850.00,
      "listing": {
        "id": "1234567890",
        "title": "RTX 3090 24GB - excellent condition",
        "url": "https://www.marktplaats.nl/v/...",
        "active": true
      }
    }
  ]
}
```

- Thread-safe writes with file-level locking
- Accumulates all historical results
- Listings tracked by unique `listing.id` with `active` flag
- Date format: ISO 8601 (YYYY-MM-DDTHH:MM:SS)

## Running the Application

### Local Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run application
python app.py
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up

# Access at http://localhost:5000
```

## Configuration

### Python Version

Specified in `.python-version`: Python 3.12

### Dependencies

Defined in `pyproject.toml`:
- flask: Web framework
- marktplaats: Marktplaats API wrapper
- rapidfuzz: Fuzzy string matching
- requests: HTTP library (transitive)

### Search Interval

Set in `search_worker.py`:
```python
SEARCH_INTERVAL = 8  # hours
```

### Validation Threshold

Set in `validation.py`:
```python
DEFAULT_THRESHOLD = 70  # out of 100
```

## Development Workflow

1. **Add new GPU**: Edit `src/gpuutje_kopen/gpu_list.py`, add to `GPU_LIST`
2. **Add new route**: Edit `app.py`, implement Flask route
3. **Add tests**: Create files in `tests/`, import from package
4. **Update docs**: Add/edit files in `docs/`

All imports within the package use relative imports for clean dependency management.

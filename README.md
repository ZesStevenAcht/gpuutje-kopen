# GPU Price Tracker for Marktplaats

A Flask-based web application that periodically searches for GPUs on Marktplaats and displays price trends, analysis graphs, and a searchable results table.

## Features

### Search & Data Collection
- **Periodic Searches**: Runs automatic GPU searches every 8 hours
- **Spelling Variations**: Handles different GPU naming conventions (Ti/ti, capitalization variations)
- **Listing Validation**: Uses fuzzy matching to verify listings match the correct GPU model
- **Accumulating Results**: Stores all historical search results for trend analysis

### Web Interface
- **3 Interactive Graphs**:
  - Price trend graph for individual GPUs (with dropdown selector)
  - VRAM vs Average Price scatter plot with Pareto front highlighting
  - Tokens/s vs Average Price scatter plot with Pareto front highlighting
  - Time period filters (1 day, 7 days, 30 days, all-time)

- **Search Results Table**:
  - Filterable by minimum VRAM, minimum tokens/s, and maximum price
  - Searchable by title
  - Direct links to Marktplaats listings
  - Shows GPU specs inline

### Design
- Responsive mobile-first design (works on all screen sizes)
- Modern gradient UI with smooth interactions
- Real-time stats dashboard

## Project Structure

```
/home/Marktplaats_scraper/
├── main.py                  # GPU list definitions with specs
├── app.py                   # Flask web application
├── search_worker.py         # Periodic search background worker
├── storage.py              # Data persistence (JSON-based)
├── analytics.py            # Price analysis and Pareto front calculation
├── templates/
│   └── index.html          # Web interface
├── data/
│   └── results.json        # Accumulated search results
├── pyproject.toml          # Python dependencies
└── README.md              # This file
```

## Installation & Running

### Install Dependencies
```bash
pip install -e .
# or with uv:
uv sync
```

### Start the Application
```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

### Run One-Time Search (Testing)
```bash
python search_worker.py
```

## How It Works

1. **Search Worker** (`search_worker.py`):
   - Runs every 8 hours in a background thread
   - Searches for each GPU in `GPU_LIST` using multiple search query variations
   - **Validates each listing** using fuzzy matching to ensure it matches the correct GPU model
   - Corrects mismatched listings (e.g., RTX 3080 Ti found for RTX 3080 search)
   - Rejects listings with low confidence matches
   - Saves validated results to `data/results.json` with timestamps

2. **Listing Validation** (`validation.py`):
   - Uses `rapidfuzz` library for intelligent fuzzy matching
   - Compares listing titles against all GPU models to find the best match
   - **Detects mismatches**: If a listing mentions a different GPU than searched, it corrects it
   - **Example**: "RTX 3080 Ti found for RTX 3080 search" → Automatically corrected to RTX 3080 Ti
   - Rejects listings with generic titles that don't clearly identify a GPU
   - Threshold: 60/100 match score minimum

3. **Storage** (`storage.py`):
   - Stores all search results with timestamps and pricing data
   - Handles duplicate detection (same GPU, title, price)
   - Provides queries for historical data and aggregations

3. **Analytics** (`analytics.py`):
   - Calculates price averages over different time periods
   - Identifies Pareto front (optimal GPU value combinations)
   - Aggregates daily price history

4. **Web App** (`app.py`):
   - Flask server with JSON APIs
   - Serves the interactive HTML interface
   - Automatically starts search worker thread

## Testing

### Test Listing Validation
To verify the fuzzy matching validation works correctly:
```bash
python test_validation.py
```

This demonstrates how the validation system:
- Corrects listings found for the wrong GPU
- Accepts listings that match the expected GPU
- Rejects overly generic listings with low confidence

### Test Search Worker
To run a single search cycle:
```bash
python search_worker.py
```

Check the logs for validation results. When a listing is corrected, you'll see:
```
INFO: Listing corrected: 'RTX 3080 Ti...' -> RTX 3080 10GB corrected to RTX 3080 Ti 12GB (score: 100.0)
```

## Configuration

### Adding/Removing GPUs
Edit `GPU_LIST` in [main.py](main.py):
```python
GPU("RTX 5090 32GB", tokens_per_second, vram_gb, ["search", "queries"]),
```

### Changing Search Interval
Edit `SEARCH_INTERVAL` in [search_worker.py](search_worker.py):
```python
SEARCH_INTERVAL = 8 * 60 * 60  # seconds
```

### Adjusting Validation Threshold
To make validation more/less strict, adjust the threshold in calls to `validate_listing()` in [search_worker.py](search_worker.py):
```python
is_valid, corrected_gpu, match_score = validate_listing(gpu.name, title, threshold=60)
```
- Lower threshold (e.g., 50) = More lenient, accepts more listings
- Higher threshold (e.g., 70) = Stricter, rejects more borderline cases

### Customizing Filters
Edit the form controls in [templates/index.html](templates/index.html)

## API Endpoints

- `GET /` - Main web interface
- `GET /api/gpus` - List of all tracked GPUs
- `GET /api/price-history/<gpu_name>` - Daily price history for a GPU
- `GET /api/scatter-data?days=7&metric=vram` - Scatter plot data with Pareto front
- `GET /api/results` - Search results with filters
- `GET /api/stats` - Statistics and update info

## Tech Stack

- **Backend**: Flask (Python 3.12+)
- **Frontend**: Bootstrap 5, Plotly.js
- **Data**: JSON (easily upgradeable to SQLite)
- **Search**: Marktplaats API (via `marktplaats` package)
- **Fuzzy Matching**: RapidFuzz (for listing validation)

## Next Steps

After testing, the application can be deployed using Docker. See `dockerfile` commands later.

## PEP-8 Compliance

All code follows PEP-8 style guidelines with:
- Short, descriptive variable names
- Clear function and class docstrings
- Proper type hints where beneficial
- Simple, readable code structure

## Notes

- No specific Marktplaats category filters applied - searches across all categories
- Automatic duplicate detection prevents storing same listing multiple times
- Results are stored indefinitely - consider implementing cleanup for very old data
- Mobile-responsive design tested on common viewport sizes

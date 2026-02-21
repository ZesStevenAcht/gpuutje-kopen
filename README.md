# GPU Price Tracker for Marktplaats

A Flask-based web application that periodically searches for GPUs on Marktplaats and displays price trends, analysis graphs, and a searchable results table.

## Features

### Search & Data Collection
- **Periodic Searches**: Runs automatic GPU searches every 8 hours
- **Spelling Variations**: Handles different GPU naming conventions (Ti/ti, capitalization variations)
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
   - Saves results to `data/results.json` with timestamps

2. **Storage** (`storage.py`):
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

## API Endpoints

- `GET /` - Main web interface
- `GET /api/gpus` - List of all tracked GPUs
- `GET /api/price-history/<gpu_name>` - Daily price history for a GPU
- `GET /api/scatter-data?days=7&metric=vram` - Scatter plot data with Pareto front
- `GET /api/results` - Search results with filters
- `GET /api/stats` - Statistics and update info

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

### Customizing Filters
Edit the form controls in [templates/index.html](templates/index.html)

## Tech Stack

- **Backend**: Flask (Python 3.12+)
- **Frontend**: Bootstrap 5, Plotly.js
- **Data**: JSON (easily upgradeable to SQLite)
- **Search**: Marktplaats API (via `marktplaats` package)

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

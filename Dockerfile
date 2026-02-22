FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/ZesStevenAcht/gpuutje-kopen.git .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir -e .

# Ensure data directory exists
RUN mkdir -p /app/data

# Expose Flask port
EXPOSE 5000

# Run the Flask app (search worker runs in background thread)
CMD ["python", "app.py"]

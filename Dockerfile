FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy local repository files into the container
COPY . /app

# Ensure data directory exists
RUN mkdir -p /app/data

# Expose Flask port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
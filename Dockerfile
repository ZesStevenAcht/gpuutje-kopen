FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
    
# Copy local repository files into the container
COPY . /app
    
# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Ensure data directory exists
RUN mkdir -p /app/data

# Expose Flask ports (public + admin)
EXPOSE 5000
EXPOSE 5001

# Run both apps via a small shell wrapper
CMD ["sh", "-c", "python admin_app.py & python app.py"]
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy repository files (provided by docker-compose build context)
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Ensure data directory exists (will be overridden by volume mount)
RUN mkdir -p /app/data

# Expose Flask ports (public + admin)
EXPOSE 5000
EXPOSE 5001

# Run both apps via a small shell wrapper
CMD ["sh", "-c", "python admin_app.py & python app.py"]
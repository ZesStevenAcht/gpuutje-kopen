FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy repository files (provided by docker-compose build context)
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Ensure data directory exists (will be overridden by volume mount)
RUN mkdir -p /app/data

# Build a pre-seeded database at build time into a safe location
# that won't be overridden by a volume mount on /app/data
RUN mkdir -p /app/data_builtin && \
    python -c "import sys; sys.path.insert(0,'/app/src'); \
import gpuutje_kopen.db as db; db.init_db()" && \
    cp /app/data/gpuutje.db /app/data_builtin/gpuutje.db

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose Flask ports (public + admin)
EXPOSE 5000
EXPOSE 5001

# Entrypoint handles DB seeding / merging, then runs CMD
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-c", "python admin_app.py & python app.py"]
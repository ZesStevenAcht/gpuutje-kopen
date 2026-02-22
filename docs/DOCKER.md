# Docker Setup Guide for GPUutje Kopen

This setup uses Docker and Docker Compose to run the GPU price tracker in a containerized environment with persistent data storage.

## Prerequisites

- Docker: https://docs.docker.com/get-docker/
- Docker Compose: https://docs.docker.com/compose/install/

## Quick Start

### Standalone (No Local Clone or Dockerfile Required)

The simplest way to run the application is with just the docker-compose.yml file. No repository clone or Dockerfile needed:

```bash
# Download docker-compose.yml to any directory
curl -o docker-compose.yml https://raw.githubusercontent.com/ZesStevenAcht/gpuutje-kopen/master/docker-compose.yml

# Start the application
docker-compose up
```

The app will:
- Pull the pre-built image from GitHub Container Registry
- Start the Flask web app on port 5000
- Run the search worker in a background thread (searches every 8 hours)

Access the dashboard:

Open your browser to `http://localhost:5000`

### From Local Repository (Optional)

If you have the repository cloned and want to build locally:

```bash
cd gpuutje-kopen

# Edit docker-compose.yml to use local build
# Replace: image: ghcr.io/zessstevenacht/gpuutje-kopen:latest
# With: build: .

docker-compose up --build
```

## Data Persistence

The `data/results.json` file is stored in a **Docker named volume** (`gpuutje-data`). This means:

- All search results persist across container restarts
- The setup works standalone without requiring local directories
- Data is stored on your Docker host machine

To access the data:

```bash
# View all Docker volumes
docker volume ls | grep gpuutje

# Inspect the volume location
docker volume inspect gpuutje-data

# Copy data from volume to host
docker cp gpuutje-kopen-app:/app/data/results.json ./results.json

# Or, export data from volume
docker run --rm -v gpuutje-data:/data -v $(pwd):/backup alpine cp /data/results.json /backup/results.json
```

## Stopping the Container

```bash
docker-compose down
```

To also remove the downloaded image:

```bash
docker-compose down --rmi all
```

To remove the persistent data volume:

```bash
docker volume rm gpuutje-data
```

## Image Updates

The Docker image is automatically built and pushed to GitHub Container Registry whenever code is pushed to the `master` branch. 

**Available tags:**
- `latest`: Most recent version (always points to the latest master build)
- Commit SHAs: Specific builds (e.g., `abcd1234`) for reproducible deployments

To use a specific version:

```bash
# Edit docker-compose.yml
sed -i 's|ghcr.io/zessstevenacht/gpuutje-kopen:latest|ghcr.io/zessstevenacht/gpuutje-kopen:COMMIT_SHA|g' docker-compose.yml

# Pull and run
docker-compose up
```

## Configuration

### Custom Data Directory (Bind Mount)

If you want to store `results.json` in a specific host directory instead of using Docker volumes, edit `docker-compose.yml`:

**Replace this:**
```yaml
volumes:
  gpuutje-data:
    driver: local
```

**With:**
```yaml
volumes:
  gpuutje-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/your/data
```

Or use a bind mount in the service:
```yaml
volumes:
  - ./data:/app/data
```

Then create the directory locally:
```bash
mkdir -p ./data
```

### Adjusting Search Interval

Edit `src/gpuutje_kopen/search_worker.py` in the repository to change `SEARCH_INTERVAL` (currently 8 hours = 28800 seconds).

### Environment Variables

In `docker-compose.yml`, you can add or modify environment variables:

```yaml
environment:
  - FLASK_ENV=production
  - FLASK_APP=app.py
  - MY_CUSTOM_VAR=value
```

## Logs

To view container logs in real-time:

```bash
docker-compose logs -f
```

To view logs from a specific service:

```bash
docker-compose logs -f gpuutje-kopen
```

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, change the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8080:5000"
```

Then access the app at `http://localhost:8080`.

### Permission Issues with Named Volumes

Named volumes are managed by Docker and usually don't have permission issues. If you encounter problems:

```bash
# Remove and recreate the volume
docker volume rm gpuutje-data
docker-compose down
docker-compose up --build
```

If using bind mounts (`./data`), ensure the folder is readable/writable:

```bash
mkdir -p ./data
chmod 755 ./data
```

### Local Development with Local Build

If you're developing locally and want to build from your modified code:

1. Edit docker-compose.yml to use local build:
```yaml
services:
  gpuutje-kopen:
    build: .
    # ... rest of config
```

2. Build and run:
```bash
docker-compose up --build
```

3. When done, revert to using the remote image to avoid unnecessary rebuilds

## Development Mode

For development with hot reloads and debugging, you can override the command:

```bash
docker-compose run --service-ports gpuutje-kopen python -m flask run --host=0.0.0.0
```

However, note that the search worker won't auto-reload.

## More Information

- GitHub Repository: https://github.com/ZesStevenAcht/gpuutje-kopen.git
- Flask Documentation: https://flask.palletsprojects.com/
- Docker Compose Documentation: https://docs.docker.com/compose/

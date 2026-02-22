# Docker Setup Guide for GPUutje Kopen

This setup uses Docker and Docker Compose to run the GPU price tracker in a containerized environment with persistent data storage.

## Prerequisites

- Docker: https://docs.docker.com/get-docker/
- Docker Compose: https://docs.docker.com/compose/install/

## Quick Start

1. Clone or navigate to the project directory (or use the pre-built image):

```bash
cd gpuutje-kopen
```

2. Start the application:

```bash
docker-compose up --build
```

The app will:
- Clone/build from the GitHub repository
- Install all dependencies
- Start the Flask web app on port 5000
- Run the search worker in a background thread (searches every 8 hours)

3. Access the dashboard:

Open your browser to `http://localhost:5000`

## Data Persistence

The `data/results.json` file is stored on your **host machine** in the `./data` directory (relative to where you run `docker-compose`). This means:

- All search results persist across container restarts
- You can easily backup or inspect the data
- Changes to `data/results.json` on the host are immediately visible to the container

## Stopping the Container

```bash
docker-compose down
```

To also remove the built image:

```bash
docker-compose down --rmi local
```

## Configuration

### Custom Data Directory

If you want to store `results.json` in a different location, edit `docker-compose.yml`:

```yaml
volumes:
  - /path/to/your/data:/app/data
```

Replace `/path/to/your/data` with your desired host directory.

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

### Permission Issues with Data Folder

If you encounter permission errors accessing `./data`, ensure the folder exists and is readable/writable:

```bash
mkdir -p ./data
chmod 755 ./data
```

### Rebuilding the Image

If you modify the code and want to rebuild the Docker image:

```bash
docker-compose up --build
```

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

# AI Trip Planner - Run Commands

## Current Configuration

- **Model**: `llama3.2` (3B parameters)
- **Database**: PostgreSQL 15
- **App Port**: 8000
- **Ollama Port**: 11435 (mapped from 11434)

## Start Application (Production)

### Full Setup (First Time)
```bash
# Stop any existing containers
docker-compose down

# Build containers from scratch
docker-compose build --no-cache

# Start all services (app, postgres, ollama)
docker-compose up -d

# Wait for services to initialize
timeout 15

# Pull the llama3.2 model into Ollama
docker-compose exec ollama ollama pull llama3.2

# View logs (Ctrl+C to exit)
docker-compose logs -f
```

### Quick Start (After First Setup)
```bash
docker-compose up -d
docker-compose logs -f
```

### One-Line Command
```bash
docker-compose down && docker-compose build --no-cache && docker-compose up -d && timeout 15 && docker-compose exec ollama ollama pull llama3.2
```

## Access Application

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Ollama API**: http://localhost:11435

## Run Tests

### Start Test Database
```bash
# Start test PostgreSQL (port 5433)
docker-compose -f docker-compose.test.yml up -d

# Wait for database to be ready
timeout 10

# Run all tests
pytest test_api.py -v

# Stop test database when done
docker-compose -f docker-compose.test.yml down
```

### One-Line Command
```bash
docker-compose -f docker-compose.test.yml up -d && timeout 10 && pytest test_api.py -v
```

## Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f ollama
docker-compose logs -f postgres
```

### Check Status
```bash
# List running containers
docker-compose ps

# Check environment variables in app
docker-compose exec app printenv | grep OLLAMA
```

### Restart Services
```bash
# Restart specific service
docker-compose restart app

# Restart all services
docker-compose restart
```

### Stop Application
```bash
# Stop all services (keeps data)
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

### Database Access
```bash
# Connect to production database
docker-compose exec postgres psql -U postgres -d trip_planner

# Connect to test database
docker-compose -f docker-compose.test.yml exec postgres_test psql -U postgres -d trip_planner_test
```

### Verify Ollama
```bash
# List available models
docker-compose exec ollama ollama list

# Test Ollama from app container
docker-compose exec app curl -X POST http://ollama:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2", "prompt": "Hello", "stream": false}'
```

## Troubleshooting

### Application won't start
```bash
# Check logs for errors
docker-compose logs app

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Ollama connection errors
```bash
# Verify Ollama is running
docker-compose ps ollama

# Check if model is pulled
docker-compose exec ollama ollama list

# Pull model if missing
docker-compose exec ollama ollama pull llama3.2
```

### Database connection errors
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Restart database
docker-compose restart postgres
```

### Tests failing
```bash
# Ensure test database is running
docker-compose -f docker-compose.test.yml ps

# Restart test database
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml up -d
timeout 10
pytest test_api.py -v
```

## Development Workflow

### Make Code Changes
```bash
# 1. Edit your code files
# 2. Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# 3. View logs to verify
docker-compose logs -f app
```

### Run Tests After Changes
```bash
# Ensure test DB is running
docker-compose -f docker-compose.test.yml up -d
timeout 10

# Run tests
pytest test_api.py -v

# Run specific test
pytest test_api.py::TestTripCreation::test_create_trip_success -v
```

## Clean Slate (Reset Everything)

```bash
# Stop all containers
docker-compose down -v
docker-compose -f docker-compose.test.yml down -v

# Remove all images (optional)
docker-compose down --rmi all

# Start fresh
docker-compose build --no-cache
docker-compose up -d
timeout 15
docker-compose exec ollama ollama pull llama3.2
```

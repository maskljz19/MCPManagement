# Starting MongoDB for Property Tests

## Current Status

Docker is installed on your system (version 29.0.1) but Docker Desktop is not currently running.

## Steps to Run Property Tests

### 1. Start Docker Desktop

1. Open Docker Desktop application
2. Wait for Docker to fully start (the whale icon in system tray should be steady)
3. Verify Docker is running:
   ```bash
   docker ps
   ```

### 2. Start MongoDB Container

Once Docker is running, start MongoDB:

```bash
# Start MongoDB container
docker run -d --name mongodb -p 27017:27017 mongo:latest

# Verify MongoDB is running
docker ps | grep mongodb

# Check MongoDB logs (optional)
docker logs mongodb
```

### 3. Run Property Tests

Now you can run the property tests:

```bash
# Run all AI Analyzer property tests
pytest tests/property/test_ai_analysis_properties.py -v

# Or run with Hypothesis statistics
pytest tests/property/test_ai_analysis_properties.py -v --hypothesis-show-statistics
```

### 4. Stop MongoDB (When Done)

After testing, you can stop and remove the MongoDB container:

```bash
# Stop MongoDB
docker stop mongodb

# Remove container (optional)
docker rm mongodb
```

## Alternative: Use Docker Compose

If you prefer, you can use Docker Compose to manage all services:

```bash
# Start all services (if docker-compose.yml exists)
docker-compose up -d mongodb

# Stop all services
docker-compose down
```

## Troubleshooting

### Docker Desktop Won't Start

1. Check if Hyper-V or WSL2 is enabled (Windows)
2. Restart your computer
3. Reinstall Docker Desktop if necessary

### MongoDB Connection Issues

If tests still fail after starting MongoDB:

1. Check if port 27017 is available:
   ```bash
   netstat -an | findstr 27017
   ```

2. Test MongoDB connection:
   ```bash
   docker exec -it mongodb mongosh --eval "db.adminCommand('ping')"
   ```

3. Check firewall settings (ensure port 27017 is not blocked)

### Property Tests Still Skip

If tests are still skipped:

1. Verify MongoDB is accessible:
   ```bash
   # Install mongosh if needed
   mongosh --eval "db.adminCommand('ping')"
   ```

2. Check the test output for specific error messages

3. Ensure no other service is using port 27017

## What the Property Tests Validate

Once MongoDB is running, the property tests will validate:

- **Property 9**: AI analysis responses contain valid scores (0.0-1.0) and non-empty reasoning
- **Property 10**: Improvement suggestions always return at least one recommendation
- **Property 11**: Generated configurations are valid dictionaries with proper structure
- **Property 12**: Analysis results are correctly persisted in MongoDB with TTL

Each test runs 100 iterations with randomly generated inputs to ensure comprehensive coverage.

## Current Test Results

✅ **Unit Tests**: 11/11 passing (no external dependencies required)
⏸️ **Property Tests**: 4/4 written but not run (MongoDB required)

The unit tests provide good coverage of the core functionality. The property tests add additional confidence by testing with a wide range of random inputs.

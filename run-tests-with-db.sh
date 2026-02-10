#!/bin/bash
# Start PostgreSQL test database and run EDI 835 parser tests
# Usage: ./run-tests-with-db.sh [--keep-data] [--keep-db]

set -e

# Parse arguments
KEEP_DATA=""
KEEP_DB=false

for arg in "$@"; do
    case $arg in
        --keep-data)
            KEEP_DATA="--keep-data"
            ;;
        --keep-db)
            KEEP_DB=true
            ;;
    esac
done

echo "🚀 EDI 835 Parser - Test Database Runner"
echo "=========================================="

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Clean up any existing database
echo ""
echo "🧹 Cleaning up existing database..."
docker compose -f docker-compose.test.yml down -v 2>/dev/null || true

# Start fresh database
echo ""
echo "🐘 Starting fresh PostgreSQL test database..."
docker compose -f docker-compose.test.yml up -d

# Wait for database to be healthy
echo ""
echo "⏳ Waiting for database to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if docker compose -f docker-compose.test.yml ps | grep -q "healthy"; then
        echo "✅ Database is ready!"
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    echo "   Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 1
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ Database failed to become healthy after $MAX_ATTEMPTS seconds"
    echo "   Check logs with: docker compose -f docker-compose.test.yml logs"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "🐍 Activating virtual environment..."
    source venv/bin/activate
fi

# Run tests
echo ""
echo "🧪 Running tests with database seeding..."
echo "=========================================="
echo ""

if [ -n "$KEEP_DATA" ]; then
    python test_with_db.py --keep-data
else
    python test_with_db.py
fi

TEST_EXIT_CODE=$?

# Cleanup or keep database running
echo ""
echo "=========================================="

if [ $KEEP_DB = true ]; then
    echo "💾 Database is still running (--keep-db flag)"
    echo "   Connection: localhost:5433/bot_automation"
    echo "   User: bot / Password: bot_test_password"
    echo ""
    echo "   To stop: docker compose -f docker-compose.test.yml down"
    echo "   To view logs: docker compose -f docker-compose.test.yml logs"
else
    echo "🛑 Stopping database..."
    docker compose -f docker-compose.test.yml down
    echo "✅ Database stopped"
fi

echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests completed successfully!"
    exit 0
else
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE"
    exit $TEST_EXIT_CODE
fi

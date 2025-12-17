#!/bin/bash
# start-docker.sh - One-click start

echo "🤖 Telegram Forwarder - One Click Start"
echo "========================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Create .env file with:"
    echo "API_ID=xxx"
    echo "API_HASH=xxx"
    echo "SESSION_STRING=xxx"
    exit 1
fi

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERROR: Docker is not running!"
    echo "Please start Docker Desktop first."
    exit 1
fi

# Cleanup previous
echo "🧹 Cleaning up previous containers..."
docker-compose down 2>/dev/null
docker rm -f telegram-forwarder-24-7 2>/dev/null

# Build image
echo "🔨 Building Docker image..."
docker-compose build

# Start container
echo "🚀 Starting container..."
docker-compose up -d

# Wait for startup
echo "⏳ Waiting for bot to initialize..."
sleep 10

# Show status
echo ""
echo "📊 STATUS:"
echo "========================================"
docker-compose ps

echo ""
echo "📋 LOGS (last 20 lines):"
echo "========================================"
docker-compose logs --tail=20

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:        docker-compose logs -f"
echo "   Stop bot:         docker-compose down"
echo "   Restart:          docker-compose restart"
echo "   Check health:     curl http://localhost:3000/health"
echo "   Enter container:  docker-compose exec telegram-bot sh"
echo ""
echo "🔍 Check PM2 status inside container:"
docker-compose exec telegram-bot pm2 status

#!/bin/bash
# stop.sh - Stop script

echo "🛑 Stopping Telegram Forwarder..."

# Stop docker-compose
docker-compose down

# Remove container if exists
docker rm -f telegram-forwarder-24-7 2>/dev/null

# Remove volumes
docker volume rm -f telegram-forwader_pm2-data 2>/dev/null
docker volume rm -f telegram-forwader_pm2-logs 2>/dev/null

# Remove dangling images
docker image prune -f

echo "✅ Cleanup completed!"
echo ""
echo "To start again: ./start-docker.sh"
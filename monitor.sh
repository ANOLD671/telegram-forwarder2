#!/bin/bash
# monitor.sh - Monitor and auto-heal

echo "🔍 Starting Telegram Bot Monitor..."
echo "Monitoring interval: 60 seconds"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    clear
    echo "========================================"
    echo "🤖 TELEGRAM BOT MONITOR - $(date)"
    echo "========================================"
    
    # Check if container is running
    if docker ps | grep -q "telegram-forwarder-24-7"; then
        echo "✅ Container: RUNNING"
        
        # Check health endpoint
        HEALTH=$(curl -s http://localhost:3000/health 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$HEALTH" = "UP" ]; then
            echo "✅ Health: UP"
        else
            echo "❌ Health: DOWN - Restarting..."
            docker-compose restart
        fi
        
        # Check PM2 status inside container
        echo ""
        echo "📊 PM2 Status:"
        docker-compose exec telegram-bot pm2 status | grep -A5 "telegram-forwarder"
        
        # Show logs tail
        echo ""
        echo "📝 Recent Logs:"
        docker-compose logs --tail=5 --since=1m
        
    else
        echo "❌ Container: STOPPED"
        echo "Attempting to restart..."
        docker-compose up -d
        sleep 10
    fi
    
    echo ""
    echo "========================================"
    echo "Next check in 60 seconds..."
    echo "========================================"
    
    sleep 60
done
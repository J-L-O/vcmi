#!/bin/bash

# Kill any existing processes
echo "Killing existing processes..."
pkill -f tcp_server.py || true
pkill -f vcmiclient || true
sleep 2

# Start the TCP server in the background
cd /home/jona/CLionProjects/vcmi/AI/RLBattleAI/python
echo "Starting TCP server..."
nohup python tcp_server.py > server.log 2>&1 &
sleep 2

# Check if server started successfully
if grep -q "VCMI TCP Server started" server.log; then
    echo "✓ Server started successfully"
else
    echo "✗ Server failed to start"
    tail -10 server.log
    exit 1
fi

# Start the VCMI game
cd /home/jona/CLionProjects/vcmi
echo "Starting VCMI game..."
timeout 30 /home/jona/CLionProjects/vcmi/build/bin/vcmiclient --testmap "Maps/Arrogance.h3m" --headless --onlyai > game.log 2>&1 &

# Check results
sleep 30
echo "\n=== Server Log ==="
cat /home/jona/CLionProjects/vcmi/AI/RLBattleAI/python/server.log

echo "\n=== Game Log ==="
cat /home/jona/CLionProjects/vcmi/game.log

echo "\n=== Test Complete ==="

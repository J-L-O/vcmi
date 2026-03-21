#!/bin/bash

# Kill any existing processes
echo "Killing existing processes..."
pkill -9 -f rl_server.py || true
pkill -9 -f tcp_server.py || true
pkill -9 -f vcmiclient || true
sleep 3

# Start the RL Training server in the background
cd /home/jona/CLionProjects/vcmi/AI/RLBattleAI/python
echo "Starting RL Training server..."
nohup python3 rl_server.py > server.log 2>&1 &
sleep 3

# Check if server started successfully
if grep -q "RL Training Server started" server.log; then
    echo "✓ RL Server started successfully"
else
    echo "✗ Server failed to start"
    tail -20 server.log
    exit 1
fi

# Start the VCMI game
cd /home/jona/CLionProjects/vcmi
echo "Starting VCMI game..."
timeout 60 /home/jona/CLionProjects/vcmi/build/bin/vcmiclient --testmap "Maps/Arrogance.h3m" --headless --onlyai > game.log 2>&1 &
GAME_PID=$!

# Wait for game or server output
echo "Waiting for game interaction..."
sleep 10

# Show partial server log for debugging
echo "\n=== Server Log (last 50 lines) ==="
tail -50 /home/jona/CLionProjects/vcmi/AI/RLBattleAI/python/server.log

echo "\n=== Game Log (last 30 lines) ==="
tail -30 /home/jona/CLionProjects/vcmi/game.log

echo "\n=== Test Complete ==="

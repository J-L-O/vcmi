#!/bin/bash

# Kill any existing processes
echo "Killing existing processes..."
pkill -f training_loop.py || true
pkill -f tcp_server.py || true
pkill -f vcmiclient || true
sleep 2

# Start the training loop server in the background
cd /home/jona/CLionProjects/vcmi/AI/RLBattleAI/python
echo "Starting training loop server..."
nohup python training_loop.py > server.log 2>&1 &
SERVER_PID=$!
sleep 2

# Check if server started successfully
if grep -q "Starting RL training loop server" server.log; then
    echo "Server started successfully (PID: $SERVER_PID)"
else
    echo "Server failed to start"
    tail -20 server.log
    exit 1
fi

# Start the VCMI game
cd /home/jona/CLionProjects/vcmi
echo "Starting VCMI game..."
timeout 60 /home/jona/CLionProjects/vcmi/build/bin/vcmiclient --testmap "Maps/Arrogance.h3m" --headless --onlyai > game.log 2>&1 &
GAME_PID=$!

# Wait for the game to finish or timeout
echo "Waiting for game to complete (max 60s)..."
wait $GAME_PID 2>/dev/null
GAME_EXIT=$?

echo ""
echo "=== Server Log ==="
cat /home/jona/CLionProjects/vcmi/AI/RLBattleAI/python/server.log

echo ""
echo "=== Game Log (last 50 lines) ==="
tail -50 /home/jona/CLionProjects/vcmi/game.log

# Check for success indicators
echo ""
echo "=== Results ==="
if grep -q "Sending action" /home/jona/CLionProjects/vcmi/AI/RLBattleAI/python/server.log; then
    echo "SUCCESS: Training loop sent actions to the game"
else
    echo "FAILURE: No actions were sent"
fi

if grep -q "Executing action" /home/jona/CLionProjects/vcmi/game.log; then
    echo "SUCCESS: Game received and executed actions from training loop"
else
    echo "FAILURE: Game did not execute any actions from training loop"
fi

# Cleanup
kill $SERVER_PID 2>/dev/null || true

echo ""
echo "=== Test Complete ==="

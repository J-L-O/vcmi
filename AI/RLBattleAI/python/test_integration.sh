#!/bin/bash

# Test script for full RL Battle AI integration
# Tests the interaction between Python RL training loop and VCMI game

set -e  # Exit on error

echo "=========================================="
echo "VCMI RL Battle AI Integration Test"
echo "=========================================="
echo ""

# Configuration
PYTHON_SERVER="/home/jona/CLionProjects/vcmi/AI/RLBattleAI/python/rl_training_loop.py"
SERVER_LOG="/home/jona/CLionProjects/vcmi/AI/RLBattleAI/python/server.log"
GAME_LOG="/home/jona/CLionProjects/vcmi/game.log"
TIMEOUT_SECONDS=30

# Kill any existing processes
echo "[1/5] Cleaning up existing processes..."
pkill -f rl_training_loop.py 2>/dev/null || true
pkill -f tcp_server.py 2>/dev/null || true
pkill -f vcmiclient 2>/dev/null || true
sleep 2

# Clean up old log files
rm -f "$SERVER_LOG" "$GAME_LOG"

# Start the RL training server in the background
echo "[2/5] Starting RL training server..."
cd /home/jona/CLionProjects/vcmi/AI/RLBattleAI/python
python rl_training_loop.py --verbose > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
sleep 3

# Check if server started successfully
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "ERROR: Server failed to start!"
    echo "Server log:"
    cat "$SERVER_LOG"
    exit 1
fi

if grep -q "VCMI RL Training Server" "$SERVER_LOG"; then
    echo "✓ Server started successfully (PID: $SERVER_PID)"
else
    echo "WARNING: Server may not have started properly, continuing..."
fi

echo ""
echo "[3/5] Waiting for server to be ready..."
sleep 2

# Check if the server is listening on port 65432
if netstat -tlnp 2>/dev/null | grep -q ":65432"; then
    echo "✓ Server is listening on port 65432"
else
    echo "WARNING: Server may not be listening on port 65432, continuing..."
fi

# Start the VCMI game
echo ""
echo "[4/5] Starting VCMI game client..."
cd /home/jona/CLionProjects/vcmi
timeout $TIMEOUT_SECONDS /home/jona/CLionProjects/vcmi/build/bin/vcmiclient --testmap "Maps/Arrogance.h3m" --headless --onlyai > "$GAME_LOG" 2>&1 &
GAME_PID=$!

echo "✓ Game started (PID: $GAME_PID)"
echo ""
echo "[5/5] Running test for ${TIMEOUT_SECONDS} seconds..."

# Wait for the game to run
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $TIMEOUT_SECONDS ]; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))

    # Check if game is still running
    if ! kill -0 $GAME_PID 2>/dev/null; then
        echo "Game finished early after ${WAIT_COUNT} seconds"
        break
    fi

    # Show progress
    if [ $((WAIT_COUNT % 5)) -eq 0 ]; then
        echo "  ... ${WAIT_COUNT}s elapsed"
    fi
done

# Kill remaining processes
echo ""
echo "Cleaning up processes..."
kill $SERVER_PID 2>/dev/null || true
kill $GAME_PID 2>/dev/null || true
sleep 1

# Display results
echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
echo ""

echo "=== Server Log (last 50 lines) ==="
if [ -f "$SERVER_LOG" ]; then
    tail -50 "$SERVER_LOG"
else
    echo "Server log not found"
fi

echo ""
echo "=== Game Log (last 50 lines) ==="
if [ -f "$GAME_LOG" ]; then
    tail -50 "$GAME_LOG"
else
    echo "Game log not found"
fi

echo ""
echo "=== Checking for successful interaction ==="

# Check if server received connections
if grep -q "Connection established" "$SERVER_LOG" 2>/dev/null; then
    echo "✓ Server received connections from game"
    CONNECTIONS=$(grep -c "Connection established" "$SERVER_LOG" 2>/dev/null || echo "0")
    echo "  Total connections: $CONNECTIONS"
else
    echo "✗ No connections established"
fi

# Check if server received battle events
if grep -q "BattleStart received" "$SERVER_LOG" 2>/dev/null; then
    echo "✓ Server received BattleStart events"
    BATTLES=$(grep -c "BattleStart received" "$SERVER_LOG" 2>/dev/null || echo "0")
    echo "  Total battles: $BATTLES"
else
    echo "✗ No BattleStart events received"
fi

# Check if server received active stack events
if grep -q "BattleSetActiveStack received" "$SERVER_LOG" 2>/dev/null; then
    echo "✓ Server received BattleSetActiveStack events"
    ACTIONS=$(grep -c "BattleSetActiveStack received" "$SERVER_LOG" 2>/dev/null || echo "0")
    echo "  Total active stack events: $ACTIONS"
else
    echo "✗ No BattleSetActiveStack events received"
fi

# Check if actions were sent back
if grep -q "Sent action:" "$SERVER_LOG" 2>/dev/null; then
    echo "✓ Server sent actions back to game"
    SENT_ACTIONS=$(grep -c "Sent action:" "$SERVER_LOG" 2>/dev/null || echo "0")
    echo "  Total actions sent: $SENT_ACTIONS"
else
    echo "✗ No actions sent back to game"
fi

# Check if C++ side received actions
if grep -q "Received packet from Python server" "$GAME_LOG" 2>/dev/null; then
    echo "✓ Game received actions from Python server"
    RECEIVED_ACTIONS=$(grep -c "Received packet from Python server" "$GAME_LOG" 2>/dev/null || echo "0")
    echo "  Total packets received: $RECEIVED_ACTIONS"
else
    echo "✗ Game did not receive actions from Python server"
fi

# Check if actions were executed
if grep -q "Executing action from Python server" "$GAME_LOG" 2>/dev/null; then
    echo "✓ Game executed actions from Python server"
    EXECUTED_ACTIONS=$(grep -c "Executing action from Python server" "$GAME_LOG" 2>/dev/null || echo "0")
    echo "  Total actions executed: $EXECUTED_ACTIONS"
else
    echo "✗ Game did not execute actions from Python server"
fi

echo ""
echo "=========================================="
echo "Integration Test Complete"
echo "=========================================="

# Return success if we had successful interaction
if grep -q "Executing action from Python server" "$GAME_LOG" 2>/dev/null; then
    echo ""
    echo "✓ FULL SYSTEM TEST PASSED"
    echo "  Python RL training loop successfully communicated with VCMI game!"
    exit 0
else
    echo ""
    echo "✗ FULL SYSTEM TEST INCOMPLETE"
    echo "  Actions were not fully executed. Check logs for details."
    exit 1
fi

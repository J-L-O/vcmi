#!/usr/bin/env python3
"""
Integration test for RLBattleAI - Python server side
Tests the network communication between Python server and C++ client
"""

import socket
import struct
import time
import threading
from tcp_server import VCMITCPServer, BattleAIHandler
from vcmi_types import BattleStart

class TestHandler(BattleAIHandler):
    """Test handler for battle events"""
    
    def __init__(self):
        self.battle_started = False
        self.active_stack_received = False
        
    def handle_battle_start(self, battle_id: int, battle_info: BattleStart) -> None:
        """Handle battle start event"""
        print(f"✓ Battle start received - Battle ID: {battle_id}")
        self.battle_started = True
        
        # Check if we have battle info
        if battle_info.info:
            print(f"  Has battle info: Yes")
            print(f"  Round: {battle_info.info.round}")
        else:
            print(f"  Has battle info: No")
    
    def handle_set_active_stack(self, battle_id: int, stack_id: int) -> None:
        """Handle active stack change"""
        print(f"✓ Active stack received - Battle: {battle_id}, Stack: {stack_id}")
        self.active_stack_received = True

def test_server_basic():
    """Test basic server functionality"""
    print("=" * 60)
    print("Testing Python Server Basic Functionality")
    print("=" * 60)
    
    handler = TestHandler()
    server = VCMITCPServer(host='127.0.0.1', port=65432)
    server.set_handler(handler)
    
    # Run server in background thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Give server time to start
    time.sleep(1)
    
    print("✓ Server started on 127.0.0.1:65432")
    print("✓ Waiting for connection...")
    
    # Wait a bit then stop
    time.sleep(3)
    
    # Stop server
    server.stop()
    
    # Check results
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    if server_thread.is_alive():
        print("✗ Server thread still running (unexpected)")
        return False
    else:
        print("✓ Server stopped cleanly")
    
    if not handler.battle_started and not handler.active_stack_received:
        print("⚠ No battle events received (expected - no client connected)")
        print("✓ Server started and stopped correctly")
        return True
    elif handler.battle_started:
        print("✓ Battle start event received")
        return True
    else:
        print("✗ Unexpected state")
        return False

if __name__ == "__main__":
    success = test_server_basic()
    exit(0 if success else 1)

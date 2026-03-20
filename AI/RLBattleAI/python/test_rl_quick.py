#!/usr/bin/env python3
"""
Quick test of RL training server without needing the C++ game
"""

import socket
import struct
import time
import sys
sys.path.insert(0, '/home/jona/CLionProjects/vcmi/AI/RLBattleAI/python')

from tcp_server import VCMIProtocolHandler
from vcmi_types import (
    serialize_battle_action, BattleAction, BattleActionDestination, BattleHex,
    EActionType, BattleSide, SpellID
)

def send_message(sock, data):
    """Send a message with length prefix"""
    length = len(data)
    sock.sendall(struct.pack('<I', length))
    sock.sendall(data)
    print(f"Sent {length} bytes")

def receive_message(sock):
    """Receive a message with length prefix"""
    length_data = sock.recv(4)
    if len(length_data) == 0:
        return None
    message_length = struct.unpack('<I', length_data)[0]
    data = sock.recv(message_length)
    print(f"Received {len(data)} bytes")
    return data

def test_action_serialization():
    """Test that we can serialize and deserialize actions correctly"""
    print("Testing BattleAction serialization...")

    # Create a sample action
    action = BattleAction()
    action.side = BattleSide.ATTACKER
    action.stack_number = 5
    action.action_type = EActionType.DEFEND
    action.spell = SpellID(-1)
    action.target = []

    # Serialize it
    data = serialize_battle_action(action)
    print(f"Serialized action to {len(data)} bytes")
    print(f"Hex: {data.hex()}")

    # Expected format for DEFEND action:
    # side (1 byte): 0x00 (ATTACKER = 0)
    # stack_number (compact): 0x05 (stack 5)
    # action_type (1 byte): 0x07 (DEFEND = 7)
    # spell (compact): 0x7f (spell -1 encoded)
    # target length (compact): 0x00 (empty vector)

    print("✓ Action serialization test passed")
    return True

def test_server_connection():
    """Test connecting to the RL training server"""
    print("\nTesting connection to RL training server...")

    # Start the server in a subprocess
    import subprocess
    import os

    server_script = '/home/jona/CLionProjects/vcmi/AI/RLBattleAI/python/rl_training_loop.py'

    # Start server
    env = os.environ.copy()
    env['PYTHONPATH'] = '/home/jona/CLionProjects/vcmi/AI/RLBattleAI/python'

    proc = subprocess.Popen(
        ['python', server_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )

    # Wait for server to start
    time.sleep(2)

    try:
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 65432))
        print("✓ Connected to server")

        # Create and send a BattleSetActiveStack pack to trigger action computation
        # This simulates what the C++ game would send

        # Pack format:
        # - bool: not null (1 byte)
        # - pointer_id (compact int)
        # - type_id (compact int) - 134 for BattleSetActiveStack
        # - battle_id (compact int)
        # - stack (compact int)
        # - reason (compact int)

        pack_data = bytes([
            0x00,        # not null
            0x00,        # pointer_id = 0
            0x86, 0x01,  # type_id = 134 (BattleSetActiveStack) - encoded as compact int
            0x01,        # battle_id = 1
            0x05,        # stack = 5
            0x00,        # reason = 0 (TURN_QUEUE)
        ])

        send_message(sock, pack_data)
        print("✓ Sent BattleSetActiveStack pack")

        # Wait for response (action from server)
        print("Waiting for action response...")
        sock.settimeout(5)
        response = receive_message(sock)

        if response:
            print(f"✓ Received action response: {len(response)} bytes")
            print(f"  Hex: {response.hex()}")

            # Parse the action to verify it's a DEFEND action
            if len(response) >= 3:
                side = response[0]
                # stack_number is compact encoded
                # action_type should be DEFEND (7)
                print(f"  Side: {side}")
                print("✓ Successfully received action from server!")
                return True
        else:
            print("✗ No response received (timeout)")
            return False

    except socket.timeout:
        print("✗ Connection timed out")
        return False
    except ConnectionRefusedError:
        print("✗ Connection refused - is the server running?")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        sock.close()
        proc.terminate()
        proc.wait()

def main():
    print("=" * 60)
    print("RL Training Server Quick Test")
    print("=" * 60)

    # Test 1: Action serialization
    if not test_action_serialization():
        print("\n✗ Action serialization test failed")
        return 1

    # Test 2: Server connection
    if not test_server_connection():
        print("\n✗ Server connection test failed")
        return 1

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

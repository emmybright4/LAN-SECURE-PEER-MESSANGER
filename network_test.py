#!/usr/bin/env python3
"""
Network Test Script - Run on both devices to test connectivity
"""

import socket
import json
import threading
import time

def test_network():
    """Test UDP discovery and TCP messaging"""
    
    def udp_listener(port=6666):
        """Listen for UDP broadcasts"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.settimeout(2)
        
        print(f"[UDP] Listening on port {port}...")
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                print(f"[UDP] Received from {addr[0]}: {data[:50]}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[UDP] Error: {e}")
                break
    
    def udp_broadcast(port=6666):
        """Send UDP broadcasts"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        message = {
            'type': 'test',
            'message': 'Hello from test',
            'time': time.time()
        }
        
        while True:
            try:
                sock.sendto(json.dumps(message).encode(), ('255.255.255.255', port))
                print("[UDP] Broadcast sent")
                time.sleep(3)
            except Exception as e:
                print(f"[UDP] Broadcast error: {e}")
                break
    
    def tcp_server(port=6667):
        """Run TCP server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.listen(5)
        sock.settimeout(2)
        
        print(f"[TCP] Server listening on port {port}...")
        
        while True:
            try:
                client, addr = sock.accept()
                print(f"[TCP] Connection from {addr[0]}")
                
                data = client.recv(4096)
                if data:
                    print(f"[TCP] Received: {data[:100]}")
                    client.send(b'{"status":"ok"}')
                
                client.close()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[TCP] Server error: {e}")
                break
    
    def tcp_client(target_ip, port=6667):
        """Connect to TCP server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        try:
            print(f"[TCP] Connecting to {target_ip}:{port}...")
            sock.connect((target_ip, port))
            
            message = {'type': 'test', 'message': 'Hello from client'}
            sock.send(json.dumps(message).encode())
            
            response = sock.recv(4096)
            print(f"[TCP] Response: {response[:100]}")
            
            sock.close()
            return True
        except Exception as e:
            print(f"[TCP] Client error: {e}")
            return False
    
    print("="*60)
    print("NETWORK TEST TOOL")
    print("="*60)
    print("1. Run full test (UDP listen + TCP server)")
    print("2. Run UDP broadcast only")
    print("3. Run TCP client only")
    print("4. Test connectivity to specific IP")
    
    choice = input("\nChoose (1-4): ").strip()
    
    if choice == '1':
        # Run UDP listener and TCP server
        threading.Thread(target=udp_listener, daemon=True).start()
        threading.Thread(target=tcp_server, daemon=True).start()
        
        print("\nRunning UDP listener and TCP server...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
    
    elif choice == '2':
        # Run UDP broadcast only
        udp_broadcast()
    
    elif choice == '3':
        # Run TCP client only
        target_ip = input("Enter target IP: ").strip()
        if target_ip:
            tcp_client(target_ip)
    
    elif choice == '4':
        # Test connectivity
        target_ip = input("Enter target IP: ").strip()
        if target_ip:
            print("\nTesting connectivity...")
            
            # Test UDP
            print(f"\n1. Testing UDP to {target_ip}:6666")
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.settimeout(2)
            try:
                udp_sock.sendto(b'ping', (target_ip, 6666))
                data, addr = udp_sock.recvfrom(1024)
                print(f"   ✓ UDP response received")
            except:
                print(f"   ✗ No UDP response")
            udp_sock.close()
            
            # Test TCP
            print(f"\n2. Testing TCP to {target_ip}:6667")
            if tcp_client(target_ip):
                print(f"   ✓ TCP connection successful")
            else:
                print(f"   ✗ TCP connection failed")

if __name__ == "__main__":
    test_network()
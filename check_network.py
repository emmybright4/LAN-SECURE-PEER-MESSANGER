#!/usr/bin/env python3
"""
Test network discovery and connectivity
"""

import socket
import threading
import time
import json

def test_discovery():
    """Test UDP discovery between devices"""
    
    def broadcaster(name, port=6667):
        """Broadcast presence"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        print(f"[{name}] Broadcasting on port {port}")
        
        while True:
            message = {
                'type': 'discovery',
                'name': name,
                'time': time.time()
            }
            
            try:
                sock.sendto(
                    json.dumps(message).encode(),
                    ('255.255.255.255', port)
                )
                print(f"[{name}] Broadcast sent")
            except Exception as e:
                print(f"[{name}] Broadcast error: {e}")
            
            time.sleep(3)
    
    def listener(name, port=6667):
        """Listen for broadcasts"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.settimeout(1)
        
        print(f"[{name}] Listening on port {port}")
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                
                try:
                    packet = json.loads(data.decode())
                    if packet.get('type') == 'discovery':
                        print(f"[{name}] Found {packet.get('name')} at {addr[0]}")
                except:
                    # Not JSON, might be simple ping
                    if data == b'PING':
                        sock.sendto(b'PONG', addr)
                        
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[{name}] Listen error: {e}")
                break
    
    print("="*60)
    print("NETWORK DISCOVERY TEST")
    print("="*60)
    
    print("1. Run on Device A (Broadcast + Listen)")
    print("2. Run on Device B (Listen only)")
    print("3. Run on Device C (Broadcast only)")
    print("4. Exit")
    
    choice = input("\nChoose (1-4): ").strip()
    
    if choice == '1':
        name = input("Enter device name: ").strip() or "DeviceA"
        # Start both broadcast and listen
        b_thread = threading.Thread(target=broadcaster, args=(name,), daemon=True)
        l_thread = threading.Thread(target=listener, args=(name,), daemon=True)
        
        b_thread.start()
        l_thread.start()
        
        print(f"\nStarted as {name}. Press Ctrl+C to stop.")
        
    elif choice == '2':
        name = input("Enter device name: ").strip() or "DeviceB"
        # Start listener only
        l_thread = threading.Thread(target=listener, args=(name,), daemon=True)
        l_thread.start()
        
        print(f"\nListening as {name}. Press Ctrl+C to stop.")
        
    elif choice == '3':
        name = input("Enter device name: ").strip() or "DeviceC"
        # Start broadcaster only
        b_thread = threading.Thread(target=broadcaster, args=(name,), daemon=True)
        b_thread.start()
        
        print(f"\nBroadcasting as {name}. Press Ctrl+C to stop.")
    
    else:
        print("Exiting...")
        return
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping test...")

def test_tcp_connection():
    """Test TCP connectivity between devices"""
    
    def server(port=6667):
        """Simple TCP echo server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.listen(1)
        
        print(f"[SERVER] Listening on port {port}")
        
        while True:
            client, addr = sock.accept()
            print(f"[SERVER] Connection from {addr}")
            
            data = client.recv(1024).decode()
            print(f"[SERVER] Received: {data}")
            
            # Echo back
            client.send(f"ECHO: {data}".encode())
            client.close()
    
    def client(server_ip, port=6667):
        """Simple TCP client"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            print(f"[CLIENT] Connecting to {server_ip}:{port}")
            sock.connect((server_ip, port))
            
            message = input("Enter message to send: ")
            sock.send(message.encode())
            
            response = sock.recv(1024).decode()
            print(f"[CLIENT] Server says: {response}")
            
            sock.close()
            return True
        except Exception as e:
            print(f"[CLIENT] Error: {e}")
            return False
    
    print("\n" + "="*60)
    print("TCP CONNECTION TEST")
    print("="*60)
    
    print("1. Run server")
    print("2. Run client")
    
    choice = input("\nChoose (1-2): ").strip()
    
    if choice == '1':
        print("\nStarting server...")
        server()
    elif choice == '2':
        server_ip = input("\nEnter server IP: ").strip()
        if server_ip:
            client(server_ip)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    print("Network Testing Tool")
    print("="*60)
    
    print("1. Test UDP Discovery")
    print("2. Test TCP Connection")
    print("3. Exit")
    
    choice = input("\nChoose (1-3): ").strip()
    
    if choice == '1':
        test_discovery()
    elif choice == '2':
        test_tcp_connection()
    else:
        print("Goodbye!")
"""
Network Manager - TCP/UDP handling
Discovery, presence, messaging, key exchange and typing notifications.
"""
import socket
import threading
import json
import time
import select
import uuid

class NetworkManager:
    def __init__(self, database):
        self.database = database

        self.port = 6667
        self.broadcast_port = 6666
        self.buffer_size = 16384

        self.udp_socket = None
        self.tcp_socket = None
        self.running = False
        self.local_ip = self.get_local_ip()

        self.username = None
        self.online_users = {}
        self.encrypted_peers = set()

        self.typing_peers = {}

        self.message_callback = None
        self.key_exchange_callback = None

        self.udp_thread = None
        self.tcp_thread = None
        self.discovery_thread = None
        self.cleanup_thread = None

        self.users_lock = threading.Lock()
        self.socket_lock = threading.Lock()

        print(f"[NETWORK] Initialized on {self.local_ip}")

    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            try:
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
            except:
                ip = '127.0.0.1'
            finally:
                s.close()
            return ip
        except:
            return '127.0.0.1'

    def send_presence(self, status='online', additional_data=None):
        """Send presence packet for peer discovery"""
        if not self.username or not self.udp_socket:
            return

        packet = {
            'type': 'presence',
            'username': self.username,
            'ip': self.local_ip,
            'port': self.port,
            'timestamp': time.time(),
            'status': status
        }
        if additional_data:
            packet.update(additional_data)

        self._broadcast(packet)

    def send_discovery(self):
        """Send discovery packet"""
        if not self.username or not self.udp_socket:
            return

        packet = {
            'type': 'discovery',
            'username': self.username,
            'ip': self.local_ip,
            'port': self.port,
            'timestamp': time.time()
        }

        self._broadcast(packet)

    def _broadcast(self, packet):
        """Broadcast a UDP packet on common broadcast addresses"""
        try:
            broadcast_data = json.dumps(packet).encode('utf-8')
            targets = ['255.255.255.255', '192.168.1.255', '192.168.0.255', '10.0.0.255']
            for target in targets:
                try:
                    self.udp_socket.sendto(broadcast_data, (target, self.broadcast_port))
                except:
                    pass
        except Exception as e:
            if self.running and e:
                pass

    def start(self):
        """Start network services"""
        if self.running:
            print("[NETWORK] Already running")
            return True

        try:
            print("[NETWORK] Starting network services...")

            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_socket.bind(('0.0.0.0', self.broadcast_port))
            self.udp_socket.settimeout(1)

            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind(('0.0.0.0', self.port))
            self.tcp_socket.listen(10)
            self.tcp_socket.settimeout(1)

            self.running = True
            print(f"[NETWORK] Sockets created - UDP:{self.broadcast_port} TCP:{self.port}")

            self.udp_thread = threading.Thread(target=self.udp_listener, daemon=True)
            self.tcp_thread = threading.Thread(target=self.tcp_listener, daemon=True)
            self.discovery_thread = threading.Thread(target=self.discovery_broadcaster, daemon=True)
            self.cleanup_thread = threading.Thread(target=self.cleanup_old_users, daemon=True)

            self.udp_thread.start()
            self.tcp_thread.start()
            self.discovery_thread.start()
            self.cleanup_thread.start()

            print("[NETWORK] All threads started successfully")
            return True

        except Exception as e:
            print(f"[NETWORK] Error starting: {e}")
            import traceback
            traceback.print_exc()
            self.stop()
            return False

    def stop(self):
        """Stop network services"""
        print("[NETWORK] Stopping network services...")
        self.running = False

        with self.socket_lock:
            if self.udp_socket:
                try: self.udp_socket.close()
                except: pass
                self.udp_socket = None

            if self.tcp_socket:
                try: self.tcp_socket.close()
                except: pass
                self.tcp_socket = None

        print("[NETWORK] Services stopped")

    def set_username(self, username):
        """Set current username and add self to online users"""
        with self.users_lock:
            self.username = username
            if username:
                self.online_users[username] = {
                    'username': username,
                    'ip': self.local_ip,
                    'port': self.port,
                    'last_seen': time.time(),
                    'encrypted': False
                }
                print(f"[NETWORK] Username set to: {username}")

    def register_message_callback(self, callback):
        self.message_callback = callback

    def register_key_exchange_callback(self, callback):
        self.key_exchange_callback = callback

    def udp_listener(self):
        """Listen for UDP discovery / presence / typing packets"""
        print("[NETWORK] UDP listener started")

        while self.running:
            try:
                if not self.udp_socket:
                    break

                data, addr = self.udp_socket.recvfrom(4096)

                try:
                    packet = json.loads(data.decode('utf-8'))
                    packet_type = packet.get('type', '')
                    sender = packet.get('username', '')

                    if packet_type == 'discovery':
                        if sender and sender != self.username and self.username:
                            with self.users_lock:
                                self.online_users[sender] = {
                                    'username': sender,
                                    'ip': packet.get('ip', addr[0]),
                                    'port': packet.get('port', self.port),
                                    'last_seen': time.time(),
                                    'encrypted': packet.get('encrypted', False),
                                    'status': packet.get('status', 'online')
                                }
                            print(f"[NETWORK] Discovered user: {sender} at {addr[0]}")

                            response = {
                                'type': 'presence',
                                'username': self.username,
                                'ip': self.local_ip,
                                'port': self.port,
                                'encrypted': False,
                                'timestamp': time.time()
                            }
                            try:
                                self.udp_socket.sendto(
                                    json.dumps(response).encode('utf-8'),
                                    addr
                                )
                                print(f"[NETWORK] Sent presence response to {sender}")
                            except Exception as e:
                                print(f"[NETWORK] Failed to respond: {e}")

                    elif packet_type == 'presence':
                        status = packet.get('status', 'online')
                        if sender and sender != self.username:
                            with self.users_lock:
                                self.online_users[sender] = {
                                    'username': sender,
                                    'ip': packet.get('ip', addr[0]),
                                    'port': packet.get('port', self.port),
                                    'last_seen': time.time(),
                                    'encrypted': packet.get('encrypted', False),
                                    'status': status
                                }
                            print(f"[NETWORK] Presence update: {sender} at {addr[0]}")

                    elif packet_type == 'typing':
                        recipient = packet.get('to', '')
                        if sender and sender != self.username and recipient == self.username:
                            with self.users_lock:
                                self.typing_peers[sender] = time.time()
                            print(f"[NETWORK] {sender} is typing...")

                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"[NETWORK] UDP packet handling error: {e}")

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[NETWORK] UDP listener error: {e}")
                time.sleep(0.5)

    def tcp_listener(self):
        """Listen for TCP connections (messages & key exchanges)"""
        print(f"[NETWORK] TCP listener started on port {self.port}")

        while self.running:
            try:
                if not self.tcp_socket:
                    break

                readable, _, _ = select.select([self.tcp_socket], [], [], 1)

                if readable:
                    client_socket, addr = self.tcp_socket.accept()
                    threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    ).start()

            except Exception as e:
                if self.running:
                    print(f"[NETWORK] TCP listener error: {e}")
                time.sleep(0.5)

    def handle_client(self, client_socket, addr):
        """Handle incoming TCP connection"""
        try:
            client_socket.settimeout(10)
            data = client_socket.recv(self.buffer_size)

            if not data:
                return

            try:
                packet = json.loads(data.decode('utf-8'))
            except:
                print(f"[NETWORK] Invalid JSON from {addr[0]}")
                return

            packet_type = packet.get('type', '')

            if packet_type == 'message':
                sender = packet.get('sender', '')
                recipient = packet.get('recipient', '')
                is_encrypted = packet.get('is_encrypted', False)
                message_id = packet.get('message_id', '')

                print(f"[NETWORK] Received message from {sender} to {recipient}")

                if sender:
                    with self.users_lock:
                        self.online_users[sender] = {
                            'username': sender,
                            'ip': addr[0],
                            'port': packet.get('port', self.port),
                            'last_seen': time.time(),
                            'encrypted': is_encrypted
                        }

                if self.message_callback:
                    self.message_callback(packet)

                ack = {'type': 'ack', 'message_id': message_id, 'status': 'received'}
                client_socket.send(json.dumps(ack).encode('utf-8'))

            elif packet_type == 'key_exchange':
                sender = packet.get('sender', '')
                key_data = packet.get('key_data', {})

                print(f"[NETWORK] Key exchange from {sender}")

                if sender and self.key_exchange_callback:
                    self.key_exchange_callback(sender, key_data)
                    with self.users_lock:
                        self.encrypted_peers.add(sender)
                        if sender in self.online_users:
                            self.online_users[sender]['encrypted'] = True

                ack = {'type': 'ack', 'status': 'key_received'}
                client_socket.send(json.dumps(ack).encode('utf-8'))

            elif packet_type == 'ping':
                pong = {'type': 'pong', 'time': time.time()}
                client_socket.send(json.dumps(pong).encode('utf-8'))

        except socket.timeout:
            print(f"[NETWORK] Client {addr[0]} timeout")
        except Exception as e:
            print(f"[NETWORK] Client handler error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass

    def discovery_broadcaster(self):
        """Broadcast our presence periodically"""
        print("[NETWORK] Discovery broadcaster started")

        while self.running:
            try:
                self.send_presence()

                for _ in range(6):
                    if not self.running:
                        return
                    time.sleep(0.5)

            except Exception as e:
                if self.running:
                    print(f"[NETWORK] Broadcaster error: {e}")
                time.sleep(1)

    def cleanup_old_users(self):
        """Remove users not seen recently"""
        while self.running:
            time.sleep(5)
            if not self.running:
                break

            current_time = time.time()
            to_remove = []

            with self.users_lock:
                for username, info in list(self.online_users.items()):
                    if username != self.username:
                        if current_time - info.get('last_seen', 0) > 30:
                            to_remove.append(username)

                for username in to_remove:
                    del self.online_users[username]
                    self.encrypted_peers.discard(username)
                    print(f"[NETWORK] User {username} timed out")

    def get_typing_peers(self, max_age=4.0):
        """Usernames that typed within the last few seconds"""
        current_time = time.time()
        typing = []
        with self.users_lock:
            for user, ts in list(self.typing_peers.items()):
                if current_time - ts <= max_age:
                    typing.append(user)
                else:
                    del self.typing_peers[user]
        return typing

    def send_typing(self, recipient):
        """Notify a peer that we are typing (direct UDP to their discovery port)"""
        if not self.username or not self.udp_socket:
            return False

        with self.users_lock:
            recipient_info = self.online_users.get(recipient)

        if not recipient_info:
            return False

        packet = {
            'type': 'typing',
            'username': self.username,
            'to': recipient,
            'timestamp': time.time()
        }

        try:
            self.udp_socket.sendto(json.dumps(packet).encode('utf-8'),
                                   (recipient_info['ip'], self.broadcast_port))
            return True
        except Exception as e:
            print(f"[NETWORK] Typing notify failed for {recipient}: {e}")
            return False

    def send_message(self, sender, recipient, message, is_encrypted=False):
        """Send a message. Returns the packet message_id on success, else False."""
        with self.users_lock:
            recipient_info = self.online_users.get(recipient)

        if not recipient_info:
            print(f"[NETWORK] Recipient {recipient} not found in online_users")
            return False

        message_id = f"{int(time.time())}_{sender[:3]}_{recipient[:3]}_{uuid.uuid4().hex[:8]}"

        packet = {
            'type': 'message',
            'sender': sender,
            'recipient': recipient,
            'message': message,
            'is_encrypted': is_encrypted,
            'timestamp': time.time(),
            'message_id': message_id,
            'port': self.port
        }

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((recipient_info['ip'], recipient_info['port']))
            sock.send(json.dumps(packet).encode('utf-8'))

            response = sock.recv(self.buffer_size)
            if response:
                ack = json.loads(response.decode('utf-8'))
                if ack.get('status') == 'received':
                    with self.users_lock:
                        if recipient in self.online_users:
                            self.online_users[recipient]['last_seen'] = time.time()
                            if is_encrypted:
                                self.online_users[recipient]['encrypted'] = True
                    print(f"[NETWORK] Message {message_id} sent to {recipient}")
                    return message_id

            return False

        except socket.timeout:
            print(f"[NETWORK] Timeout to {recipient} at {recipient_info['ip']}")
        except ConnectionRefusedError:
            print(f"[NETWORK] Connection refused by {recipient}")
        except Exception as e:
            print(f"[NETWORK] Error sending message to {recipient}: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass

        return False

    def send_key_exchange(self, sender, key_data, recipient):
        with self.users_lock:
            recipient_info = self.online_users.get(recipient)

        if not recipient_info:
            print(f"[NETWORK] Recipient {recipient} not found for key exchange")
            return False

        packet = {
            'type': 'key_exchange',
            'sender': sender,
            'key_data': key_data,
            'timestamp': time.time(),
            'port': self.port
        }

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((recipient_info['ip'], recipient_info['port']))
            sock.send(json.dumps(packet).encode('utf-8'))

            response = sock.recv(self.buffer_size)
            if response:
                ack = json.loads(response.decode('utf-8'))
                if ack.get('status') == 'key_received':
                    with self.users_lock:
                        self.encrypted_peers.add(recipient)
                        if recipient in self.online_users:
                            self.online_users[recipient]['encrypted'] = True
                    print(f"[NETWORK] Key exchange successful with {recipient}")
                    return True

            return False

        except Exception as e:
            print(f"[NETWORK] Error sending key to {recipient}: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass

        return False

    def auto_exchange_keys(self, username, key_data):
        exchanged = 0
        with self.users_lock:
            peers = list(self.online_users.keys())

        for peer_name in peers:
            if peer_name != username and peer_name not in self.encrypted_peers:
                if self.send_key_exchange(username, key_data, peer_name):
                    exchanged += 1
                    time.sleep(0.1)

        return exchanged

    def get_online_users(self):
        users = []
        current_time = time.time()

        with self.users_lock:
            for username, info in self.online_users.items():
                if username != self.username:
                    if current_time - info.get('last_seen', 0) > 30:
                        continue
                    users.append({
                        'username': username,
                        'ip': info.get('ip', 'unknown'),
                        'last_seen': info.get('last_seen', 0),
                        'encrypted': info.get('encrypted', False),
                        'status': info.get('status', 'online')
                    })

        return users

    def ping_user(self, username):
        with self.users_lock:
            info = self.online_users.get(username)

        if not info:
            return False

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((info['ip'], info['port']))

            packet = {'type': 'ping', 'time': time.time()}
            sock.send(json.dumps(packet).encode('utf-8'))

            response = sock.recv(1024)
            return bool(response)

        except:
            return False
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass

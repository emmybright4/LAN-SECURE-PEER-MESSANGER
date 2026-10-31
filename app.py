#!/usr/bin/env python3
"""
SecureLocal Chat - Running fixed (app import + app.py syntax fixed)
"""
import sys
import os
import re
import json
import time
import socket
import threading
import webbrowser
import uuid
from pathlib import Path

# Fix Windows console encoding for emoji/unicode
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass


import os
import json
import time
import socket
import threading
import webbrowser
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import timedelta, datetime

from security import SecurityManager
from database import DatabaseManager
from network import NetworkManager
from mesh_tower import init_mesh, get_mesh

app = Flask(__name__)

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

secret_key_file = Path('data') / 'secret.key'
if secret_key_file.exists():
    with open(secret_key_file, 'rb') as f:
        app.secret_key = f.read()
else:
    Path('data').mkdir(parents=True, exist_ok=True)
    app.secret_key = os.urandom(32)
    with open(secret_key_file, 'wb') as f:
        f.write(app.secret_key)

security = None
database = None
network = None
mesh = None
network_lock = threading.RLock()
browser_opened = False

def initialize_app():
    global security, database, network
    try:
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        data_path = Path(application_path) / 'data'
        data_path.mkdir(parents=True, exist_ok=True)

        print(f"[APP] Data path: {data_path}")
        print(f"[APP] Application path: {application_path}")

        database = DatabaseManager(str(data_path / 'chat.db'))
        security = SecurityManager(str(data_path))
        network = NetworkManager(database)

        network.register_message_callback(handle_incoming_message)
        network.register_key_exchange_callback(handle_key_exchange)

        if not network.start():
            print("[APP] WARNING: Network failed to start, will retry on login")

        # Init mesh/tower layer (non-invasive)
        try:
            global mesh
            mesh = init_mesh(network, database)
            print("[APP] Mesh/Tower layer initialized")
        except Exception as me:
            print(f"[APP] Mesh init skipped: {me}")

        print("[APP] All components initialized successfully")
        return True
    except Exception as e:
        print(f"[APP] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def open_browser():
    global browser_opened
    time.sleep(2)
    if not browser_opened:
        try:
            webbrowser.open('http://localhost:5000')
            print(f"[APP] âœ… Browser opened automatically")
            browser_opened = True
        except Exception as e:
            print(f"[APP] âš ï¸ Could not open browser: {e}")

@app.before_request
def check_session():
    if request.endpoint in ['health', 'static', 'debug_network_status', 'debug_check_connection']:
        return
    if 'username' in session:
        session.permanent = True
        if 'last_activity' in session:
            idle_time = time.time() - session['last_activity']
            if idle_time > 3600:
                session.clear()
                return redirect(url_for('login'))
        session['last_activity'] = time.time()
        with network_lock:
            global network
            if network and network.username != session['username']:
                network.set_username(session['username'])

def handle_incoming_message(packet):
    try:
        sender = packet.get('sender', 'unknown')
        recipient = packet.get('recipient', '')
        message = packet.get('message', '')
        is_encrypted = packet.get('is_encrypted', False)
        print(f"[APP] ðŸ“¥ Received message from {sender} to {recipient}")
        if database and message:
            db_message_id = database.save_message(
                sender, recipient, message, is_encrypted,
                client_msg_id=packet.get('message_id')
            )
            print(f"[APP] âœ… Saved message from {sender} to {recipient} (ID: {db_message_id})")
    except Exception as e:
        print(f"[APP] âŒ Error handling message: {e}")
        import traceback
        traceback.print_exc()

def handle_key_exchange(sender, key_data):
    try:
        print(f"[APP] ðŸ”‘ Received key from {sender}")
        print(f"[APP] Key data: {key_data.get('key_id', 'unknown')}")
    except Exception as e:
        print(f"[APP] Error handling key exchange: {e}")

if not initialize_app():
    print("âš ï¸ WARNING: Failed to initialize app fully. Running in limited mode.")

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('chat'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('chat'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Please enter username and password', 'error')
            return render_template('login.html')
        try:
            if security and security.verify_user(username, password):
                session['username'] = username
                session.permanent = True
                session['last_activity'] = time.time()
                session['login_time'] = time.time()

                with network_lock:
                    global network
                    if network:
                        try:
                            if network.running:
                                print("[LOGIN] Stopping existing network...")
                                network.stop()
                                time.sleep(1)
                        except:
                            pass
                    print(f"[LOGIN] Creating fresh network instance for {username}")
                    network = NetworkManager(database)
                    network.register_message_callback(handle_incoming_message)
                    network.register_key_exchange_callback(handle_key_exchange)
                    if network.start():
                        print("[LOGIN] âœ… Network started successfully")
                    else:
                        print("[LOGIN] âŒ Network failed to start")
                    network.set_username(username)
                    print(f"[LOGIN] Network username set to {username}")
                    try:
                        global mesh
                        mesh = init_mesh(network, database)
                    except Exception as me:
                        print(f"[LOGIN] Mesh reinit skipped: {me}")
                    time.sleep(1)

                if database and not database.user_exists(username):
                    database.add_user(username, 2)

                flash('Login successful!', 'success')
                print(f"[LOGIN] âœ… User {username} logged in successfully")
                return redirect(url_for('chat'))
            else:
                flash('Invalid username or password', 'error')
                return render_template('login.html')
        except Exception as e:
            print(f"[LOGIN] âŒ Error: {e}")
            import traceback
            traceback.print_exc()
            flash('Login error. Please try again.', 'error')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('chat'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        errors = []
        if not username:
            errors.append('Username required')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters')
        elif security and security.user_exists(username):
            errors.append('Username already exists')
        if not password:
            errors.append('Password required')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters')
        elif password != confirm:
            errors.append('Passwords do not match')
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('login.html', face='register')

        if security and security.create_user(username, password):
            if database:
                database.add_user(username, 2)
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed', 'error')
            return render_template('login.html', face='register')
    return redirect(url_for('login') + '#register')

@app.route('/chat')
def chat():
    if 'username' not in session:
        print(f"[CHAT] No username in session, redirecting to login")
        return redirect(url_for('login'))
    print(f"[CHAT] User {session['username']} accessing chat")
    return render_template('chat.html', username=session['username'])

@app.route('/api/users')
def get_users():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    if not network:
        print(f"[API] Network is None, returning empty list")
        return jsonify({'users': []})
    try:
        with network_lock:
            if not network.running:
                network.start()
                time.sleep(0.5)
                if network.username != session['username']:
                    network.set_username(session['username'])
            users = network.get_online_users()
            print(f"[API] Returning {len(users)} online users for {session['username']}")
        return jsonify({'users': users})
    except Exception as e:
        print(f"[API] âŒ Error getting users: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'users': []})

@app.route('/api/conversations')
def get_conversations():
    """Last message per peer, decrypted, for the conversation list."""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']

    previews = {}
    if database:
        previews = database.get_conversation_previews(username)

    for peer, item in previews.items():
        text = item.get('message', '')
        if item.get('is_encrypted') and security and text:
            try:
                decrypted = security.decrypt_from_peer(username, peer, text)
                if decrypted and decrypted != text:
                    item['message'] = decrypted
            except Exception as e:
                print(f"[API] Preview decryption error for {peer}: {e}")
        # Messages we cannot decrypt stay hidden rather than showing a cipher blobs.
        if _looks_like_ciphertext(item.get('message', '')):
            item['message'] = ''
            item['undecryptable'] = True

    return jsonify({'conversations': previews})


def _looks_like_ciphertext(text):
    text = (text or '').strip()
    return len(text) >= 48 and not any(ch.isspace() for ch in text) and bool(re.fullmatch(r'[A-Za-z0-9+/=_\-]+', text))


@app.route('/api/messages', methods=['GET', 'POST'])
def handle_messages():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']

    if request.method == 'POST':
        try:
            try:
                data = request.get_json()
            except Exception as e:
                print(f"[API] JSON parse error: {e}")
                return jsonify({'error': 'Invalid JSON format'}), 400

            if not data:
                print(f"[API] No JSON data received")
                return jsonify({'error': 'No data received'}), 400

            recipient = data.get('recipient', '').strip()
            message = data.get('message', '').strip()

            if not recipient:
                print(f"[API] Missing recipient")
                return jsonify({'error': 'Recipient required'}), 400
            if not message:
                print(f"[API] Missing message")
                return jsonify({'error': 'Message required'}), 400

            with network_lock:
                global network
                if not network:
                    network = NetworkManager(database)
                    network.register_message_callback(handle_incoming_message)
                    network.register_key_exchange_callback(handle_key_exchange)
                    if not network.start():
                        return jsonify({'error': 'Network failed to initialize'}), 500
                    network.set_username(username)

                if not network.running:
                    if not network.start():
                        return jsonify({'error': 'Network failed to start'}), 500
                    network.set_username(username)
                    time.sleep(0.5)

            is_encrypted = False
            try:
                is_encrypted = recipient in network.encrypted_peers
            except Exception as e:
                print(f"[API] Error checking encryption status: {e}")

            final_message = message
            if is_encrypted and security:
                try:
                    encrypted = security.encrypt_for_peer(username, recipient, message)
                    if encrypted != message:
                        final_message = encrypted
                    else:
                        print(f"[API] âš ï¸ Encryption returned same message")
                except Exception as e:
                    print(f"[API] âŒ Encryption error: {e}")
                    import traceback
                    traceback.print_exc()
                    is_encrypted = False
                    final_message = message

            delivered_id = False
            try:
                delivered_id = network.send_message(
                    username,
                    recipient,
                    final_message,
                    is_encrypted=is_encrypted
                )
                if not delivered_id:
                    if recipient not in network.online_users:
                        error_msg = f"User '{recipient}' is offline"
                    else:
                        error_msg = f"Failed to connect to {recipient}"
            except Exception as e:
                print(f"[API] âŒ Exception in network.send_message: {e}")
                import traceback
                traceback.print_exc()
                error_msg = str(e)
                success = False

            success = bool(delivered_id)

            if success:
                message_id = None
                if database:
                    try:
                        message_id = database.save_message(
                            username,
                            recipient,
                            final_message,
                            is_encrypted=is_encrypted,
                            client_msg_id=delivered_id if isinstance(delivered_id, str) else None
                        )
                    except Exception as e:
                        print(f"[API] âš ï¸ Database save error: {e}")
                return jsonify({
                    'success': True,
                    'encrypted': is_encrypted,
                    'message_id': message_id,
                    'message': 'Message sent successfully'
                })
            else:
                print(f"[API] âŒ Failed to send message to {recipient}")
                return jsonify({
                    'error': error_msg or f'Failed to send message to {recipient}'
                }), 500
        except Exception as e:
            print(f"[API] âŒâŒâŒ UNHANDLED EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Server error: {str(e)}'}), 500
    else:
        try:
            recipient = request.args.get('with', '').strip()
            if not recipient:
                return jsonify({'error': 'Recipient required'}), 400

            messages = []
            if database:
                messages = database.get_messages(username, recipient, limit=100)

            decrypted_messages = []
            for msg in messages:
                message_text = msg.get('message', '')
                if msg.get('is_encrypted') and security:
                    try:
                        sender = msg.get('sender', '')
                        other_user = sender if sender != username else recipient
                        decrypted = security.decrypt_from_peer(
                            username,
                            other_user,
                            message_text
                        )
                        if decrypted != message_text:
                            msg['message'] = decrypted
                            msg['was_decrypted'] = True
                        else:
                            msg['was_decrypted'] = False
                    except Exception as e:
                        print(f"[API] Decryption error: {e}")
                        msg['was_decrypted'] = False
                else:
                    msg['was_decrypted'] = False
                decrypted_messages.append(msg)

            return jsonify({'messages': decrypted_messages})
        except Exception as e:
            print(f"[API] âŒ Error getting messages: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'messages': []})

@app.route('/api/encryption/status')
def encryption_status():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    try:
        users = []
        if network:
            with network_lock:
                users = network.get_online_users()
        status = {}
        for user in users:
            user_name = user.get('username', '')
            status[user_name] = {
                'online': True,
                'encrypted': user.get('encrypted', False),
                'last_seen': user.get('last_seen', 0)
            }
        return jsonify(status)
    except Exception as e:
        print(f"[API] Error getting encryption status: {e}")
        return jsonify({})

@app.route('/api/encryption/exchange', methods=['POST'])
def exchange_keys():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        recipient = data.get('recipient', '').strip()
        if not recipient:
            return jsonify({'error': 'Recipient required'}), 400
        print(f"[API] ðŸ”‘ Exchanging keys with {recipient}")
        my_key_data = None
        if security:
            my_key_data = security.get_my_public_key(username)
        if not my_key_data:
            return jsonify({'error': 'No encryption key found'}), 400
        success = False
        if network:
            with network_lock:
                if not network.running:
                    network.start()
                    network.set_username(username)
                    time.sleep(0.5)
                success = network.send_key_exchange(username, my_key_data, recipient)
        if success:
            print(f"[API] âœ… Key exchange successful with {recipient}")
            return jsonify({
                'success': True,
                'message': f'Key exchange initiated with {recipient}'
            })
        else:
            print(f"[API] âŒ Key exchange failed with {recipient}")
            return jsonify({'error': 'Failed to exchange keys'}), 500
    except Exception as e:
        print(f"[API] âŒ Error exchanging keys: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/encryption/exchange_all', methods=['POST'])
def exchange_keys_all():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    try:
        my_key_data = None
        if security:
            my_key_data = security.get_my_public_key(username)
        if not my_key_data:
            return jsonify({'error': 'No encryption key found'}), 400
        exchanged = 0
        if network:
            with network_lock:
                if network.running:
                    exchanged = network.auto_exchange_keys(username, my_key_data)
        print(f"[API] Exchanged keys with {exchanged} user(s)")
        return jsonify({
            'success': True,
            'exchanged': exchanged,
            'message': f'Exchanged keys with {exchanged} user(s)'
        })
    except Exception as e:
        print(f"[API] âŒ Error exchanging keys: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/network/info')
def network_info():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    info = {
        'local_ip': network.local_ip if network else 'Unknown',
        'port': network.port if network else 6667,
        'online_count': len(network.get_online_users()) if network else 0,
    }
    return jsonify(info)

@app.route('/api/debug/network_status')
def debug_network_status():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    username = session['username']
    status = {
        'username': username,
        'network': {
            'running': network.running if network else False,
            'username_set': network.username if network else None,
            'local_ip': network.local_ip if network else None,
            'port': network.port if network else None
        },
        'online_users': {},
        'encrypted_peers': [],
        'can_connect_to_self': False,
        'session_active': True
    }
    if network:
        with network_lock:
            for user, info in network.online_users.items():
                status['online_users'][user] = {
                    'ip': info.get('ip'),
                    'port': info.get('port'),
                    'last_seen': info.get('last_seen'),
                    'encrypted': info.get('encrypted', False),
                    'age': time.time() - info.get('last_seen', 0)
                }
            status['encrypted_peers'] = list(network.encrypted_peers)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect(('127.0.0.1', network.port))
                sock.close()
                status['can_connect_to_self'] = True
            except:
                pass
    return jsonify(status)

@app.route('/api/debug/check_connection')
def debug_check_connection():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    username = session['username']
    target_ip = request.args.get('ip', '')
    if not target_ip:
        return jsonify({'error': 'IP address required'}), 400
    results = {
        'target_ip': target_ip,
        'port_6666_udp': False,
        'port_6667_tcp': False,
        'error': None
    }
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.sendto(b'ping', (target_ip, 6666))
        data, addr = sock.recvfrom(1024)
        results['port_6666_udp'] = True
        sock.close()
    except:
        pass
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect((target_ip, 6667))
        sock.close()
        results['port_6667_tcp'] = True
    except Exception as e:
        results['error'] = str(e)
    return jsonify(results)

@app.route('/api/debug/network')
def debug_network():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    debug_info = {
        'network_running': network.running if network else False,
        'username': network.username if network else None,
        'online_users': [],
        'encrypted_peers': list(network.encrypted_peers) if network else []
    }
    if network:
        with network_lock:
            for user, info in network.online_users.items():
                debug_info['online_users'].append({
                    'username': user,
                    'ip': info.get('ip', 'unknown'),
                    'last_seen': info.get('last_seen', 0),
                    'encrypted': info.get('encrypted', False)
                })
    return jsonify(debug_info)

@app.route('/logout')
def logout():
    print(f"[LOGOUT] User {session.get('username', 'Unknown')} logging out")
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/health')
def health():
    status = {
        'status': 'ok',
        'components': {
            'database': database is not None,
            'security': security is not None,
            'network': network is not None,
        },
        'timestamp': time.time()
    }
    if network:
        status['components']['network_running'] = network.running
    if 'username' in session:
        status['session'] = {
            'has_username': True,
            'username': session['username'],
            'last_activity': session.get('last_activity', 0),
            'idle_time': time.time() - session.get('last_activity', 0) if 'last_activity' in session else 0
        }
    else:
        status['session'] = {'has_username': False}
    return jsonify(status)

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    print(f"[APP] 500 error: {e}")
    import traceback
    traceback.print_exc()
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/groups', methods=['GET', 'POST'])
def handle_groups():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    if request.method == 'POST':
        try:
            data = request.get_json()
            group_name = data.get('name', '').strip()
            members = data.get('members', [])
            description = data.get('description', '').strip()
            if not group_name:
                return jsonify({'error': 'Group name required'}), 400
            group_id = str(uuid.uuid4())
            if database and database.create_group(group_id, group_name, username, description):
                for member in members:
                    if member != username:
                        database.add_group_member(group_id, member)
                return jsonify({'success': True, 'group_id': group_id})
            return jsonify({'error': 'Failed to create group'}), 500
        except Exception as e:
            print(f"[API] Error creating group: {e}")
            return jsonify({'error': str(e)}), 500
    else:
        try:
            if database:
                groups = database.get_user_groups(username)
                return jsonify({'groups': groups})
            return jsonify({'groups': []})
        except Exception as e:
            print(f"[API] Error getting groups: {e}")
            return jsonify({'groups': []})

@app.route('/api/groups/<group_id>/members', methods=['GET'])
def get_group_members_route(group_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        if database:
            members = database.get_group_members(group_id)
            return jsonify({'members': members})
        return jsonify({'members': []})
    except Exception as e:
        print(f"[API] Error getting group members: {e}")
        return jsonify({'members': []})

@app.route('/api/groups/<group_id>/messages', methods=['GET', 'POST'])
def handle_group_messages(group_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    if request.method == 'POST':
        try:
            data = request.get_json()
            message = data.get('message', '').strip()
            if not message:
                return jsonify({'error': 'Message required'}), 400
            if database:
                msg_id = database.save_group_message(group_id, username, message)
                return jsonify({'success': True, 'message_id': msg_id})
            return jsonify({'error': 'Failed to send'}), 500
        except Exception as e:
            print(f"[API] Error sending group message: {e}")
            return jsonify({'error': str(e)}), 500
    else:
        try:
            if database:
                messages = database.get_group_messages(group_id)
                return jsonify({'messages': messages})
            return jsonify({'messages': []})
        except Exception as e:
            print(f"[API] Error getting group messages: {e}")
            return jsonify({'messages': []})

@app.route('/api/status', methods=['GET', 'POST'])
def handle_status():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    if request.method == 'POST':
        try:
            try:
                data = request.get_json()
            except Exception:
                data = None

            # Support photo statuses: multipart with an image field
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    content = request.form.get('content', '').strip() or 'Photo'
                    background_color = request.form.get('background_color', '#4CAF50')
                    # Resize / recompress the image on the server as a safety net
                    media_url = _save_resized_image(file, max_side=1080, quality=80)
                    if not media_url:
                        return jsonify({'error': 'Invalid image file'}), 400
                    media_data = media_url
                    media_type = 'image'
                else:
                    return jsonify({'error': 'Invalid image file'}), 400
            else:
                data = data or {}
                content = (data.get('content') or '').strip()
                background_color = data.get('background_color', '#4CAF50')
                media_type = 'text'
                media_data = None
                # Client-side resized, base64-encoded photo status
                image_data_url = data.get('media_data')
                if image_data_url and image_data_url.startswith('data:image/'):
                    media_type = 'image'
                    media_data = _save_data_url_image(image_data_url)
                    if not media_data:
                        return jsonify({'error': 'Invalid image data'}), 400

            if not content:
                return jsonify({'error': 'Content required'}), 400
            if database:
                status_id = database.create_status(
                    username, content, media_type=media_type,
                    media_data=media_data, background_color=background_color
                )
                if status_id:
                    return jsonify({'success': True, 'status_id': status_id})
            return jsonify({'error': 'Failed to create status'}), 500
        except Exception as e:
            print(f"[API] Error creating status: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    else:
        try:
            if database:
                statuses = database.get_statuses()
                return jsonify({'statuses': statuses})
            return jsonify({'statuses': []})
        except Exception as e:
            print(f"[API] Error getting statuses: {e}")
            return jsonify({'statuses': []})

@app.route('/api/status/<int:status_id>/view', methods=['POST'])
def view_status_route(status_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    username = session['username']
    try:
        if database:
            database.view_status(status_id, username)
            return jsonify({'success': True})
        return jsonify({'success': False})
    except Exception as e:
        print(f"[API] Error viewing status: {e}")
        return jsonify({'success': False})

@app.route('/api/call/initiate', methods=['POST'])
def initiate_call():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    try:
        data = request.get_json()
        receiver = data.get('receiver')
        call_type = data.get('call_type', 'video')
        call_mode = data.get('call_mode', 'individual')
        if not receiver:
            return jsonify({'error': 'Receiver required'}), 400
        call_id = None
        if database:
            call_id = database.save_call(username, receiver, call_type, call_mode, 'ringing')
        return jsonify({'success': True, 'call_id': call_id})
    except Exception as e:
        print(f"[API] Error initiating call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/call/<int:call_id>/answer', methods=['POST'])
def answer_call(call_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        if database:
            database.update_call(call_id, 'answered')
        return jsonify({'success': True})
    except Exception as e:
        print(f"[API] Error answering call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/call/<int:call_id>/end', methods=['POST'])
def end_call(call_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        data = request.get_json()
        duration = data.get('duration', 0)
        if database:
            database.update_call(call_id, 'ended', duration)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[API] Error ending call: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calls/history', methods=['GET'])
def call_history():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    username = session['username']
    try:
        if database:
            calls = database.get_call_history(username)
            return jsonify({'calls': calls})
        return jsonify({'calls': []})
    except Exception as e:
        print(f"[API] Error getting call history: {e}")
        return jsonify({'calls': []})

# ========== TYPING NOTIFICATION ROUTES ==========

@app.route('/api/typing', methods=['POST'])
def send_typing_route():
    """Tell a peer that this user started typing."""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        data = request.get_json() or {}
        recipient = (data.get('recipient') or '').strip()
        if not recipient:
            return jsonify({'error': 'Recipient required'}), 400
        sent = False
        with network_lock:
            if network and network.running:
                sent = network.send_typing(recipient)
                # Same machine / shared instance: the UDP listener only records
                # typing aimed at *this* device, so register it directly here too
                with network.users_lock:
                    info = network.online_users.get(recipient)
                if info and info.get('ip') == network.local_ip:
                    network.typing_peers[network.username] = time.time()
                    sent = True
        return jsonify({'success': bool(sent)})
    except Exception as e:
        print(f"[API] Typing notify error: {e}")
        return jsonify({'success': False})

@app.route('/api/typing/status')
def typing_status_route():
    """Who is currently typing to the logged-in user."""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        typing = []
        with network_lock:
            if network:
                typing = network.get_typing_peers()
        return jsonify({'typing': typing})
    except Exception as e:
        print(f"[API] Typing status error: {e}")
        return jsonify({'typing': []})

# ========== SETTINGS ROUTE ==========

@app.route('/settings')
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('settings.html', username=session['username'])

# ========== AVATAR UPLOAD ROUTE ==========

@app.route('/api/upload-avatar', methods=['POST'])
def upload_avatar():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    try:
        if 'avatar' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        file = request.files['avatar']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        if file:
            # Save avatar to static/avatars folder (resized when Pillow is available)
            media_url = _save_resized_image(file, max_side=512, quality=85, subdir='avatars')
            if not media_url:
                return jsonify({'error': 'Invalid image file'}), 400
            if database:
                database.update_user_avatar(username, media_url)
            return jsonify({'success': True, 'avatar_url': media_url})
    except Exception as e:
        print(f"[API] Error uploading avatar: {e}")
        return jsonify({'error': str(e)}), 500

# ========== IMAGE RESIZE HELPERS ==========

def _reencode_image_bytes(data, max_side=1080, quality=80):
    """Scale down and re-encode image bytes with Pillow; returns (bytes, ext) or (None, None).
    Pillow is optional - if it is not installed the original bytes pass through untouched."""
    try:
        from PIL import Image
        from PIL import ImageOps
        import io
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        w, h = img.size
        if w > max_side or h > max_side:
            scale = min(max_side / w, max_side / h)
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        # Always save small images as JPEG/PNG to shrink status payloads
        if img.mode == 'L':
            fmt, ext = 'PNG', 'png'
        else:
            fmt, ext = 'JPEG', 'jpg'
        buf = io.BytesIO()
        if fmt == 'JPEG':
            img.save(buf, format=fmt, quality=quality, optimize=True)
        else:
            img.save(buf, format=fmt, optimize=True)
        return buf.getvalue(), ext
    except ImportError:
        print("[APP] Pillow not installed - saving images without server-side resize")
        return None, None  # caller keeps original bytes
    except Exception as e:
        print(f"[APP] Image re-encode failed: {e}")
        return None, None


def _save_resized_image(file, max_side=1080, quality=80, subdir='status_media'):
    """Save an uploaded image (resized when Pillow is available), return its public URL or None."""
    try:
        file.seek(0)
        data = file.read()
        reencoded, ext = _reencode_image_bytes(data, max_side=max_side, quality=quality)
        if reencoded is None and ext is None:
            # Pillow missing or unreadable image: keep the original upload
            ext = (Path(file.filename).suffix or '.jpg').lstrip('.').lower() or 'jpg'
        elif reencoded is None:
            return None  # corrupt/unreadable image
        else:
            data = reencoded
        if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'):
            ext = 'jpg'
        if len(data) > 8 * 1024 * 1024:
            print("[APP] Image rejected: too large after resize")
            return None
        media_dir = Path('static') / subdir
        media_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
        (media_dir / filename).write_bytes(data)
        return f"/static/{subdir}/{filename}"
    except Exception as e:
        print(f"[APP] Error saving resized image: {e}")
        return None


def _save_data_url_image(data_url, max_side=1080, quality=80, subdir='status_media'):
    """Save an already-resized base64 data URL image, return its public URL or None."""
    try:
        import base64 as _base64
        payload = data_url.split(',', 1)[1]
        data = _base64.b64decode(payload)
        reencoded, ext = _reencode_image_bytes(data, max_side=max_side, quality=quality)
        if reencoded is None and ext is None:
            ext = 'jpg'  # Pillow missing - store as-is with a safe extension
        elif reencoded is None:
            return None
        else:
            data = reencoded
        if len(data) > 8 * 1024 * 1024:
            print("[APP] Image rejected: too large after resize")
            return None
        media_dir = Path('static') / subdir
        media_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
        (media_dir / filename).write_bytes(data)
        return f"/static/{subdir}/{filename}"
    except Exception as e:
        print(f"[APP] Error saving data-url image: {e}")
        return None

# ========== CHANGE PASSWORD ROUTE ==========

@app.route('/api/change-password', methods=['POST'])
def change_password_route():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    try:
        data = request.get_json() or {}
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        if not old_password or not new_password:
            return jsonify({'error': 'Current and new password are required'}), 400
        if len(new_password) < 6:
            return jsonify({'error': 'New password must be at least 6 characters'}), 400
        ok = False
        if security:
            ok = security.change_user_password(username, old_password, new_password)
        if ok:
            return jsonify({'success': True, 'message': 'Password updated'})
        return jsonify({'error': 'Current password is incorrect'}), 400
    except Exception as e:
        print(f"[API] Error changing password: {e}")
        return jsonify({'error': str(e)}), 500

# ========== NETWORK QUALITY ROUTE ==========

def _wifi_info_windows():
    """SSid + signal + radio type on Windows via netsh."""
    ssid, signal, radio = None, None, None
    try:
        import subprocess
        out = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True,
                             text=True, timeout=5, errors='replace').stdout
        m = re.search(r'^\s*SSID\s*:\s*(\S.*)$', out, re.M)
        if m:
            ssid = m.group(1).strip()
        m = re.search(r'Signal\s*:\s*(\d+)%', out)
        if m:
            signal = int(m.group(1))
        m = re.search(r'Radio type\s*:\s*(\S+)', out)
        if m:
            radio = m.group(1).strip()
    except Exception as e:
        print(f"[API] WiFi info unavailable: {e}")
    return ssid, signal, radio


def _gateway_ip_windows():
    try:
        import subprocess
        out = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=5,
                             errors='replace').stdout
        for line in out.splitlines():
            if 'Gateway' in line or 'Gateway' in line.lower():
                m = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', line)
                if m and m.group(1) != '0.0.0.0':
                    return m.group(1)
    except Exception as e:
        print(f"[API] Gateway lookup failed: {e}")
    return None


def _ping_latency(host, timeout_ms=1500):
    """ICMP ping latency in ms, or None."""
    if not host:
        return None
    try:
        import subprocess
        out = subprocess.run(['ping', '-n', '1', '-w', str(timeout_ms), host], capture_output=True,
                             text=True, timeout=timeout_ms / 1000 + 3, errors='replace').stdout
        m = re.search(r'(?:time|temps|zeit|tiempo)[=<>]\s*(\d+)\s*ms', out, re.I)
        if m:
            return int(m.group(1))
    except Exception as e:
        print(f"[API] Ping failed for {host}: {e}")
    return None


def _quality_label(signal=None, latency=None):
    """Overall connection quality from signal strength and/or latency."""
    if signal is not None and latency is not None:
        score = (signal / 100.0) * 0.6 + (1.0 - min(latency, 200) / 200.0) * 0.4
    elif signal is not None:
        score = signal / 100.0
    elif latency is not None:
        score = 1.0 - min(latency, 200) / 200.0
    else:
        return 'unknown', 0
    if score >= 0.75:
        return 'excellent', int(score * 100)
    if score >= 0.5:
        return 'good', int(score * 100)
    if score >= 0.3:
        return 'fair', int(score * 100)
    return 'poor', int(score * 100)

@app.route('/api/network/quality')
def network_quality():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    try:
        ssid, signal, radio = _wifi_info_windows()
        gateway = _gateway_ip_windows()
        latency = _ping_latency(gateway)
        connection_type = 'wifi' if ssid else 'ethernet'
        quality_label, quality_score = _quality_label(signal, latency)
        online_count = 0
        local_ip, port = None, None
        running = False
        if network:
            local_ip = network.local_ip
            port = network.port
            running = bool(network.running)
            with network_lock:
                try:
                    online_count = len(network.get_online_users())
                except Exception:
                    pass
        hostname = socket.gethostname()
        return jsonify({
            'connected': running,
            'network_name': ssid or 'Ethernet / Wired LAN',
            'connection_type': connection_type,
            'radio_type': radio,
            'signal_percent': signal,
            'latency_ms': latency,
            'gateway': gateway,
            'quality': quality_label,
            'quality_score': quality_score,
            'local_ip': local_ip,
            'hostname': hostname,
            'port': port or 6667,
            'online_count': online_count
        })
    except Exception as e:
        print(f"[API] Network quality error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ========== BROADCAST / MESH ROUTES (NON-INVASIVE) ==========

@app.route('/broadcast')
def broadcast_page():
    if 'username' not in session:
        return redirect(url_for('login'))
    m = get_mesh()
    return render_template('broadcast.html', username=session['username'], mesh=m)

@app.route('/network/dashboard')
def network_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    m = get_mesh()
    return render_template('network_dashboard.html', username=session['username'], mesh=m)

@app.route('/api/mesh/tower', methods=['GET', 'POST'])
def mesh_tower():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    m = get_mesh()
    if not m:
        return jsonify({'error': 'mesh not ready'}), 500
    if request.method == 'POST':
        data = request.get_json() or {}
        enable = bool(data.get('enable'))
        name = data.get('name') or ''
        info = m.set_tower_mode(enable, name)
        return jsonify({'ok': True, 'tower': info})
    else:
        return jsonify({'tower': m.get_tower_info()})

@app.route('/api/mesh/topology')
def mesh_topology():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    m = get_mesh()
    if not m:
        return jsonify({'ok': False})
    return jsonify(m.build_topology())

@app.route('/api/mesh/discover-manual', methods=['POST'])
def mesh_discover_manual():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json() or {}
    ip = (data.get('ip') or '').strip()
    port = data.get('port') or 6667
    if not ip:
        return jsonify({'error': 'ip required'}), 400
    # Non-invasive: just record intent in logs; existing network discovery handles connectivity
    try:
        print(f"[MESH] Manual peer add requested: {ip}:{port}")
    except:
        pass
    return jsonify({'ok': True, 'ip': ip, 'port': port})

@app.route('/api/mesh/freq', methods=['GET', 'POST'])
def mesh_freq():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    m = get_mesh()
    if not m:
        return jsonify({'error': 'mesh not ready'}), 500
    if request.method == 'POST':
        data = request.get_json() or {}
        action = data.get('action')
        if action == 'create':
            name = data.get('name') or ''
            desc = data.get('desc') or ''
            f = m.create_frequency(name, desc)
            return jsonify({'ok': True, 'freq': {'id': f['id'], 'name': f['name'], 'desc': f['desc']}})
        elif action == 'join':
            fid = data.get('id')
            m.join_frequency(fid)
            return jsonify({'ok': True})
        elif action == 'leave':
            fid = data.get('id')
            m.leave_frequency(fid)
            return jsonify({'ok': True})
        else:
            return jsonify({'error': 'bad action'}), 400
    else:
        return jsonify({'freqs': m.list_frequencies()})

@app.route('/api/mesh/freq/<fid>/members')
def mesh_freq_members(fid):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    m = get_mesh()
    if not m:
        return jsonify({'members': []})
    return jsonify({'members': m.get_freq_members(fid)})

@app.route('/api/mesh/emergency', methods=['GET', 'POST'])
def mesh_emergency():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    m = get_mesh()
    if not m:
        return jsonify({'active': False})
    if request.method == 'POST':
        data = request.get_json() or {}
        action = data.get('action')
        if action == 'trigger':
            msg = data.get('msg') or 'EMERGENCY BROADCAST'
            ed = m.trigger_emergency(msg)
            return jsonify({'ok': True, 'emergency': ed})
        elif action == 'clear':
            m.clear_emergency()
            return jsonify({'ok': True})
        else:
            return jsonify({'error': 'bad action'}), 400
    else:
        return jsonify(m.get_emergency())

# ========== UPDATE PROFILE ROUTE ==========

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    session['last_activity'] = time.time()
    username = session['username']
    try:
        data = request.get_json()
        bio = data.get('bio')
        status = data.get('status')
        if database:
            database.update_user_profile(username, bio=bio, status=status)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[API] Error updating profile: {e}")
        return jsonify({'error': str(e)}), 500

# ========== GET USER PROFILE ROUTE ==========

@app.route('/api/user-profile/<target_username>', methods=['GET'])
def get_user_profile(target_username):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        if database:
            profile = database.get_user_profile(target_username)
            if profile:
                return jsonify({'profile': profile})
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        print(f"[API] Error getting profile: {e}")
        return jsonify({'error': str(e)}), 500

webrtc_signals = []

@app.route('/api/webrtc/signal', methods=['POST'])
def webrtc_signal():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    username = session['username']
    try:
        data = request.get_json()
        data['from'] = username
        data['timestamp'] = time.time()
        webrtc_signals.append(data)
        if len(webrtc_signals) > 300:
            webrtc_signals.pop(0)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[API] Error signaling: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/webrtc/poll', methods=['GET'])
def webrtc_poll():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    username = session['username']
    try:
        global webrtc_signals
        signals = [s for s in list(webrtc_signals) if s.get('to') == username]
        webrtc_signals = [s for s in webrtc_signals if s.get('to') != username]
        return jsonify({'signals': signals})
    except Exception as e:
        print(f"[API] Error polling signals: {e}")
        return jsonify({'signals': []})

def main():
    print("\n" + "="*60)
    print("ðŸ”’ SECURELOCAL CHAT - RUNNING")
    print("="*60)
    print("Network Features:")
    if network:
        print(f"â€¢ UDP Discovery: Port {network.broadcast_port}")
        print(f"â€¢ TCP Messaging: Port {network.port}")
        print(f"â€¢ Network Running: {network.running}")
    print("="*60)
    print("ðŸ“± Opening browser automatically...")
    print("ðŸŒ Web Interface: http://localhost:5000")
    print("="*60)
    print("ðŸ“ Debug endpoints available:")
    print("   â€¢ /api/debug/network_status")
    print("   â€¢ /api/debug/check_connection?ip=XXX.XXX.XXX.XXX")
    print("="*60)
    print("â„¹ï¸  App is running in background")
    print("â„¹ï¸  Close this window to stop the server")
    print("="*60)

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\nðŸ‘‹ Shutting down...")
    except Exception as e:
        print(f"\nâŒ Error: {e}")
        input("Press Enter to exit...")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nðŸ‘‹ Goodbye!")
    except Exception as e:
        print(f"\nâŒ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")




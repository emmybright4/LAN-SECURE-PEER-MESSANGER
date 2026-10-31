"""
Security Manager - Handles encryption, decryption, and key management
"""
import os
import json
import base64
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

class SecurityManager:
    def __init__(self, data_path):
        self.data_path = Path(data_path)
        self.keys_path = self.data_path / 'keys'
        self.keys_path.mkdir(exist_ok=True)
        
        # Simple in-memory key storage
        self.user_keys = {}
        self.peer_keys = {}
        
        print(f"[SECURITY] Initialized with path: {self.data_path}")
    
    def _get_user_file(self, username):
        """Get user's key file path"""
        return self.keys_path / f"{username}.key"
    
    def _derive_key(self, password, salt=None):
        """Derive encryption key from password using PBKDF2"""
        if salt is None:
            salt = os.urandom(16)
        
        # Use PBKDF2HMAC to derive a key from the password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def create_user(self, username, password):
        """Create a new user with encryption keys"""
        try:
            # Generate a random key for the user
            user_key = Fernet.generate_key()
            
            # Derive a key from the password to encrypt the user key
            encryption_key, salt = self._derive_key(password)
            fernet = Fernet(encryption_key)
            
            # Encrypt the user key
            encrypted_user_key = fernet.encrypt(user_key)
            
            # Store the encrypted key and salt
            user_data = {
                'username': username,
                'encrypted_key': base64.b64encode(encrypted_user_key).decode(),
                'salt': base64.b64encode(salt).decode(),
                'public_key': base64.b64encode(user_key).decode(),
                'created': str(os.path.getctime(__file__))
            }
            
            # Save to file
            user_file = self._get_user_file(username)
            with open(user_file, 'w') as f:
                json.dump(user_data, f)
            
            # Store in memory
            self.user_keys[username] = {
                'key': user_key,
                'public_key': user_key
            }
            
            print(f"[SECURITY] Created user: {username}")
            return True
            
        except Exception as e:
            print(f"[SECURITY] Error creating user: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_user(self, username, password):
        """Verify user password and load keys"""
        try:
            user_file = self._get_user_file(username)
            
            if not user_file.exists():
                return False
            
            # Load user data
            with open(user_file, 'r') as f:
                user_data = json.load(f)
            
            # Get salt and encrypted key
            salt = base64.b64decode(user_data['salt'])
            encrypted_key = base64.b64decode(user_data['encrypted_key'])
            
            # Derive key from password
            encryption_key, _ = self._derive_key(password, salt)
            
            # Try to decrypt the user key
            fernet = Fernet(encryption_key)
            try:
                user_key = fernet.decrypt(encrypted_key)
                
                # Store in memory
                self.user_keys[username] = {
                    'key': user_key,
                    'public_key': base64.b64decode(user_data['public_key'])
                }
                
                print(f"[SECURITY] User verified: {username}")
                return True
                
            except Exception as e:
                # Wrong password or corrupted data
                print(f"[SECURITY] Decryption failed: {e}")
                return False
                
        except Exception as e:
            print(f"[SECURITY] Error verifying user: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def change_user_password(self, username, old_password, new_password):
        """Change a user's password: re-encrypt their key under a new password."""
        try:
            user_file = self._get_user_file(username)
            if not user_file.exists():
                return False

            with open(user_file, 'r') as f:
                user_data = json.load(f)

            salt = base64.b64decode(user_data['salt'])
            encrypted_key = base64.b64decode(user_data['encrypted_key'])

            # Decrypt the user key using the OLD password
            old_derived, _ = self._derive_key(old_password, salt)
            try:
                user_key = Fernet(old_derived).decrypt(encrypted_key)
            except Exception:
                print(f"[SECURITY] Old password incorrect for {username}")
                return False

            # Re-encrypt under the NEW password
            new_derived, new_salt = self._derive_key(new_password)
            new_encrypted = Fernet(new_derived).encrypt(user_key)

            user_data['salt'] = base64.b64encode(new_salt).decode()
            user_data['encrypted_key'] = base64.b64encode(new_encrypted).decode()

            with open(user_file, 'w') as f:
                json.dump(user_data, f)

            # Keep the in-memory key alive under the new credentials
            self.user_keys[username] = {
                'key': user_key,
                'public_key': base64.b64decode(user_data['public_key'])
            }

            print(f"[SECURITY] Password changed for {username}")
            return True

        except Exception as e:
            print(f"[SECURITY] Error changing password: {e}")
            import traceback
            traceback.print_exc()
            return False

    def user_exists(self, username):
        """Check if user exists"""
        return self._get_user_file(username).exists()
    
    def get_my_key(self, username):
        """Get user's own encryption key"""
        return self.user_keys.get(username, {}).get('key')
    
    def get_my_public_key(self, username):
        """Get user's public key for exchange"""
        key = self.user_keys.get(username, {}).get('public_key')
        if key:
            return {
                'key': base64.b64encode(key).decode(),
                'key_id': hashlib.sha256(key).hexdigest()[:16]
            }
        return None
    
    def add_peer_key(self, username, peer_name, key_data):
        """Add another user's public key"""
        try:
            if username not in self.peer_keys:
                self.peer_keys[username] = {}
            
            # Decode if it's base64
            if isinstance(key_data, str):
                key = base64.b64decode(key_data)
            else:
                key = key_data
            
            self.peer_keys[username][peer_name] = key
            
            # Save to file
            peer_file = self.keys_path / f"{username}.peers"
            peers = {}
            if peer_file.exists():
                with open(peer_file, 'r') as f:
                    peers = json.load(f)
            
            peers[peer_name] = base64.b64encode(key).decode()
            
            with open(peer_file, 'w') as f:
                json.dump(peers, f)
            
            print(f"[SECURITY] Added peer key for {peer_name}")
            return True
            
        except Exception as e:
            print(f"[SECURITY] Error adding peer key: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def encrypt_for_peer(self, username, peer_name, message):
        """Encrypt message for a peer"""
        try:
            # Get peer's key
            peer_key = self.peer_keys.get(username, {}).get(peer_name)
            if not peer_key:
                print(f"[SECURITY] No key found for peer: {peer_name}")
                return message  # No encryption key available
            
            # Use Fernet for encryption
            fernet = Fernet(peer_key)
            encrypted = fernet.encrypt(message.encode())
            
            # Return as base64 string
            return base64.b64encode(encrypted).decode()
            
        except Exception as e:
            print(f"[SECURITY] Error encrypting for peer: {e}")
            import traceback
            traceback.print_exc()
            return message
    
    def decrypt_from_peer(self, username, peer_name, encrypted_message):
        """Decrypt message from a peer"""
        try:
            # Get our own key
            my_key = self.get_my_key(username)
            if not my_key:
                print(f"[SECURITY] No key found for user: {username}")
                return encrypted_message
            
            # Try to decode base64
            try:
                encrypted_data = base64.b64decode(encrypted_message)
            except:
                # Not base64 encoded, return as is
                print(f"[SECURITY] Message not base64 encoded: {encrypted_message[:50]}")
                return encrypted_message
            
            # Use Fernet for decryption
            fernet = Fernet(my_key)
            decrypted = fernet.decrypt(encrypted_data)
            
            return decrypted.decode()
            
        except Exception as e:
            print(f"[SECURITY] Error decrypting from peer: {e}")
            import traceback
            traceback.print_exc()
            return encrypted_message
    
    def has_peer_key(self, username, peer_name):
        """Check if we have a key for this peer"""
        return peer_name in self.peer_keys.get(username, {})
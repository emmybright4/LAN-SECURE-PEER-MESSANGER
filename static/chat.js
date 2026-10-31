/**
 * SecureLocal Chat - Main JavaScript
 * Handles chat UI, encryption status, and network communication
 */

class SecureLocalChat {
    constructor() {
        this.currentUser = null;
        this.currentRecipient = null;
        this.usersData = {};
        this.messages = {};
        this.encryptionStatus = {};
        this.autoRefreshInterval = null;
        this.messageRefreshInterval = null;
        
        this.init();
    }
    
    init() {
        console.log("🔒  LAN SECURE PEER MESSANGER initialized");
        
        // Get username from page
        this.username = document.getElementById('username')?.textContent || 'Unknown';
        
        // Initialize event listeners
        this.setupEventListeners();
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Auto-exchange keys on page load
        setTimeout(() => this.autoExchangeKeys(), 2000);
    }
    
    setupEventListeners() {
        // Message input enter key
        const messageInput = document.getElementById('message-text');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }
        
        // Auto-exchange keys button
        const autoExchangeBtn = document.getElementById('auto-exchange-btn');
        if (autoExchangeBtn) {
            autoExchangeBtn.addEventListener('click', () => this.autoExchangeKeys());
        }
        
        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                window.location.href = '/logout';
            });
        }
    }
    
    startAutoRefresh() {
        // Refresh user list every 3 seconds
        this.autoRefreshInterval = setInterval(() => {
            this.updateUserList();
        }, 3000);
        
        // Refresh messages every 2 seconds (if in a conversation)
        this.messageRefreshInterval = setInterval(() => {
            if (this.currentRecipient) {
                this.loadMessages();
                this.updateEncryptionStatus();
            }
        }, 2000);
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        if (this.messageRefreshInterval) {
            clearInterval(this.messageRefreshInterval);
        }
    }
    
    // ===== USER MANAGEMENT =====
    async updateUserList() {
        try {
            const response = await fetch('/api/users');
            if (!response.ok) throw new Error('Failed to fetch users');
            
            const data = await response.json();
            this.renderUserList(data.users);
            
            // Update encryption status
            data.users.forEach(user => {
                this.encryptionStatus[user.username] = user.encrypted;
            });
            
        } catch (error) {
            console.error('Error updating user list:', error);
            this.showNotification('Failed to update user list', 'error');
        }
    }
    
    renderUserList(users) {
        const container = document.getElementById('users');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (users.length === 0) {
            container.innerHTML = '<div class="no-users"><i class="fas fa-users-slash"></i><p>No users online</p></div>';
            return;
        }
        
        users.forEach(user => {
            const isActive = user.username === this.currentRecipient;
            const isEncrypted = user.encrypted || false;
            const status = user.status || 'online';
            const statusClass = status === 'online' ? 'online' : 'offline';
            
            const userItem = document.createElement('div');
            userItem.className = `user-item ${isActive ? 'active' : ''}`;
            userItem.innerHTML = `
                <div class="user-info">
                    <span class="user-name">${user.username}</span>
                    <span class="user-status ${statusClass}"><i class="fas fa-circle"></i> ${status.charAt(0).toUpperCase() + status.slice(1)}</span>
                </div>
                <div class="status-dot ${statusClass}"></div>
                <button class="chat-btn" data-username="${user.username}">
                    ${isActive ? 'Chatting...' : 'Chat'}
                </button>
            `;
            
            // Add click event
            const chatBtn = userItem.querySelector('.chat-btn');
            chatBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectUser(user.username, isEncrypted);
            });
            
            container.appendChild(userItem);
        });
    }
    
    selectUser(username, isEncrypted) {
        this.currentRecipient = username;
        
        // Update UI
        document.querySelectorAll('.user-item').forEach(item => {
            item.classList.remove('active');
        });
        
        document.querySelector(`[data-username="${username}"]`)?.closest('.user-item')?.classList.add('active');
        
        // Update message input placeholder
        const messageInput = document.getElementById('message-text');
        if (messageInput) {
            messageInput.placeholder = `Message ${username}...`;
            messageInput.focus();
        }
        
        // Update encryption status display
        this.updateEncryptionStatus();
        
        // Load messages
        this.loadMessages();
        
        // Auto-exchange keys if not encrypted
        if (!isEncrypted) {
            this.autoExchangeKeysWithUser(username);
        }
    }
    
    updateEncryptionStatus() {
        const statusDiv = document.getElementById('encryption-status');
        if (!statusDiv || !this.currentRecipient) return;
        
        const isEncrypted = this.encryptionStatus[this.currentRecipient] || false;
        
        if (isEncrypted) {
            statusDiv.innerHTML = `
                <div class="status-encrypted">
                    🔒 End-to-end encryption is active
                    <small>Messages are encrypted and secure</small>
                </div>
            `;
            statusDiv.className = 'status-encrypted';
        } else {
            statusDiv.innerHTML = `
                <div class="status-unencrypted">
                    ⚠️ Encryption not established
                    <small>Click "Auto-Exchange Keys" to enable E2EE</small>
                </div>
            `;
            statusDiv.className = 'status-unencrypted';
        }
    }
    
    // ===== MESSAGING =====
    async sendMessage() {
        if (!this.currentRecipient) {
            this.showNotification('Please select a user to chat with', 'warning');
            return;
        }
        
        const messageInput = document.getElementById('message-text');
        const message = messageInput?.value.trim();
        
        if (!message) return;
        
        try {
            // Disable input while sending
            messageInput.disabled = true;
            
            const response = await fetch('/api/messages', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    recipient: this.currentRecipient,
                    message: message
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Clear input
                messageInput.value = '';
                
                // Show success notification
                if (data.encrypted) {
                    this.showNotification('Message sent with 🔒 encryption', 'success');
                } else {
                    this.showNotification('Message sent (unencrypted)', 'warning');
                }
                
                // Reload messages
                this.loadMessages();
                
            } else {
                this.showNotification(`Error: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.showNotification('Failed to send message', 'error');
        } finally {
            // Re-enable input
            if (messageInput) {
                messageInput.disabled = false;
                messageInput.focus();
            }
        }
    }
    
    async loadMessages() {
        if (!this.currentRecipient) return;
        
        try {
            const response = await fetch(`/api/messages?with=${this.currentRecipient}`);
            if (!response.ok) throw new Error('Failed to load messages');
            
            const data = await response.json();
            this.renderMessages(data.messages);
            
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }
    
    renderMessages(messages) {
        const container = document.getElementById('messages');
        if (!container) return;
        
        // Store messages for this conversation
        if (!this.messages[this.currentRecipient]) {
            this.messages[this.currentRecipient] = [];
        }
        
        // Only update if messages changed
        const currentMessageCount = this.messages[this.currentRecipient].length;
        if (currentMessageCount === messages.length) {
            // Check if any message content changed
            let changed = false;
            for (let i = 0; i < messages.length; i++) {
                if (JSON.stringify(this.messages[this.currentRecipient][i]) !== JSON.stringify(messages[i])) {
                    changed = true;
                    break;
                }
            }
            if (!changed) return;
        }
        
        // Update stored messages
        this.messages[this.currentRecipient] = messages;
        
        // Render messages
        container.innerHTML = '';
        
        if (messages.length === 0) {
            container.innerHTML = `
                <div class="no-messages">
                    No messages yet. Start the conversation!
                </div>
            `;
            return;
        }
        
        messages.forEach(msg => {
            const isSent = msg.sender === this.username;
            const isEncrypted = msg.was_encrypted || msg.is_encrypted;
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isSent ? 'sent' : 'received'} ${isEncrypted ? 'encrypted' : ''}`;
            messageDiv.innerHTML = `
                <div class="message-header">
                    <span class="sender">${msg.sender}</span>
                    <span class="time">${msg.display_time || msg.timestamp}</span>
                    ${isEncrypted ? '<span class="encryption-icon">🔒</span>' : ''}
                </div>
                <div class="message-content">${this.escapeHtml(msg.message)}</div>
                <div class="message-footer">
                    ${isEncrypted ? '<small>End-to-end encrypted</small>' : '<small>Not encrypted</small>'}
                </div>
            `;
            
            container.appendChild(messageDiv);
        });
        
        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }
    
    // ===== ENCRYPTION =====
    async autoExchangeKeys() {
        try {
            this.showNotification('Exchanging encryption keys...', 'info');
            
            const response = await fetch('/api/encryption/auto_exchange');
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Exchanged keys with ${data.exchanged} user(s)`, 'success');
                
                // Update user list to show new encryption status
                setTimeout(() => this.updateUserList(), 1000);
                
                // If we're chatting with someone, update status
                if (this.currentRecipient) {
                    setTimeout(() => this.updateEncryptionStatus(), 1000);
                }
            } else {
                this.showNotification(`Key exchange failed: ${data.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error exchanging keys:', error);
            this.showNotification('Failed to exchange keys', 'error');
        }
    }
    
    async autoExchangeKeysWithUser(username) {
        try {
            const response = await fetch('/api/encryption/exchange', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    recipient: username
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Key exchange initiated with ${username}`, 'success');
                this.encryptionStatus[username] = true;
                this.updateEncryptionStatus();
            }
            
        } catch (error) {
            console.error('Error exchanging key with user:', error);
        }
    }
    
    // ===== UTILITIES =====
    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existing = document.querySelectorAll('.notification');
        existing.forEach(el => el.remove());
        
        // Create notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        
        // Style based on type
        switch(type) {
            case 'success':
                notification.style.background = '#4CAF50';
                break;
            case 'error':
                notification.style.background = '#f44336';
                break;
            case 'warning':
                notification.style.background = '#ff9800';
                break;
            default:
                notification.style.background = '#2196F3';
        }
        
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // ===== NETWORK INFO =====
    async updateNetworkInfo() {
        try {
            const response = await fetch('/api/network/info');
            if (response.ok) {
                const data = await response.json();
                
                const infoDiv = document.getElementById('network-info');
                if (infoDiv) {
                    infoDiv.innerHTML = `
                        <small>
                            IP: ${data.local_ip} | 
                            Online: ${data.online_count} | 
                            Encrypted: ${data.encrypted_count}
                        </small>
                    `;
                }
            }
        } catch (error) {
            console.error('Error fetching network info:', error);
        }
    }
    
    // ===== TAB SWITCHING =====
    switchTab(tabName) {
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.getElementById('tab-' + tabName).classList.add('active');
        event.target.closest('.tab-btn')?.classList.add('active');
    }

    // ===== USER LIST =====
    async refreshUsers() {
        try {
            const response = await fetch('/api/users');
            const data = await response.json();
            this.renderUserList(data.users || []);
            data.users.forEach(u => { this.encryptionStatus[u.username] = u.encrypted || false; });
        } catch (e) { console.error('refreshUsers error', e); }
    }

    renderUserList(users) {
        const container = document.getElementById('users-list');
        if (!container) return;
        container.innerHTML = '';
        if (users.length === 0) { container.innerHTML = '<div class="empty-state"><i class="fas fa-users-slash"></i><p>No users online</p></div>'; return; }
        users.forEach(user => {
            const isActive = user.username === this.currentRecipient;
            const isEncrypted = user.encrypted || false;
            const div = document.createElement('div');
            div.className = 'list-item ' + (isActive ? 'active' : '');
            div.onclick = () => this.selectUser(user.username);
            const initial = user.username.charAt(0).toUpperCase();
            const avatarHtml = user.avatar ? '<img src="' + user.avatar + '" alt="avatar">' : '<span class="avatar-initial">' + initial + '</span>';
            div.innerHTML = '<div class="item-avatar">' + avatarHtml + '</div><div class="item-info"><div class="item-name">' + user.username + ' <span class="item-status-dot"></span></div><div class="item-subtext">' + (isEncrypted ? 'E2EE Encrypted' : 'Not encrypted') + '</div></div>';
            container.appendChild(div);
        });
    }

    async selectUser(username) {
        this.currentRecipient = username;
        document.getElementById('chat-name').textContent = username;
        document.getElementById('chat-status').textContent = 'Online';
        document.getElementById('chat-avatar').innerHTML = '<span class="avatar-initial">' + username.charAt(0).toUpperCase() + '</span>';
        this.loadMessages();
        this.updateEncryptionStatus();
        this.refreshUsers();
    }

    // ===== GROUPS =====
    async refreshGroups() {
        try {
            const response = await fetch('/api/groups');
            const data = await response.json();
            const container = document.getElementById('groups-list');
            if (!container) return;
            container.innerHTML = '';
            (data.groups || []).forEach(g => {
                const div = document.createElement('div');
                div.className = 'group-item';
                div.innerHTML = '<div class="group-avatar">' + g.name.charAt(0).toUpperCase() + '</div><div class="item-info"><div class="item-name">' + g.name + '</div><div class="item-subtext">Group chat</div></div>';
                container.appendChild(div);
            });
        } catch (e) { console.error('refreshGroups error', e); }
    }

    // ===== STATUS =====
    async refreshStatuses() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            const container = document.getElementById('status-list');
            if (!container) return;
            container.innerHTML = '';
            (data.statuses || []).slice(0, 5).forEach(s => {
                const div = document.createElement('div');
                div.className = 'status-item';
                const initial = s.username.charAt(0).toUpperCase();
                div.innerHTML = '<div class="status-avatar"><span class="avatar-initial">' + initial + '</span></div><div class="status-info"><div class="status-name">' + s.username + '</div><div class="status-text">' + s.content + '</div><div class="status-time">' + new Date(s.created_at || Date.now()).toLocaleTimeString() + '</div></div>';
                container.appendChild(div);
            });
        } catch (e) { console.error('refreshStatuses error', e); }
    }

    // ===== MESSAGES =====
    async loadMessages() {
        if (!this.currentRecipient) return;
        try {
            const response = await fetch('/api/messages?with=' + encodeURIComponent(this.currentRecipient));
            const data = await response.json();
            const container = document.getElementById('messages-area');
            if (!container) return;
            container.innerHTML = '';
            (data.messages || []).forEach(msg => {
                const div = document.createElement('div');
                div.className = 'message ' + (msg.sender === this.username ? 'sent' : 'received');
                const time = new Date(msg.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const encrypted = msg.is_encrypted ? '<div class="message-encrypted"><i class="fas fa-lock"></i> Encrypted</div>' : '';
                div.innerHTML = (msg.sender !== this.username ? '<div class="message-sender">' + msg.sender + '</div>' : '') + '<div>' + msg.message + '</div><div class="message-time">' + time + '</div>' + encrypted;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        } catch (e) { console.error('loadMessages error', e); }
    }

    async sendMessage() {
        const input = document.getElementById('message-text');
        const text = input.value.trim();
        if (!text || !this.currentRecipient) return;
        try {
            const response = await fetch('/api/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ recipient: this.currentRecipient, message: text })
            });
            const data = await response.json();
            if (data.success) {
                input.value = '';
                this.loadMessages();
            } else {
                showNotification(data.error || 'Failed to send', 'error');
            }
        } catch (e) { console.error('sendMessage error', e); }
    }

    // ===== ENCRYPTION =====
    async updateEncryptionStatus() {
        if (!this.currentRecipient) return;
        const enc = this.encryptionStatus[this.currentRecipient];
        const el = document.getElementById('chat-status');
        if (el) el.textContent = enc ? 'Encrypted' : 'Online';
    }

    async autoExchangeKeys() {
        try {
            const response = await fetch('/api/encryption/exchange_all', { method: 'POST' });
            const data = await response.json();
            if (data.success) this.showNotification('Keys exchanged with ' + data.exchanged + ' peer(s)', 'success');
        } catch (e) { console.error('autoExchangeKeys error', e); }
    }

    // ===== INIT =====
    async init() {
        console.log("LAN SECURE PEER MESSANGER initialized");
        this.username = document.getElementById('username')?.textContent || 'Unknown';
        this.setupEventListeners();
        this.startAutoRefresh();
        setTimeout(() => this.autoExchangeKeys(), 2000);
        setTimeout(() => this.refreshGroups(), 1000);
        setTimeout(() => this.refreshStatuses(), 1000);
    }    // Cleanup
    destroy() {
        this.stopAutoRefresh();
        console.log("Chat destroyed");
    }
}

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new SecureLocalChat();
});

// Export for debugging
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SecureLocalChat;
}

// Global wrappers for HTML onclick handlers
function switchTab(e, tabName) {
    if (window.chatApp) {
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.getElementById('tab-' + tabName).classList.add('active');
        if (e && e.target) e.target.classList.add('active');
        if (tabName === 'groups') window.chatApp.refreshGroups();
        if (tabName === 'status') window.chatApp.refreshStatuses();
    }
}

function refreshUsers() { if (window.chatApp) window.chatApp.refreshUsers(); }

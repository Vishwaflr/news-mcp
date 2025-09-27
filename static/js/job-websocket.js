/**
 * WebSocket Client for Real-time Job Updates
 * Auto-reconnect, event handling, and fallback support
 */

class JobWebSocketClient {
    constructor(options = {}) {
        this.options = {
            url: options.url || `ws://${window.location.host}/ws/jobs`,
            clientId: options.clientId || this.generateClientId(),
            reconnectInterval: options.reconnectInterval || 5000,
            maxReconnectAttempts: options.maxReconnectAttempts || 10,
            heartbeatInterval: options.heartbeatInterval || 30000,
            debug: options.debug || false,
            ...options
        };

        this.ws = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.heartbeatTimer = null;
        this.subscriptions = new Set();
        this.messageQueue = [];
        this.eventHandlers = {};

        // Default event handlers
        this.on('connection', this.handleConnection.bind(this));
        this.on('job_update', this.handleJobUpdate.bind(this));
        this.on('error', this.handleError.bind(this));
        this.on('ping', this.handlePing.bind(this));

        // Auto-connect
        this.connect();
    }

    generateClientId() {
        return 'client-' + Math.random().toString(36).substring(2, 10);
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.log('Already connected');
            return;
        }

        const wsUrl = `${this.options.url}?client_id=${this.options.clientId}`;
        this.log(`Connecting to ${wsUrl}...`);

        try {
            this.ws = new WebSocket(wsUrl);
            this.setupEventListeners();
        } catch (error) {
            this.log('Connection failed:', error);
            this.scheduleReconnect();
        }
    }

    setupEventListeners() {
        this.ws.onopen = () => {
            this.log('Connected!');
            this.isConnected = true;
            this.reconnectAttempts = 0;

            // Resubscribe to jobs
            this.subscriptions.forEach(jobId => {
                this.subscribe(jobId);
            });

            // Process queued messages
            while (this.messageQueue.length > 0) {
                const message = this.messageQueue.shift();
                this.send(message);
            }

            // Start heartbeat
            this.startHeartbeat();

            this.emit('connected');
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.log('Received:', message);

                // Emit event based on message type
                if (message.type) {
                    this.emit(message.type, message);
                }
            } catch (error) {
                this.log('Error parsing message:', error);
            }
        };

        this.ws.onerror = (error) => {
            this.log('WebSocket error:', error);
            this.emit('error', error);
        };

        this.ws.onclose = (event) => {
            this.log('Connection closed:', event.code, event.reason);
            this.isConnected = false;
            this.stopHeartbeat();

            if (!event.wasClean) {
                this.scheduleReconnect();
            }

            this.emit('disconnected', event);
        };
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            this.log('Max reconnection attempts reached');
            this.emit('reconnect_failed');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(
            this.options.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1),
            30000
        );

        this.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            if (!this.isConnected) {
                this.connect();
            }
        }, delay);
    }

    send(message) {
        if (this.isConnected && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
            this.log('Sent:', message);
        } else {
            this.log('Queuing message (not connected):', message);
            this.messageQueue.push(message);
        }
    }

    subscribe(jobId) {
        this.subscriptions.add(jobId);
        this.send({
            action: 'subscribe',
            job_id: jobId
        });
        this.log(`Subscribed to job ${jobId}`);
    }

    unsubscribe(jobId) {
        this.subscriptions.delete(jobId);
        this.send({
            action: 'unsubscribe',
            job_id: jobId
        });
        this.log(`Unsubscribed from job ${jobId}`);
    }

    startHeartbeat() {
        this.stopHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                this.send({ action: 'ping' });
            }
        }, this.options.heartbeatInterval);
    }

    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    // Event handling
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
        return this;
    }

    off(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event] = this.eventHandlers[event].filter(h => h !== handler);
        }
        return this;
    }

    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }

    // Default handlers
    handleConnection(data) {
        this.log('Connection established:', data);
    }

    handleJobUpdate(data) {
        this.log('Job update:', data);

        // Emit specific update type
        if (data.update_type) {
            this.emit(`job_${data.update_type}`, data);
        }

        // Update UI if handler is registered
        if (window.updateJobProgress) {
            window.updateJobProgress(data.job_id, data.data);
        }
    }

    handleError(error) {
        console.error('WebSocket error:', error);
    }

    handlePing() {
        this.send({ action: 'pong' });
    }

    // Utility methods
    log(...args) {
        if (this.options.debug) {
            console.log(`[JobWS ${this.options.clientId}]`, ...args);
        }
    }

    disconnect() {
        this.log('Disconnecting...');
        this.stopHeartbeat();
        this.reconnectAttempts = this.options.maxReconnectAttempts; // Prevent auto-reconnect

        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }

        this.isConnected = false;
        this.subscriptions.clear();
        this.messageQueue = [];
    }

    getStatus() {
        return {
            connected: this.isConnected,
            clientId: this.options.clientId,
            subscriptions: Array.from(this.subscriptions),
            queuedMessages: this.messageQueue.length,
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

// Auto-initialize if included in HTML
if (typeof window !== 'undefined') {
    window.JobWebSocketClient = JobWebSocketClient;

    // Auto-connect on page load
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.jobWS) {
            window.jobWS = new JobWebSocketClient({
                debug: true,
                reconnectInterval: 3000
            });

            // Example: Auto-update progress bars
            window.jobWS.on('job_progress', (data) => {
                const progressBar = document.querySelector(`#progress-${data.job_id}`);
                if (progressBar) {
                    const percent = data.data.percent || 0;
                    progressBar.style.width = percent + '%';
                    progressBar.textContent = Math.round(percent) + '%';
                }
            });

            // Example: Update status badges
            window.jobWS.on('job_status_changed', (data) => {
                const badge = document.querySelector(`#status-${data.job_id}`);
                if (badge) {
                    badge.textContent = data.data.status;
                    badge.className = 'badge ' + getStatusClass(data.data.status);
                }
            });

            console.log('JobWebSocketClient initialized:', window.jobWS.getStatus());
        }
    });

    // Helper function for status badge classes
    function getStatusClass(status) {
        const statusClasses = {
            'preview': 'bg-secondary',
            'confirmed': 'bg-info',
            'running': 'bg-primary',
            'completed': 'bg-success',
            'failed': 'bg-danger',
            'cancelled': 'bg-warning'
        };
        return statusClasses[status] || 'bg-secondary';
    }
}
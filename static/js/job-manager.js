/**
 * JobManager - ES6 Class for Job-based Analysis System
 * Uses /api/analysis/jobs/* endpoints from ENDPOINTS.md
 */
class JobManager {
    constructor(callbacks = {}) {
        this.callbacks = {
            onQueued: callbacks.onQueued || (() => {}),
            onRunning: callbacks.onRunning || (() => {}),
            onDone: callbacks.onDone || (() => {}),
            onError: callbacks.onError || (() => {})
        };

        this.currentJobId = null;
        this.pollInterval = null;
        this.pollIntervalMs = 2000; // 2 seconds
        this.maxRetries = 3;
        this.retryCount = 0;
    }

    /**
     * Start a new job with preview
     * @param {Object} selection - Selection configuration
     * @param {Object} parameters - Analysis parameters
     * @param {Object} filters - Additional filters
     * @returns {Promise<string>} Job ID
     */
    async start(selection, parameters, filters = {}) {
        try {
            // Create preview job first
            const payload = {
                selection: selection,
                parameters: parameters,
                filters: filters
            };

            console.log('Creating job preview:', payload);

            const response = await fetch('/api/analysis/jobs/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Job creation failed: ${response.statusText}`);
            }

            const result = await response.json();

            if (!result.success || !result.job_id) {
                throw new Error(result.error || 'Job creation failed');
            }

            this.currentJobId = result.job_id;
            this.retryCount = 0;

            // Start polling for job status
            this.startPolling();

            // Trigger queued callback
            this.callbacks.onQueued(this.currentJobId, result.estimates);

            return this.currentJobId;

        } catch (error) {
            console.error('JobManager start failed:', error);
            this.callbacks.onError(error.message);
            throw error;
        }
    }

    /**
     * Confirm job for execution
     * @param {string} jobId - Job ID to confirm
     * @returns {Promise<void>}
     */
    async confirm(jobId = null) {
        const targetJobId = jobId || this.currentJobId;
        if (!targetJobId) {
            throw new Error('No job ID available for confirmation');
        }

        try {
            const response = await fetch(`/api/analysis/jobs/${targetJobId}/confirm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`Job confirmation failed: ${response.statusText}`);
            }

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || 'Job confirmation failed');
            }

            console.log('Job confirmed:', targetJobId);

        } catch (error) {
            console.error('JobManager confirm failed:', error);
            this.callbacks.onError(error.message);
            throw error;
        }
    }

    /**
     * Get job status
     * @param {string} jobId - Job ID
     * @returns {Promise<Object>} Job status
     */
    async getStatus(jobId = null) {
        const targetJobId = jobId || this.currentJobId;
        if (!targetJobId) {
            throw new Error('No job ID available for status check');
        }

        const response = await fetch(`/api/analysis/jobs/${targetJobId}`);

        if (!response.ok) {
            throw new Error(`Status check failed: ${response.statusText}`);
        }

        return await response.json();
    }

    /**
     * Start polling for job status updates
     */
    startPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        this.pollInterval = setInterval(async () => {
            try {
                await this.checkStatus();
                this.retryCount = 0; // Reset retry count on success

            } catch (error) {
                console.error('Status polling error:', error);
                this.retryCount++;

                if (this.retryCount >= this.maxRetries) {
                    console.error('Max retries reached, stopping polling');
                    this.stop();
                    this.callbacks.onError('Status polling failed after max retries');
                }
            }
        }, this.pollIntervalMs);
    }

    /**
     * Check current job status and trigger callbacks
     */
    async checkStatus() {
        if (!this.currentJobId) return;

        const status = await this.getStatus();

        console.log('Job status check:', status);

        // Handle different status states
        switch (status.status) {
            case 'queued':
            case 'created':
                // Still queued, no additional action needed
                break;

            case 'running':
                this.callbacks.onRunning(this.currentJobId, status);
                break;

            case 'completed':
            case 'done':
                this.stop();
                this.callbacks.onDone(this.currentJobId, status);
                break;

            case 'failed':
            case 'error':
                this.stop();
                this.callbacks.onError(status.error || 'Job failed');
                break;

            default:
                console.warn('Unknown job status:', status.status);
        }
    }

    /**
     * Stop polling and reset state
     */
    stop() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.currentJobId = null;
        this.retryCount = 0;
        console.log('JobManager stopped');
    }

    /**
     * Check if job is currently active
     * @returns {boolean}
     */
    isActive() {
        return this.currentJobId !== null && this.pollInterval !== null;
    }

    /**
     * Get current job ID
     * @returns {string|null}
     */
    getCurrentJobId() {
        return this.currentJobId;
    }
}

// Export for ES6 modules or attach to window for legacy use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = JobManager;
} else {
    window.JobManager = JobManager;
}
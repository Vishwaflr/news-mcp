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
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Job creation failed: ${response.statusText}`);
            }

            const result = await response.json();

            // Handle both direct job response and wrapped response
            const jobId = result.job_id || result.data?.job_id;
            const estimates = result.estimates || result.data?.estimates || result;

            if (!jobId) {
                throw new Error('No job ID returned from preview');
            }

            this.currentJobId = jobId;
            this.retryCount = 0;

            // Don't start polling yet - wait for confirmation
            // this.startPolling();

            // Trigger queued callback with estimates
            this.callbacks.onQueued(this.currentJobId, estimates);

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

        // Extract run information if job is executing
        if (status.run_id) {
            // Fetch actual run status for progress
            const runStatus = await this.getRunStatus(status.run_id);
            status.progress = runStatus;
        }

        // Handle different status states
        switch (status.status) {
            case 'queued':
            case 'created':
            case 'confirmed':
                // Still queued, no additional action needed
                break;

            case 'running':
            case 'executing':
                this.callbacks.onRunning(this.currentJobId, status.progress || status);
                break;

            case 'completed':
            case 'done':
                this.stop();
                this.callbacks.onDone(this.currentJobId, status.progress || status);
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
     * Get run status for progress tracking
     * @param {string} runId - Run ID
     * @returns {Promise<Object>} Run status with progress
     */
    async getRunStatus(runId) {
        try {
            const response = await fetch(`/api/analysis/status/${runId}`);
            if (!response.ok) {
                console.warn('Failed to get run status:', response.statusText);
                return null;
            }
            return await response.json();
        } catch (error) {
            console.error('Error getting run status:', error);
            return null;
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
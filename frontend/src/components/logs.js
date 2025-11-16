/**
 * Logs Component
 *
 * Handles the log viewer interface:
 * - Displaying system logs
 * - Filtering by type and category
 * - Showing log details
 */

const LogsComponent = {
    // Current filters
    currentFilters: {
        logType: '',
        logCategory: '',
        limit: 100
    },

    /**
     * Initialize the logs component
     */
    init() {
        console.log('Logs component initialized');
    },

    /**
     * Load and display logs
     * @param {Object} filters - Optional filter overrides
     */
    async loadLogs(filters = {}) {
        const logsContainer = document.getElementById('logs-container');
        logsContainer.innerHTML = '<p class="loading">Loading logs...</p>';

        // Merge filters
        const activeFilters = { ...this.currentFilters, ...filters };

        try {
            const logs = await getLogs(activeFilters);

            if (logs.length === 0) {
                logsContainer.innerHTML = '<p>No logs found matching the current filters.</p>';
                return;
            }

            let html = '';

            for (const log of logs) {
                // Format timestamp
                const timestamp = new Date(log.timestamp).toLocaleString();

                html += `
                    <div class="log-entry ${log.log_type}">
                        <div class="log-timestamp">${timestamp}</div>
                        <div>
                            <span class="log-type">[${log.log_type}]</span>
                            <span style="color: #9ca3af;">[${log.log_category || 'general'}]</span>
                        </div>
                        <div class="log-message">${this.escapeHtml(log.message)}</div>
                `;

                // Show details if present
                if (log.details) {
                    try {
                        const details = JSON.parse(log.details);
                        html += `
                            <div class="log-details">
                                ${this.formatDetails(details)}
                            </div>
                        `;
                    } catch (e) {
                        // Not JSON, show as-is
                        html += `
                            <div class="log-details">
                                ${this.escapeHtml(log.details)}
                            </div>
                        `;
                    }
                }

                html += '</div>';
            }

            logsContainer.innerHTML = html;
            console.log(`Loaded ${logs.length} logs`);

        } catch (error) {
            console.error('Error loading logs:', error);
            logsContainer.innerHTML = `<p>Error loading logs: ${error.message}</p>`;
        }
    },

    /**
     * Update filter and reload logs
     * @param {string} filterType - 'type' or 'category'
     * @param {string} value - Filter value
     */
    updateFilter(filterType, value) {
        if (filterType === 'type') {
            this.currentFilters.logType = value;
        } else if (filterType === 'category') {
            this.currentFilters.logCategory = value;
        }

        console.log('Filters updated:', this.currentFilters);
        this.loadLogs();
    },

    /**
     * Format log details object for display
     * @param {Object} details - Details object
     * @returns {string} Formatted HTML
     */
    formatDetails(details) {
        if (typeof details !== 'object') {
            return this.escapeHtml(String(details));
        }

        let html = '';
        for (const [key, value] of Object.entries(details)) {
            const formattedValue = typeof value === 'object'
                ? JSON.stringify(value, null, 2)
                : String(value);

            html += `<strong>${this.escapeHtml(key)}:</strong> ${this.escapeHtml(formattedValue)}\n`;
        }
        return html;
    },

    /**
     * Escape HTML special characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Refresh logs with current filters
     */
    refresh() {
        this.loadLogs();
    },

    /**
     * Clear filters and show all logs
     */
    clearFilters() {
        this.currentFilters = {
            logType: '',
            logCategory: '',
            limit: 100
        };

        // Reset select elements
        document.getElementById('log-type-filter').value = '';
        document.getElementById('log-category-filter').value = '';

        this.loadLogs();
    }
};

console.log('Logs component loaded');

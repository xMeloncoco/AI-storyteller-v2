/**
 * Settings Component
 *
 * Handles application settings:
 * - Display preferences
 * - API configuration
 * - System information
 */

const SettingsComponent = {
    // Settings storage
    settings: {
        showRelationships: true,
        showFlags: false,
        apiUrl: 'http://localhost:8000'
    },

    /**
     * Initialize settings component
     * Load saved settings and set up event listeners
     */
    init() {
        // Load saved settings from localStorage
        this.loadSettings();

        // Apply settings to UI
        document.getElementById('setting-show-relationships').checked = this.settings.showRelationships;
        document.getElementById('setting-show-flags').checked = this.settings.showFlags;
        document.getElementById('setting-api-url').value = this.settings.apiUrl;

        // Update API URL in api.js
        setApiUrl(this.settings.apiUrl);

        console.log('Settings component initialized', this.settings);
    },

    /**
     * Load settings from localStorage
     */
    loadSettings() {
        const saved = localStorage.getItem('dreamwalkers_settings');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                this.settings = { ...this.settings, ...parsed };
            } catch (e) {
                console.error('Error loading settings:', e);
            }
        }
    },

    /**
     * Save settings to localStorage
     */
    saveSettings() {
        localStorage.setItem('dreamwalkers_settings', JSON.stringify(this.settings));
        console.log('Settings saved:', this.settings);
    },

    /**
     * Update a specific setting
     * @param {string} key - Setting key
     * @param {any} value - Setting value
     */
    updateSetting(key, value) {
        this.settings[key] = value;
        this.saveSettings();

        // Apply setting immediately
        if (key === 'apiUrl') {
            setApiUrl(value);
        }

        console.log(`Setting updated: ${key} = ${value}`);
    },

    /**
     * Load and display system information
     */
    async loadSystemInfo() {
        const infoContainer = document.getElementById('system-info');

        try {
            // Check backend health
            const health = await checkHealth();
            const apiInfo = await getApiInfo();
            const stats = await getStats();

            let html = `
                <p><strong>Backend Status:</strong> ${health.status}</p>
                <p><strong>Database:</strong> ${health.database}</p>
                <p><strong>AI Provider:</strong> ${health.ai_provider}</p>
                <p><strong>AI Configured:</strong> ${health.ai_configured ? 'Yes' : 'No'}</p>
                <p><strong>Version:</strong> ${health.version}</p>
                <br>
                <p><strong>Statistics:</strong></p>
                <p>Stories: ${stats.stories}</p>
                <p>Playthroughs: ${stats.playthroughs}</p>
                <p>Sessions: ${stats.sessions}</p>
                <p>Conversations: ${stats.conversations}</p>
                <p>Log Entries: ${stats.logs}</p>
            `;

            if (health.ai_warning) {
                html += `<p style="color: #fbbf24;"><strong>Warning:</strong> ${health.ai_warning}</p>`;
            }

            infoContainer.innerHTML = html;

        } catch (error) {
            infoContainer.innerHTML = `
                <p style="color: #ef4444;"><strong>Error connecting to backend:</strong></p>
                <p>${error.message}</p>
                <p>Make sure the backend is running at: ${this.settings.apiUrl}</p>
            `;
        }
    },

    /**
     * Reset settings to defaults
     */
    resetToDefaults() {
        this.settings = {
            showRelationships: true,
            showFlags: false,
            apiUrl: 'http://localhost:8000'
        };

        // Update UI
        document.getElementById('setting-show-relationships').checked = true;
        document.getElementById('setting-show-flags').checked = false;
        document.getElementById('setting-api-url').value = 'http://localhost:8000';

        this.saveSettings();
        setApiUrl(this.settings.apiUrl);

        console.log('Settings reset to defaults');
    },

    /**
     * Load and display available test data
     */
    async loadTestDataList() {
        const listContainer = document.getElementById('test-data-list');

        try {
            const data = await getAvailableTestData();

            if (data.count === 0) {
                listContainer.innerHTML = `<p style="color: #9ca3af;">No test data files found in test_data directory.</p>`;
                return;
            }

            let html = '<div style="font-size: 0.9em;">';
            html += `<p style="margin-bottom: 5px;"><strong>Available stories (${data.count}):</strong></p>`;
            html += '<ul style="margin: 5px 0; padding-left: 20px;">';

            for (const file of data.available) {
                if (file.error) {
                    html += `<li style="color: #ef4444;">${file.filename} - Error: ${file.description}</li>`;
                } else {
                    html += `<li><strong>${file.title}</strong> (${file.filename})<br>`;
                    html += `<span style="color: #9ca3af; font-size: 0.9em;">${file.description}</span></li>`;
                }
            }

            html += '</ul></div>';
            listContainer.innerHTML = html;

        } catch (error) {
            listContainer.innerHTML = `<p style="color: #ef4444;">Error loading test data list: ${error.message}</p>`;
        }
    },

    /**
     * Load all test data
     */
    async loadAllTestData() {
        const statusContainer = document.getElementById('test-data-status');
        const btn = document.getElementById('btn-load-all-testdata');

        btn.disabled = true;
        btn.textContent = 'Loading...';
        statusContainer.innerHTML = '<p style="color: #3b82f6;">Loading test data...</p>';

        try {
            const result = await loadTestData(null, true);

            let html = '<div style="font-size: 0.9em;">';
            html += `<p style="color: #10b981;"><strong>Success!</strong> Loaded ${result.loaded.length} stories</p>`;

            if (result.loaded.length > 0) {
                html += '<ul style="margin: 5px 0; padding-left: 20px;">';
                for (const story of result.loaded) {
                    html += `<li>${story.title} (ID: ${story.story_id})</li>`;
                }
                html += '</ul>';
            }

            if (result.errors.length > 0) {
                html += `<p style="color: #ef4444;">Errors (${result.errors.length}):</p>`;
                html += '<ul style="margin: 5px 0; padding-left: 20px;">';
                for (const error of result.errors) {
                    html += `<li>${error.filename}: ${error.error}</li>`;
                }
                html += '</ul>';
            }

            html += '<p style="margin-top: 10px;">Summary:</p>';
            html += `<ul style="margin: 0; padding-left: 20px;">`;
            html += `<li>Characters: ${result.summary.total_characters}</li>`;
            html += `<li>Relationships: ${result.summary.total_relationships}</li>`;
            html += `<li>Story Arcs: ${result.summary.total_story_arcs}</li>`;
            html += '</ul></div>';

            statusContainer.innerHTML = html;

            // Refresh the test data list
            await this.loadTestDataList();

        } catch (error) {
            statusContainer.innerHTML = `<p style="color: #ef4444;"><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Load All Test Data';
        }
    },

    /**
     * Clear all test data
     */
    async clearAllTestData() {
        if (!confirm('WARNING: This will delete all stories that don\'t have active playthroughs. Are you sure?')) {
            return;
        }

        const statusContainer = document.getElementById('test-data-status');
        const btn = document.getElementById('btn-clear-testdata');

        btn.disabled = true;
        btn.textContent = 'Clearing...';
        statusContainer.innerHTML = '<p style="color: #f59e0b;">Clearing test data...</p>';

        try {
            const result = await clearTestData();

            let html = '<div style="font-size: 0.9em;">';
            html += `<p style="color: #10b981;"><strong>Success!</strong></p>`;
            html += `<p>Deleted ${result.deleted} template stories</p>`;
            html += `<p>Kept ${result.kept} stories with active playthroughs</p>`;
            html += '</div>';

            statusContainer.innerHTML = html;

            // Refresh the test data list
            await this.loadTestDataList();

        } catch (error) {
            statusContainer.innerHTML = `<p style="color: #ef4444;"><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Clear All Templates';
        }
    }
};

console.log('Settings component loaded');

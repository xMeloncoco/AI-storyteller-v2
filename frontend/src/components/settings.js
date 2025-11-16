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
    }
};

console.log('Settings component loaded');

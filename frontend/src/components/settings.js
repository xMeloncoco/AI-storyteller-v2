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

        // Load validation mode from backend and set up change handler
        this.loadValidationMode();
        document.getElementById('setting-validation-mode').addEventListener('change', async (e) => {
            await this.saveValidationMode(e.target.value);
        });

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

    async loadValidationMode() {
        const select = document.getElementById('setting-validation-mode');
        const status = document.getElementById('validation-mode-status');
        try {
            const data = await getValidationMode();
            select.value = data.validation_mode;
            status.textContent = '';
        } catch (e) {
            status.style.color = '#ef4444';
            status.textContent = 'Could not load mode from backend.';
        }
    },

    async saveValidationMode(mode) {
        const status = document.getElementById('validation-mode-status');
        status.style.color = '#9ca3af';
        status.textContent = 'Saving…';
        try {
            await setValidationMode(mode);
            status.style.color = '#10b981';
            status.textContent = `Saved: ${mode}`;
        } catch (e) {
            status.style.color = '#ef4444';
            status.textContent = `Error: ${e.message}`;
        }
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

    _testDataCache: [],

    /**
     * Load available test data files and populate the dropdown.
     */
    async loadTestDataList() {
        const select = document.getElementById('select-testdata-file');
        const desc = document.getElementById('test-data-selected-desc');
        const statusContainer = document.getElementById('test-data-status');

        select.innerHTML = '<option value="">Loading…</option>';
        desc.textContent = '';

        try {
            const data = await getAvailableTestData();
            this._testDataCache = data.available || [];

            if (!this._testDataCache.length) {
                select.innerHTML = '<option value="">No files found</option>';
                desc.textContent = 'No JSON files in backend/test_data/.';
                return;
            }

            select.innerHTML = '';
            for (const file of this._testDataCache) {
                const opt = document.createElement('option');
                opt.value = file.filename;
                opt.textContent = file.error
                    ? `${file.filename} (error)`
                    : file.title;
                select.appendChild(opt);
            }

            this.updateSelectedTestDataDescription();

        } catch (error) {
            select.innerHTML = '<option value="">Error</option>';
            statusContainer.innerHTML = `<p style="color: #ef4444;">Error loading test data list: ${error.message}</p>`;
        }
    },

    updateSelectedTestDataDescription() {
        const select = document.getElementById('select-testdata-file');
        const desc = document.getElementById('test-data-selected-desc');
        const file = this._testDataCache.find(f => f.filename === select.value);

        if (!file) {
            desc.textContent = '';
            return;
        }
        if (file.error) {
            desc.style.color = '#ef4444';
            desc.textContent = `Error parsing ${file.filename}: ${file.description}`;
        } else {
            desc.style.color = '#9ca3af';
            desc.textContent = `${file.filename} — ${file.description}`;
        }
    },

    async loadSelectedTestData() {
        const select = document.getElementById('select-testdata-file');
        const statusContainer = document.getElementById('test-data-status');
        const btn = document.getElementById('btn-load-selected-testdata');
        const filename = select.value;

        if (!filename) {
            statusContainer.innerHTML = `<p style="color: #f59e0b;">No file selected.</p>`;
            return;
        }

        btn.disabled = true;
        btn.textContent = 'Loading…';
        statusContainer.innerHTML = `<p style="color: #3b82f6;">Loading ${filename}…</p>`;

        try {
            const result = await loadTestData(filename, false);

            let html = '<div style="font-size: 0.9em;">';
            if (result.loaded.length) {
                const s = result.loaded[0];
                html += `<p style="color: #10b981;"><strong>Loaded:</strong> ${s.title} (ID: ${s.story_id})</p>`;
            }
            if (result.errors.length) {
                html += `<p style="color: #ef4444;">Errors:</p><ul style="margin: 5px 0; padding-left: 20px;">`;
                for (const err of result.errors) {
                    html += `<li>${err.filename}: ${err.error}</li>`;
                }
                html += '</ul>';
            }
            html += '</div>';
            statusContainer.innerHTML = html;

            if (typeof loadStories === 'function') {
                await loadStories();
            }

        } catch (error) {
            statusContainer.innerHTML = `<p style="color: #ef4444;"><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Load Selected';
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

            // Refresh the stories list if the loadStories function is available
            if (typeof loadStories === 'function') {
                console.log('Refreshing stories list after loading test data...');
                await loadStories();
            }

        } catch (error) {
            statusContainer.innerHTML = `<p style="color: #ef4444;"><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Load All Test Data';
        }
    },

    /**
     * Delete stories that have no playthroughs (kept for backward compatibility).
     */
    async clearAllTestData() {
        if (!confirm('Delete all stories that have no playthroughs?\n\nStories with active playthroughs will be kept.')) {
            return;
        }

        const statusContainer = document.getElementById('test-data-status');
        const btn = document.getElementById('btn-clear-testdata');

        btn.disabled = true;
        btn.textContent = 'Deleting…';
        statusContainer.innerHTML = '<p style="color: #f59e0b;">Deleting unused templates…</p>';

        try {
            const result = await clearTestData();

            statusContainer.innerHTML =
                `<div style="font-size: 0.9em;">
                    <p style="color: #10b981;"><strong>Done.</strong></p>
                    <p>Deleted ${result.deleted} unused story templates</p>
                    <p>Kept ${result.kept} stories with active playthroughs</p>
                </div>`;

            await this.loadTestDataList();
            if (typeof loadStories === 'function') await loadStories();

        } catch (error) {
            statusContainer.innerHTML = `<p style="color: #ef4444;"><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Delete Unused Templates';
        }
    },

    /**
     * Delete every playthrough (sessions, conversations, scene state, flags,
     * playthrough-scoped entities). Stories and templates remain.
     */
    async deleteAllPlaythroughs() {
        if (!confirm('Delete ALL playthroughs?\n\nThis removes every playthrough, its sessions, conversations, scene state, and flags.\n\nStories themselves are kept. This cannot be undone.')) {
            return;
        }

        const statusContainer = document.getElementById('test-data-status');
        const btn = document.getElementById('btn-delete-playthroughs');

        btn.disabled = true;
        btn.textContent = 'Deleting…';
        statusContainer.innerHTML = '<p style="color: #f59e0b;">Deleting playthroughs…</p>';

        try {
            const result = await deleteAllPlaythroughs();

            statusContainer.innerHTML =
                `<div style="font-size: 0.9em;">
                    <p style="color: #10b981;"><strong>Done.</strong></p>
                    <p>Deleted ${result.deleted_playthroughs} playthroughs</p>
                </div>`;

            if (typeof loadStories === 'function') await loadStories();

        } catch (error) {
            statusContainer.innerHTML = `<p style="color: #ef4444;"><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Delete All Playthroughs';
        }
    },

    /**
     * Nuke everything: every story AND every playthrough.
     */
    async deleteAllStoriesAndPlaythroughs() {
        if (!confirm('Delete ALL stories AND playthroughs?\n\nThis is a full wipe of all game data: stories, characters, relationships, locations, story arcs, playthroughs, sessions, conversations.\n\nThis cannot be undone.')) {
            return;
        }
        if (!confirm('Are you absolutely sure? This deletes EVERYTHING.')) {
            return;
        }

        const statusContainer = document.getElementById('test-data-status');
        const btn = document.getElementById('btn-delete-everything');

        btn.disabled = true;
        btn.textContent = 'Deleting…';
        statusContainer.innerHTML = '<p style="color: #f59e0b;">Wiping all game data…</p>';

        try {
            const result = await deleteAllStoriesAndPlaythroughs();

            statusContainer.innerHTML =
                `<div style="font-size: 0.9em;">
                    <p style="color: #10b981;"><strong>Done.</strong></p>
                    <p>Deleted ${result.deleted_stories} stories and ${result.deleted_playthroughs} playthroughs</p>
                </div>`;

            await this.loadTestDataList();
            if (typeof loadStories === 'function') await loadStories();

        } catch (error) {
            statusContainer.innerHTML = `<p style="color: #ef4444;"><strong>Error:</strong> ${error.message}</p>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Delete All Stories & Playthroughs';
        }
    }
};

console.log('Settings component loaded');

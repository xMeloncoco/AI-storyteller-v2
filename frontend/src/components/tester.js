/**
 * Tester Component
 *
 * Handles testing and debugging features:
 * - Database viewer (characters, relationships, locations, arcs, flags)
 * - Context window viewer
 * - Playthrough reset
 * - Grouped logs
 */

const TesterComponent = {
    // Current state
    currentPlaythrough: null,
    currentSession: null,
    currentView: 'characters', // Current active view

    /**
     * Initialize tester component
     * @param {number} playthroughId - Playthrough ID
     * @param {number} sessionId - Optional session ID
     */
    async init(playthroughId, sessionId = null) {
        this.currentPlaythrough = playthroughId;
        this.currentSession = sessionId;
        this.currentView = 'characters';

        console.log('Tester component initialized', {
            playthroughId,
            sessionId
        });

        await this.loadPlaythroughData();
        this.showView('characters');
    },

    /**
     * Load playthrough data
     */
    async loadPlaythroughData() {
        try {
            const data = await getPlaythroughData(this.currentPlaythrough);

            // Update playthrough info
            document.getElementById('tester-playthrough-info').innerHTML = `
                <h4>${data.playthrough.name}</h4>
                <p>Story: ${data.playthrough.story_title}</p>
                <p>Location: ${data.playthrough.current_location || 'Unknown'}</p>
                <p>Time: ${data.playthrough.current_time || 'Unknown'}</p>
            `;

            // Store data for navigation
            this.playthroughData = data;

        } catch (error) {
            const errorMsg = error.message || error.toString() || 'Unknown error occurred';
            console.error('Error loading playthrough data:', error);
            const container = document.getElementById('tester-view-container');
            container.innerHTML = `<p style="color: #ef4444;">Error loading playthrough data: ${errorMsg}</p>`;
        }
    },

    /**
     * Show specific view
     * @param {string} viewType - Type of view to show
     */
    async showView(viewType) {
        this.currentView = viewType;
        const container = document.getElementById('tester-view-container');

        // Update button states
        document.querySelectorAll('.tester-nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.getElementById(`btn-tester-${viewType}`)?.classList.add('active');

        // Handle different views
        switch (viewType) {
            case 'prompt':
                await this.loadPromptView();
                break;
            case 'logs':
                await this.loadLogsView();
                break;
            case 'dbchanges':
                await this.loadDbChangesView();
                break;
            case 'characters':
            case 'relationships':
            case 'locations':
            case 'arcs':
            case 'flags':
            case 'scene':
                this.showDatabaseView(viewType);
                break;
        }
    },

    /**
     * Show database view
     * @param {string} viewType - Type of data to show
     */
    showDatabaseView(viewType) {
        const container = document.getElementById('tester-view-container');
        const data = this.playthroughData;

        // Check if data is loaded
        if (!data) {
            container.innerHTML = '<p style="color: #fbbf24;">Playthrough data not loaded. Please reload the tester.</p>';
            return;
        }

        switch (viewType) {
            case 'characters':
                this.displayCharacters(data.characters);
                break;
            case 'relationships':
                this.displayRelationships(data.relationships);
                break;
            case 'locations':
                this.displayLocations(data.locations);
                break;
            case 'arcs':
                this.displayStoryArcs(data.story_arcs);
                break;
            case 'flags':
                this.displayFlags(data.story_flags, data.memory_flags);
                break;
            case 'scene':
                this.displayCurrentScene(data.current_scene);
                break;
        }
    },

    /**
     * Display characters
     */
    displayCharacters(characters) {
        const container = document.getElementById('tester-view-container');

        if (characters.length === 0) {
            container.innerHTML = '<p style="color: #9ca3af;">No characters found.</p>';
            return;
        }

        let html = '<div class="tester-data-grid">';

        for (const char of characters) {
            html += `
                <div class="tester-data-card">
                    <h4>${char.name} <span class="char-type">(${char.type})</span></h4>
                    <p><strong>Age:</strong> ${char.age || 'Unknown'}</p>
                    ${char.appearance ? `<p><strong>Appearance:</strong> ${char.appearance}</p>` : ''}
                    ${char.backstory ? `<p><strong>Backstory:</strong> ${char.backstory}</p>` : ''}
                    ${char.personality_traits ? `<p><strong>Traits:</strong> ${char.personality_traits}</p>` : ''}
                    ${char.speech_patterns ? `<p><strong>Speech:</strong> ${char.speech_patterns}</p>` : ''}

                    ${char.core_values ? `<p><strong>Core Values:</strong> ${char.core_values}</p>` : ''}
                    ${char.core_fears ? `<p><strong>Core Fears:</strong> ${char.core_fears}</p>` : ''}
                    ${char.decision_style ? `<p><strong>Decision Style:</strong> ${char.decision_style}</p>` : ''}
                    ${char.internal_contradiction ? `<p><strong>Internal Contradiction:</strong> ${char.internal_contradiction}</p>` : ''}
                    ${char.secret_kept ? `<p><strong>Secret:</strong> ${char.secret_kept}</p>` : ''}
                    ${char.vulnerability ? `<p><strong>Vulnerability:</strong> ${char.vulnerability}</p>` : ''}
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * Display relationships
     */
    displayRelationships(relationships) {
        const container = document.getElementById('tester-view-container');

        if (relationships.length === 0) {
            container.innerHTML = '<p style="color: #9ca3af;">No relationships found.</p>';
            return;
        }

        let html = '<div class="tester-data-grid">';

        for (const rel of relationships) {
            html += `
                <div class="tester-data-card">
                    <h4>${rel.character1} ↔ ${rel.character2}</h4>
                    <p><strong>Type:</strong> ${rel.type}</p>
                    <div class="relationship-metrics">
                        <span>Trust: ${(rel.trust * 100).toFixed(0)}%</span>
                        <span>Affection: ${(rel.affection * 100).toFixed(0)}%</span>
                        <span>Familiarity: ${(rel.familiarity * 100).toFixed(0)}%</span>
                    </div>
                    ${rel.closeness ? `<p><strong>Closeness:</strong> ${(rel.closeness * 100).toFixed(0)}%</p>` : ''}
                    ${rel.importance ? `<p><strong>Importance:</strong> ${rel.importance}/10</p>` : ''}
                    ${rel.first_meeting ? `<p><strong>First Meeting:</strong> ${rel.first_meeting}</p>` : ''}
                    ${rel.history ? `<p><strong>History:</strong> ${rel.history}</p>` : ''}
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * Display locations
     */
    displayLocations(locations) {
        const container = document.getElementById('tester-view-container');

        if (locations.length === 0) {
            container.innerHTML = '<p style="color: #9ca3af;">No locations found.</p>';
            return;
        }

        let html = '<div class="tester-data-grid">';

        for (const loc of locations) {
            html += `
                <div class="tester-data-card">
                    <h4>${loc.name}</h4>
                    <p><strong>Type:</strong> ${loc.type} | <strong>Scope:</strong> ${loc.scope}</p>
                    ${loc.description ? `<p>${loc.description}</p>` : ''}
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * Display story arcs
     */
    displayStoryArcs(arcs) {
        const container = document.getElementById('tester-view-container');

        if (arcs.length === 0) {
            container.innerHTML = '<p style="color: #9ca3af;">No story arcs found.</p>';
            return;
        }

        let html = '<div class="tester-data-grid">';

        for (const arc of arcs) {
            const status = arc.is_completed ? 'Completed' : (arc.is_active ? 'Active' : 'Inactive');
            const statusColor = arc.is_completed ? '#10b981' : (arc.is_active ? '#3b82f6' : '#6b7280');

            html += `
                <div class="tester-data-card">
                    <h4>${arc.name} <span style="color: ${statusColor};">(${status})</span></h4>
                    <p><strong>Order:</strong> ${arc.order}</p>
                    ${arc.description ? `<p>${arc.description}</p>` : ''}
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * Display flags
     */
    displayFlags(storyFlags, memoryFlags) {
        const container = document.getElementById('tester-view-container');

        let html = '<div class="tester-flags-container">';

        // Story flags
        html += '<div class="tester-flags-section"><h4>Story Flags</h4>';
        if (storyFlags.length === 0) {
            html += '<p style="color: #9ca3af;">No story flags set.</p>';
        } else {
            html += '<ul class="tester-flags-list">';
            for (const flag of storyFlags) {
                html += `<li><strong>${flag.flag_name}:</strong> ${flag.flag_value}</li>`;
            }
            html += '</ul>';
        }
        html += '</div>';

        // Memory flags
        html += '<div class="tester-flags-section"><h4>Memory Flags</h4>';
        if (memoryFlags.length === 0) {
            html += '<p style="color: #9ca3af;">No memory flags set.</p>';
        } else {
            html += '<ul class="tester-flags-list">';
            for (const flag of memoryFlags) {
                html += `<li><strong>${flag.flag_type}:</strong> ${flag.flag_value || 'N/A'}`;
                if (flag.importance) html += `<br><span style="color: #9ca3af; font-size: 0.9em;">Importance: ${flag.importance}/10</span>`;
                html += `</li>`;
            }
            html += '</ul>';
        }
        html += '</div>';

        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * Display scene state (location, time, characters present, etc.)
     */
    displayCurrentScene(scene) {
        const container = document.getElementById('tester-view-container');

        if (!scene) {
            container.innerHTML = '<p style="color: #9ca3af;">No scene state available.</p>';
            return;
        }

        let html = '<div class="tester-scene-container">';
        html += `<h4>Scene State</h4>`;
        html += `<p><strong>Location:</strong> ${scene.location || 'Unknown'}</p>`;
        html += `<p><strong>Time:</strong> ${scene.time_of_day || 'Unknown'}</p>`;
        if (scene.weather) html += `<p><strong>Weather:</strong> ${scene.weather}</p>`;
        if (scene.emotional_tone) html += `<p><strong>Mood:</strong> ${scene.emotional_tone}</p>`;
        if (scene.scene_context) html += `<p><strong>Context:</strong> ${scene.scene_context}</p>`;

        // Display characters present
        if (scene.characters_present && scene.characters_present.length > 0) {
            html += `<p><strong>Characters Present:</strong></p><ul>`;
            for (const char of scene.characters_present) {
                html += `<li>${char.character_name} (${char.character_type})`;
                if (char.mood) html += ` - Mood: ${char.mood}`;
                if (char.intent) html += ` - Intent: ${char.intent}`;
                html += `</li>`;
            }
            html += `</ul>`;
        }

        html += '</div>';

        container.innerHTML = html;
    },

    /**
     * Load prompt window view - shows exactly what the LLM would see.
     */
    async loadPromptView() {
        const container = document.getElementById('tester-view-container');

        if (!this.currentSession) {
            container.innerHTML = `
                <p style="color: #fbbf24;">No active session. Start a chat to see the prompt.</p>
            `;
            return;
        }

        container.innerHTML = '<p>Loading prompt...</p>';

        try {
            const data = await getPromptWindow(this.currentSession);

            let html = '<div class="tester-context-container">';
            html += `<h4>AI Prompt (${data.prompt_length} characters)</h4>`;
            html += `<pre class="context-display">${data.full_prompt}</pre>`;
            html += '</div>';

            container.innerHTML = html;

        } catch (error) {
            const errorMsg = error.message || error.toString() || 'Unknown error occurred';
            console.error('Error loading prompt:', error);
            container.innerHTML = `<p style="color: #ef4444;">Error loading prompt: ${errorMsg}</p>`;
        }
    },

    /**
     * Load logs view
     */
    async loadLogsView() {
        const container = document.getElementById('tester-view-container');

        if (!this.currentSession) {
            container.innerHTML = `
                <p style="color: #fbbf24;">No active session. Start a chat to see logs.</p>
            `;
            return;
        }

        container.innerHTML = '<p>Loading logs...</p>';

        try {
            const data = await getGroupedLogs(this.currentSession);

            // Pre-decode the JSON `details` string once per log so we can read
            // the `stage` field for filtering without re-parsing on every render.
            const stagesPresent = new Set();
            if (data.grouped_logs) {
                for (const group of data.grouped_logs) {
                    if (!group.logs) continue;
                    for (const log of group.logs) {
                        log._parsedDetails = this.parseLogDetails(log.details);
                        const stage = log._parsedDetails && log._parsedDetails.stage;
                        if (stage) stagesPresent.add(stage);
                    }
                }
            }
            this._logsData = data;
            this._stagesPresent = Array.from(stagesPresent).sort();
            this._activeStageFilter = this._activeStageFilter || '';

            this.renderLogsView();

        } catch (error) {
            const errorMsg = error.message || error.toString() || 'Unknown error occurred';
            console.error('Error loading logs:', error);
            container.innerHTML = `<p style="color: #ef4444;">Error loading logs: ${errorMsg}</p>`;
        }
    },

    /**
     * Render the logs view using whatever filter is currently active.
     * Split out from loadLogsView so the stage dropdown can re-render without
     * a network call.
     */
    renderLogsView() {
        const container = document.getElementById('tester-view-container');
        const data = this._logsData;
        if (!data) return;

        const stageOptions = [
            `<option value="">All stages</option>`,
            ...this._stagesPresent.map(s =>
                `<option value="${s}" ${s === this._activeStageFilter ? 'selected' : ''}>${s}</option>`
            )
        ].join('');

        let html = '<div class="tester-logs-container">';
        html += `<div class="tester-logs-header">`;
        html += `<h4>Session Logs (${data.total_logs} entries)</h4>`;
        html += `<label style="margin-left: 16px;">Stage: `;
        html += `<select id="tester-log-stage-filter">${stageOptions}</select></label>`;
        html += `<button id="btn-export-logs" class="secondary-btn">Export Logs</button>`;
        html += `</div>`;

        if (data.grouped_logs && data.grouped_logs.length > 0) {
            for (const group of data.grouped_logs) {
                const visibleLogs = (group.logs || []).filter(log =>
                    !this._activeStageFilter ||
                    (log._parsedDetails && log._parsedDetails.stage === this._activeStageFilter)
                );

                // Skip groups with no visible logs when a stage filter is active
                // so the user only sees turns that contain matching entries.
                if (this._activeStageFilter && visibleLogs.length === 0) continue;

                html += `<div class="log-group">`;
                html += `<div class="log-group-header">`;
                html += `<strong>User:</strong> ${group.user_message.substring(0, 100)}${group.user_message.length > 100 ? '...' : ''}`;
                html += `</div>`;

                if (visibleLogs.length > 0) {
                    html += `<div class="log-entries">`;
                    for (const log of visibleLogs) {
                        const categoryColor = this.getLogCategoryColor(log.category);
                        const stage = log._parsedDetails && log._parsedDetails.stage;
                        html += `<div class="log-entry">`;
                        html += `<span class="log-category" style="background-color: ${categoryColor};">${log.category}</span>`;
                        html += `<span class="log-type">${log.type}</span>`;
                        html += `<span class="log-message">`;
                        if (stage) {
                            html += `<span class="log-stage">[STAGE:${stage}]</span>`;
                        }
                        html += `${log.message}</span>`;
                        if (log.details) {
                            const detailsText = log._parsedDetails
                                ? JSON.stringify(log._parsedDetails, null, 2)
                                : log.details;
                            html += `<pre class="log-details">${detailsText}</pre>`;
                        }
                        html += `</div>`;
                    }
                    html += `</div>`;
                }
                html += `</div>`;
            }
        } else {
            html += '<p style="color: #9ca3af;">No logs found for this session.</p>';
        }

        html += '</div>';
        container.innerHTML = html;

        document.getElementById('btn-export-logs')?.addEventListener('click', () => this.exportLogs(data));
        document.getElementById('tester-log-stage-filter')?.addEventListener('change', (e) => {
            this._activeStageFilter = e.target.value;
            this.renderLogsView();
        });
    },

    /**
     * Load the "DB Changes" view - shows only the database edits made on each
     * turn. Reuses the grouped-logs endpoint and filters to edit-type entries,
     * so the user can see exactly what the turn wrote to the database.
     */
    async loadDbChangesView() {
        const container = document.getElementById('tester-view-container');

        if (!this.currentSession) {
            container.innerHTML = `
                <p style="color: #fbbf24;">No active session. Start a chat to see database changes.</p>
            `;
            return;
        }

        container.innerHTML = '<p>Loading database changes...</p>';

        try {
            const data = await getGroupedLogs(this.currentSession);

            let html = '<div class="tester-logs-container">';
            html += `<h4>Database Changes by Turn</h4>`;

            let totalEdits = 0;

            if (data.grouped_logs && data.grouped_logs.length > 0) {
                for (const group of data.grouped_logs) {
                    const edits = (group.logs || []).filter(log => log.type === 'edit');
                    if (edits.length === 0) continue;
                    totalEdits += edits.length;

                    html += `<div class="log-group">`;
                    html += `<div class="log-group-header">`;
                    html += `<strong>User:</strong> ${group.user_message.substring(0, 100)}${group.user_message.length > 100 ? '...' : ''}`;
                    html += ` <span style="color: #9ca3af;">(${edits.length} change${edits.length === 1 ? '' : 's'})</span>`;
                    html += `</div>`;

                    html += `<div class="log-entries">`;
                    for (const log of edits) {
                        const categoryColor = this.getLogCategoryColor(log.category);
                        const parsed = this.parseLogDetails(log.details);
                        html += `<div class="log-entry">`;
                        html += `<span class="log-category" style="background-color: ${categoryColor};">${log.category}</span>`;
                        html += `<span class="log-message">${log.message}</span>`;
                        if (log.details) {
                            const detailsText = parsed
                                ? JSON.stringify(parsed, null, 2)
                                : log.details;
                            html += `<pre class="log-details">${detailsText}</pre>`;
                        }
                        html += `</div>`;
                    }
                    html += `</div>`;
                    html += `</div>`;
                }
            }

            if (totalEdits === 0) {
                html += '<p style="color: #9ca3af;">No database changes recorded for this session yet.</p>';
            }

            html += '</div>';
            container.innerHTML = html;

        } catch (error) {
            const errorMsg = error.message || error.toString() || 'Unknown error occurred';
            console.error('Error loading database changes:', error);
            container.innerHTML = `<p style="color: #ef4444;">Error loading database changes: ${errorMsg}</p>`;
        }
    },

    /**
     * The backend ships log.details as a JSON string (or null). Return the
     * decoded object, or null if it isn't JSON / wasn't present.
     */
    parseLogDetails(raw) {
        if (raw == null) return null;
        if (typeof raw === 'object') return raw;
        try {
            return JSON.parse(raw);
        } catch (e) {
            return null;
        }
    },

    /**
     * Get color for log category
     */
    getLogCategoryColor(category) {
        const colors = {
            'system': '#6b7280',
            'ai': '#3b82f6',
            'character': '#10b981',
            'story': '#8b5cf6',
            'memory': '#f59e0b',
            'database': '#ef4444',
            'validation': '#ec4899'
        };
        return colors[category] || '#6b7280';
    },

    /**
     * Export logs to JSON file
     */
    exportLogs(data) {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `session-${this.currentSession}-logs-${new Date().toISOString()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    /**
     * Reset current playthrough
     */
    async resetCurrentPlaythrough() {
        if (!confirm('WARNING: This will reset the playthrough to its initial state. All progress will be lost. Are you sure?')) {
            return;
        }

        const statusContainer = document.getElementById('tester-reset-status');
        statusContainer.innerHTML = '<p style="color: #f59e0b;">Resetting playthrough...</p>';

        try {
            const result = await resetPlaythrough(this.currentPlaythrough);

            statusContainer.innerHTML = `<p style="color: #10b981;">${result.message}</p>`;

            // Reload playthrough data
            await this.loadPlaythroughData();
            await this.showView(this.currentView);

            // Refresh the main app view
            setTimeout(() => {
                statusContainer.innerHTML = '';
            }, 5000);

        } catch (error) {
            const errorMsg = error.message || error.toString() || 'Unknown error occurred';
            console.error('Error resetting playthrough:', error);
            statusContainer.innerHTML = `<p style="color: #ef4444;">Error: ${errorMsg}</p>`;
        }
    },

    /**
     * Export the current playthrough as a JSON fixture into backend/test_data/.
     */
    async exportCurrentPlaythrough() {
        if (!this.currentPlaythrough) return;

        const btn = document.getElementById('btn-tester-export');
        const statusContainer = document.getElementById('tester-export-status');

        btn.disabled = true;
        const originalLabel = btn.textContent;
        btn.textContent = 'Exporting…';
        statusContainer.innerHTML = `<span style="color: #3b82f6;">Exporting playthrough…</span>`;

        try {
            const result = await exportPlaythrough(this.currentPlaythrough);

            const s = result.summary || {};
            statusContainer.innerHTML =
                `<div style="color: #10b981;"><strong>Saved:</strong> ${result.filename}</div>` +
                `<div style="color: #9ca3af;">${s.sessions ?? 0} session(s), ` +
                `${s.conversations ?? 0} message(s), ` +
                `${s.playthrough_characters ?? 0} character instance(s)</div>`;

        } catch (error) {
            const errorMsg = error.message || error.toString() || 'Unknown error occurred';
            console.error('Error exporting playthrough:', error);
            statusContainer.innerHTML = `<span style="color: #ef4444;">Error: ${errorMsg}</span>`;
        } finally {
            btn.disabled = false;
            btn.textContent = originalLabel;
        }
    }
};

console.log('Tester component loaded');

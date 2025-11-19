/**
 * Dreamwalkers - Main Renderer Process
 *
 * This is the main entry point for the frontend logic.
 * Coordinates all components and manages application state.
 */

// =============================================================================
// Application State
// =============================================================================

const AppState = {
    currentStory: null,
    currentPlaythrough: null,
    currentSession: null,
    isConnected: false
};

// =============================================================================
// Screen Management
// =============================================================================

/**
 * Show a specific screen
 * @param {string} screenId - ID of screen to show (without 'screen-' prefix)
 */
function showScreen(screenId) {
    // Hide all screens
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });

    // Show requested screen
    const screen = document.getElementById(`screen-${screenId}`);
    if (screen) {
        screen.classList.add('active');
        console.log(`Showing screen: ${screenId}`);
    } else {
        console.error(`Screen not found: ${screenId}`);
    }
}

// =============================================================================
// Story Management
// =============================================================================

/**
 * Load and display all available stories
 */
async function loadStories() {
    const storiesList = document.getElementById('stories-list');
    storiesList.innerHTML = '<p class="loading">Loading stories...</p>';

    try {
        const stories = await getStories();

        if (stories.length === 0) {
            storiesList.innerHTML = `
                <p>No stories found. Please import test data first.</p>
                <p style="color: #9ca3af; margin-top: 10px;">
                    Run in backend folder:<br>
                    <code>python test_data/import_test_data.py --story both</code>
                </p>
            `;
            return;
        }

        let html = '';
        for (const story of stories) {
            html += `
                <div class="story-card" data-story-id="${story.id}">
                    <h3>${story.title}</h3>
                    <p>${story.description || 'No description available.'}</p>
                </div>
            `;
        }

        storiesList.innerHTML = html;

        // Add click handlers
        document.querySelectorAll('.story-card').forEach(card => {
            card.addEventListener('click', () => {
                const storyId = parseInt(card.dataset.storyId);
                selectStory(storyId);
            });
        });

        console.log(`Loaded ${stories.length} stories`);

    } catch (error) {
        console.error('Error loading stories:', error);
        storiesList.innerHTML = `
            <p style="color: #ef4444;">Error loading stories: ${error.message}</p>
            <p style="color: #9ca3af;">Make sure the backend is running.</p>
        `;
    }
}

/**
 * Select a story and show its playthroughs
 * @param {number} storyId - Story ID
 */
async function selectStory(storyId) {
    try {
        // Get story details
        const story = await getStory(storyId);
        AppState.currentStory = story;

        // Update UI
        document.getElementById('selected-story-title').textContent = story.title;

        // Load playthroughs
        await loadPlaythroughs(storyId);

        // Show playthroughs screen
        showScreen('playthroughs');

    } catch (error) {
        console.error('Error selecting story:', error);
        alert(`Error: ${error.message}`);
    }
}

/**
 * Load playthroughs for a story
 * @param {number} storyId - Story ID
 */
async function loadPlaythroughs(storyId) {
    const playthroughsList = document.getElementById('playthroughs-list');
    playthroughsList.innerHTML = '<p class="loading">Loading playthroughs...</p>';

    try {
        const playthroughs = await getPlaythroughs(storyId);

        if (playthroughs.length === 0) {
            playthroughsList.innerHTML = '<p>No saved playthroughs. Start a new one!</p>';
            return;
        }

        let html = '';
        for (const pt of playthroughs) {
            const lastPlayed = new Date(pt.last_played).toLocaleString();
            html += `
                <div class="playthrough-item" data-playthrough-id="${pt.id}">
                    <div>
                        <h4>${pt.playthrough_name}</h4>
                        <span class="last-played">Last played: ${lastPlayed}</span>
                    </div>
                    <button class="secondary-btn">Continue</button>
                </div>
            `;
        }

        playthroughsList.innerHTML = html;

        // Add click handlers
        document.querySelectorAll('.playthrough-item').forEach(item => {
            item.addEventListener('click', () => {
                const playthroughId = parseInt(item.dataset.playthroughId);
                loadPlaythrough(playthroughId);
            });
        });

        console.log(`Loaded ${playthroughs.length} playthroughs`);

    } catch (error) {
        console.error('Error loading playthroughs:', error);
        playthroughsList.innerHTML = `<p style="color: #ef4444;">Error: ${error.message}</p>`;
    }
}

/**
 * Load a playthrough and start/continue the story
 * @param {number} playthroughId - Playthrough ID
 */
async function loadPlaythrough(playthroughId) {
    try {
        // Get playthrough details
        const playthrough = await getPlaythrough(playthroughId);
        AppState.currentPlaythrough = playthrough;

        // Get or create session
        let session;
        try {
            session = await getLatestSession(playthroughId);
        } catch (e) {
            // No session exists, create one
            session = await createSession(playthroughId);
        }
        AppState.currentSession = session;

        // Get conversation history
        const history = await getChatHistory(session.id);

        // Initialize chat component
        await ChatComponent.init(playthrough, session, history);

        // Show chat screen
        showScreen('chat');

        console.log('Playthrough loaded', {
            playthrough: playthroughId,
            session: session.id
        });

    } catch (error) {
        console.error('Error loading playthrough:', error);
        alert(`Error: ${error.message}`);
    }
}

/**
 * Create a new playthrough for the current story
 */
async function createNewPlaythrough() {
    const nameInput = document.getElementById('new-playthrough-name');
    const name = nameInput.value.trim();

    if (!name) {
        alert('Please enter a name for your playthrough.');
        return;
    }

    if (!AppState.currentStory) {
        alert('No story selected.');
        return;
    }

    try {
        // Create playthrough
        const playthrough = await createPlaythrough(AppState.currentStory.id, name);

        // Close modal
        document.getElementById('modal-new-playthrough').classList.remove('active');
        nameInput.value = '';

        // Load the new playthrough
        await loadPlaythrough(playthrough.id);

    } catch (error) {
        console.error('Error creating playthrough:', error);
        alert(`Error: ${error.message}`);
    }
}

// =============================================================================
// Connection Management
// =============================================================================

/**
 * Check backend connection
 */
async function checkConnection() {
    const statusIndicator = document.getElementById('connection-status');

    try {
        const health = await checkHealth();

        if (health.status === 'healthy') {
            statusIndicator.textContent = 'Connected';
            statusIndicator.className = 'status-indicator connected';
            AppState.isConnected = true;
        } else {
            statusIndicator.textContent = 'Degraded';
            statusIndicator.className = 'status-indicator';
            AppState.isConnected = true;
        }

    } catch (error) {
        statusIndicator.textContent = 'Disconnected';
        statusIndicator.className = 'status-indicator disconnected';
        AppState.isConnected = false;
    }
}

// =============================================================================
// Event Listeners
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Dreamwalkers renderer initializing...');

    // Initialize components
    SettingsComponent.init();
    LogsComponent.init();

    // Check connection
    checkConnection();

    // Load stories
    loadStories();

    // Set up periodic connection check
    setInterval(checkConnection, 30000); // Every 30 seconds

    // Header buttons
    document.getElementById('btn-logs').addEventListener('click', () => {
        showScreen('logs');
        LogsComponent.loadLogs();
    });

    document.getElementById('btn-settings').addEventListener('click', () => {
        showScreen('settings');
        SettingsComponent.loadSystemInfo();
        SettingsComponent.loadTestDataList();
    });

    document.getElementById('btn-tester').addEventListener('click', () => {
        // Need an active playthrough to use tester
        if (AppState.currentPlaythrough) {
            showScreen('tester');
            TesterComponent.init(AppState.currentPlaythrough.id, AppState.currentSession?.id);
        } else {
            alert('Please select a playthrough first before using the Tester.');
        }
    });

    // Story screen
    document.getElementById('btn-back-to-stories').addEventListener('click', () => {
        showScreen('stories');
    });

    document.getElementById('btn-new-playthrough').addEventListener('click', () => {
        document.getElementById('modal-new-playthrough').classList.add('active');
    });

    // Chat screen
    document.getElementById('btn-back-to-playthroughs').addEventListener('click', () => {
        showScreen('playthroughs');
    });

    document.getElementById('btn-send').addEventListener('click', () => {
        ChatComponent.sendMessage();
    });

    document.getElementById('btn-generate-more').addEventListener('click', () => {
        ChatComponent.generateMore();
    });

    document.getElementById('btn-show-characters').addEventListener('click', () => {
        ChatComponent.showCharacters();
    });

    // Handle Enter key in chat input (Shift+Enter for newline)
    document.getElementById('user-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            ChatComponent.sendMessage();
        }
    });

    // Logs screen
    document.getElementById('btn-close-logs').addEventListener('click', () => {
        // Go back to previous screen (chat if in session, otherwise stories)
        if (AppState.currentSession) {
            showScreen('chat');
        } else {
            showScreen('stories');
        }
    });

    document.getElementById('btn-refresh-logs').addEventListener('click', () => {
        LogsComponent.refresh();
    });

    document.getElementById('log-type-filter').addEventListener('change', (e) => {
        LogsComponent.updateFilter('type', e.target.value);
    });

    document.getElementById('log-category-filter').addEventListener('change', (e) => {
        LogsComponent.updateFilter('category', e.target.value);
    });

    // Settings screen
    document.getElementById('btn-close-settings').addEventListener('click', () => {
        if (AppState.currentSession) {
            showScreen('chat');
        } else {
            showScreen('stories');
        }
    });

    document.getElementById('setting-show-relationships').addEventListener('change', (e) => {
        SettingsComponent.updateSetting('showRelationships', e.target.checked);
    });

    document.getElementById('setting-show-flags').addEventListener('change', (e) => {
        SettingsComponent.updateSetting('showFlags', e.target.checked);
    });

    document.getElementById('setting-api-url').addEventListener('change', (e) => {
        SettingsComponent.updateSetting('apiUrl', e.target.value);
        checkConnection();
    });

    // Test Data Management
    document.getElementById('btn-load-all-testdata').addEventListener('click', () => {
        SettingsComponent.loadAllTestData();
    });

    document.getElementById('btn-refresh-testdata').addEventListener('click', () => {
        SettingsComponent.loadTestDataList();
    });

    document.getElementById('btn-clear-testdata').addEventListener('click', () => {
        SettingsComponent.clearAllTestData();
    });

    // Tester screen
    document.getElementById('btn-close-tester').addEventListener('click', () => {
        if (AppState.currentSession) {
            showScreen('chat');
        } else {
            showScreen('playthroughs');
        }
    });

    // Tester view switching
    document.getElementById('btn-tester-view-database').addEventListener('click', () => {
        TesterComponent.switchView('database');
    });

    document.getElementById('btn-tester-view-context').addEventListener('click', () => {
        TesterComponent.switchView('context');
    });

    // Tester database navigation
    document.getElementById('btn-tester-characters').addEventListener('click', () => {
        TesterComponent.showDataView('characters');
    });

    document.getElementById('btn-tester-relationships').addEventListener('click', () => {
        TesterComponent.showDataView('relationships');
    });

    document.getElementById('btn-tester-locations').addEventListener('click', () => {
        TesterComponent.showDataView('locations');
    });

    document.getElementById('btn-tester-arcs').addEventListener('click', () => {
        TesterComponent.showDataView('arcs');
    });

    document.getElementById('btn-tester-flags').addEventListener('click', () => {
        TesterComponent.showDataView('flags');
    });

    document.getElementById('btn-tester-scene').addEventListener('click', () => {
        TesterComponent.showDataView('scene');
    });

    // Tester reset button
    document.getElementById('btn-tester-reset').addEventListener('click', () => {
        TesterComponent.resetCurrentPlaythrough();
    });

    // Modals
    document.getElementById('btn-close-characters').addEventListener('click', () => {
        document.getElementById('modal-characters').classList.remove('active');
    });

    document.getElementById('btn-close-new-playthrough').addEventListener('click', () => {
        document.getElementById('modal-new-playthrough').classList.remove('active');
    });

    document.getElementById('btn-create-playthrough').addEventListener('click', () => {
        createNewPlaythrough();
    });

    // Close modals when clicking outside
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    console.log('Dreamwalkers renderer initialized');
    document.getElementById('footer-status').textContent = 'Ready';
});

console.log('Renderer script loaded');

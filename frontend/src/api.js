/**
 * Dreamwalkers - API Client
 *
 * Handles all communication with the backend API.
 * All API calls are centralized here for easy management and logging.
 */

// API Configuration
const API_CONFIG = {
    baseUrl: 'http://localhost:8000',
    timeout: 60000 // 60 seconds for AI responses
};

/**
 * Update the API base URL
 * @param {string} url - New base URL
 */
function setApiUrl(url) {
    API_CONFIG.baseUrl = url;
    console.log(`API URL set to: ${url}`);
}

/**
 * Make an API request
 * @param {string} endpoint - API endpoint (e.g., '/stories')
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_CONFIG.baseUrl}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    const fetchOptions = { ...defaultOptions, ...options };

    console.log(`API Request: ${fetchOptions.method || 'GET'} ${url}`);

    try {
        const response = await fetch(url, fetchOptions);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(`API Response:`, data);
        return data;

    } catch (error) {
        console.error(`API Error: ${error.message}`);
        throw error;
    }
}

// =============================================================================
// Health and Status
// =============================================================================

/**
 * Check if the backend is healthy
 * @returns {Promise<Object>} Health status
 */
async function checkHealth() {
    return apiRequest('/health');
}

/**
 * Get API information
 * @returns {Promise<Object>} API info
 */
async function getApiInfo() {
    return apiRequest('/info');
}

/**
 * Get system statistics
 * @returns {Promise<Object>} Statistics
 */
async function getStats() {
    return apiRequest('/stats');
}

// =============================================================================
// Stories
// =============================================================================

/**
 * Get all available stories
 * @returns {Promise<Array>} List of stories
 */
async function getStories() {
    return apiRequest('/stories/');
}

/**
 * Get a specific story
 * @param {number} storyId - Story ID
 * @returns {Promise<Object>} Story details
 */
async function getStory(storyId) {
    return apiRequest(`/stories/${storyId}`);
}

// =============================================================================
// Playthroughs
// =============================================================================

/**
 * Get all playthroughs for a story
 * @param {number} storyId - Story ID
 * @returns {Promise<Array>} List of playthroughs
 */
async function getPlaythroughs(storyId) {
    return apiRequest(`/stories/${storyId}/playthroughs`);
}

/**
 * Get a specific playthrough
 * @param {number} playthroughId - Playthrough ID
 * @returns {Promise<Object>} Playthrough details
 */
async function getPlaythrough(playthroughId) {
    return apiRequest(`/stories/playthroughs/${playthroughId}`);
}

/**
 * Create a new playthrough
 * @param {number} storyId - Story ID
 * @param {string} name - Playthrough name
 * @returns {Promise<Object>} Created playthrough
 */
async function createPlaythrough(storyId, name) {
    return apiRequest('/stories/playthroughs', {
        method: 'POST',
        body: JSON.stringify({
            story_id: storyId,
            playthrough_name: name
        })
    });
}

/**
 * Get characters for a playthrough
 * @param {number} playthroughId - Playthrough ID
 * @returns {Promise<Array>} List of characters
 */
async function getPlaythroughCharacters(playthroughId) {
    return apiRequest(`/stories/playthroughs/${playthroughId}/characters`);
}

/**
 * Get relationships for a playthrough
 * @param {number} playthroughId - Playthrough ID
 * @returns {Promise<Array>} List of relationships
 */
async function getPlaythroughRelationships(playthroughId) {
    return apiRequest(`/stories/playthroughs/${playthroughId}/relationships`);
}

// =============================================================================
// Sessions
// =============================================================================

/**
 * Create a new session for a playthrough
 * @param {number} playthroughId - Playthrough ID
 * @returns {Promise<Object>} Created session
 */
async function createSession(playthroughId) {
    return apiRequest('/stories/sessions', {
        method: 'POST',
        body: JSON.stringify({
            playthrough_id: playthroughId
        })
    });
}

/**
 * Get the latest session for a playthrough
 * @param {number} playthroughId - Playthrough ID
 * @returns {Promise<Object>} Latest session
 */
async function getLatestSession(playthroughId) {
    return apiRequest(`/stories/playthroughs/${playthroughId}/latest-session`);
}

// =============================================================================
// Chat
// =============================================================================

/**
 * Send a message and get AI response
 * @param {number} sessionId - Session ID
 * @param {string} message - User's message/action
 * @returns {Promise<Object>} AI response with metadata
 */
async function sendMessage(sessionId, message) {
    return apiRequest('/chat/send', {
        method: 'POST',
        body: JSON.stringify({
            session_id: sessionId,
            message: message
        })
    });
}

/**
 * Generate more story content without user input
 * @param {number} sessionId - Session ID
 * @returns {Promise<Object>} AI response
 */
async function generateMore(sessionId) {
    return apiRequest('/chat/generate-more', {
        method: 'POST',
        body: JSON.stringify({
            session_id: sessionId
        })
    });
}

/**
 * Get chat history for a session
 * @param {number} sessionId - Session ID
 * @param {number} limit - Maximum messages to retrieve
 * @returns {Promise<Array>} Conversation history
 */
async function getChatHistory(sessionId, limit = 50) {
    return apiRequest(`/chat/history/${sessionId}?limit=${limit}`);
}

/**
 * Get all conversation history for a playthrough
 * @param {number} playthroughId - Playthrough ID
 * @param {number} limit - Maximum messages to retrieve
 * @returns {Promise<Array>} Conversation history
 */
async function getPlaythroughHistory(playthroughId, limit = 100) {
    return apiRequest(`/chat/playthrough-history/${playthroughId}?limit=${limit}`);
}

// =============================================================================
// Logs
// =============================================================================

/**
 * Get logs with optional filtering
 * @param {Object} filters - Filter options
 * @returns {Promise<Array>} Log entries
 */
async function getLogs(filters = {}) {
    const params = new URLSearchParams();

    if (filters.sessionId) params.append('session_id', filters.sessionId);
    if (filters.logType) params.append('log_type', filters.logType);
    if (filters.logCategory) params.append('log_category', filters.logCategory);
    if (filters.limit) params.append('limit', filters.limit);
    if (filters.offset) params.append('offset', filters.offset);

    const queryString = params.toString();
    const endpoint = queryString ? `/logs/?${queryString}` : '/logs/';

    return apiRequest(endpoint);
}

/**
 * Get recent logs
 * @param {number} limit - Number of logs to retrieve
 * @returns {Promise<Array>} Recent log entries
 */
async function getRecentLogs(limit = 50) {
    return apiRequest(`/logs/recent?limit=${limit}`);
}

/**
 * Get error logs only
 * @param {number} limit - Number of logs to retrieve
 * @returns {Promise<Array>} Error log entries
 */
async function getErrorLogs(limit = 50) {
    return apiRequest(`/logs/errors?limit=${limit}`);
}

/**
 * Get AI decision logs
 * @param {number} sessionId - Optional session ID filter
 * @param {number} limit - Number of logs to retrieve
 * @returns {Promise<Array>} AI decision log entries
 */
async function getAiDecisionLogs(sessionId = null, limit = 50) {
    let endpoint = `/logs/ai-decisions?limit=${limit}`;
    if (sessionId) endpoint += `&session_id=${sessionId}`;
    return apiRequest(endpoint);
}

/**
 * Get log statistics
 * @returns {Promise<Object>} Log statistics
 */
async function getLogStats() {
    return apiRequest('/logs/stats');
}

// =============================================================================
// Admin - Test Data Management
// =============================================================================

/**
 * Get available test data files
 * @returns {Promise<Object>} Available test data files
 */
async function getAvailableTestData() {
    return apiRequest('/admin/test-data/available');
}

/**
 * Load test data from files
 * @param {string} filename - Optional specific filename to load
 * @param {boolean} loadAll - Load all available test data
 * @returns {Promise<Object>} Load result
 */
async function loadTestData(filename = null, loadAll = false) {
    let endpoint = '/admin/test-data/load?';
    if (filename) {
        endpoint += `filename=${encodeURIComponent(filename)}`;
    } else if (loadAll) {
        endpoint += 'load_all=true';
    }
    return apiRequest(endpoint, { method: 'POST' });
}

/**
 * Clear all template data (stories without playthroughs)
 * @returns {Promise<Object>} Clear result
 */
async function clearTestData() {
    return apiRequest('/admin/test-data/clear', { method: 'DELETE' });
}

// =============================================================================
// Tester / Debug Functions
// =============================================================================

/**
 * Get complete playthrough data for testing/debugging
 * @param {number} playthroughId - Playthrough ID
 * @returns {Promise<Object>} Complete playthrough data
 */
async function getPlaythroughData(playthroughId) {
    return apiRequest(`/admin/tester/playthrough/${playthroughId}`);
}

/**
 * Get current context window for a session
 * @param {number} sessionId - Session ID
 * @returns {Promise<Object>} Context window data
 */
async function getContextWindow(sessionId) {
    return apiRequest(`/admin/tester/context/${sessionId}`);
}

/**
 * Reset a playthrough to initial state
 * @param {number} playthroughId - Playthrough ID
 * @returns {Promise<Object>} Reset result
 */
async function resetPlaythrough(playthroughId) {
    return apiRequest(`/admin/tester/playthrough/${playthroughId}/reset`, { method: 'DELETE' });
}

/**
 * Get logs grouped by conversation turn
 * @param {number} sessionId - Session ID
 * @param {number} limit - Number of logs to retrieve
 * @returns {Promise<Object>} Grouped logs
 */
async function getGroupedLogs(sessionId, limit = 50) {
    return apiRequest(`/admin/tester/logs/${sessionId}?limit=${limit}`);
}

// Export all functions for use in other modules
console.log('API client loaded');

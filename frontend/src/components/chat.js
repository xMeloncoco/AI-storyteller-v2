/**
 * Chat Component
 *
 * Handles the main storytelling interface:
 * - Displaying story messages
 * - Sending user input
 * - Generate More functionality
 * - Character information display
 */

const ChatComponent = {
    // Current state
    currentSession: null,
    currentPlaythrough: null,
    isLoading: false,

    /**
     * Initialize the chat component
     * @param {Object} playthrough - Playthrough data
     * @param {Object} session - Session data
     * @param {Array} history - Conversation history
     */
    async init(playthrough, session, history = []) {
        this.currentPlaythrough = playthrough;
        this.currentSession = session;

        // Update UI
        document.getElementById('playthrough-title').textContent = playthrough.playthrough_name;
        document.getElementById('current-location').textContent =
            `Location: ${playthrough.current_location || 'Unknown'}`;

        // Clear and load history
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';

        // If no history, show initial story message
        if (history.length === 0) {
            // Get the story to show initial message
            const story = await getStory(playthrough.story_id);
            if (story && story.initial_message) {
                this.addMessage('narrator', 'Narrator', story.initial_message);
            }
        } else {
            // Load existing history
            for (const msg of history) {
                this.addMessage(msg.speaker_type, msg.speaker_name || msg.speaker_type, msg.message);
            }
        }

        // Scroll to bottom
        this.scrollToBottom();

        console.log('Chat component initialized', {
            playthrough: playthrough.id,
            session: session.id,
            historyLength: history.length
        });
    },

    /**
     * Add a message to the chat display
     * @param {string} type - 'narrator' or 'user'
     * @param {string} speaker - Speaker name
     * @param {string} content - Message content
     */
    addMessage(type, speaker, content) {
        const messagesContainer = document.getElementById('chat-messages');

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        const header = document.createElement('div');
        header.className = 'message-header';
        header.textContent = speaker;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(header);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        this.scrollToBottom();
    },

    /**
     * Send user message to the AI
     */
    async sendMessage() {
        if (this.isLoading || !this.currentSession) {
            console.log('Cannot send: loading or no session');
            return;
        }

        const inputElement = document.getElementById('user-input');
        const message = inputElement.value.trim();

        if (!message) {
            console.log('Empty message, not sending');
            return;
        }

        // Clear input
        inputElement.value = '';

        // Add user message to display
        this.addMessage('user', 'You', message);

        // Show loading state
        this.setLoading(true);

        try {
            // Send to API
            console.log('Sending message to AI...');
            const response = await sendMessage(this.currentSession.id, message);

            // Add AI response to display
            this.addMessage('narrator', 'Narrator', response.message);

            // Update location if changed
            if (response.current_location) {
                document.getElementById('current-location').textContent =
                    `Location: ${response.current_location}`;
            }

            // Log any relationship updates
            if (response.relationship_updates && Object.keys(response.relationship_updates).length > 0) {
                console.log('Relationship updates:', response.relationship_updates);
            }

            // Log any story flags set
            if (response.story_flags_set && response.story_flags_set.length > 0) {
                console.log('Story flags set:', response.story_flags_set);
            }

        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('narrator', 'System', `Error: ${error.message}. Please check the logs.`);
        } finally {
            this.setLoading(false);
        }
    },

    /**
     * Generate more story content without user input
     */
    async generateMore() {
        if (this.isLoading || !this.currentSession) {
            return;
        }

        this.setLoading(true);

        try {
            console.log('Generating more content...');
            const response = await generateMore(this.currentSession.id);

            // Add AI response
            this.addMessage('narrator', 'Narrator', response.message);

        } catch (error) {
            console.error('Error generating more:', error);
            this.addMessage('narrator', 'System', `Error: ${error.message}`);
        } finally {
            this.setLoading(false);
        }
    },

    /**
     * Set loading state
     * @param {boolean} loading - Is loading
     */
    setLoading(loading) {
        this.isLoading = loading;

        const sendBtn = document.getElementById('btn-send');
        const generateBtn = document.getElementById('btn-generate-more');
        const input = document.getElementById('user-input');

        if (loading) {
            sendBtn.disabled = true;
            sendBtn.textContent = 'Sending...';
            generateBtn.disabled = true;
            input.disabled = true;
            document.getElementById('footer-status').textContent = 'AI is thinking...';
        } else {
            sendBtn.disabled = false;
            sendBtn.textContent = 'Send';
            generateBtn.disabled = false;
            input.disabled = false;
            document.getElementById('footer-status').textContent = 'Ready';
        }
    },

    /**
     * Scroll chat to bottom
     */
    scrollToBottom() {
        const container = document.getElementById('chat-container');
        container.scrollTop = container.scrollHeight;
    },

    /**
     * Show characters modal with current scene characters
     */
    async showCharacters() {
        const modal = document.getElementById('modal-characters');
        const infoContainer = document.getElementById('characters-info');

        infoContainer.innerHTML = '<p class="loading">Loading characters...</p>';
        modal.classList.add('active');

        try {
            // Get characters for this playthrough
            const characters = await getPlaythroughCharacters(this.currentPlaythrough.id);

            if (characters.length === 0) {
                infoContainer.innerHTML = '<p>No characters loaded.</p>';
                return;
            }

            // Also get relationships
            const relationships = await getPlaythroughRelationships(this.currentPlaythrough.id);

            let html = '';

            for (const char of characters) {
                html += `
                    <div class="character-card">
                        <h4>${char.character_name}</h4>
                        <div class="character-type">${char.character_type}</div>
                `;

                if (char.age) {
                    html += `<p>Age: ${char.age}</p>`;
                }

                if (char.appearance) {
                    html += `<p><strong>Appearance:</strong> ${char.appearance}</p>`;
                }

                // Find relationship with this character
                const rel = relationships.find(r =>
                    r.entity2_id === char.id || r.entity1_id === char.id
                );

                if (rel && char.character_type !== 'User') {
                    html += `
                        <div style="margin-top: 10px; padding: 10px; background: #0f3460; border-radius: 4px;">
                            <strong>Relationship:</strong> ${rel.relationship_type}<br>
                            Trust: ${(rel.trust * 100).toFixed(0)}% |
                            Affection: ${(rel.affection * 100).toFixed(0)}% |
                            Familiarity: ${(rel.familiarity * 100).toFixed(0)}%
                        </div>
                    `;
                }

                html += '</div>';
            }

            infoContainer.innerHTML = html;

        } catch (error) {
            console.error('Error loading characters:', error);
            infoContainer.innerHTML = `<p>Error loading characters: ${error.message}</p>`;
        }
    }
};

console.log('Chat component loaded');

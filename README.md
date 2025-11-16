# Dreamwalkers - AI Interactive Storytelling Application

A complete AI-powered interactive storytelling application where characters have their own personalities, relationships evolve naturally, and stories progress through structured arcs.

## Features

- **Interactive AI Storytelling**: Chat with AI-driven narratives that respond to your actions
- **Character Consistency**: Characters make autonomous decisions based on their personalities
- **Dynamic Relationships**: Trust, affection, and familiarity evolve through interactions
- **Story Progression**: Track story arcs, episodes, and important events
- **Comprehensive Logging**: Full visibility into what the AI is thinking and doing
- **Generate More**: Continue stories without user input
- **Session Resume**: Save and continue your stories
- **Multiple AI Providers**: Support for OpenRouter, Nebius, or local models

## Project Structure

```
dreamwalkers/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── ai/             # AI integration (LLM, prompts, context)
│   │   ├── relationships/   # Relationship tracking
│   │   ├── story/          # Story progression management
│   │   ├── routers/        # API endpoints
│   │   ├── utils/          # Logging and helpers
│   │   ├── models.py       # Database models
│   │   ├── schemas.py      # API validation
│   │   ├── crud.py         # Database operations
│   │   └── main.py         # Application entry point
│   ├── test_data/          # Test stories and import scripts
│   └── data/               # Database and ChromaDB storage
├── frontend/               # Electron desktop application
│   └── src/
│       ├── components/     # UI components (chat, logs, settings)
│       ├── api.js          # Backend communication
│       └── renderer.js     # Main frontend logic
└── docs/                   # Additional documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- An AI API key (OpenRouter or Nebius) OR local Ollama installation

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from example
cp .env.example .env
# Edit .env with your API key
```

Configure your `.env` file:
```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
SMALL_MODEL=meta-llama/llama-3.2-3b-instruct
LARGE_MODEL=meta-llama/llama-3.1-8b-instruct
```

### 2. Import Test Data

```bash
# Import both test stories
python test_data/import_test_data.py --story both --create-playthroughs

# Or reset and reimport
python test_data/import_test_data.py --story both --reset --create-playthroughs
```

### 3. Start Backend

```bash
# From backend directory
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### 4. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start application
npm start
```

## Test Stories Included

### Sterling Hearts
A romance drama about reunited childhood friends navigating complicated feelings and past wounds.

- Characters: You, Alex Sterling (main love interest), Maya Chen (best friend), Jordan Blake (potential rival)
- Themes: Reconnection, trust, forgiveness, choice

### The Moonweaver's Apprentice
A fantasy story about discovering magical powers and learning to control them.

- Characters: You, Master Silvara (mentor), Finn (best friend), The Shadow (antagonist), Elder Thorne (village elder)
- Themes: Power, responsibility, temptation, growth

## Key API Endpoints

### Chat
- `POST /chat/send` - Send message and get AI response
- `POST /chat/generate-more` - Continue story without user input
- `GET /chat/history/{session_id}` - Get conversation history

### Stories
- `GET /stories/` - List all stories
- `POST /stories/playthroughs` - Create new playthrough
- `GET /stories/playthroughs/{id}/characters` - Get characters

### Logs
- `GET /logs/` - View system logs with filtering
- `GET /logs/ai-decisions` - See AI decision-making
- `GET /logs/errors` - View errors only

## Architecture

### AI Workflow
1. User sends action/dialogue
2. Lightweight model detects scene changes
3. Character Decision Layer asks: "What would this character do?"
4. Main LLM generates story response
5. Relationship values update based on interaction
6. Story flags are set if important events occur
7. Response returned to user with metadata

### Database Schema Pattern
- Templates: `playthrough_id = NULL` (story-level data)
- Instances: `playthrough_id = <value>` (playthrough-specific data)

When you create a playthrough, all templates are copied to instances.

## Configuration

### AI Provider Options

**OpenRouter** (default):
```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key
```

**Nebius**:
```env
AI_PROVIDER=nebius
NEBIUS_API_KEY=your_key
```

**Local Ollama** (future):
```env
AI_PROVIDER=local
OLLAMA_HOST=http://localhost:11434
SMALL_MODEL=phi3:mini
LARGE_MODEL=llama3.1:8b-instruct-q4_0
```

### Context Settings
```env
MAX_CONTEXT_MESSAGES=20      # How many messages in context
MEMORY_SAVE_INTERVAL=5       # Auto-save memory every N responses
```

## Logging System

The logging system is critical for understanding what's happening:

- **notification**: Normal system events
- **error**: Problems that occurred
- **edit**: Database changes (relationships, flags)
- **ai_decision**: What the AI decided and why
- **context**: Memory and context operations

View logs through the frontend "View Logs" button or via API.

## Development Notes

### Adding New Stories
1. Create a JSON file in `backend/test_data/`
2. Follow the structure of `sterling_story.json`
3. Include characters, locations, relationships, and story arcs
4. Import using the import script

### Extending Character Behavior
- Modify prompts in `backend/app/ai/prompts.py`
- Adjust character decision logic in `backend/app/ai/llm_manager.py`
- Update relationship calculations in `backend/app/relationships/updater.py`

### Adding New Features
- Most features can be added by:
  1. Adding new database models in `models.py`
  2. Creating schemas in `schemas.py`
  3. Adding CRUD operations in `crud.py`
  4. Creating API endpoints in routers
  5. Updating frontend components

## Future Features (Not Implemented Yet)

- ChromaDB vector memory (placeholder exists)
- Character knowledge tracking (prevent mind-reading)
- Story coherence checking
- User character customization
- Multiple AI model support simultaneously
- Mobile version
- Visual enhancements
- Secret/hidden character data

## Troubleshooting

### Backend won't start
- Check Python version: `python --version`
- Verify virtual environment is activated
- Check all dependencies installed: `pip install -r requirements.txt`
- Verify .env file exists and has valid API key

### AI responses are errors
- Check API key is valid
- Verify model names are correct for your provider
- Check logs for specific error messages
- Ensure backend is running at http://localhost:8000

### Frontend won't connect
- Verify backend is running
- Check API URL in settings matches backend
- Look at browser dev tools console for errors

### Database issues
- Reset database: `POST /reset-database`
- Reimport data with `--reset` flag
- Check `backend/data/` directory exists

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with clear comments
4. Test thoroughly
5. Submit a pull request

---

**Happy Storytelling!**

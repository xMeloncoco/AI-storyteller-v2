# Dreamwalkers - AI Interactive Storytelling App

An AI-powered interactive storytelling desktop application where users experience immersive narratives with intelligent characters, evolving relationships, and dynamic story progression.

## Features

### Core Functionality
- **AI-Powered Narratives**: Chat with AI characters that remember context and respond consistently
- **Character Depth**: Each character has detailed personality, values, fears, speech patterns, and secrets
- **Dynamic Relationships**: Relationships evolve based on interactions (trust, affection, familiarity metrics)
- **Story Progression**: Structured story arcs with conditions and progression tracking
- **Context Awareness**: AI remembers conversation history and story state
- **Multiple Stories**: Load different story templates and create multiple playthroughs

### Developer/Testing Tools
- **Tester/Debugger**: Database viewer and context window inspector
  - Browse characters, relationships, locations, story arcs, and flags
  - View the exact context sent to the AI
  - Reset playthroughs for fresh testing
- **Comprehensive Logging**: All AI decisions and system operations
- **Test Data Loader**: Load story templates with one click
- **Database Management**: View and reset playthrough data easily

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- An AI provider: local [Ollama](https://ollama.com/) (default, no key) or a free API key (see [AI_SETUP.md](./AI_SETUP.md))

### One-command start (recommended)

See [TESTING.md](./TESTING.md). On Linux/Mac: `./start-test.sh`. On Windows: `start-test.bat`.

### Manual installation

1. **Backend setup:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure AI provider:**
Copy `backend/.env.example` to `backend/.env`. The default uses local Ollama (no API key). To use OpenRouter or Nebius instead, see [AI_SETUP.md](./AI_SETUP.md).

3. **Frontend setup:**
```bash
cd ../frontend
npm install
```

### Running the App

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python -m app.main
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

The app will open automatically. Backend runs on `http://localhost:8000`.

## Using the App

### First Time Setup
1. **Load Test Data**: Click Settings → Load All Test Data
2. **Select a Story**: Go to Stories screen and pick one
3. **Create Playthrough**: Click "New Playthrough", name it
4. **Start Chatting**: Type messages and interact with characters

### Tester/Debugger (🧪 button)
- **Database Viewer**: Browse all playthrough data
  - Characters: personalities, traits, secrets
  - Relationships: trust/affection metrics
  - Locations, story flags, and scene state
- **Context Window**: See exactly what the AI sees
- **Logs**: Per-turn grouped logs of AI decisions
- **Reset**: Start playthrough fresh for testing

## Project Structure

```
AI-storyteller-v2/
├── backend/
│   ├── app/
│   │   ├── ai/              # AI integration (LLM, context building)
│   │   ├── routers/         # API endpoints (chat, stories, admin, logs)
│   │   ├── models.py        # Database models
│   │   ├── schemas.py       # Pydantic validation
│   │   ├── crud.py          # Database operations
│   │   └── config.py        # Configuration
│   ├── test_data/           # Story template JSON files
│   └── data/                # Database and vector store
├── frontend/
│   ├── src/
│   │   ├── components/      # UI components (chat, tester, settings)
│   │   ├── api.js           # Backend API client
│   │   ├── renderer.js      # Main app logic
│   │   └── styles.css       # Styling
│   └── main.js              # Electron entry point
└── AI_SETUP.md              # AI provider setup guide
```

## Creating Stories

Stories are defined in JSON. See `backend/test_data/` for examples.

### Basic Story Structure
```json
{
  "title": "Your Story Name",
  "description": "Brief description",
  "initial_message": "Opening narration...",
  "characters": [...],
  "relationships": [...],
  "locations": [...],
  "story_arcs": [...]
}
```

### Loading Stories
1. Create JSON file in `backend/test_data/`
2. Open Settings → Test Data Management
3. Click "Refresh List" → "Load All Test Data"

## Configuration

Defaults live in `backend/app/config.py` and can be overridden via `backend/.env`. See `backend/.env.example` for a full template. Common keys:

```bash
# AI Provider: local (Ollama, default), openrouter, nebius, or demo
AI_PROVIDER=local

# Models for the default local provider
SMALL_MODEL=llama3.2:3b
LARGE_MODEL=llama3.2

# Database
DATABASE_URL=sqlite:///./data/dreamwalkers.db

# Context Settings
MAX_CONTEXT_MESSAGES=40
MAX_TOKENS_SMALL=500
MAX_TOKENS_LARGE=3000
```

## API Endpoints

### Stories & Playthroughs
- `GET /stories/` - List all stories
- `POST /stories/playthroughs` - Create new playthrough
- `GET /stories/{id}/playthroughs` - List playthroughs for a story

### Chat
- `POST /chat/send` - Send message and get AI response
- `POST /chat/generate-more` - Generate story without user input

### Admin/Testing
- `POST /admin/test-data/load` - Load test data files
- `GET /admin/tester/playthrough/{id}` - Get complete playthrough data
- `GET /admin/tester/context/{session_id}` - View context window
- `DELETE /admin/tester/playthrough/{id}/reset` - Reset playthrough

### Logs
- `GET /logs` - View system logs
- `GET /admin/tester/logs/{session_id}` - Get grouped logs

## Key Technologies

- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic
- **Frontend**: Electron, JavaScript, HTML/CSS
- **Database**: SQLite
- **AI**: Ollama (local, default), OpenRouter, or Nebius
- **Architecture**: REST API, Client-Server

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (need 3.11+)
- Verify venv is activated
- Install requirements: `pip install -r requirements.txt`

### Frontend won't connect
- Ensure backend is running first
- Check Settings → API URL is `http://localhost:8000`
- Look for errors in browser console (F12)

### AI not responding
- Verify `.env` file has correct AI_PROVIDER and API key
- Check Settings → System Info → AI Configured should be "Yes"
- See [AI_SETUP.md](./AI_SETUP.md) for free API keys

### Rate limit errors (429)
Free tier models are shared resources and may be rate-limited during peak usage:
- **Quick fix**: Wait 1-2 minutes and try again
- **Better solution**: Get a free API key from https://openrouter.ai/ and add to `.env`:
  ```
  OPENROUTER_API_KEY=your_key_here
  ```
- This accumulates your own rate limits instead of using shared limits
- OpenRouter free tier includes $1 free credit and generous rate limits

### No stories available
- Go to Settings → Test Data Management
- Click "Load All Test Data"
- Refresh Stories screen

## Documentation

- **AI_SETUP.md** - Configure local Ollama or free online AI providers
- **TESTING.md** - Quick-start scripts for local testing
- **backend/app/PIPELINE_STAGES.md** - AI processing pipeline explanation
- **docs/AI_PROMPT_CONSTRUCTION.md** - How prompts are built
- **docs/RESPONSE_FLOW.md** - End-to-end response flow
- **docs/STORY_DATA_STRUCTURE.md** - Story JSON schema reference

## Contributing

This is a personal project, but suggestions and feedback are welcome.

## License

MIT License - Feel free to use and modify for your own projects.

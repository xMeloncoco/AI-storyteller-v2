# 🌟 Dreamwalkers - AI Interactive Storytelling App

An AI-powered interactive storytelling desktop application where users experience immersive narratives with intelligent characters, evolving relationships, and dynamic story progression.

## ✨ Features

### Core Functionality
- **AI-Powered Narratives**: Chat with intelligent AI characters that remember context and respond consistently
- **Character Depth**: Each character has detailed personality, values, fears, speech patterns, and secrets
- **Dynamic Relationships**: Relationships evolve based on interactions (trust, affection, familiarity metrics)
- **Story Progression**: Structured story arcs with conditions and progression tracking
- **Context Awareness**: AI remembers conversation history and story state
- **Multiple Stories**: Load different story templates and create multiple playthroughs

### Developer/Testing Tools
- **🧪 Tester/Debugger**: Complete database viewer and context window inspector
  - Browse characters, relationships, locations, story arcs, and flags
  - View the exact context sent to the AI
  - Reset playthroughs for fresh testing
- **📊 Comprehensive Logging**: Track all AI decisions and system operations
- **💾 Test Data Loader**: Load story templates with one click
- **🎮 Database Management**: View and reset playthrough data easily

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Free AI API key (see [AI_SETUP.md](./AI_SETUP.md))

### Installation

1. **Clone and setup backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure AI provider:**
Create `backend/.env` file:
```bash
AI_PROVIDER=openrouter  # or nebius
OPENROUTER_API_KEY=your_free_api_key_here
```

3. **Install frontend:**
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

## 📖 Using the App

### First Time Setup
1. **Load Test Data**: Click Settings → Load All Test Data
2. **Select a Story**: Go to Stories screen, choose "Starling Contract"
3. **Create Playthrough**: Click "New Playthrough", name it
4. **Start Chatting**: Type messages and interact with characters!

### Tester/Debugger (🧪 Button)
- **Database Viewer**: Browse all playthrough data
  - Characters: View personalities, traits, secrets
  - Relationships: Check trust/affection metrics
  - Story Arcs: Track progression
  - Flags: See what's been triggered
- **Context Window**: See exactly what the AI sees
- **Reset**: Start playthrough fresh for testing

## 🏗️ Project Structure

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

## 🎮 Creating Stories

Stories are defined in JSON format. See `backend/test_data/TEMPLATE_story.json` for a comprehensive template with documentation.

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

## 🔧 Configuration

Edit `backend/.env`:

```bash
# AI Provider (openrouter, nebius, or demo)
AI_PROVIDER=openrouter

# API Keys
OPENROUTER_API_KEY=your_key
NEBIUS_API_KEY=your_key

# Models (free options - updated for reliability)
SMALL_MODEL=microsoft/phi-3-mini-128k-instruct:free
LARGE_MODEL=google/gemma-2-9b-it:free

# Database
DATABASE_URL=sqlite:///./data/dreamwalkers.db

# Context Settings
MAX_CONTEXT_MESSAGES=20
MAX_TOKENS_SMALL=500
MAX_TOKENS_LARGE=2000
```

## 🌐 API Endpoints

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

## 🧩 Key Technologies

- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic
- **Frontend**: Electron, JavaScript, HTML/CSS
- **Database**: SQLite
- **AI**: OpenRouter / Nebius (free tiers available)
- **Architecture**: REST API, Client-Server

## 🎯 Development Roadmap

### ✅ Completed
- [x] Core chat system with AI integration
- [x] Character and relationship tracking
- [x] Story arc progression
- [x] Database viewer and tester tools
- [x] Test data loading system
- [x] Context window tracking
- [x] Comprehensive logging

### 🚧 Future Features
- [ ] ChromaDB vector memory for long-term context
- [ ] Character decision validation
- [ ] Relationship update triggers
- [ ] Story flag automation
- [ ] Memory summarization
- [ ] User character customization
- [ ] Visual novel mode
- [ ] Story creation UI

## 🐛 Troubleshooting

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

## 📚 Documentation

- **AI_SETUP.md** - How to get free AI API keys and configure providers
- **backend/test_data/TEMPLATE_story.json** - Story creation template with full documentation
- **backend/app/models.py** - Database schema documentation
- **backend/app/PIPELINE_STAGES.md** - AI processing pipeline explanation

## 🤝 Contributing

This is a personal project, but suggestions and feedback are welcome!

## 📄 License

MIT License - Feel free to use and modify for your own projects.

## 🎉 Acknowledgments

Built with:
- FastAPI for the incredible async Python framework
- Electron for cross-platform desktop apps
- OpenRouter & Nebius for free AI model access
- The open-source AI community

---

**Ready to create amazing stories? See [AI_SETUP.md](./AI_SETUP.md) to get started!** 🚀

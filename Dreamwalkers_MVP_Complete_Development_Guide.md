# Dreamwalkers - AI Storytelling App
## Complete MVP Development Guide for Claude Code

**Version:** 1.0  
**Target Platform:** Windows Desktop (Electron)  
**Development Time:** 8-10 weeks  
**Final MVP:** Version 3.2

---

## 📋 Document Overview

This is your complete guide to building the Dreamwalkers AI Storytelling application from scratch. This document is specifically designed for use with Claude Code and provides:

- **Phase-by-phase development plan** with clear checkpoints
- **Complete code examples** for all major components
- **Testing procedures** for each version
- **Troubleshooting guides** for common issues
- **Performance optimization** tips

**How to Use This Document:**
1. Start with Phase 0 (Setup)
2. Complete each version in order
3. Test thoroughly before moving to next version
4. Use logs extensively to debug issues
5. Refer back to this document when stuck

---

## 🎯 Project Goals Recap

**What We're Building:**
An AI-powered interactive storytelling application where:
- Users engage in branching narratives
- Characters have consistent personalities and can refuse the user
- Relationships develop naturally based on interactions
- Story arcs progress logically
- Memory persists across sessions
- Everything runs locally on the user's PC

**Key Technical Decisions:**
- **Frontend:** Electron (desktop app wrapping HTML/CSS/JS)
- **Backend:** FastAPI (Python)
- **Database:** SQLite (easy, local, no configuration)
- **AI Models:** Local LLMs via Ollama
  - Small model (Phi-3 mini) for quick analysis
  - Medium model (Llama 3.1 8B) for story generation
- **Memory:** ChromaDB for semantic search

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  ELECTRON DESKTOP APP                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Chat UI    │  │  Log Viewer  │  │   Settings   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            │                            │
│                   ┌────────▼────────┐                   │
│                   │  API Client     │                   │
└───────────────────┴────────┬────────┴───────────────────┘
                             │ HTTP/REST
                    ┌────────▼────────┐
                    │   FastAPI       │
                    │   Backend       │
                    │   (Python)      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐
   │ SQLite   │      │  ChromaDB   │     │   Ollama    │
   │ Database │      │  (Memory)   │     │  (LLMs)     │
   └──────────┘      └─────────────┘     └─────────────┘
```

---

## 📊 Development Phases Overview

### Phase 0: Setup (Week 1)
- Install all tools
- Create project structure
- Test basic connectivity

### Phase 1: Core Functionality (Weeks 2-4)
- **v1.1:** Database + Logging
- **v1.2:** Basic Chat + LLM Integration
- **v1.3:** Context System + Memory

### Phase 2: Intelligence (Weeks 5-7)
- **v2.1:** Character Decision Layer
- **v2.2:** Story Arcs & Episodes

### Phase 3: Polish (Weeks 8-10)
- **v3.1:** Dynamic Relationships
- **v3.2:** Final Features & Polish

---

## 🚀 PHASE 0: Environment Setup

### Week 1: Getting Everything Ready

#### Step 1: Install Required Software

**Python 3.11+ Installation:**
1. Download from python.org
2. During installation, check "Add Python to PATH"
3. Verify: `python --version` (should show 3.11 or higher)

**Node.js Installation:**
1. Download from nodejs.org (LTS version)
2. Install with default settings
3. Verify: `node --version` and `npm --version`

**Ollama Installation:**
1. Visit ollama.ai
2. Download for Windows
3. Install
4. Open terminal and run:
```bash
ollama pull phi3:mini
ollama pull llama3.1:8b-instruct-q4_0
```
5. Verify: `ollama list` (should show both models)

**VS Code (Recommended IDE):**
1. Download from code.visualstudio.com
2. Install Python extension
3. Install JavaScript extension

#### Step 2: Create Project Structure

Create this folder structure:

```
C:\Projects\dreamwalkers\
├── backend\
│   ├── app\
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── ai\
│   │   │   ├── __init__.py
│   │   │   ├── llm_manager.py
│   │   │   ├── prompts.py
│   │   │   └── context_builder.py
│   │   ├── relationships\
│   │   │   ├── __init__.py
│   │   │   └── updater.py
│   │   ├── story\
│   │   │   ├── __init__.py
│   │   │   └── progression.py
│   │   ├── utils\
│   │   │   ├── __init__.py
│   │   │   ├── logger.py
│   │   │   └── helpers.py
│   │   └── routers\
│   │       ├── __init__.py
│   │       ├── chat.py
│   │       ├── stories.py
│   │       └── logs.py
│   ├── data\
│   │   └── (will contain dreamwalkers.db and chroma folder)
│   ├── test_data\
│   │   ├── import_test_data.py
│   │   ├── sterling_story.json
│   │   └── moonweaver_story.json
│   ├── requirements.txt
│   └── .env
├── frontend\
│   ├── src\
│   │   ├── index.html
│   │   ├── styles.css
│   │   ├── main.js
│   │   ├── renderer.js
│   │   ├── api.js
│   │   └── components\
│   │       ├── chat.js
│   │       ├── logs.js
│   │       └── settings.js
│   ├── package.json
│   └── package-lock.json
├── docs\
│   ├── API.md
│   ├── DATABASE.md
│   └── TESTING.md
└── README.md
```

#### Step 3: Initialize Backend

**Create backend/requirements.txt:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-multipart==0.0.6
chromadb==0.4.18
ollama==0.1.5
python-dotenv==1.0.0
```

**Install Python packages:**
```bash
cd C:\Projects\dreamwalkers\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Create backend/.env:**
```env
DATABASE_URL=sqlite:///./data/dreamwalkers.db
CHROMA_PATH=./data/chroma
OLLAMA_HOST=http://localhost:11434
SMALL_MODEL=phi3:mini
LARGE_MODEL=llama3.1:8b-instruct-q4_0
LOG_LEVEL=INFO
```

**Create minimal backend/app/main.py:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Dreamwalkers API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Dreamwalkers API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

**Test backend:**
```bash
cd backend
uvicorn app.main:app --reload
```
Visit http://localhost:8000 - should see {"message": "Dreamwalkers API is running"}

#### Step 4: Initialize Frontend

**Create frontend/package.json:**
```json
{
  "name": "dreamwalkers",
  "version": "0.1.0",
  "main": "src/main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder"
  },
  "devDependencies": {
    "electron": "^27.0.0",
    "electron-builder": "^24.6.4"
  }
}
```

**Install Node packages:**
```bash
cd C:\Projects\dreamwalkers\frontend
npm install
```

**Create frontend/src/main.js:**
```javascript
const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  win.loadFile('src/index.html');
  win.webContents.openDevTools();
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
```

**Create frontend/src/index.html:**
```html
<!DOCTYPE html>
<html>
<head>
  <title>Dreamwalkers</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #1a1a2e;
      color: #e0e0e0;
      padding: 20px;
    }
    h1 { color: #c77dff; }
    button {
      background: #7209b7;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 5px;
      cursor: pointer;
      margin: 10px 0;
    }
    button:hover { background: #9d4edd; }
    #result {
      margin-top: 20px;
      padding: 15px;
      background: #16213e;
      border-radius: 5px;
    }
  </style>
</head>
<body>
  <h1>✦ Dreamwalkers Setup Test</h1>
  <p>Click the button to test backend connection:</p>
  <button id="testBackend">Test Backend Connection</button>
  <div id="result"></div>
  
  <script>
    document.getElementById('testBackend').addEventListener('click', async () => {
      try {
        const response = await fetch('http://localhost:8000/health');
        const data = await response.json();
        document.getElementById('result').innerHTML = 
          `✅ <strong>Success!</strong><br>Backend Status: ${data.status}`;
      } catch (error) {
        document.getElementById('result').innerHTML = 
          `❌ <strong>Error:</strong><br>${error.message}<br><br>
          Make sure the backend is running:<br>
          <code>cd backend && uvicorn app.main:app --reload</code>`;
      }
    });
  </script>
</body>
</html>
```

**Test frontend:**
```bash
cd frontend
npm start
```
Should open a window. Click the test button.

#### Phase 0 Testing Checklist

- [ ] Python 3.11+ installed
- [ ] Node.js installed
- [ ] Ollama installed with both models
- [ ] Project structure created
- [ ] Backend starts without errors
- [ ] Frontend opens and displays test page
- [ ] Frontend can connect to backend
- [ ] Test button shows "Success!"

**If everything works: ✅ Phase 0 Complete!**

---

*The complete document continues with detailed implementation guides for all phases. Due to length constraints, I'm providing this as a starting point. Would you like me to create separate detailed documents for each phase, or would you prefer me to continue with a specific phase?*

---

## 📚 Quick Start Summary

Once Phase 0 is complete, you'll work through:

1. **Phase 1 (Weeks 2-4):** Build the core chat system with AI responses and memory
2. **Phase 2 (Weeks 5-7):** Add character intelligence and story structure
3. **Phase 3 (Weeks 8-10):** Implement relationships and polish features

Each phase builds on the previous one, so complete testing is essential before moving forward.

**For detailed implementation of each phase, refer to the complete document sections below or request specific phase details.**


# Dreamwalkers - Complete Setup Guide

This guide walks you through setting up and running the Dreamwalkers AI Storytelling application.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Backend Setup](#backend-setup)
3. [API Configuration](#api-configuration)
4. [Import Test Data](#import-test-data)
5. [Start the Backend](#start-the-backend)
6. [Frontend Setup](#frontend-setup)
7. [Running the Application](#running-the-application)
8. [Verifying Everything Works](#verifying-everything-works)
9. [Common Issues](#common-issues)

---

## Prerequisites

Before starting, ensure you have:

### Required Software
- **Python 3.11 or higher**
  - Download from: https://python.org
  - During installation, check "Add Python to PATH"
  - Verify: `python --version`

- **Node.js 18 or higher**
  - Download from: https://nodejs.org (LTS version)
  - Verify: `node --version` and `npm --version`

### AI Provider (Choose One)
- **OpenRouter** (Recommended)
  - Get API key from: https://openrouter.ai
  - Provides access to multiple models
  - Pay-per-use pricing

- **Nebius**
  - Alternative cloud provider
  - Get API key from their platform

- **Local Ollama** (Future - Not fully implemented)
  - For offline use
  - Download from: https://ollama.ai

---

## Backend Setup

### Step 1: Navigate to Backend
```bash
cd backend
```

### Step 2: Create Virtual Environment
```bash
# Create the virtual environment
python -m venv venv

# Activate it (Windows Command Prompt)
venv\Scripts\activate

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate it (Mac/Linux)
source venv/bin/activate
```

You should see `(venv)` in your command prompt now.

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- SQLAlchemy (database ORM)
- Pydantic (data validation)
- httpx (HTTP client for AI APIs)
- And other necessary packages

### Step 4: Create Data Directory
```bash
mkdir -p data
```

This is where the SQLite database and ChromaDB will be stored.

---

## API Configuration

### Step 1: Create Environment File
```bash
# Copy the example file
cp .env.example .env

# Or on Windows
copy .env.example .env
```

### Step 2: Edit Configuration

Open `.env` in a text editor and configure:

#### For OpenRouter (Recommended):
```env
# AI Provider
AI_PROVIDER=openrouter

# Your OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here

# Models to use
SMALL_MODEL=meta-llama/llama-3.2-3b-instruct
LARGE_MODEL=meta-llama/llama-3.1-8b-instruct

# Database (leave as default)
DATABASE_URL=sqlite:///./data/dreamwalkers.db
CHROMA_PATH=./data/chroma

# Settings
LOG_LEVEL=INFO
MAX_CONTEXT_MESSAGES=20
MEMORY_SAVE_INTERVAL=5
```

#### For Nebius:
```env
AI_PROVIDER=nebius
NEBIUS_API_KEY=your-nebius-key-here
# Update model names according to Nebius documentation
```

#### Model Selection Tips:
- **Small Model**: Used for quick analysis (character decisions, scene detection)
  - Should be fast and cheap
  - Examples: llama-3.2-3b, phi-3-mini

- **Large Model**: Used for story generation
  - Should be more capable
  - Examples: llama-3.1-8b, llama-3.1-70b (if budget allows)

---

## Import Test Data

### Basic Import
```bash
# Import both test stories
python test_data/import_test_data.py --story both
```

### Import with Test Playthroughs
```bash
# Creates ready-to-play playthroughs
python test_data/import_test_data.py --story both --create-playthroughs
```

### Reset and Import
```bash
# Clear database and reimport (useful for fresh start)
python test_data/import_test_data.py --story both --reset --create-playthroughs
```

### What Gets Imported
- **Sterling Hearts**: Romance drama story
  - 4 characters with full backstories
  - 3 locations
  - 3 relationships with initial values
  - 3 story arcs with episodes

- **The Moonweaver's Apprentice**: Fantasy story
  - 5 characters
  - 5 locations
  - 4 relationships
  - 3 story arcs

You should see output like:
```
==================================================
IMPORTING STERLING HEARTS
==================================================
Importing story: Sterling Hearts
  Created story with ID: 1
  Importing 4 characters...
    Characters imported
  Importing 3 locations...
    Locations imported
  Importing 3 relationships...
    Relationships imported
  Importing 3 story arcs...
    Story arcs imported
  Creating test playthrough: Sterling Hearts Test Run
    Playthrough created with ID: 1

==================================================
IMPORT COMPLETE
==================================================
  - Sterling Hearts (ID: 1)
  - The Moonweaver's Apprentice (ID: 2)
```

---

## Start the Backend

### Option 1: Development Mode (Recommended)
```bash
# From backend directory with venv activated
uvicorn app.main:app --reload
```

The `--reload` flag auto-restarts when you change code.

### Option 2: Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Verify Backend is Running
Visit in your browser: http://localhost:8000

You should see:
```json
{
  "name": "Dreamwalkers API",
  "version": "0.1.0",
  "status": "running",
  "description": "AI-powered interactive storytelling backend"
}
```

Check health: http://localhost:8000/health
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "ai_provider": "openrouter",
  "ai_configured": true
}
```

---

## Frontend Setup

### Step 1: Navigate to Frontend
Open a **new terminal** (keep backend running):
```bash
cd frontend
```

### Step 2: Install Dependencies
```bash
npm install
```

This installs:
- Electron (desktop app framework)
- electron-builder (for packaging)

---

## Running the Application

### Terminal 1: Backend (must be running)
```bash
cd backend
venv\Scripts\activate  # or source venv/bin/activate
uvicorn app.main:app --reload
```

### Terminal 2: Frontend
```bash
cd frontend
npm start
```

The Electron window should open automatically.

### For Development (with DevTools)
```bash
npm run dev
```

---

## Verifying Everything Works

### 1. Check Connection
- The status indicator in the top-left should show "Connected"
- If "Disconnected", check backend is running

### 2. View Stories
- You should see Sterling Hearts and Moonweaver's Apprentice
- If empty, reimport test data

### 3. Start a Story
- Click on a story
- Either continue an existing playthrough or create new
- You should see the initial story message

### 4. Send a Message
- Type an action (e.g., "I smile warmly and invite him inside")
- Click Send or press Enter
- You should receive an AI response within 10-30 seconds

### 5. Check Logs
- Click "View Logs" in the header
- You should see system activity
- Filter by type to see AI decisions

### 6. View Characters
- In the chat screen, click "Characters"
- You should see character information and relationship stats

---

## Common Issues

### "Disconnected" Status
**Problem**: Frontend can't reach backend

**Solutions**:
1. Verify backend is running (Terminal 1)
2. Check URL: http://localhost:8000
3. In Settings, ensure API URL is correct
4. Check for firewall blocking port 8000

### "No stories found"
**Problem**: Database is empty

**Solution**:
```bash
cd backend
python test_data/import_test_data.py --story both --reset
```

### API Key Not Configured
**Problem**: Backend health shows `ai_configured: false`

**Solution**:
1. Check `.env` file exists in `backend/`
2. Verify API key is correct (no extra spaces)
3. Restart backend after changing `.env`

### AI Response Takes Forever / Timeout
**Problem**: No response from AI

**Solutions**:
1. Check API key is valid (test on provider's website)
2. Verify model names are correct
3. Check internet connection
4. Look at backend terminal for errors

### Import Script Fails
**Problem**: Can't import test data

**Solutions**:
1. Ensure you're in the backend directory
2. Virtual environment is activated
3. Run `python -c "import app"` to verify imports work
4. Check for Python syntax errors in terminal

### Frontend Window is Blank
**Problem**: Electron opens but shows nothing

**Solutions**:
1. Open DevTools (View menu or F12)
2. Check Console for errors
3. Verify `index.html` and other files exist
4. Reinstall node_modules: `npm install`

### Database Locked Error
**Problem**: SQLite reports database is locked

**Solutions**:
1. Close any database browsers (DB Browser for SQLite)
2. Restart the backend
3. Only one process should access the database

---

## Next Steps

Once everything is working:

1. **Explore the Stories**: Try both test stories to see how they work
2. **Check the Logs**: See what the AI is thinking
3. **Monitor Relationships**: Watch how trust/affection change
4. **Test Character Behavior**: Try actions that characters might refuse
5. **Create New Playthroughs**: Start fresh runs to see different paths

### Development Tips
- Keep logs open to understand system behavior
- Use "Generate More" to see autonomous story progression
- Test edge cases to see how AI handles them
- Review the code comments for implementation details

### Getting Help
- Check logs first - they show everything happening
- Backend terminal shows Python errors
- Frontend DevTools shows JavaScript errors
- Review this setup guide for common issues

---

**You're all set! Enjoy your AI storytelling experience!**

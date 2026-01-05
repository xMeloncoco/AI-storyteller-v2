# Quick Testing Guide

This guide explains how to quickly start the Dreamwalkers application for testing.

## Quick Start (One Command!)

```bash
./start-test.sh
```

That's it! The script will:
1. Check for Python and Node.js
2. Set up the Python virtual environment
3. Install dependencies (if needed)
4. Create `.env` file from `.env.example` (if needed)
5. Start the backend server
6. Start the frontend application
7. Ask if you want to load test data
8. Show combined logs from both services

## Stopping the Application

Press `Ctrl+C` in the terminal running `start-test.sh`, or run:

```bash
./stop-test.sh
```

## First Time Setup

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher

### AI Provider Setup (Choose One)

**Option 1: Local AI (Recommended for Testing)**
1. Install Ollama from https://ollama.com/download
2. Pull models:
   ```bash
   ollama pull llama3.2:3b
   ollama pull llama3.2
   ```
3. The `.env` file will already be configured for local AI

**Option 2: Online API (OpenRouter)**
1. Get API key from https://openrouter.ai
2. Edit `backend/.env` and change:
   ```
   AI_PROVIDER=openrouter
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   SMALL_MODEL=microsoft/phi-3-mini-128k-instruct:free
   LARGE_MODEL=google/gemma-2-9b-it:free
   ```

**Option 3: Demo Mode (No AI)**
1. Edit `backend/.env`:
   ```
   AI_PROVIDER=demo
   ```
   This returns mock responses without calling any AI service.

## Testing Workflow

1. **Start the app**: `./start-test.sh`
2. **Load test data** when prompted (recommended: yes)
3. **Create a playthrough**: Open the app → Stories → Select "Starling Contract" → New Playthrough
4. **Send messages** to test the chat functionality
5. **Open Tester Panel** (🧪 button) to view database, context, and logs
6. **Reset playthrough** if needed via Tester Panel
7. **Stop the app**: Press `Ctrl+C` or run `./stop-test.sh`

## Logs

While running, you can view logs in separate terminals:

```bash
# Backend logs
tail -f backend.log

# Frontend logs
tail -f frontend.log
```

## Troubleshooting

### Backend won't start
- Check `backend.log` for errors
- Verify `.env` file exists and has valid AI provider settings
- Make sure port 8000 is not in use: `lsof -i :8000`

### Frontend won't connect
- Ensure backend is running and healthy: `curl http://localhost:8000/health`
- Check `frontend.log` for errors

### Test data won't load
- Make sure backend is running first
- Check that `backend/test_data/` directory exists
- Manually run: `cd backend && python load_test_data.py`

## Manual Testing (Old Way)

If you prefer to start services manually:

### Terminal 1 - Backend
```bash
cd backend
source venv/bin/activate  # or: python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

### Terminal 2 - Frontend
```bash
cd frontend
npm install
npm start
```

### Terminal 3 - Load Test Data
```bash
cd backend
source venv/bin/activate
python load_test_data.py
```

## What's Different?

**Before**: 3 terminals, multiple commands, manual dependency management

**Now**: 1 command, automatic setup, integrated logging

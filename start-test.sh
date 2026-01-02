#!/bin/bash

# Dreamwalkers Test Environment Startup Script
# This script starts both backend and frontend services for testing

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
PID_FILE="$SCRIPT_DIR/.test-pids"

echo -e "${BLUE}=================================================="
echo "Dreamwalkers Test Environment Startup"
echo -e "==================================================${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            if ps -p $pid > /dev/null 2>&1; then
                kill $pid 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm "$PID_FILE"
    fi
    echo -e "${GREEN}Cleanup complete${NC}"
}

trap cleanup EXIT INT TERM

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found: $(python3 --version)${NC}"
echo -e "${GREEN}✓ Node.js found: $(node --version)${NC}"
echo ""

# Setup Python virtual environment
echo -e "${BLUE}Setting up Python environment...${NC}"
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate

# Check if dependencies need to be installed
if [ ! -f "venv/.deps_installed" ] || [ requirements.txt -nt venv/.deps_installed ]; then
    echo -e "${YELLOW}Installing/updating Python dependencies...${NC}"
    pip install -q -r requirements.txt
    touch venv/.deps_installed
fi

echo -e "${GREEN}✓ Python environment ready${NC}"
echo ""

# Check for .env file
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found in backend directory${NC}"
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    if [ -f "$BACKEND_DIR/.env.example" ]; then
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
        echo -e "${YELLOW}Please edit backend/.env with your AI provider settings${NC}"
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Setup Frontend
echo -e "${BLUE}Setting up Frontend environment...${NC}"
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

echo -e "${GREEN}✓ Frontend environment ready${NC}"
echo ""

# Start Backend
echo -e "${BLUE}Starting backend server...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate

# Start backend in background and capture PID
python -m app.main > "$SCRIPT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID >> "$PID_FILE"

echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo -e "  Logs: backend.log"

# Wait for backend to be ready
echo -e "${BLUE}Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Error: Backend failed to start. Check backend.log${NC}"
        exit 1
    fi
    sleep 1
done
echo ""

# Ask about test data
read -p "Load test data? (y/n, default: y): " LOAD_DATA
LOAD_DATA=${LOAD_DATA:-y}

if [[ $LOAD_DATA =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Loading test data...${NC}"
    cd "$BACKEND_DIR"
    python load_test_data.py
    echo -e "${GREEN}✓ Test data loaded${NC}"
    echo ""
fi

# Start Frontend
echo -e "${BLUE}Starting frontend application...${NC}"
cd "$FRONTEND_DIR"

# Start frontend in background
npm start > "$SCRIPT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID >> "$PID_FILE"

echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "  Logs: frontend.log"
echo ""

echo -e "${GREEN}=================================================="
echo "Test Environment Ready!"
echo "==================================================${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: Desktop application should open automatically"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo -e "${BLUE}To stop:${NC}"
echo "  Press Ctrl+C or run ./stop-test.sh"
echo ""
echo -e "${YELLOW}Monitoring logs (Ctrl+C to stop)...${NC}"
echo ""

# Tail both log files
tail -f "$SCRIPT_DIR/backend.log" "$SCRIPT_DIR/frontend.log"

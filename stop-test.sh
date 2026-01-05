#!/bin/bash

# Dreamwalkers Test Environment Shutdown Script
# This script stops all services started by start-test.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/.test-pids"

echo -e "${BLUE}=================================================="
echo "Dreamwalkers Test Environment Shutdown"
echo -e "==================================================${NC}"
echo ""

if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}No running services found (PID file not found)${NC}"
    echo -e "${YELLOW}Checking for processes manually...${NC}"

    # Try to find and kill processes manually
    BACKEND_PID=$(pgrep -f "python -m app.main")
    FRONTEND_PID=$(pgrep -f "npm start")

    if [ -n "$BACKEND_PID" ]; then
        echo -e "${YELLOW}Found backend process: $BACKEND_PID${NC}"
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}✓ Backend stopped${NC}"
    fi

    if [ -n "$FRONTEND_PID" ]; then
        echo -e "${YELLOW}Found frontend process: $FRONTEND_PID${NC}"
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}✓ Frontend stopped${NC}"
    fi

    if [ -z "$BACKEND_PID" ] && [ -z "$FRONTEND_PID" ]; then
        echo -e "${GREEN}No processes found${NC}"
    fi
else
    echo -e "${BLUE}Stopping services...${NC}"

    while read pid; do
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}Stopping process $pid...${NC}"
            kill $pid 2>/dev/null || true

            # Wait for process to stop
            for i in {1..5}; do
                if ! ps -p $pid > /dev/null 2>&1; then
                    echo -e "${GREEN}✓ Process $pid stopped${NC}"
                    break
                fi
                sleep 1
            done

            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${RED}Force stopping process $pid...${NC}"
                kill -9 $pid 2>/dev/null || true
            fi
        fi
    done < "$PID_FILE"

    rm "$PID_FILE"
fi

# Clean up log files (optional)
read -p "Remove log files? (y/n, default: n): " CLEAN_LOGS
if [[ $CLEAN_LOGS =~ ^[Yy]$ ]]; then
    rm -f "$SCRIPT_DIR/backend.log" "$SCRIPT_DIR/frontend.log"
    echo -e "${GREEN}✓ Log files removed${NC}"
fi

echo ""
echo -e "${GREEN}=================================================="
echo "Shutdown complete!"
echo -e "==================================================${NC}"

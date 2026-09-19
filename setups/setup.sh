#!/usr/bin/env bash
#
# Mimic setup.
#
# Dependencies now install during the Docker build rather than on every
# container start, so this script only has to check prerequisites, create
# .env, and start the stack.

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m'

cd "$(dirname "$0")/.."

echo -e "${GREEN}=== Mimic setup ===${NC}"
echo

# --- 1. Docker ---------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}Docker is not installed.${NC}"
    echo "Install it from https://docs.docker.com/get-docker/ and run this again."
    exit 1
fi

COMPOSE="docker compose"
if ! docker compose version >/dev/null 2>&1; then
    if command -v docker-compose >/dev/null 2>&1; then
        COMPOSE="docker-compose"
    else
        echo -e "${RED}Docker Compose is not available.${NC}"
        echo "Install Docker Desktop, or the compose plugin, and run this again."
        exit 1
    fi
fi

if ! docker info >/dev/null 2>&1; then
    if command -v sudo >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker needs elevated permissions — using sudo.${NC}"
        COMPOSE="sudo $COMPOSE"
    else
        echo -e "${RED}Cannot talk to the Docker daemon.${NC}"
        echo "Make sure Docker is running, then try again."
        exit 1
    fi
fi
echo -e "${GREEN}✔${NC} Docker is ready"

# --- 2. Environment ----------------------------------------------------------
if [ -f .env ]; then
    echo -e "${GREEN}✔${NC} .env already exists ${DIM}(left untouched)${NC}"
else
    cp .env.example .env
    echo -e "${GREEN}✔${NC} Created .env from .env.example"
fi

API_PORT="$(grep -E '^API_PORT=' .env | cut -d= -f2 || true)"
UI_PORT="$(grep -E '^UI_PORT=' .env | cut -d= -f2 || true)"
API_PORT="${API_PORT:-5000}"
UI_PORT="${UI_PORT:-3000}"

# --- 3. Port check -----------------------------------------------------------
port_in_use() {
    if command -v ss >/dev/null 2>&1; then
        ss -ltn 2>/dev/null | grep -q ":$1 "
    elif command -v lsof >/dev/null 2>&1; then
        lsof -i ":$1" -sTCP:LISTEN >/dev/null 2>&1
    else
        return 1
    fi
}

for port in "$API_PORT" "$UI_PORT"; do
    if port_in_use "$port"; then
        echo -e "${YELLOW}!${NC} Port $port is already in use."
        echo "  Change API_PORT or UI_PORT in .env, or stop whatever is using it."
    fi
done

# --- 4. Start ----------------------------------------------------------------
echo
echo -n "Build and start Mimic now? [Y/n]: "
read -r reply
reply="${reply:-Y}"

if [[ ! "$reply" =~ ^[Yy]$ ]]; then
    echo
    echo "Nothing started. When you are ready:"
    echo -e "  ${DIM}$COMPOSE up --build${NC}"
    exit 0
fi

echo
echo -e "${GREEN}Starting Mimic…${NC} ${DIM}(first build takes a few minutes)${NC}"
echo -e "${DIM}The app will be at http://localhost:$UI_PORT — press Ctrl+C to stop.${NC}"
echo

$COMPOSE up --build

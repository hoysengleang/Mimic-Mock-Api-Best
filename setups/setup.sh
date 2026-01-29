#!/bin/bash

# COLORS
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== MIMIC SETUP WIZARD ===${NC}"

# 1. SMART PERMISSION CHECK
echo "Checking Docker permissions..."
DOCKER_COMPOSE="docker compose"

if ! docker info > /dev/null 2>&1; then
    if command -v sudo >/dev/null 2>&1; then
        echo -e "${YELLOW}Notice: Docker requires sudo. Switching mode.${NC}"
        DOCKER_COMPOSE="sudo docker compose"
    else
        echo -e "${RED}Error: Cannot connect to Docker Daemon.${NC}"
        exit 1
    fi
else
    echo "✔ Docker permission granted."
fi

# 2. CHECK DEPENDENCIES
MISSING_PACKAGES=false
if [ ! -f "src/Mimic.API/.deps_installed" ]; then MISSING_PACKAGES=true; fi
if [ ! -d "src/Mimic.UI/node_modules" ]; then MISSING_PACKAGES=true; fi

# 3. INSTALLATION
if [ "$MISSING_PACKAGES" = true ]; then
    echo ""
    echo -e "${YELLOW}Dependencies are missing.${NC}"
    echo -n "Do you want to install them using Docker? [y/N]: "
    read USE_DOCKER

    if [[ "$USE_DOCKER" =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Running installation...${NC}"
        
        $DOCKER_COMPOSE build
        
        echo "Installing backend packages..."
        $DOCKER_COMPOSE run --rm mimic-api sh -c "pip install --no-cache-dir -r /app/requirements.txt && touch /app/.deps_installed"

        echo "Installing Frontend packages..."
        $DOCKER_COMPOSE run --rm mimic-ui yarn install

        echo -e "${GREEN}✔ Installation Complete!${NC}"
    else
        echo -e "${RED}Skipped installation.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✔ All dependencies look good.${NC}"
fi

# 4. START
echo ""
echo -n "Do you want to start the project now? [y/N]: "
read START_APP

if [[ "$START_APP" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Starting Mimic... (Press Ctrl+C to stop)${NC}"
    $DOCKER_COMPOSE up
fi
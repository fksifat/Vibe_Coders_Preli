#!/bin/bash
# ==============================================================================
# QueueStorm EC2 Auto-Deployment & Setup Script (Ubuntu)
# ==============================================================================
# This script automates the installation of Docker, Docker Compose, and starts
# the QueueStorm FastAPI application on port 80 (or 8000).
# Run this script on your Ubuntu EC2 instance:
#   chmod +x deploy_ec2.sh
#   ./deploy_ec2.sh
# ==============================================================================

set -euo pipefail

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0;80m' # No Color
RESET='\033[0m'

echo -e "${BLUE}=====================================================${RESET}"
echo -e "${BLUE}     QueueStorm EC2 Deployment Automation Script     ${RESET}"
echo -e "${BLUE}=====================================================${RESET}"

# 1. Update and Upgrade System Packages
echo -e "\n${YELLOW}[1/5] Updating system packages...${RESET}"
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. Check and Install Docker
echo -e "\n${YELLOW}[2/5] Installing Docker & Docker Compose...${RESET}"
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release
    
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
      
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Add current user to the docker group so sudo is not needed
    sudo usermod -aG docker "$USER"
    echo -e "${GREEN}Docker installed successfully!${RESET}"
else
    echo -e "${GREEN}Docker is already installed.${RESET}"
fi



# 3. Handle Environment File
echo -e "\n${YELLOW}[3/5] Checking environment configuration...${RESET}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo -e "${YELLOW}Please edit the '.env' file and add your GEMINI_API_KEY.${RESET}"
    else
        echo "Creating blank .env file..."
        echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
    fi
else
    echo -e "${GREEN}.env file already exists.${RESET}"
fi

# 4. Prompt for GEMINI_API_KEY if default or empty
ENV_KEY=$(grep "GEMINI_API_KEY" .env | cut -d '=' -f2 | tr -d ' "') || true
if [ -z "$ENV_KEY" ] || [ "$ENV_KEY" == "your_gemini_api_key_here" ] || [ "$ENV_KEY" == "your-api-key-here" ]; then
    echo -e "${RED}WARNING: GEMINI_API_KEY is not configured in .env.${RESET}"
    read -p "Enter your GEMINI_API_KEY (or press Enter to skip and configure later): " USER_KEY
    if [ -n "$USER_KEY" ]; then
        # Replace the GEMINI_API_KEY line in .env
        sed -i "s|GEMINI_API_KEY=.*|GEMINI_API_KEY=$USER_KEY|g" .env
        echo -e "${GREEN}GEMINI_API_KEY updated in .env!${RESET}"
    fi
fi

# 5. Start the Application
echo -e "\n${YELLOW}[4/5] Building and starting QueueStorm application...${RESET}"
# We'll run it on port 80 by default. If the user wants to customize, they can change the compose port mapping.
echo -e "Starting containers in the background..."
sudo docker compose up --build -d

# 6. Verification
echo -e "\n${YELLOW}[5/5] Verifying deployment...${RESET}"
sleep 5
if curl -s http://localhost/health > /dev/null; then
    echo -e "${GREEN}SUCCESS: The QueueStorm service is live and healthy at http://localhost/health${RESET}"
else
    echo -e "${YELLOW}Warning: Direct health check to port 80 didn't respond yet. Running containers check...${RESET}"
    sudo docker compose ps
fi

echo -e "\n${BLUE}=====================================================${RESET}"
echo -e "${GREEN}                    DEPLOYMENT COMPLETE              ${RESET}"
echo -e "${BLUE}=====================================================${RESET}"
echo -e "1. Direct API Access: http://<your-ec2-public-ip>/"
echo -e "2. Interactive Docs:  http://<your-ec2-public-ip>/docs"
echo -e "3. Health Check:      http://<your-ec2-public-ip>/health"
echo -e ""
echo -e "To view logs, run:    ${YELLOW}docker compose logs -f${RESET}"
echo -e "To stop services:     ${YELLOW}docker compose down${RESET}"
echo -e "${BLUE}=====================================================${RESET}"
echo -e "${YELLOW}NOTE: If you cannot access the service externally, please ensure your"
echo -e "AWS EC2 Security Group allows Inbound TCP Traffic on port 80.${RESET}"

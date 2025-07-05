#!/bin/bash

# Test SSH Connection Script
echo "🔍 Testing SSH Connection to 91.99.118.65"
echo "=========================================="

SERVER_IP="91.99.118.65"
SSH_KEY="$HOME/.ssh/cmsvs_deploy_key"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[INFO]${NC} Testing basic connectivity..."

# Test ping
if ping -n 1 $SERVER_IP > /dev/null 2>&1 || ping -c 1 $SERVER_IP > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server is reachable${NC}"
else
    echo -e "${RED}❌ Server is not reachable${NC}"
    exit 1
fi

echo -e "${YELLOW}[INFO]${NC} Testing SSH key authentication..."

# Test SSH with key
if ssh -i $SSH_KEY -o ConnectTimeout=10 -o BatchMode=yes root@$SERVER_IP "echo 'SSH key authentication successful'" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH key authentication works!${NC}"
    echo -e "${GREEN}🚀 Ready to deploy! Run: ./deploy-production.sh${NC}"
else
    echo -e "${RED}❌ SSH key authentication failed${NC}"
    echo -e "${YELLOW}[INFO]${NC} Trying password authentication..."
    
    # Test SSH with password prompt
    if ssh -o ConnectTimeout=10 root@$SERVER_IP "echo 'SSH password authentication works'" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH password authentication works${NC}"
        echo -e "${YELLOW}[RECOMMENDATION]${NC} Set up SSH key for automated deployment"
        echo -e "${YELLOW}[NEXT STEP]${NC} Follow instructions in setup-ssh-access.md"
    else
        echo -e "${RED}❌ SSH connection failed${NC}"
        echo
        echo -e "${YELLOW}Possible solutions:${NC}"
        echo "1. Check if SSH is enabled on the server"
        echo "2. Verify the correct IP address: $SERVER_IP"
        echo "3. Check if port 22 is open"
        echo "4. Contact your hosting provider for SSH access"
        echo
        echo -e "${YELLOW}For detailed setup instructions, see:${NC} setup-ssh-access.md"
    fi
fi

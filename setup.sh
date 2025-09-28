#!/bin/bash

# Simplified Monero Mining Server Setup Script

echo "🚀 Setting up Monero Mining Server..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if script is run as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${YELLOW}⚠️  This script should not be run as root${NC}"
   echo "Please run as a regular user"
   exit 1
fi

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt &> /dev/null; then
            OS="ubuntu"
        elif command -v pacman &> /dev/null; then
            OS="arch"
        else
            OS="linux"
        fi
    else
        OS="unknown"
    fi
    echo -e "${BLUE}Detected OS: $OS${NC}"
}

# Install Python dependencies
install_python_deps() {
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 not found${NC}"
        case $OS in
            ubuntu)
                sudo apt update && sudo apt install -y python3 python3-pip
                ;;
            arch)
                sudo pacman -S python python-pip --noconfirm
                ;;
        esac
    fi
    
    python3 -m pip install --user -r requirements.txt
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
}

# Install XMRig
install_xmrig() {
    echo -e "${BLUE}Installing XMRig...${NC}"
    
    if command -v xmrig &> /dev/null; then
        echo -e "${GREEN}✅ XMRig already installed${NC}"
        return 0
    fi
    
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    case $OS in
        ubuntu|arch|linux)
            XMRIG_VERSION="6.24.0"
            XMRIG_URL="https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/xmrig-${XMRIG_VERSION}-linux-static-x64.tar.gz"
            
            wget -q "$XMRIG_URL"
            tar -xzf "xmrig-${XMRIG_VERSION}-linux-static-x64.tar.gz"
            sudo cp "xmrig-${XMRIG_VERSION}/xmrig" /usr/local/bin/
            sudo chmod +x /usr/local/bin/xmrig
            ;;
    esac
    
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    echo -e "${GREEN}✅ XMRig installed${NC}"
}

# Create example config
create_config() {
    echo -e "${BLUE}Creating example config...${NC}"
    
    cat > example_mining_config.json << 'EOF'
{
    "cpu_cores_num": 4,
    "cpu_ram": 8,
    "pool_url": "pool.supportxmr.com:443",
    "wallet_address": "YOUR_MONERO_WALLET_ADDRESS_REPLACE_THIS",
    "worker_id": "my-mining-rig-001",
    "password": "x"
}
EOF
    
    echo -e "${GREEN}✅ Config created${NC}"
}

# Test installation
test_installation() {
    echo -e "${BLUE}Testing installation...${NC}"
    
    if command -v xmrig &> /dev/null; then
        echo -e "${GREEN}✅ XMRig found${NC}"
    else
        echo -e "${RED}❌ XMRig not found${NC}"
        return 1
    fi
    
    if python3 -c "import fastapi, uvicorn, psutil, pydantic" 2>/dev/null; then
        echo -e "${GREEN}✅ Python dependencies OK${NC}"
    else
        echo -e "${RED}❌ Python dependencies missing${NC}"
        return 1
    fi
    
    return 0
}

# Main function
main() {
    echo -e "${BLUE}=== Monero Mining Setup ===${NC}"
    
    detect_os
    install_python_deps
    install_xmrig
    create_config
    
    if test_installation; then
        echo -e "${GREEN}✅ Setup completed successfully!${NC}"
        echo "Starting mining server..."
        python3 main.py
    else
        echo -e "${RED}❌ Setup failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"

#!/bin/bash

# Monero Mining Server Setup Script

echo "🚀 Setting up Monero Mining Server..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip for Python 3."
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if XMRig is available
if ! command -v xmrig &> /dev/null; then
    echo "⚠️  XMRig not found in PATH. Installing XMRig..."

    # Detect OS and install XMRig accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "🐧 Detected Linux. Installing XMRig..."

        # For Ubuntu/Debian
        if command -v apt &> /dev/null; then
            sudo apt update
            sudo apt install -y wget
            wget https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-static-x64.tar.gz
            tar -xzf xmrig-6.21.0-linux-static-x64.tar.gz
            sudo cp xmrig-6.21.0/xmrig /usr/local/bin/
            rm -rf xmrig-6.21.0*
            echo "✅ XMRig installed to /usr/local/bin/xmrig"
        fi

        # For CentOS/RHEL/Fedora
        if command -v yum &> /dev/null || command -v dnf &> /dev/null; then
            echo "Installing via package manager..."
            if command -v dnf &> /dev/null; then
                sudo dnf install -y wget
            else
                sudo yum install -y wget
            fi
            wget https://github.com/xmrig/xmrig/releases/download/v6.21.0/xmrig-6.21.0-linux-static-x64.tar.gz
            tar -xzf xmrig-6.21.0-linux-static-x64.tar.gz
            sudo cp xmrig-6.21.0/xmrig /usr/local/bin/
            rm -rf xmrig-6.21.0*
        fi

    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "🍎 Detected macOS. Installing XMRig..."
        if command -v brew &> /dev/null; then
            brew install xmrig
        else
            echo "Please install Homebrew first, then run: brew install xmrig"
        fi

    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "🪟 Detected Windows. Please manually download XMRig from:"
        echo "https://github.com/xmrig/xmrig/releases"
        echo "Extract and add to your PATH"
    fi
else
    echo "✅ XMRig found in PATH"
fi

# Create example configuration
echo "📝 Creating example configuration..."
cat > example_config.json << EOF
{
    "cpu_cores_num": 4,
    "cpu_ram": 8,
    "pool_url": "pool.supportxmr.com:443",
    "wallet_address": "YOUR_MONERO_WALLET_ADDRESS_HERE",
    "worker_id": "fastapi-miner-001",
    "password": "x"
}
EOF

echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Edit example_config.json with your Monero wallet address"
echo "2. Run: python3 monero_mining_server.py"
echo "3. Access API at: http://localhost:8000/docs"
echo ""
echo "📚 API Endpoints:"
echo "  POST /start - Start mining with configuration"
echo "  POST /stop  - Stop mining"
echo "  GET  /status - Get mining status"
echo "  GET  /system - Get system information"
echo ""
echo "⚠️  Remember to:"
echo "  - Use a real Monero wallet address"
echo "  - Check local laws regarding cryptocurrency mining"
echo "  - Monitor system temperature and power consumption"

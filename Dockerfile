FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    wget \
    curl \
    tar \
    gzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Install XMRig
ENV XMRIG_VERSION=6.24.0
RUN wget -q "https://github.com/xmrig/xmrig/releases/download/v${XMRIG_VERSION}/xmrig-${XMRIG_VERSION}-linux-static-x64.tar.gz" && \
    tar -xzf "xmrig-${XMRIG_VERSION}-linux-static-x64.tar.gz" && \
    cp "xmrig-${XMRIG_VERSION}/xmrig" /usr/local/bin/ && \
    chmod +x /usr/local/bin/xmrig && \
    rm -rf "xmrig-${XMRIG_VERSION}*"

# Create example config
RUN echo '{\
    "cpu_cores_num": 4,\
    "cpu_ram": 8,\
    "pool_url": "pool.supportxmr.com:443",\
    "wallet_address": "YOUR_MONERO_WALLET_ADDRESS_REPLACE_THIS",\
    "worker_id": "my-mining-rig-001",\
    "password": "x"\
}' > example_mining_config.json

# Copy application files
COPY main.py .
COPY mining_config.json* ./

# Expose port
EXPOSE 8000

# Start the mining server
CMD ["python3", "main.py"]

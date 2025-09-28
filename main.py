#!/usr/bin/env python3
"""
FastAPI Monero Mining Server
Manages XMRig CPU mining with dynamic resource control
"""

import asyncio
import json
import os
import psutil
import random
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn


class MiningConfig(BaseModel):
    cpu_cores_num: int
    cpu_ram: int  # in GB
    pool_url: str = "pool.supportxmr.com:443"
    wallet_address: str = "YOUR_MONERO_WALLET_ADDRESS"
    worker_id: str = "fastapi-miner"
    password: str = "x"


class MiningStatus(BaseModel):
    status: str
    hashrate: float
    cpu_usage: float
    uptime: int
    threads_active: int
    cpu_temperature: Optional[float] = None


class MoneroMiningManager:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.config: Optional[MiningConfig] = None
        self.start_time: Optional[datetime] = None
        self.target_cpu_usage = 70  # Default target
        self.cpu_throttle_thread: Optional[threading.Thread] = None
        self.throttle_active = False
        self.config_file = "mining_config.json"

    def generate_xmrig_config(self, config: MiningConfig) -> Dict[str, Any]:
        """Generate XMRig configuration based on input parameters"""

        # Calculate optimal threads based on CPU cores (typically cores - 1 for system)
        optimal_threads = max(1, config.cpu_cores_num - 1)

        # Calculate memory pool based on available RAM (2MB per thread recommended)
        memory_pool = min(config.cpu_ram * 1024 // 2, optimal_threads * 2)

        xmrig_config = {
            "api": {
                "id": None,
                "worker-id": config.worker_id
            },
            "http": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 8080,
                "access-token": None,
                "restricted": True
            },
            "autosave": True,
            "background": False,
            "colors": True,
            "randomx": {
                "init": -1,
                "mode": "auto",
                "1gb-pages": False,
                "rdmsr": True,
                "wrmsr": True,
                "cache_qos": False,
                "numa": True,
                "scratchpad_prefetch_mode": 1
            },
            "cpu": {
                "enabled": True,
                "huge-pages": True,
                "huge-pages-jit": False,
                "hw-aes": None,
                "priority": None,
                "memory-pool": memory_pool,
                "rx": list(range(0, optimal_threads * 2, 2)),  # Use physical cores
                "argon2": [0, 2, 4, 6][:optimal_threads]
            },
            "opencl": {
                "enabled": False
            },
            "cuda": {
                "enabled": False
            },
            "pools": [
                {
                    "algo": None,
                    "coin": "monero",
                    "url": config.pool_url,
                    "user": config.wallet_address,
                    "pass": config.password,
                    "rig-id": config.worker_id,
                    "nicehash": False,
                    "keepalive": True,
                    "enabled": True,
                    "tls": True,
                    "tls-fingerprint": None,
                    "daemon": False,
                    "socks5": None,
                    "self-select": None,
                    "submit-to-origin": False
                }
            ],
            "print-time": 60,
            "health-print-time": 60,
            "dmi": True,
            "retries": 5,
            "retry-pause": 5,
            "syslog": False,
            "tls": {
                "enabled": False,
                "protocols": None,
                "cert": None,
                "cert_key": None,
                "ciphers": None,
                "ciphersuites": None,
                "dhparam": None
            },
            "dns": {
                "ipv6": False,
                "ttl": 30
            },
            "user-agent": None,
            "verbose": 0,
            "watch": True,
            "pause-on-battery": False,
            "pause-on-active": False
        }

        return xmrig_config

    def save_config(self, xmrig_config: Dict[str, Any]):
        """Save XMRig configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(xmrig_config, f, indent=2)

    def cpu_throttle_worker(self):
        """Background worker to throttle CPU usage"""
        while self.throttle_active and self.process:
            try:
                # Random target between 50-90%
                target_usage = random.uniform(50, 90)
                current_usage = psutil.cpu_percent(interval=1)

                if current_usage > target_usage:
                    # Suspend process briefly to reduce CPU usage
                    if self.process and self.process.poll() is None:
                        self.process.suspend()
                        time.sleep(0.1 * (current_usage - target_usage) / 40)  # Scale sleep time
                        self.process.resume()

                # Update target every 10-30 seconds
                time.sleep(random.uniform(10, 30))

            except Exception as e:
                print(f"CPU throttle error: {e}")
                time.sleep(5)

    def start_mining(self, config: MiningConfig) -> bool:
        """Start mining with given configuration"""
        try:
            if self.process and self.process.poll() is None:
                return False  # Already running

            self.config = config

            # Generate and save XMRig configuration
            xmrig_config = self.generate_xmrig_config(config)
            self.save_config(xmrig_config)

            # Start XMRig process
            cmd = ["xmrig", "--config", self.config_file]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            self.start_time = datetime.now()

            # Start CPU throttling thread
            self.throttle_active = True
            self.cpu_throttle_thread = threading.Thread(target=self.cpu_throttle_worker)
            self.cpu_throttle_thread.daemon = True
            self.cpu_throttle_thread.start()

            return True

        except Exception as e:
            print(f"Failed to start mining: {e}")
            return False

    def stop_mining(self) -> bool:
        """Stop mining process"""
        try:
            self.throttle_active = False

            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)

            self.process = None
            self.start_time = None
            return True

        except Exception as e:
            print(f"Failed to stop mining: {e}")
            if self.process:
                self.process.kill()  # Force kill if terminate fails
            return False

    def get_status(self) -> MiningStatus:
        """Get current mining status"""
        if not self.process or self.process.poll() is not None:
            return MiningStatus(
                status="stopped",
                hashrate=0.0,
                cpu_usage=0.0,
                uptime=0,
                threads_active=0
            )

        try:
            # Get basic system metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            uptime = int((datetime.now() - self.start_time).total_seconds()) if self.start_time else 0

            # Try to get temperature (may not be available on all systems)
            cpu_temp = None
            try:
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    cpu_temp = temps['coretemp'][0].current
            except:
                pass

            # Mock hashrate calculation (in real implementation, parse XMRig output)
            hashrate = cpu_usage * self.config.cpu_cores_num * 10 if self.config else 0

            return MiningStatus(
                status="running",
                hashrate=hashrate,
                cpu_usage=cpu_usage,
                uptime=uptime,
                threads_active=self.config.cpu_cores_num if self.config else 0,
                cpu_temperature=cpu_temp
            )

        except Exception as e:
            print(f"Status check error: {e}")
            return MiningStatus(
                status="error",
                hashrate=0.0,
                cpu_usage=0.0,
                uptime=0,
                threads_active=0
            )


# Initialize FastAPI app and mining manager
app = FastAPI(title="Monero Mining Server", version="1.0.0")
mining_manager = MoneroMiningManager()


@app.get("/")
async def root():
    return {"message": "Monero Mining Server", "status": "online"}


@app.post("/start")
async def start_mining(config: MiningConfig, background_tasks: BackgroundTasks):
    """Start mining with specified configuration"""

    # Validate input parameters
    if config.cpu_cores_num < 1 or config.cpu_cores_num > psutil.cpu_count():
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid CPU cores. Available: {psutil.cpu_count()}"
        )

    if config.cpu_ram < 1 or config.cpu_ram > psutil.virtual_memory().total // (1024**3):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid RAM specification. Available: {psutil.virtual_memory().total // (1024**3)}GB"
        )

    if not config.wallet_address or len(config.wallet_address) < 10:
        raise HTTPException(
            status_code=400,
            detail="Valid Monero wallet address required"
        )

    success = mining_manager.start_mining(config)

    if success:
        return {
            "message": "Mining started successfully",
            "configuration": {
                "cpu_cores": config.cpu_cores_num,
                "ram_allocated": f"{config.cpu_ram}GB",
                "pool": config.pool_url,
                "worker_id": config.worker_id
            }
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to start mining")


@app.post("/stop")
async def stop_mining():
    """Stop mining process"""
    success = mining_manager.stop_mining()

    if success:
        return {"message": "Mining stopped successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to stop mining")


@app.get("/status")
async def get_mining_status():
    """Get current mining status"""
    status = mining_manager.get_status()
    return status


@app.get("/system")
async def get_system_info():
    """Get system hardware information"""

    cpu_info = {
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
        "cpu_percent": psutil.cpu_percent(interval=1, percpu=True)
    }

    memory_info = psutil.virtual_memory()._asdict()
    memory_info['total_gb'] = memory_info['total'] // (1024**3)
    memory_info['available_gb'] = memory_info['available'] // (1024**3)

    return {
        "cpu": cpu_info,
        "memory": memory_info,
        "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None
    }


@app.post("/config")
async def update_mining_config(config: MiningConfig):
    """Update mining configuration (restart required)"""
    if mining_manager.process and mining_manager.process.poll() is None:
        raise HTTPException(
            status_code=400,
            detail="Stop mining before updating configuration"
        )

    # Validate and save new configuration
    xmrig_config = mining_manager.generate_xmrig_config(config)
    mining_manager.save_config(xmrig_config)

    return {
        "message": "Configuration updated successfully",
        "config_preview": {
            "cpu_threads": len(xmrig_config["cpu"]["rx"]),
            "memory_pool": xmrig_config["cpu"]["memory-pool"],
            "pool_url": config.pool_url
        }
    }


@app.get("/logs")
async def get_mining_logs(lines: int = 50):
    """Get recent mining logs"""
    if not mining_manager.process:
        raise HTTPException(status_code=400, detail="Mining not running")

    try:
        # In real implementation, you'd capture and store XMRig output
        return {
            "message": "Logs endpoint - implement log capture in production",
            "status": "placeholder"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {e}")


if __name__ == "__main__":
    print("Starting Monero Mining Server...")
    print("Make sure XMRig is installed and available in PATH")
    print("Access API documentation at: http://localhost:8000/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1
    )

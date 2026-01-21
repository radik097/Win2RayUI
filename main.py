#!/usr/bin/env python3
"""
V2Ray Core Manager - WebUI wrapper for V2Ray proxy management
"""
import json
import base64
import subprocess
import os
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI(title="V2Ray Core Manager", version="1.0.0")

# Global state
v2ray_process: Optional[subprocess.Popen] = None
current_config: Optional[Dict[str, Any]] = None
proxy_list: List[Dict[str, Any]] = []

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
CONFIG_DIR = BASE_DIR / "config"
V2RAY_CONFIG_PATH = CONFIG_DIR / "config.json"

# Create directories if they don't exist
CONFIG_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Repository list file
REPO_LIST_FILE = CONFIG_DIR / "repositories.json"


def parse_vmess_link(vmess_link: str) -> Optional[Dict[str, Any]]:
    """
    Parse a vmess:// link into a dictionary
    
    Format: vmess://base64encoded_json
    """
    try:
        if not vmess_link.startswith("vmess://"):
            return None
        
        # Decode base64
        encoded = vmess_link[8:]  # Remove 'vmess://'
        # Add padding if needed
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += '=' * padding
        
        decoded = base64.b64decode(encoded).decode('utf-8')
        vmess_data = json.loads(decoded)
        
        return vmess_data
    except Exception as e:
        print(f"Error parsing vmess link: {e}")
        return None


def create_v2ray_config(vmess_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a V2Ray config.json from parsed vmess data
    """
    config = {
        "log": {
            "loglevel": "info"
        },
        "inbounds": [
            {
                "port": 1080,
                "protocol": "socks",
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                },
                "settings": {
                    "auth": "noauth",
                    "udp": True
                }
            },
            {
                "port": 1081,
                "protocol": "http",
                "settings": {}
            }
        ],
        "outbounds": [
            {
                "protocol": "vmess",
                "settings": {
                    "vnext": [
                        {
                            "address": vmess_data.get("add", ""),
                            "port": int(vmess_data.get("port", 443)),
                            "users": [
                                {
                                    "id": vmess_data.get("id", ""),
                                    "alterId": int(vmess_data.get("aid", 0)),
                                    "security": vmess_data.get("scy", "auto")
                                }
                            ]
                        }
                    ]
                },
                "streamSettings": {
                    "network": vmess_data.get("net", "tcp"),
                    "security": vmess_data.get("tls", ""),
                }
            }
        ]
    }
    
    # Add transport specific settings
    net = vmess_data.get("net", "tcp")
    if net == "ws":
        config["outbounds"][0]["streamSettings"]["wsSettings"] = {
            "path": vmess_data.get("path", "/"),
            "headers": {
                "Host": vmess_data.get("host", "")
            }
        }
    elif net == "tcp" and vmess_data.get("type") == "http":
        config["outbounds"][0]["streamSettings"]["tcpSettings"] = {
            "header": {
                "type": "http",
                "request": {
                    "path": [vmess_data.get("path", "/")],
                    "headers": {
                        "Host": [vmess_data.get("host", "")]
                    }
                }
            }
        }
    
    return config


def download_proxy_links(repos: List[str]) -> List[str]:
    """
    Download proxy links from repository list
    Returns a list of vmess:// links
    """
    links = []
    
    for repo_url in repos:
        try:
            # Basic URL validation
            if not repo_url.startswith(('http://', 'https://')):
                print(f"Invalid URL scheme: {repo_url}")
                continue
            
            # Download with size limit (5MB max)
            response = requests.get(repo_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Read with size limit
            content = ""
            size = 0
            max_size = 5 * 1024 * 1024  # 5MB
            
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    size += len(chunk)
                    if size > max_size:
                        print(f"Repository {repo_url} exceeds size limit")
                        break
                    content += chunk
            
            # Parse the content - assuming it contains vmess:// links
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('vmess://'):
                    links.append(line)
        except Exception as e:
            print(f"Error downloading from {repo_url}: {e}")
    
    return links


def start_v2ray(config_path: Path) -> bool:
    """
    Start the v2ray process with the given config
    """
    global v2ray_process
    
    # Stop existing process if running
    stop_v2ray()
    
    try:
        # Try to find v2ray binary
        v2ray_bin = "v2ray"
        
        # Check if v2ray binary exists in common locations
        possible_paths = [
            "/usr/local/bin/v2ray",
            "/usr/bin/v2ray",
            "./v2ray",
            str(BASE_DIR / "v2ray"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                v2ray_bin = path
                break
        
        # Start v2ray process
        v2ray_process = subprocess.Popen(
            [v2ray_bin, "-config", str(config_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        return True
    except Exception as e:
        print(f"Error starting v2ray: {e}")
        return False


def stop_v2ray() -> bool:
    """
    Stop the running v2ray process
    """
    global v2ray_process
    
    if v2ray_process is not None:
        try:
            if os.name == 'nt':
                # Windows
                v2ray_process.terminate()
            else:
                # Unix-like
                os.killpg(os.getpgid(v2ray_process.pid), signal.SIGTERM)
            
            v2ray_process.wait(timeout=5)
            v2ray_process = None
            return True
        except Exception as e:
            print(f"Error stopping v2ray: {e}")
            try:
                v2ray_process.kill()
                v2ray_process = None
            except:
                pass
    
    return True


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Main page - show proxy list and controls
    """
    return templates.TemplateResponse("index.html", {
        "request": request,
        "proxies": proxy_list,
        "v2ray_running": v2ray_process is not None and v2ray_process.poll() is None
    })


@app.get("/api/proxies/refresh")
async def refresh_proxies():
    """
    Refresh proxy list from repositories
    """
    global proxy_list
    
    try:
        # Load repository list
        if not REPO_LIST_FILE.exists():
            # Create default repository list
            default_repos = {
                "repositories": [
                    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt"
                ]
            }
            REPO_LIST_FILE.write_text(json.dumps(default_repos, indent=2))
        
        repo_config = json.loads(REPO_LIST_FILE.read_text())
        repos = repo_config.get("repositories", [])
        
        # Download links
        vmess_links = download_proxy_links(repos)
        
        # Parse links
        proxy_list = []
        for idx, link in enumerate(vmess_links):
            parsed = parse_vmess_link(link)
            if parsed:
                proxy_list.append({
                    "id": idx,
                    "name": parsed.get("ps", f"Proxy {idx}"),
                    "address": parsed.get("add", ""),
                    "port": parsed.get("port", ""),
                    "link": link,
                    "data": parsed
                })
        
        return {"success": True, "count": len(proxy_list), "proxies": proxy_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxy/start/{proxy_id}")
async def start_proxy(proxy_id: int):
    """
    Start v2ray with the selected proxy
    """
    global current_config
    
    try:
        # Find proxy
        proxy = None
        for p in proxy_list:
            if p["id"] == proxy_id:
                proxy = p
                break
        
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")
        
        # Create config
        config = create_v2ray_config(proxy["data"])
        current_config = config
        
        # Save config
        V2RAY_CONFIG_PATH.write_text(json.dumps(config, indent=2))
        
        # Start v2ray
        success = start_v2ray(V2RAY_CONFIG_PATH)
        
        if success:
            return {
                "success": True,
                "message": f"Started proxy: {proxy['name']}",
                "proxy": proxy['name']
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start v2ray")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxy/stop")
async def stop_proxy():
    """
    Stop the running v2ray process
    """
    try:
        success = stop_v2ray()
        return {"success": success, "message": "V2Ray stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """
    Get current v2ray status
    """
    running = v2ray_process is not None and v2ray_process.poll() is None
    
    status = {
        "running": running,
        "proxy_count": len(proxy_list)
    }
    
    if running and current_config:
        try:
            vnext = current_config["outbounds"][0]["settings"]["vnext"][0]
            status["current_proxy"] = {
                "address": vnext["address"],
                "port": vnext["port"]
            }
        except:
            pass
    
    return status


if __name__ == "__main__":
    import uvicorn
    # NOTE: For production, bind to 127.0.0.1 only or add authentication
    # Current binding (0.0.0.0) exposes the service to the network
    uvicorn.run(app, host="0.0.0.0", port=8000)

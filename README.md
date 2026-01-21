# V2Ray Core Manager (WebUI wrapper)

A simple Python FastAPI wrapper that provides a WebUI for managing V2Ray proxy connections.

## Features

- 📥 Downloads proxy links (vmess links) from a repository list
- 🔄 Parses vmess links into V2Ray `config.json`
- ▶️ Starts/stops the `v2ray` binary with the generated config
- 🌐 Simple WebUI to pick a proxy and restart the core
- 🚀 FastAPI backend with modern responsive UI

## Requirements

- Python 3.8+
- V2Ray core binary (optional: Go if you need to build `v2ray` from source)

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install V2Ray Core

#### Option A: Download pre-built binary (Recommended)

**Linux/macOS:**
```bash
# Download and install v2ray
curl -L https://github.com/v2fly/v2ray-core/releases/latest/download/v2ray-linux-64.zip -o v2ray.zip
unzip v2ray.zip
chmod +x v2ray
sudo mv v2ray /usr/local/bin/
```

**Windows:**
Download from [V2Ray Releases](https://github.com/v2fly/v2ray-core/releases) and add to PATH.

#### Option B: Build from source

If you need to build `v2ray` from source:

```bash
# Install Go (if not already installed)
# Download from https://golang.org/dl/

# Clone and build v2ray
git clone https://github.com/v2fly/v2ray-core.git
cd v2ray-core
go build -o v2ray ./main
sudo mv v2ray /usr/local/bin/
```

## Usage

### 1. Configure Repository List

Edit `config/repositories.json` to add your vmess link sources:

```json
{
  "repositories": [
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    "https://example.com/your-vmess-list.txt"
  ]
}
```

### 2. Start the WebUI

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Access the WebUI

Open your browser and navigate to:
```
http://localhost:8000
```

### 4. Use the WebUI

1. Click **"Refresh Proxies"** to download and parse vmess links from your configured repositories
2. Browse the available proxies
3. Click **"Connect"** on any proxy to start V2Ray with that configuration
4. Click **"Stop"** to stop the V2Ray process
5. The status indicator shows whether V2Ray is running

## API Endpoints

- `GET /` - WebUI homepage
- `GET /api/status` - Get V2Ray status
- `GET /api/proxies/refresh` - Refresh proxy list from repositories
- `POST /api/proxy/start/{proxy_id}` - Start V2Ray with selected proxy
- `POST /api/proxy/stop` - Stop V2Ray

## Configuration

### Proxy Configuration

The application uses SOCKS5 and HTTP proxies on the following ports:
- SOCKS5: `localhost:1080`
- HTTP: `localhost:1081`

You can configure your browser or system to use these proxies when V2Ray is running.

### V2Ray Binary Location

The application looks for the v2ray binary in the following locations:
1. `/usr/local/bin/v2ray`
2. `/usr/bin/v2ray`
3. `./v2ray` (current directory)
4. `<app_directory>/v2ray`

## Development

### Project Structure

```
Win2RayUI/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── templates/              # HTML templates
│   └── index.html         # WebUI
├── config/                # Configuration files
│   ├── repositories.json  # Repository list
│   └── config.json        # Generated V2Ray config
└── README.md
```

## Security Notes

⚠️ **Important Security Considerations:**

1. This application starts local proxy servers (SOCKS5/HTTP) without authentication
2. Only run on trusted networks or bind to localhost only
3. V2Ray process runs with the same privileges as the Python application
4. Repository URLs should be from trusted sources only

## Troubleshooting

### V2Ray won't start

- Ensure v2ray binary is installed and accessible
- Check that ports 1080 and 1081 are not in use
- Verify the generated config is valid JSON

### No proxies showing

- Check your internet connection
- Verify repository URLs are accessible
- Check console logs for error messages

### Permission denied

- On Linux/macOS, you may need to make v2ray executable: `chmod +x v2ray`
- Some systems require elevated privileges to bind to low ports

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes. Users are responsible for complying with local laws and regulations regarding proxy usage. 

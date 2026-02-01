# Remote Tunnel Access Guide

## Overview

This guide explains how to access the Shape Shifter Project Editor remotely using GitHub's VS Code Remote Tunnels feature.

## Prerequisites

- VS Code installed locally
- GitHub account
- Application running (backend on port 8012, frontend on port 5173)

## Setup Steps

### 1. Enable Remote Tunnels in VS Code

#### On the Remote Machine (where the app is running):

1. **Install VS Code Server** (if not already installed):
   ```bash
   # VS Code will prompt to install when you first use tunnels
   # Or install manually:
   code tunnel --install
   ```

2. **Start the Tunnel**:
   ```bash
   # Login with GitHub
   code tunnel --accept-server-license-terms
   
   # Follow the prompts to authenticate with GitHub
   # You'll get a URL like: https://github.com/login/device
   # Enter the code shown
   ```

3. **Note the Tunnel URL**:
   After authentication, you'll see something like:
   ```
   * 
   * Visual Studio Code Server
   * 
   * By using the software, you agree to
   * the Visual Studio Code Server License Terms (https://aka.ms/vscode-server-license)
   * 
   * Tunnel name: machine-name-12345
   * vscode.dev URL: https://vscode.dev/tunnel/machine-name-12345
   ```

### 2. Connect from Your Local Machine

1. **Open the Tunnel URL** in your browser or VS Code:
   - Browser: Navigate to the `vscode.dev` URL from step 1
   - VS Code Desktop: Use Command Palette (Ctrl+Shift+P) → "Remote-Tunnels: Connect to Tunnel" → Enter tunnel name

2. **Open the Workspace**:
   - File → Open Folder → `/home/roger/source/sead_shape_shifter`

### 3. Start the Application

#### Option A: Using Makefile (Recommended)

1. **Start Backend** (in one terminal):
   ```bash
   make backend-run
   # Backend will run on http://localhost:8012
   ```

2. **Start Frontend** (in another terminal):
   ```bash
   make frontend-run
   # Frontend will run on http://localhost:5173
   ```

#### Option B: Manual Start

1. **Backend**:
   ```bash
   cd backend
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8012
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev -- --host
   ```

### 4. Forward Ports

VS Code will automatically detect running servers on ports 8012 and 5173.

#### Manual Port Forwarding:

1. **Open Ports Panel**:
   - View → Ports (or Ctrl+Shift+P → "Ports: Focus on Ports View")

2. **Forward Port 8012** (Backend):
   - Click "+ Forward a Port"
   - Enter: 8012
   - **Set Visibility**: Right-click port → Change Port Visibility → **Public**
   - You'll get a URL like: `https://machine-name-12345-8012.preview.app.github.dev`

3. **Forward Port 5173** (Frontend):
   - Click "+ Forward a Port"
   - Enter: 5173
   - **Set Visibility**: Right-click port → Change Port Visibility → **Public**
   - You'll get a URL like: `https://machine-name-12345-5173.preview.app.github.dev`

### 5. Configure Frontend for Remote Access

Create a `.env.local` file in the frontend directory with the remote backend URL:

```bash
cd frontend
cat > .env.local << 'EOF'
# Remote tunnel backend URL (replace with your actual URL from step 4)
VITE_API_BASE_URL=https://machine-name-12345-8012.preview.app.github.dev
EOF
```

**Replace** `machine-name-12345-8012.preview.app.github.dev` with your actual forwarded backend port URL.

### 6. Restart Frontend

After creating `.env.local`:

```bash
# Stop the frontend (Ctrl+C in the terminal)
# Restart it
npm run dev -- --host
```

### 7. Access the Application

Open your **frontend tunnel URL** in a browser:
```
https://machine-name-12345-5173.preview.app.github.dev
```

The frontend will now communicate with the backend through the tunneled URLs!

## Troubleshooting

### Issue: "CORS Error"

> CORS problem still persisted. But when I opened https://tgx7q4bq-8012.euw.devtunnels.ms/ in a browser, I got a redirect message. After that the CORS problem disappeared..

> Ah, that's a DevTunnels-specific security feature! DevTunnels require you to visit the backend URL in a browser first to authenticate/accept the tunnel before cross-origin requests will work. This is expected behavior.

For future reference, when using DevTunnels:

1. Always visit the backend URL first (https://tgx7q4bq-8012.euw.devtunnels.ms/) in your browser
2. Accept any authentication prompts or security warnings
3. Then the frontend can make cross-origin requests to it
4. This is a one-time requirement per tunnel session. If you restart the tunnel or get a new tunnel URL, you'll need to visit it again.

The CORS configuration we added is still correct and necessary - the initial block was just the DevTunnels authentication gate, not a CORS issue per se.


### Issue: "Cannot connect to backend"

**Solution 1: Check Port Visibility**
- Ports must be set to **Public** (not Private)
- Right-click port in Ports panel → Change Port Visibility → Public

**Solution 2: Check .env.local**
- Ensure `VITE_API_BASE_URL` points to the correct forwarded backend URL
- URL should include `https://` and the full GitHub preview domain
- No trailing slash

**Solution 3: Check Backend Host**
- Backend must bind to `0.0.0.0` (not `127.0.0.1`)
- Add `--host 0.0.0.0` to uvicorn command:
  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8012
  ```

**Solution 4: Check CORS**
- Backend must allow the frontend tunnel domain
- Update `backend/app/main.py` CORS origins if needed

### Issue: "Port forwarding not working"

**Solution 1: Authenticate GitHub**
- Run: `code tunnel user logout`
- Run: `code tunnel user login`
- Restart tunnel

**Solution 2: Check Firewall**
- Ensure ports 8012 and 5173 are not blocked
- Check with: `netstat -tuln | grep -E '8012|5173'`

**Solution 3: Restart Tunnel**
- Stop tunnel (Ctrl+C)
- Restart: `code tunnel --accept-server-license-terms`

### Issue: "Tunnel disconnects frequently"

**Solution**: Use a persistent tunnel service:
```bash
# Create a systemd service (Linux)
sudo nano /etc/systemd/system/code-tunnel.service
```

```ini
[Unit]
Description=VS Code Tunnel
After=network.target

[Service]
Type=simple
User=roger
WorkingDirectory=/home/roger
ExecStart=/usr/bin/code tunnel --accept-server-license-terms --name shapeshifter-tunnel
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable code-tunnel
sudo systemctl start code-tunnel
sudo systemctl status code-tunnel
```

### Issue: "Mixed content errors"

**Cause**: Frontend (HTTPS) trying to access backend (HTTP)

**Solution**: Both frontend and backend must use the same protocol (HTTPS via tunnel)
- Ensure both ports are forwarded
- Use the tunnel URLs for both services
- Check .env.local uses `https://` not `http://`

### Issue: "API requests timeout"

**Solution**: Increase timeout in Vite config:

```bash
cd frontend
```

Edit `vite.config.ts`:
```typescript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: process.env.VITE_API_BASE_URL || 'http://localhost:8012',
      changeOrigin: true,
      timeout: 300000, // 5 minutes
    },
  },
},
```

## Alternative: Using ngrok

If GitHub tunnels don't work, you can use ngrok:

### Setup ngrok

1. **Install ngrok**:
   ```bash
   # Linux
   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
   tar -xvzf ngrok-v3-stable-linux-amd64.tgz
   sudo mv ngrok /usr/local/bin/
   
   # Mac
   brew install ngrok
   ```

2. **Authenticate**:
   ```bash
   ngrok config add-authtoken YOUR_TOKEN
   # Get token from: https://dashboard.ngrok.com/get-started/your-authtoken
   ```

3. **Start tunnels**:
   ```bash
   # Backend (terminal 1)
   ngrok http 8012
   # Note the URL: https://abc123.ngrok.io
   
   # Frontend (terminal 2)
   ngrok http 5173
   # Note the URL: https://def456.ngrok.io
   ```

4. **Configure frontend**:
   ```bash
   cd frontend
   cat > .env.local << 'EOF'
   VITE_API_BASE_URL=https://abc123.ngrok.io
   EOF
   ```

5. **Access**: Open `https://def456.ngrok.io` in browser

## Docker Remote Access

For production-like remote access using Docker:

1. **Update docker-compose.yml** to bind to all interfaces:
   ```yaml
   services:
     backend:
       ports:
         - "0.0.0.0:8012:8012"
     frontend:
       ports:
         - "0.0.0.0:80:80"
   ```

2. **Forward ports**: 80 and 8012

3. **Access**: Use tunnel URLs (no .env.local needed, nginx handles routing)

## Security Notes

⚠️ **Important Security Considerations**:

1. **Public Ports**: Making ports public allows anyone with the URL to access them
2. **Authentication**: Consider adding authentication to your application
3. **Temporary Access**: Use tunnels only for testing, not production
4. **Rate Limiting**: GitHub may rate-limit forwarded ports
5. **Data Safety**: Don't expose sensitive data through tunnels

## Quick Reference

### Common Commands

```bash
# Start tunnel
code tunnel --accept-server-license-terms

# Check tunnel status
code tunnel status

# List running tunnels
code tunnel list

# Stop tunnel
code tunnel service uninstall  # Stops persistent service

# Backend
make backend-run

# Frontend
make frontend-run

# Check ports
netstat -tuln | grep -E '8012|5173'
```

### URLs to Remember

- Frontend: `https://[tunnel-name]-5173.preview.app.github.dev`
- Backend: `https://[tunnel-name]-8012.preview.app.github.dev`
- API Docs: `https://[tunnel-name]-8012.preview.app.github.dev/api/v1/docs`

### Environment Variables

```bash
# .env.local (frontend)
VITE_API_BASE_URL=https://[tunnel-name]-8012.preview.app.github.dev
VITE_ENV=development
```

## Support

If you continue to have issues:

1. Check VS Code output: View → Output → "Remote-Tunnel" or "Ports"
2. Check browser console for errors (F12)
3. Check backend logs in terminal
4. Verify ports are listening: `netstat -tuln | grep -E '8012|5173'`
5. Test backend directly: `curl https://[tunnel-url]-8012.preview.app.github.dev/api/v1/health`

## Summary

✅ **Setup Steps**:
1. Start tunnel: `code tunnel --accept-server-license-terms`
2. Connect via vscode.dev URL
3. Start backend: `make backend-run`
4. Start frontend: `make frontend-run`
5. Forward ports 8012 and 5173 (set to Public)
6. Create `frontend/.env.local` with backend tunnel URL
7. Restart frontend
8. Access frontend tunnel URL in browser

🎯 **Key Points**:
- Ports must be **Public** (not Private)
- Backend URL in `.env.local` must use **HTTPS** tunnel URL
- Backend must bind to **0.0.0.0** (not 127.0.0.1)
- Restart frontend after changing `.env.local`

Happy remote testing! 🚀

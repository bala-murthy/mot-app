# MOT Nexus – Windows Server Deployment Guide

## Prerequisites

| Requirement | Version | Where to get it |
|---|---|---|
| Windows | 10 / 11 / Server 2016 or later | — |
| Python | 3.11 or 3.12 | https://www.python.org/downloads/ |
| A modern browser | Chrome / Edge / Firefox | Built-in or your standard corporate browser |

> **Python install tip:** When the Python installer runs, tick **"Add Python to PATH"**
> before clicking Install Now. Without this, none of the commands below will work.

---

## No application code changes required

The application code uses Python's `os.path` (cross-platform) throughout.
Everything works on Windows without modification.

One intentional difference from Linux: the server runs with `--workers 1` instead of 4.
Windows does not support the `fork` system call that multiple uvicorn workers need.
A single async worker is still highly efficient — FastAPI handles many concurrent
requests within that one process. For an internal enterprise tool this is more than sufficient.

---

## Step 1 – Copy the project to the Windows server

Copy the entire `mot-portal` folder to the server. Recommended location:

```
C:\mot-nexus\
```

You can use a USB drive, a shared network folder, or any file transfer method.
The folder should look like this when copied:

```
C:\mot-nexus\
  backend\
  frontend\
  start_prod.bat
  start_prod.ps1
  setup_windows.ps1
  install_service_nssm.ps1
  nginx_windows.conf
  ...
```

---

## Step 2 – Run the one-time setup

Open **PowerShell as Administrator** (right-click the Start menu → "Windows PowerShell (Admin)").

Allow PowerShell scripts to run (only needed once per machine):
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Type `Y` and press Enter when prompted.

Then run the setup script:
```powershell
cd C:\mot-nexus
.\setup_windows.ps1
```

This script will:
- Verify Python is installed
- Install the `uv` package manager
- Create a Python virtual environment (`.venv` folder)
- Install all dependencies
- Create the database and load sample data

Expected output (last few lines):
```
[5/5] Initialising database...
      Database seeded with sample data.

====================================================
  Setup complete!
  Run: .\start_prod.bat  to start the application
====================================================
```

---

## Step 3 – Open the firewall port

Still in the **Administrator PowerShell**, run:

```powershell
New-NetFirewallRule `
  -DisplayName "MOT Nexus Web Portal" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 8000 `
  -Action Allow
```

Verify the rule was added:
```powershell
Get-NetFirewallRule -DisplayName "MOT Nexus Web Portal"
```

> **Alternatively via GUI:**
> Control Panel → Windows Defender Firewall → Advanced Settings →
> Inbound Rules → New Rule → Port → TCP → 8000 → Allow → All profiles → Name it "MOT Nexus"

---

## Step 4 – Start the application

### Option A – Manual start (for testing)

Double-click `start_prod.bat`, or run from a Command Prompt:
```
cd C:\mot-nexus
start_prod.bat
```

Or from PowerShell:
```powershell
cd C:\mot-nexus
.\start_prod.ps1
```

You will see output like:
```
====================================================
  MOT Nexus - Enterprise Resourcing Portal
  Mode    : PRODUCTION
  Port    : 8000
  URL     : http://localhost:8000
====================================================
Server starting on http://0.0.0.0:8000  (Press Ctrl+C to stop)
INFO:     Application startup complete.
```

Open a browser and go to **http://localhost:8000** to confirm it works.
Press `Ctrl+C` in the window to stop the server.

---

### Option B – Install as a Windows Service (recommended for production)

A Windows Service starts automatically when the server boots and restarts itself
if it crashes — no one needs to log in and run a script.

**Step B1 – Download NSSM**

NSSM (Non-Sucking Service Manager) wraps any program as a Windows Service.

1. Go to https://nssm.cc/download
2. Download the latest ZIP (e.g. `nssm-2.24.zip`)
3. Open the ZIP, go into the `win64` folder
4. Copy `nssm.exe` to `C:\nssm\nssm.exe`
   (create the `C:\nssm` folder if it does not exist)

**Step B2 – Install the service**

In an **Administrator PowerShell**:
```powershell
cd C:\mot-nexus
.\install_service_nssm.ps1
```

Expected output:
```
Installing Windows Service: MOTNexus
  Executable : C:\mot-nexus\.venv\Scripts\uvicorn.exe
  App dir    : C:\mot-nexus
  Log dir    : C:\mot-nexus\logs

Starting service...

====================================================
  Service 'MOTNexus' is RUNNING.
  URL  : http://localhost:8000
  Logs : C:\mot-nexus\logs
====================================================
```

**Managing the service afterwards:**

| Action | PowerShell command | GUI |
|---|---|---|
| Check status | `Get-Service MOTNexus` | `services.msc` → MOT Nexus |
| Start | `Start-Service MOTNexus` | Right-click → Start |
| Stop | `Stop-Service MOTNexus` | Right-click → Stop |
| Restart | `Restart-Service MOTNexus` | Right-click → Restart |
| View logs | `Get-Content C:\mot-nexus\logs\mot-nexus.log -Tail 50` | Open the file in Notepad |
| Uninstall | `C:\nssm\nssm.exe remove MOTNexus confirm` | — |

---

## Step 5 (Optional but recommended) – nginx on port 80

Without nginx, users must type `:8000` in the URL.
With nginx, they use standard port 80 and the URL is simply `http://server-name/`.

**Install nginx for Windows:**

1. Download from https://nginx.org/en/download.html (Stable version, e.g. `nginx-1.26.3.zip`)
2. Extract to `C:\nginx`
3. Replace `C:\nginx\conf\nginx.conf` with the file `nginx_windows.conf` from this project

**Run nginx as a service (using NSSM):**

In an **Administrator PowerShell**:
```powershell
# Install nginx as a service
C:\nssm\nssm.exe install nginx C:\nginx\nginx.exe
C:\nssm\nssm.exe set nginx AppDirectory C:\nginx
C:\nssm\nssm.exe set nginx Start SERVICE_AUTO_START
Start-Service nginx
```

**Open port 80 and close port 8000:**
```powershell
New-NetFirewallRule -DisplayName "HTTP (MOT Nexus via nginx)" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
Remove-NetFirewallRule -DisplayName "MOT Nexus Web Portal"    # closes port 8000
```

Users can now reach the portal on **http://server-name/** with no port number.

---

## How to find the server's IP address

Run this in any Command Prompt or PowerShell on the server:
```powershell
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' }).IPAddress
```

Example output: `192.168.1.75`

Or use the traditional command:
```
ipconfig
```
Look for the line: `IPv4 Address . . . . . : 192.168.1.75`

---

## URLs users should type

| Setup | URL |
|---|---|
| Direct (no nginx, using IP) | `http://192.168.1.75:8000` |
| Direct (no nginx, using hostname) | `http://WIN-SERVER01:8000` |
| With nginx on port 80 | `http://192.168.1.75` |
| With nginx + DNS/hosts entry | `http://mot-nexus/` |

Replace `192.168.1.75` / `WIN-SERVER01` with your server's actual IP or hostname.

---

## What users need to do on their computers

**Nothing** — in most cases.

Users need only:
- A browser: Chrome, Edge, Firefox, or Safari (any modern version)
- Network access to the server (same office network or VPN)

### Edge case: if you use a short hostname instead of an IP

If you chose to give the server a friendly name like `mot-nexus` and
your IT team has not yet added it to the corporate DNS, each user adds
**one line** to their hosts file:

**Windows (each user's laptop):**
1. Search for "Notepad" in the Start menu
2. Right-click → **Run as administrator**
3. Open: `C:\Windows\System32\drivers\etc\hosts`
4. Add this line at the bottom (use the server's actual IP):
   ```
   192.168.1.75    mot-nexus
   ```
5. Save the file

After saving, the browser will resolve `http://mot-nexus/` correctly.

**Permanent fix:** Ask IT to add an A-record in the internal DNS:
`mot-nexus` → `192.168.1.75`
Once DNS is updated, no user ever needs to touch their hosts file.

---

## Complete setup checklist

```
On the Windows server
  [ ] Python 3.11+ installed with "Add Python to PATH" ticked
  [ ] Project copied to C:\mot-nexus
  [ ] .\setup_windows.ps1  run successfully (venv + deps + DB)
  [ ] Firewall rule added for port 8000
        New-NetFirewallRule -DisplayName "MOT Nexus" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
  [ ] Application starts: test with .\start_prod.bat
  [ ] NSSM downloaded and nssm.exe placed at C:\nssm\nssm.exe
  [ ] Service installed: .\install_service_nssm.ps1
  [ ] Service status shows Running: Get-Service MOTNexus
  [ ] (Optional) nginx installed, configured, running as a service on port 80

On each user's computer
  [ ] Open browser, type http://<server-ip>:8000
  [ ] (If using hostname and no DNS) add one line to C:\Windows\System32\drivers\etc\hosts
  [ ] Portal loads, tiles show data  ✓
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `python` not recognised | Python not in PATH | Re-install Python, tick "Add Python to PATH" |
| `setup_windows.ps1` blocked | Execution policy | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Browser can't connect from another PC | Firewall port closed | Add firewall rule for port 8000 |
| Service fails to start | Path or env var wrong | Check `C:\mot-nexus\logs\mot-nexus-error.log` |
| Large file upload fails | nginx body size limit | Already set to 100M in `nginx_windows.conf` |
| "Address already in use" on start | Port 8000 taken | `netstat -ano \| findstr :8000` then `taskkill /PID <id> /F` |

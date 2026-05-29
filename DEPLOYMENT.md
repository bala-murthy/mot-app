# MOT Nexus – Network Deployment Guide

## Overview

The app is a single-server FastAPI application. Once the server is reachable on the network,
users open a browser and navigate to a URL — no software installation needed on user laptops.

---

## 1. Application-level changes (already done)

| Item | Dev (current) | Production |
|---|---|---|
| Start flag | `--reload` | removed |
| Workers | 1 | 4 (tunable) |
| DB path | relative `./mot_nexus.db` | absolute via `DATABASE_URL` env var |
| Host binding | `0.0.0.0` ✓ | `0.0.0.0` ✓ (no change needed) |

The app already binds to `0.0.0.0` which means it accepts connections from
every network interface on the server — so no code change is required there.

---

## 2. Server-level changes

### Step 1 – Get the server's IP address

```bash
# Linux
ip addr show | grep "inet " | grep -v 127

# macOS
ifconfig | grep "inet " | grep -v 127
```

Note the IP address, e.g. `192.168.1.50`.
If the server has a hostname (e.g. `mot-server.company.com`), use that — it's cleaner.

---

### Step 2 – Deploy the project to the server

```bash
# On your developer machine — zip and copy to server
cd /Users/bala/Documents/study/claude
zip -r mot-nexus.zip mot-portal/ --exclude "mot-portal/.venv/*" --exclude "mot-portal/__pycache__/*"

# Copy to server (replace user@server with your details)
scp mot-nexus.zip user@192.168.1.50:/opt/

# On the server
cd /opt
unzip mot-nexus.zip
mv mot-portal mot-nexus
cd mot-nexus

# Create virtual environment and install dependencies
python3 -m pip install uv
uv venv .venv
uv pip install -r backend/requirements.txt

# Copy and edit the env file
cp .env.example .env
# Edit DATABASE_URL if you want a non-default path

# Seed initial data (only needed once)
PYTHONPATH=. .venv/bin/python backend/seed_data.py
```

---

### Step 3 – Open the firewall port

**Linux (Ubuntu/Debian with ufw):**
```bash
sudo ufw allow 8000/tcp comment "MOT Nexus"
sudo ufw reload
sudo ufw status
```

**Linux (CentOS/RHEL with firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

**macOS (hosting on a Mac):**
```
System Settings → Privacy & Security → Firewall → Firewall Options
→ Add the uvicorn / python executable and set to "Allow incoming connections"
```

Or use a simpler shortcut: run on macOS and allow the pop-up prompt that appears
("Do you want the application 'python' to accept incoming network connections?") → click **Allow**.

---

### Step 4 – Run as a persistent service (survives reboots)

**Option A – Linux systemd (recommended for Linux servers):**
```bash
# Create a dedicated user
sudo useradd -r -s /bin/false motnexus

# Give it ownership of the app directory
sudo chown -R motnexus:motnexus /opt/mot-nexus

# Install the service
sudo cp /opt/mot-nexus/mot-nexus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mot-nexus    # start on every boot
sudo systemctl start mot-nexus     # start right now

# Check status
sudo systemctl status mot-nexus

# Live logs
journalctl -u mot-nexus -f
```

**Option B – Quick background process (any OS, not persistent across reboots):**
```bash
cd /opt/mot-nexus
chmod +x start_prod.sh
nohup ./start_prod.sh > logs/mot-nexus.log 2>&1 &
echo $! > mot-nexus.pid          # save PID so you can stop it later
```

Stop it:
```bash
kill $(cat mot-nexus.pid)
```

---

### Step 5 (Optional but recommended) – Nginx reverse proxy

Using nginx lets users access the portal on **port 80** (standard HTTP) without typing `:8000`.

Install nginx:
```bash
sudo apt install nginx            # Ubuntu/Debian
sudo yum install nginx            # CentOS/RHEL
```

Create `/etc/nginx/sites-available/mot-nexus`:
```nginx
server {
    listen 80;
    server_name mot-nexus.company.com;   # or your server IP

    client_max_body_size 100M;           # allow large file uploads

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;           # allow long uploads/downloads
        proxy_send_timeout 300s;
    }
}
```

Enable it:
```bash
sudo ln -s /etc/nginx/sites-available/mot-nexus /etc/nginx/sites-enabled/
sudo nginx -t                  # test config
sudo systemctl reload nginx
sudo ufw allow 80/tcp          # open port 80 instead of 8000
```

After this you can **close port 8000** from the firewall (nginx handles all traffic):
```bash
sudo ufw delete allow 8000/tcp
```

---

## 3. URL users should use

| Setup | URL | Notes |
|---|---|---|
| Direct (no nginx) | `http://192.168.1.50:8000` | Replace with your server's IP |
| Direct with hostname | `http://mot-server.company.com:8000` | If DNS or hosts file resolves the name |
| With nginx on port 80 | `http://mot-server.company.com` | No port number needed |
| With nginx + DNS alias | `http://motnexus/` | If IT adds a short DNS alias |

**How to find your server IP:**
```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

Example output: `inet 192.168.1.50/24` → IP is `192.168.1.50`

---

## 4. Changes needed on end-user laptops / computers

**In most corporate networks: NONE.**

Users only need:
- A modern web browser (Chrome, Edge, Firefox, Safari — any version from the last 3 years)
- Network connectivity to the server (same LAN, or VPN if remote)

The portal uses no plugins, no Java, no ActiveX, no desktop software.

---

### Edge case: hostname not resolving

If you chose to use a hostname (e.g. `mot-nexus`) instead of an IP address,
and your IT team hasn't added it to the corporate DNS yet, each user can add
a one-line entry to their `hosts` file as a temporary workaround:

**Windows** — open Notepad **as Administrator**, edit:
```
C:\Windows\System32\drivers\etc\hosts
```

**macOS / Linux:**
```bash
sudo nano /etc/hosts
```

Add this line (use your server's actual IP):
```
192.168.1.50    mot-nexus mot-nexus.company.com
```

Save and close. The browser will now resolve `http://mot-nexus/` correctly.

> **Permanent fix:** Ask IT to add an A-record in the internal DNS server pointing
> `mot-nexus.company.com` → `192.168.1.50`. Once that's done, no hosts-file
> changes are needed on any user machine.

---

## Quick-reference checklist

```
Server side
  [x] App binds to 0.0.0.0:8000 (already done)
  [ ] uv venv + pip install -r requirements.txt on server
  [ ] Firewall: open port 8000 (or 80 if using nginx)
  [ ] systemd service enabled (for auto-restart on reboot)
  [ ] (Optional) nginx reverse proxy on port 80

User side
  [ ] Browser: Chrome / Edge / Firefox / Safari
  [ ] Network access to server IP/hostname
  [ ] (If hostname used and no DNS) one-line /etc/hosts entry
```

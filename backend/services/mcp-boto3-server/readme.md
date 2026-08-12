# Remote File Collection Setup Guide (Option A: Network Share / Mounted Drive)

## Overview

This guide covers connecting your FastAPI file-collection pipeline to a folder
on **another machine that you control** (e.g. your own second PC/server), by
mounting that machine's shared folder so it appears as a local path. Once
mounted, your existing `fetch_local_files()` collector works completely
unchanged.

**Requirement:** You need admin/root access on the remote machine to enable
sharing. This approach is NOT for machines you have zero access to (e.g. other
people's personal computers) — for that scenario, use a push-based upload
endpoint instead.

**Pros:** Zero code changes — your existing `fetch_local_files` just works.
**Cons:** Needs OS-level network share setup and credential management outside
your app; if the mount drops, your pipeline can silently see an empty/missing
directory (fix included at the end of this doc).

---

## Part 1: Windows → Windows (SMB Share)

### On the REMOTE machine (has the files, e.g. `192.168.1.50`)

**Step 1 — Enable file sharing (if not already on):**
```powershell
# Run as Administrator
Set-NetFirewallRule -DisplayGroup "File and Printer Sharing" -Enabled True
```

**Step 2 — Create a dedicated user for sharing (recommended — don't use your main login):**
```powershell
# Run as Administrator
New-LocalUser -Name "logshare" -Password (ConvertTo-SecureString "YourStrongPassword123!" -AsPlainText -Force)
```

**Step 3 — Share the folder via command line (no GUI needed):**
```powershell
# Run as Administrator
New-SmbShare -Name "logs" -Path "C:\logs" -FullAccess "logshare"
```

**Step 4 — Verify the share exists:**
```powershell
Get-SmbShare -Name "logs"
```

**Step 5 — Confirm the machine's IP address (you'll need this):**
```powershell
ipconfig
```
Look for `IPv4 Address` (e.g. `192.168.1.50`).

### On YOUR machine (collector / FastAPI server)

**Step 1 — Test connectivity first:**
```powershell
ping 192.168.1.50
```
If this fails, resolve the network/firewall issue before continuing.

**Step 2 — Mount the share as a drive letter:**
```powershell
net use Z: \\192.168.1.50\logs /user:logshare YourStrongPassword123!
```

**Step 3 — Make it persistent across reboots (recommended for a server):**
```powershell
net use Z: \\192.168.1.50\logs /user:logshare YourStrongPassword123! /persistent:yes
```

**Step 4 — Verify you can see files:**
```powershell
dir Z:\
```

**Step 5 — Update your config payload:**
```json
{
  "source_config": {
    "source_type": "local",
    "config_json": {
      "directory": "Z:/",
      "extensions": [".log", ".txt"]
    }
  }
}
```

---

## Part 2: Linux → Linux (NFS)

### On the REMOTE machine (has the files)

**Step 1 — Install NFS server:**
```bash
sudo apt update
sudo apt install nfs-kernel-server -y
```

**Step 2 — Define what to share — edit `/etc/exports`:**
```bash
sudo nano /etc/exports
```
Add this line (replace with your collector machine's actual IP or subnet):
```
/var/log/myapp 192.168.1.0/24(ro,sync,no_subtree_check)
```
`ro` = read-only (recommended for a log-collection use case). Use `rw` only if
write access is actually needed.

**Step 3 — Apply the export:**
```bash
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
```

**Step 4 — Open the firewall (if `ufw` is active):**
```bash
sudo ufw allow from 192.168.1.0/24 to any port nfs
```

**Step 5 — Confirm it's exported:**
```bash
sudo exportfs -v
```

### On YOUR machine (collector / FastAPI server)

**Step 1 — Install NFS client:**
```bash
sudo apt install nfs-common -y
```

**Step 2 — Create a mount point:**
```bash
sudo mkdir -p /mnt/remote-logs
```

**Step 3 — Mount it:**
```bash
sudo mount -t nfs 192.168.1.50:/var/log/myapp /mnt/remote-logs
```

**Step 4 — Make it persistent across reboots — edit `/etc/fstab`:**
```bash
sudo nano /etc/fstab
```
Add:
```
192.168.1.50:/var/log/myapp  /mnt/remote-logs  nfs  ro,auto  0  0
```

**Step 5 — Verify:**
```bash
ls -la /mnt/remote-logs
```

**Step 6 — Update your config payload:**
```json
{
  "source_config": {
    "source_type": "local",
    "config_json": {
      "directory": "/mnt/remote-logs",
      "extensions": [".log", ".txt"]
    }
  }
}
```

---

## Part 3: Windows (remote) → Linux (your server) — Mixed OS via SMB

### On the REMOTE Windows machine
Same as **Part 1, Steps 1–5** above (create share, user, firewall rule).

### On YOUR Linux machine

**Step 1 — Install CIFS utilities:**
```bash
sudo apt install cifs-utils -y
```

**Step 2 — Store credentials securely (don't put them in fstab in plain sight):**
```bash
sudo nano /etc/samba/credentials
```
```
username=logshare
password=YourStrongPassword123!
```
```bash
sudo chmod 600 /etc/samba/credentials
```

**Step 3 — Create a mount point:**
```bash
sudo mkdir -p /mnt/remote-logs
```

**Step 4 — Mount it:**
```bash
sudo mount -t cifs //192.168.1.50/logs /mnt/remote-logs -o credentials=/etc/samba/credentials,uid=$(id -u),gid=$(id -g)
```

**Step 5 — Make persistent — edit `/etc/fstab`:**
```
//192.168.1.50/logs  /mnt/remote-logs  cifs  credentials=/etc/samba/credentials,uid=1000,gid=1000  0  0
```

**Step 6 — Verify and update config**, same as above using `/mnt/remote-logs`.

---

## Important: Fixing "Silently Sees an Empty Directory"

If a mount drops (network blip, credentials expire, remote machine reboots),
`os.walk()` on a disconnected mount point can return **zero files with no
error** — your pipeline would silently think there's nothing to process
instead of failing loudly.

Update `fetch_local_files` to raise clearly instead of failing silently:

This way, a dropped mount surfaces through the existing
`except ValueError as e` handler in your `/save-config` route, instead of the
pipeline quietly reporting `file_count: 0` with no explanation.

---

## Quick Reference Table

| Remote OS | Your OS | Protocol | Remote Setup | Your Setup |
|---|---|---|---|---|
| Windows | Windows | SMB | `New-SmbShare` | `net use Z:` |
| Linux | Linux | NFS | `/etc/exports` + `exportfs` | `mount -t nfs` |
| Windows | Linux | SMB (CIFS) | `New-SmbShare` | `mount -t cifs` |

## Notes

- This entire approach assumes you have administrative access to the remote
  machine. If you don't (e.g. it belongs to someone else and you cannot make
  any changes to it), this method is not viable — use a push-based upload
  endpoint on your FastAPI server instead, where the other party uploads files
  through a browser with no setup on their end.
- Always test connectivity (`ping`) before troubleshooting mount issues —
  most "it's not working" problems trace back to firewall or network routing,
  not the share/mount configuration itself.

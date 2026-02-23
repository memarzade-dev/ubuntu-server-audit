#!/usr/bin/env bash
# =============================================================================
# Ubuntu Server Professional Audit - Installer
# Supports: Ubuntu 22.04 (Jammy) / 24.04 (Noble)
# Usage:    sudo bash install.sh
# =============================================================================
set -euo pipefail

INSTALL_DIR="/opt/server-audit"
LOG_DIR="/var/log/server-audit"
SYMLINK="/usr/local/bin/server-report"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This installer must be run as root (sudo)." >&2
    exit 1
fi

source /etc/os-release 2>/dev/null || true
if [[ "${VERSION_ID:-}" != "22.04" && "${VERSION_ID:-}" != "24.04" ]]; then
    echo "WARNING: This tool is tested on Ubuntu 22.04/24.04. Detected: ${PRETTY_NAME:-unknown}"
    echo "Proceeding anyway..."
fi

echo "=== Ubuntu Server Professional Audit Installer ==="
echo "Install dir : ${INSTALL_DIR}"
echo "Data dir    : ${LOG_DIR}/data"
echo "CLI command : server-report"
echo ""

# ---------------------------------------------------------------------------
# Install system dependencies
# ---------------------------------------------------------------------------
echo "[1/5] Installing system packages..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3 sysstat vnstat nethogs lshw dmidecode

# ---------------------------------------------------------------------------
# Deploy audit script
# ---------------------------------------------------------------------------
echo "[2/5] Deploying audit script..."
mkdir -p "${INSTALL_DIR}" "${LOG_DIR}/data"

# Copy audit.py from the same directory as this installer (if present)
# or use the embedded version
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/audit.py" ]]; then
    cp "${SCRIPT_DIR}/audit.py" "${INSTALL_DIR}/audit.py"
else
    echo "ERROR: audit.py not found in ${SCRIPT_DIR}" >&2
    echo "Place audit.py next to install.sh and re-run." >&2
    exit 1
fi

chmod 755 "${INSTALL_DIR}/audit.py"

# Create CLI symlink
ln -sf "${INSTALL_DIR}/audit.py" "${SYMLINK}"
echo "CLI available as: server-report"

# ---------------------------------------------------------------------------
# Install systemd units
# ---------------------------------------------------------------------------
echo "[3/5] Installing systemd timer..."

cat > /etc/systemd/system/server-audit.service << 'UNIT_EOF'
[Unit]
Description=Server Audit Daily Report
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/server-audit/audit.py full
User=root
Nice=10
IOSchedulingClass=best-effort
StandardOutput=journal
StandardError=journal
TimeoutStartSec=300
UNIT_EOF

cat > /etc/systemd/system/server-audit.timer << 'TIMER_EOF'
[Unit]
Description=Daily Server Audit at 01:00 AM

[Timer]
OnCalendar=*-*-* 01:00:00
AccuracySec=1s
RandomizedDelaySec=300
Persistent=true
FixedRandomDelay=true

[Install]
WantedBy=timers.target
TIMER_EOF

systemctl daemon-reload
systemctl enable --now server-audit.timer

# ---------------------------------------------------------------------------
# Run first-time setup
# ---------------------------------------------------------------------------
echo "[4/5] Running first-time setup (enable sysstat, vnstat)..."
"${INSTALL_DIR}/audit.py" setup

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
echo ""
echo "[5/5] Verifying installation..."
echo ""

echo "--- Timer status ---"
systemctl is-active server-audit.timer && echo "Timer: ACTIVE" || echo "Timer: INACTIVE"
systemctl list-timers server-audit.timer --no-pager 2>/dev/null || true

echo ""
echo "--- Installed versions ---"
echo "Python  : $(python3 --version 2>&1)"
echo "sysstat : $(sar -V 2>&1 | head -1)"
echo "vnstat  : $(vnstat --version 2>&1 | head -1)"
echo "nethogs : $(nethogs -V 2>&1 || echo 'installed')"
echo ""

echo "============================================="
echo " Installation complete!"
echo "============================================="
echo ""
echo "Commands:"
echo "  server-report full          # Full daily audit"
echo "  server-report hardware      # Hardware inventory"
echo "  server-report system        # System metrics (sysstat 24h)"
echo "  server-report processes     # Per-process snapshot"
echo "  server-report traffic       # Server traffic (vnstat 24h)"
echo "  server-report setup         # Re-run dependency setup"
echo "  server-report version       # Show version"
echo ""
echo "Reports saved to: ${LOG_DIR}/data/"
echo "Daily timer runs at 01:00 AM (systemd)."
echo ""
echo "NOTE: sysstat needs ~10 minutes to begin collecting."
echo "      vnstat needs a few hours to accumulate traffic data."
echo "      First meaningful 'full' report: tomorrow after 01:00 AM."

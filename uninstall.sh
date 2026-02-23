#!/usr/bin/env bash
# =============================================================================
# Ubuntu Server Audit - Uninstaller
# Usage: sudo bash uninstall.sh
# =============================================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Must run as root (sudo)." >&2
    exit 1
fi

echo "=== Ubuntu Server Audit Uninstaller ==="
echo ""

# Stop and disable timer
echo "[1/4] Stopping systemd timer..."
systemctl stop server-audit.timer 2>/dev/null || true
systemctl disable server-audit.timer 2>/dev/null || true

# Remove systemd units
echo "[2/4] Removing systemd units..."
rm -f /etc/systemd/system/server-audit.service
rm -f /etc/systemd/system/server-audit.timer
systemctl daemon-reload

# Remove CLI symlink
echo "[3/4] Removing CLI symlink..."
rm -f /usr/local/bin/server-report

# Remove application directory
echo "[4/4] Removing application files..."
rm -rf /opt/server-audit

echo ""
echo "Uninstall complete."
echo ""
echo "Data files preserved at: /var/log/server-audit/"
echo "To remove data too:  rm -rf /var/log/server-audit"
echo ""
echo "System packages (sysstat, vnstat, nethogs, lshw, dmidecode)"
echo "were NOT removed as they may be used by other tools."
echo "To remove them:  apt-get remove --purge sysstat vnstat nethogs"

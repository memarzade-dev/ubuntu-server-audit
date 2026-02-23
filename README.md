# Ubuntu Server Professional Audit Tool

[![CI](https://github.com/memarzade-dev/ubuntu-server-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/memarzade-dev/ubuntu-server-audit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Ubuntu 22.04](https://img.shields.io/badge/Ubuntu-22.04-orange)](https://releases.ubuntu.com/22.04/)
[![Ubuntu 24.04](https://img.shields.io/badge/Ubuntu-24.04-orange)](https://releases.ubuntu.com/24.04/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)

Production-grade daily server audit tool for Ubuntu 22.04/24.04 servers. Collects hardware inventory, system performance metrics, per-process resource usage with network snapshots, and server-wide traffic data. Outputs clean CSV files with automatic 7-day retention.

## Features

- **Hardware Inventory**: CPU, memory, disk, kernel, DMI info via `lscpu`, `free`, `df`, `lsblk`, `dmidecode`
- **System Metrics (24h)**: CPU, memory, I/O, network, load averages from `sysstat`/`sadf` historical data
- **Per-Process Snapshot**: CPU/MEM/IO per process via `pidstat` + real-time network bandwidth via `nethogs`
- **Server Traffic (24h)**: Accurate daily RX/TX from `vnstat` 2.x JSON API (values in bytes)
- **Automatic Scheduling**: systemd timer runs daily at 01:00 AM with jitter
- **Auto-Cleanup**: 7-day data retention, 1-day log retention
- **CLI Interface**: Subcommands for selective collection (`full`, `hardware`, `system`, `processes`, `traffic`)
- **Zero External Dependencies**: Python 3 stdlib only + standard apt packages

## Quick Start

```bash
# Clone and install
git clone https://github.com/memarzade-dev/ubuntu-server-audit.git
cd ubuntu-server-audit
sudo bash install.sh

# Run manually
sudo server-report full

# Check results
ls -lh /var/log/server-audit/data/
```

## Requirements

- Ubuntu 22.04 (Jammy) or 24.04 (Noble)
- Root/sudo access
- Python 3.10+ (pre-installed on both Ubuntu versions)
- System packages: `sysstat`, `vnstat`, `nethogs`, `lshw`, `dmidecode` (installed automatically)

## CLI Usage

```
server-report <command> [options]

Commands:
  full        Full daily audit (default) - all collectors
  hardware    Hardware inventory only
  system      System metrics summary (sysstat 24h)
  processes   Per-process snapshot (pidstat + nethogs)
  traffic     Server-wide traffic (vnstat 24h)
  setup       First-time install & configure dependencies
  version     Show version

Options:
  -v, --verbose     Enable verbose output to stderr
  --output-dir DIR  Override output directory
```

## Output Files

All CSV files are saved to `/var/log/server-audit/data/`:

| File | Content | Frequency |
|------|---------|-----------|
| `hardware_inventory.csv` | Static hardware info | Overwritten daily |
| `system_summary_YYYY-MM-DD.csv` | sadf CPU/MEM/IO/NET/LOAD | Daily, 7-day retention |
| `processes_YYYY-MM-DD.csv` | pidstat + nethogs per-process | Daily, 7-day retention |
| `network_traffic_YYYY-MM-DD.csv` | vnstat daily RX/TX in bytes+GB | Daily, 7-day retention |

## Architecture

```
install.sh ─► deploys audit.py to /opt/server-audit/
             ─► installs systemd timer (01:00 AM daily)
             ─► runs 'setup' (enables sysstat + vnstat)

audit.py CLI
├── setup      → apt install, systemctl enable, vnstat --add
├── full       → hardware + system + processes + traffic
├── hardware   → lscpu + free + df + lsblk + dmidecode → CSV
├── system     → sadf -d (24h sysstat data) → CSV
├── processes  → pidstat -u -r -d -h + nethogs -t → CSV
└── traffic    → vnstat --json d (24h) → CSV
```

## Compatibility Notes

### vnstat 2.x (Critical)

This tool is designed for vnstat 2.x (Ubuntu 22.04 ships 2.9, Ubuntu 24.04 ships 2.12). Key differences from 1.x:

- `vnstat -u` is **removed**. We use `vnstat --add -i <iface>` instead.
- JSON output uses `date: {year, month, day}` objects, not numeric `id` fields.
- Traffic values are in **bytes**, not KiB.

### sysstat

- Ubuntu 24.04: sysstat uses systemd timers (`sysstat-collect.timer`). `/etc/default/sysstat` is legacy.
- Ubuntu 22.04: We enable both the systemd timer and set `ENABLED="true"` in `/etc/default/sysstat`.
- Data files: `/var/log/sysstat/saDD` (Debian/Ubuntu default path).

## Uninstall

```bash
sudo bash uninstall.sh
# Data is preserved. To remove: sudo rm -rf /var/log/server-audit
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "No sysstat data available" | sysstat hasn't collected yet | Wait 10min after setup, or: `sudo systemctl restart sysstat-collect.timer` |
| vnstat shows 0 traffic | vnstat DB not initialized | `sudo server-report setup` then wait a few hours |
| nethogs columns empty | nethogs needs root + active traffic | Always run with `sudo`; nethogs captures live traffic only |
| Permission denied | Not running as root | `sudo server-report full` |
| sadf error "Invalid system activity" | sa file from different sysstat version | Delete old sa files: `sudo rm /var/log/sysstat/sa*` |

## License

[MIT](LICENSE)

## Sources

- [vnstat 2.x man page](https://humdi.net/vnstat/man/vnstat.html)
- [vnstat UPGRADE.md (1.x → 2.x)](https://github.com/vergoh/vnstat/blob/master/UPGRADE.md)
- [sadf(1) man page](https://man7.org/linux/man-pages/man1/sadf.1.html)
- [pidstat(1) man page](https://linux.die.net/man/1/pidstat)
- [nethogs man page](https://www.mankier.com/8/nethogs)
- [systemd.timer documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)
- [Ubuntu 24.04 sysstat bug #2066117](https://bugs.launchpad.net/ubuntu/+source/sysstat/+bug/2066117)
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)

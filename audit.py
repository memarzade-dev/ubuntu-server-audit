#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ubuntu Server Professional Audit Tool
======================================
Platform  : Ubuntu 22.04 (Jammy) / 24.04 (Noble)
Output    : CSV files in /var/log/server-audit/data/
Retention : 7 days data, 1 day logs
Schedule  : systemd timer daily at 01:00 AM
License   : MIT

Collects: hardware inventory, system metrics (sysstat/sadf 24h),
          per-process CPU/MEM/IO (pidstat), per-process network snapshot
          (nethogs), server-wide 24h traffic (vnstat).
"""

import argparse
import csv
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "2.0.0"
LOG_DIR = Path("/var/log/server-audit")
DATA_DIR = LOG_DIR / "data"
LOG_FILE = LOG_DIR / "audit.log"
DATA_RETENTION_DAYS = 7
LOG_RETENTION_DAYS = 1

REQUIRED_PACKAGES = ["sysstat", "vnstat", "nethogs", "lshw", "dmidecode"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging to file and optionally to stderr."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
    if verbose:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )

# ---------------------------------------------------------------------------
# Safe command execution
# ---------------------------------------------------------------------------
def run_cmd(cmd, timeout: int = 60, check: bool = False) -> subprocess.CompletedProcess:
    """
    Execute a command safely.

    - list argument  → shell=False (safe, no injection)
    - string argument → shell=True  (needed for pipes, awk, sed, grep)

    Returns CompletedProcess. On failure returns a dummy with empty stdout
    unless check=True, which raises.
    """
    if isinstance(cmd, list):
        shell = False
    else:
        shell = True

    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )
        return result
    except subprocess.CalledProcessError as exc:
        logging.error("Command failed (rc=%d): %s → stderr: %s", exc.returncode, cmd, exc.stderr.strip())
        if check:
            raise
        return subprocess.CompletedProcess(args=cmd, returncode=exc.returncode, stdout="", stderr=exc.stderr)
    except subprocess.TimeoutExpired:
        logging.error("Command timed out (%ds): %s", timeout, cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=-1, stdout="", stderr="timeout")
    except FileNotFoundError:
        logging.error("Command not found: %s", cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=-1, stdout="", stderr="not found")


def run_cmd_stdout(cmd, timeout: int = 60, check: bool = False) -> str:
    """Convenience: run command, return stripped stdout."""
    return run_cmd(cmd, timeout=timeout, check=check).stdout.strip()

# ---------------------------------------------------------------------------
# Interface detection
# ---------------------------------------------------------------------------
def get_main_interface() -> str:
    """Detect the primary network interface via default route."""
    out = run_cmd_stdout(["ip", "route", "get", "8.8.8.8"])
    match = re.search(r"dev\s+(\S+)", out)
    if match:
        iface = match.group(1)
        logging.info("Detected primary interface: %s", iface)
        return iface
    # Fallback: first non-lo interface
    out2 = run_cmd_stdout("ip -o link show up | awk -F': ' '{print $2}' | grep -v lo | head -1")
    if out2:
        logging.warning("Default route detection failed; falling back to: %s", out2)
        return out2
    logging.warning("No interface detected; using 'eth0' as last resort")
    return "eth0"

# ---------------------------------------------------------------------------
# Cleanup old files
# ---------------------------------------------------------------------------
def cleanup_old_files() -> None:
    """Remove CSV files older than DATA_RETENTION_DAYS and logs older than LOG_RETENTION_DAYS."""
    now = datetime.now()
    removed = 0

    # Data CSVs (date-stamped filenames)
    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*.csv"):
            match = re.search(r"(\d{4}-\d{2}-\d{2})", f.name)
            if match:
                try:
                    file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                    if (now - file_date).days > DATA_RETENTION_DAYS:
                        f.unlink()
                        removed += 1
                        logging.info("Removed old data file: %s", f.name)
                except ValueError:
                    pass

    # Log files (by mtime)
    for f in LOG_DIR.glob("*.log*"):
        try:
            age_days = (now - datetime.fromtimestamp(f.stat().st_mtime)).days
            if age_days > LOG_RETENTION_DAYS and f != LOG_FILE:
                f.unlink()
                removed += 1
                logging.info("Removed old log file: %s", f.name)
        except OSError:
            pass

    if removed:
        logging.info("Cleanup complete: %d file(s) removed", removed)

# ---------------------------------------------------------------------------
# Setup (first-run)
# ---------------------------------------------------------------------------
def setup_environment() -> None:
    """Install required packages, enable services, initialize vnstat DB."""
    logging.info("=== Running first-time setup ===")

    # Install packages
    run_cmd(["apt-get", "update", "-qq"], timeout=120, check=True)
    run_cmd(["apt-get", "install", "-y"] + REQUIRED_PACKAGES, timeout=180, check=True)

    # Enable sysstat timers (works on both 22.04 and 24.04)
    run_cmd(["systemctl", "enable", "--now", "sysstat"], check=False)
    # On 24.04 the collect timer is the real driver
    run_cmd(["systemctl", "enable", "--now", "sysstat-collect.timer"], check=False)
    run_cmd(["systemctl", "enable", "--now", "sysstat-summary.timer"], check=False)

    # Also set ENABLED=true in /etc/default/sysstat for 22.04 compatibility
    sysstat_default = Path("/etc/default/sysstat")
    if sysstat_default.exists():
        content = sysstat_default.read_text()
        if 'ENABLED="false"' in content:
            new_content = content.replace('ENABLED="false"', 'ENABLED="true"')
            sysstat_default.write_text(new_content)
            logging.info("Set ENABLED=true in /etc/default/sysstat (22.04 compat)")

    # Enable vnstat daemon
    run_cmd(["systemctl", "enable", "--now", "vnstat"], check=False)

    # Initialize vnstat interface with --add (vnstat 2.x; -u is removed)
    iface = get_main_interface()
    check_result = run_cmd(["vnstat", "--json", "d", "-i", iface])
    if check_result.returncode != 0:
        add_result = run_cmd(["vnstat", "--add", "-i", iface])
        if add_result.returncode == 0:
            logging.info("vnstat: added interface %s to database", iface)
        else:
            logging.warning("vnstat --add failed for %s: %s", iface, add_result.stderr.strip())
    else:
        logging.info("vnstat: interface %s already in database", iface)

    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logging.info("=== Setup completed successfully ===")
    print(f"Setup completed. Interface: {iface}")
    print("sysstat collection will begin within 10 minutes.")
    print("vnstat will accumulate traffic data over the next hours.")
    print("Daily audit runs at 01:00 AM via systemd timer (if installed).")

# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------
def collect_hardware() -> list[list[str]]:
    """Collect static hardware inventory: CPU, memory, disk, kernel, uptime."""
    rows = [["Category", "Key", "Value"]]

    # CPU info via lscpu --json
    out = run_cmd_stdout(["lscpu", "--json"])
    if out:
        try:
            data = json.loads(out)
            for item in data.get("lscpu", []):
                field = item.get("field", "").rstrip(":")
                value = item.get("data", "")
                if field and value:
                    rows.append(["CPU", field, value])
        except (json.JSONDecodeError, KeyError) as exc:
            logging.warning("lscpu JSON parse failed: %s", exc)

    # Memory
    mem_total = run_cmd_stdout("free -h | awk '/^Mem:/{print $2}'")
    mem_avail = run_cmd_stdout("free -h | awk '/^Mem:/{print $7}'")
    swap_total = run_cmd_stdout("free -h | awk '/^Swap:/{print $2}'")
    rows.append(["Memory", "Total", mem_total])
    rows.append(["Memory", "Available", mem_avail])
    rows.append(["Memory", "Swap Total", swap_total])

    # Disk
    disk_out = run_cmd_stdout("df -h / | awk 'NR==2{print $2, $3, $4, $5}'")
    if disk_out:
        parts = disk_out.split()
        if len(parts) >= 4:
            rows.append(["Disk", "Root Size", parts[0]])
            rows.append(["Disk", "Root Used", parts[1]])
            rows.append(["Disk", "Root Available", parts[2]])
            rows.append(["Disk", "Root Use%", parts[3]])

    # Block devices
    lsblk_out = run_cmd_stdout(["lsblk", "-nd", "-o", "NAME,SIZE,TYPE"])
    for line in lsblk_out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "disk":
            rows.append(["Disk", f"Block Device {parts[0]}", parts[1]])

    # System info
    rows.append(["Kernel", "Version", run_cmd_stdout(["uname", "-r"])])
    rows.append(["Kernel", "Architecture", run_cmd_stdout(["uname", "-m"])])
    rows.append(["System", "Hostname", run_cmd_stdout(["hostname", "-f"], check=False)])
    rows.append(["System", "Uptime", run_cmd_stdout(["uptime", "-p"])])
    rows.append(["System", "OS", run_cmd_stdout("cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2")])

    # DMI info (vendor, product)
    dmi_vendor = run_cmd_stdout(["dmidecode", "-s", "system-manufacturer"], check=False)
    dmi_product = run_cmd_stdout(["dmidecode", "-s", "system-product-name"], check=False)
    if dmi_vendor:
        rows.append(["Hardware", "Manufacturer", dmi_vendor])
    if dmi_product:
        rows.append(["Hardware", "Product", dmi_product])

    logging.info("Hardware inventory collected: %d rows", len(rows) - 1)
    return rows


def collect_system_summary(yesterday: datetime) -> list[list[str]]:
    """
    Collect 24h system metrics from sysstat (sadf).
    Exports CPU, memory, I/O, network, and load as semicolon-delimited CSV.
    """
    yest_dd = yesterday.strftime("%d")
    sa_file = f"/var/log/sysstat/sa{yest_dd}"

    if not os.path.exists(sa_file):
        logging.warning("sysstat data file not found: %s", sa_file)
        return [["Info"], ["No sysstat data available for yesterday. Wait 24h after setup."]]

    # Export all major metrics for the full day
    # -d = database (semicolon) format
    # -s/-e = full day window
    # -- separates sadf flags from sar flags
    cmd = f"sadf -d -s 00:00:00 -e 23:59:59 {sa_file} -- -u -r -b -n DEV -q"
    out = run_cmd_stdout(cmd, timeout=30)

    if not out:
        logging.warning("sadf returned empty output for %s", sa_file)
        return [["Info"], ["sadf returned no data. sysstat may still be collecting."]]

    rows = []
    for line in out.splitlines():
        if line.startswith("#"):
            # Header line: replace # with clean header
            header_parts = [h.strip() for h in line.lstrip("# ").split(";")]
            rows.append(header_parts)
        else:
            rows.append(line.split(";"))

    logging.info("System summary collected: %d rows from %s", len(rows), sa_file)
    return rows


def collect_processes() -> list[list[str]]:
    """
    Collect per-process snapshot: CPU/MEM/IO via pidstat + network via nethogs.
    pidstat -h gives a single merged header line with all metrics.
    """
    header = [
        "Timestamp", "UID", "PID",
        "%usr", "%system", "%guest", "%wait", "%CPU", "CPU_core",
        "minflt/s", "majflt/s", "VSZ_KB", "RSS_KB", "%MEM",
        "kB_rd/s", "kB_wr/s", "kB_ccwr/s", "iodelay",
        "Command", "Net_Sent_KB/s", "Net_Recv_KB/s"
    ]
    rows = [header]

    # --- pidstat snapshot (3 samples, 1s interval, merged header) ---
    pidstat_out = run_cmd_stdout("pidstat -u -r -d -h 1 3", timeout=30)

    pidstat_data = {}  # pid -> last sample row
    for line in pidstat_out.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("Linux"):
            continue
        parts = re.split(r"\s+", line)
        # Expected: timestamp UID PID %usr %system %guest %wait %CPU CPU minflt/s majflt/s VSZ RSS %MEM kB_rd/s kB_wr/s kB_ccwr/s iodelay Command
        # That is 19 fields minimum (Command may contain spaces)
        if len(parts) >= 19:
            try:
                int(parts[2])  # PID must be numeric
            except ValueError:
                continue
            pid = parts[2]
            cmd_name = " ".join(parts[18:])
            pidstat_data[pid] = parts[:18] + [cmd_name]

    # --- nethogs per-process network snapshot ---
    # nethogs -t = text mode, -c 5 = 5 cycles, -v 0 = KB/s
    # Output format: /path/to/binary/PID/UID\tSENT\tRECEIVED
    iface = get_main_interface()
    nethogs_out = run_cmd_stdout(
        f"nethogs -t -c 5 -v 0 {iface} 2>/dev/null",
        timeout=30
    )

    nethogs_map = {}  # pid -> (sent, recv)
    if nethogs_out:
        for line in nethogs_out.splitlines():
            line = line.strip()
            if not line or line.startswith("Refreshing"):
                continue
            tab_parts = line.split("\t")
            if len(tab_parts) == 3:
                proc_ident, sent_str, recv_str = tab_parts
                # Extract PID from /path/binary/PID/UID format
                segments = proc_ident.rsplit("/", 2)
                if len(segments) >= 3:
                    pid_candidate = segments[-2]
                    if pid_candidate.isdigit() and pid_candidate != "0":
                        nethogs_map[pid_candidate] = (sent_str.strip(), recv_str.strip())

    # --- Merge pidstat + nethogs ---
    for pid, pdata in pidstat_data.items():
        sent, recv = nethogs_map.get(pid, ("", ""))
        rows.append(pdata + [sent, recv])

    logging.info("Process snapshot collected: %d processes, %d with network data",
                 len(pidstat_data), len(nethogs_map))
    return rows


def collect_traffic(iface: str, yesterday: datetime) -> list[list[str]]:
    """
    Collect 24h server-wide traffic from vnstat JSON.
    vnstat 2.x: values are in BYTES, date is {year, month, day} object.
    """
    header = ["Interface", "Date", "RX_Bytes", "TX_Bytes", "RX_GB", "TX_GB", "Total_GB"]
    rows = [header]

    yest_str = yesterday.strftime("%Y-%m-%d")
    yest_year = yesterday.year
    yest_month = yesterday.month
    yest_day = yesterday.day

    out = run_cmd_stdout(f"vnstat -i {iface} --json d 30")
    if not out:
        logging.warning("vnstat returned empty output for interface %s", iface)
        rows.append([iface, yest_str, "0", "0", "0.00", "0.00", "0.00"])
        return rows

    try:
        data = json.loads(out)
        interfaces = data.get("interfaces", [])
        if not interfaces:
            raise ValueError("No interfaces in vnstat JSON")

        days = interfaces[0].get("traffic", {}).get("days", [])
        rx = 0
        tx = 0
        found = False

        for day_entry in days:
            d = day_entry.get("date", {})
            if (d.get("year") == yest_year and
                    d.get("month") == yest_month and
                    d.get("day") == yest_day):
                rx = day_entry.get("rx", 0)  # bytes
                tx = day_entry.get("tx", 0)  # bytes
                found = True
                break

        if not found:
            logging.warning("No vnstat data found for %s on %s", iface, yest_str)

        rx_gb = round(rx / (1024 ** 3), 3)
        tx_gb = round(tx / (1024 ** 3), 3)
        total_gb = round((rx + tx) / (1024 ** 3), 3)

        rows.append([iface, yest_str, str(rx), str(tx),
                      f"{rx_gb:.3f}", f"{tx_gb:.3f}", f"{total_gb:.3f}"])

    except (json.JSONDecodeError, KeyError, ValueError, IndexError) as exc:
        logging.error("vnstat JSON parse error: %s", exc)
        rows.append([iface, yest_str, "0", "0", "0.000", "0.000", "0.000"])

    logging.info("Traffic collected for %s on %s: RX=%s TX=%s",
                 iface, yest_str, rows[-1][4], rows[-1][5])
    return rows

# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------
def write_csv(filepath: Path, rows: list[list]) -> None:
    """Write rows to a CSV file with UTF-8 BOM for Excel compatibility."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    logging.info("CSV written: %s (%d rows)", filepath.name, len(rows))

# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_full(yesterday: datetime, iface: str) -> None:
    """Run all collectors."""
    cmd_hardware()
    cmd_system(yesterday)
    cmd_processes(yesterday)
    cmd_traffic(yesterday, iface)


def cmd_hardware() -> None:
    """Collect and write hardware inventory."""
    hw = collect_hardware()
    write_csv(DATA_DIR / "hardware_inventory.csv", hw)


def cmd_system(yesterday: datetime) -> None:
    """Collect and write system metrics summary."""
    yest_str = yesterday.strftime("%Y-%m-%d")
    sys_rows = collect_system_summary(yesterday)
    write_csv(DATA_DIR / f"system_summary_{yest_str}.csv", sys_rows)


def cmd_processes(yesterday: datetime) -> None:
    """Collect and write per-process snapshot."""
    yest_str = yesterday.strftime("%Y-%m-%d")
    proc_rows = collect_processes()
    write_csv(DATA_DIR / f"processes_{yest_str}.csv", proc_rows)


def cmd_traffic(yesterday: datetime, iface: str) -> None:
    """Collect and write traffic data."""
    yest_str = yesterday.strftime("%Y-%m-%d")
    traffic_rows = collect_traffic(iface, yesterday)
    write_csv(DATA_DIR / f"network_traffic_{yest_str}.csv", traffic_rows)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="server-report",
        description=f"Ubuntu Server Professional Audit Tool v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  server-report full          Full daily audit (hardware + system + processes + traffic)
  server-report hardware      Hardware inventory only
  server-report system        System metrics summary (sysstat 24h) only
  server-report processes     Per-process snapshot only
  server-report traffic       Server-wide traffic (vnstat 24h) only
  server-report setup         First-time install & configure dependencies
  server-report version       Show version
""",
    )
    parser.add_argument(
        "command",
        choices=["full", "hardware", "system", "processes", "traffic", "setup", "version"],
        nargs="?",
        default="full",
        help="Subcommand to run (default: full)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output to stderr",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output directory (default: /var/log/server-audit/data)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "version":
        print(f"server-report v{VERSION}")
        return 0

    # Override output dir if requested
    global DATA_DIR
    if args.output_dir:
        DATA_DIR = Path(args.output_dir)

    setup_logging(verbose=args.verbose)
    logging.info("=== Server Audit Started (v%s) === command=%s", VERSION, args.command)

    # Check root
    if os.geteuid() != 0:
        print("ERROR: This tool must be run as root (sudo).", file=sys.stderr)
        return 1

    # Setup mode
    if args.command == "setup":
        try:
            setup_environment()
            return 0
        except subprocess.CalledProcessError as exc:
            logging.error("Setup failed: %s", exc)
            print(f"ERROR: Setup failed: {exc}", file=sys.stderr)
            return 1

    # Normal audit mode
    cleanup_old_files()

    today = datetime.now()
    yesterday = today - timedelta(days=1)
    yest_str = yesterday.strftime("%Y-%m-%d")
    iface = get_main_interface()

    try:
        if args.command == "full":
            cmd_full(yesterday, iface)
        elif args.command == "hardware":
            cmd_hardware()
        elif args.command == "system":
            cmd_system(yesterday)
        elif args.command == "processes":
            cmd_processes(yesterday)
        elif args.command == "traffic":
            cmd_traffic(yesterday, iface)
    except Exception as exc:
        logging.exception("Audit failed: %s", exc)
        print(f"ERROR: Audit failed: {exc}", file=sys.stderr)
        return 1

    logging.info("=== Audit Completed Successfully ===")
    print(f"Audit finished. Files in {DATA_DIR}/ (date: {yest_str})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

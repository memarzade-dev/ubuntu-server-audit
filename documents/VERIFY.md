# VERIFY

Commands and expected outcomes for verifying the installation and functionality.

## V01: Syntax Check (no runtime needed)

```bash
python3 -m py_compile /opt/server-audit/audit.py
echo $?
# Expected: 0 (no syntax errors)
```

## V02: Help Output

```bash
server-report --help
# Expected: shows usage with subcommands: full, hardware, system, processes, traffic, setup, version
# Exit code: 0
```

## V03: Version Output

```bash
server-report version
# Expected: "server-report v2.0.0"
# Exit code: 0
```

## V04: Root Enforcement

```bash
# As a non-root user:
server-report full
# Expected stderr: "ERROR: This tool must be run as root (sudo)."
# Exit code: 1
```

## V05: Full Audit Run

```bash
sudo server-report full -v
# Expected: produces verbose output to stderr, ends with "Audit finished."
# Exit code: 0

ls -lh /var/log/server-audit/data/
# Expected: at least 4 files:
#   hardware_inventory.csv
#   system_summary_YYYY-MM-DD.csv
#   processes_YYYY-MM-DD.csv
#   network_traffic_YYYY-MM-DD.csv
```

## V06: CSV Validity Check

```bash
python3 << 'PYCHECK'
import csv, glob, sys
files = glob.glob("/var/log/server-audit/data/*.csv")
if not files:
    print("FAIL: no CSV files found")
    sys.exit(1)
for f in files:
    try:
        with open(f, encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
            print(f"PASS: {f} -> {len(rows)} rows")
    except Exception as e:
        print(f"FAIL: {f} -> {e}")
        sys.exit(1)
PYCHECK
```

## V07: No vnstat -u in Code

```bash
grep -rn 'vnstat.*-u\b' /opt/server-audit/audit.py
# Expected: no output (grep exits 1)
grep -rn 'vnstat.*--update' /opt/server-audit/audit.py
# Expected: no output
```

## V08: vnstat --add Present in Code

```bash
grep -c 'vnstat.*--add' /opt/server-audit/audit.py
# Expected: 1 or more
```

## V09: systemd Timer Active

```bash
systemctl is-active server-audit.timer
# Expected: "active"

systemctl list-timers server-audit.timer --no-pager
# Expected: shows NEXT and LAST columns, NEXT around 01:00 tomorrow
```

## V10: Systemd Timer Trigger Test

```bash
sudo systemctl start server-audit.service
journalctl -u server-audit.service --no-pager -n 20
# Expected: shows "Server Audit Started" and "Audit Completed"
```

## V11: Log File Written

```bash
tail -5 /var/log/server-audit/audit.log
# Expected: structured log lines with timestamps
# Pattern: "YYYY-MM-DD HH:MM:SS | INFO    | funcname | message"
```

## V12: Cleanup Verification

```bash
# Create a fake old file
sudo touch -d "2020-01-01" /var/log/server-audit/data/test_2020-01-01.csv
sudo server-report full
test -f /var/log/server-audit/data/test_2020-01-01.csv && echo "FAIL" || echo "PASS"
```

## V13: Individual Subcommands

```bash
sudo server-report hardware
ls /var/log/server-audit/data/hardware_inventory.csv && echo "PASS" || echo "FAIL"

sudo server-report traffic
ls /var/log/server-audit/data/network_traffic_*.csv && echo "PASS" || echo "FAIL"

sudo server-report processes
ls /var/log/server-audit/data/processes_*.csv && echo "PASS" || echo "FAIL"

sudo server-report system
ls /var/log/server-audit/data/system_summary_*.csv && echo "PASS" || echo "FAIL"
```

## V14: Uninstall Verification

```bash
sudo bash uninstall.sh
systemctl is-active server-audit.timer 2>&1 | grep -q "inactive\|could not" && echo "PASS" || echo "FAIL"
test -f /usr/local/bin/server-report && echo "FAIL" || echo "PASS"
test -d /opt/server-audit && echo "FAIL" || echo "PASS"
test -d /var/log/server-audit && echo "PASS: data preserved" || echo "WARN: data removed"
```

## V15: Dependency Versions

```bash
echo "--- Package versions ---"
dpkg -l | grep -E 'sysstat|vnstat|nethogs|lshw|dmidecode' | awk '{print $2, $3}'
# Expected:
#   sysstat   12.6.1-2    (24.04) or 12.5.2-2build2 (22.04)
#   vnstat    2.12-1      (24.04) or 2.9-1           (22.04)
#   nethogs   0.8.7-2build2 (24.04) or 0.8.6-3      (22.04)
#   lshw      02.19...
#   dmidecode 3.5-3...
```

# ACCEPTANCE

## Definition of Done

A feature is "done" when all of the following are true:

1. Code runs without errors on a clean Ubuntu 22.04 or 24.04 server
2. No `TypeError`, `CalledProcessError`, or unhandled exceptions
3. Output CSV files are valid and parseable
4. All acceptance tests below pass

## Acceptance Tests

### AT01: Clean Install on Ubuntu 24.04

```bash
# On a fresh Ubuntu 24.04 server
sudo bash install.sh
# Expected: exits 0, prints "Installation complete!"
# Verify: /opt/server-audit/audit.py exists and is executable
test -x /opt/server-audit/audit.py && echo "PASS" || echo "FAIL"
```

### AT02: Clean Install on Ubuntu 22.04

```bash
# On a fresh Ubuntu 22.04 server
sudo bash install.sh
# Expected: exits 0, no errors about vnstat -u
# Verify: no "unrecognized option" in output
```

### AT03: CLI Version Command

```bash
server-report version
# Expected: "server-report v2.0.0"
echo $?
# Expected: 0
```

### AT04: Full Audit Produces 4 CSV Files

```bash
sudo server-report full
ls /var/log/server-audit/data/*.csv | wc -l
# Expected: at least 4 files
# hardware_inventory.csv
# system_summary_YYYY-MM-DD.csv
# processes_YYYY-MM-DD.csv
# network_traffic_YYYY-MM-DD.csv
```

### AT05: Hardware CSV is Valid

```bash
python3 -c "
import csv
with open('/var/log/server-audit/data/hardware_inventory.csv', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    rows = list(reader)
    assert len(rows) > 5, f'Too few rows: {len(rows)}'
    assert rows[0] == ['Category', 'Key', 'Value'], f'Bad header: {rows[0]}'
    print(f'PASS: {len(rows)} rows')
"
```

### AT06: No vnstat -u in Codebase

```bash
grep -r 'vnstat.*-u' /opt/server-audit/audit.py && echo "FAIL: found vnstat -u" || echo "PASS"
grep -r "vnstat.*--update" /opt/server-audit/audit.py && echo "FAIL: found --update" || echo "PASS"
```

### AT07: vnstat Uses --add

```bash
grep -c 'vnstat.*--add' /opt/server-audit/audit.py
# Expected: at least 1
```

### AT08: run_cmd Does Not Have shell= as Keyword Arg in Function Calls

```bash
# The function signature accepts shell implicitly via isinstance detection
# No external caller should pass shell= as keyword
grep -n 'run_cmd.*shell=' /opt/server-audit/audit.py | grep -v 'def run_cmd' | grep -v '#' | wc -l
# Expected: 0
```

### AT09: systemd Timer is Active

```bash
systemctl is-active server-audit.timer
# Expected: "active"
systemctl list-timers server-audit.timer --no-pager | grep server-audit
# Expected: shows next elapse time around 01:00
```

### AT10: Root Check Works

```bash
# As non-root user:
server-report full 2>&1
# Expected: "ERROR: This tool must be run as root (sudo)."
echo $?
# Expected: 1
```

### AT11: Verbose Mode Produces stderr Output

```bash
sudo server-report full -v 2>&1 | grep -c "INFO"
# Expected: > 0
```

### AT12: Cleanup Removes Old Files

```bash
# Create a fake old file
sudo touch -d "2020-01-01" /var/log/server-audit/data/test_2020-01-01.csv
sudo server-report full
test -f /var/log/server-audit/data/test_2020-01-01.csv && echo "FAIL" || echo "PASS: old file removed"
```

### AT13: Uninstall Works Cleanly

```bash
sudo bash uninstall.sh
systemctl is-active server-audit.timer 2>&1
# Expected: "inactive" or not found
test -f /usr/local/bin/server-report && echo "FAIL" || echo "PASS"
test -d /opt/server-audit && echo "FAIL" || echo "PASS"
# Data preserved:
test -d /var/log/server-audit && echo "PASS: data preserved" || echo "data gone"
```

### AT14: vnstat JSON Parsing Handles 2.x Format

```bash
# Verify no reference to vnstat 1.x "id" field in traffic parsing
grep -n '"id"' /opt/server-audit/audit.py | grep -v 'VERSION_ID' | wc -l
# Expected: 0 (no vnstat 1.x id parsing)
```

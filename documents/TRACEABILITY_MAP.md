# TRACEABILITY_MAP

Maps every requirement to its source document.

| Req ID | Requirement | Source |
|--------|-------------|--------|
| R01 | Collect hardware info (CPU, MEM, disk, DMI) | Doc 2 §A, Doc 4 §E |
| R02 | Collect system metrics from sysstat (24h) | Doc 2 §A, Doc 2 §D |
| R03 | Collect per-process CPU/MEM/IO snapshot | Doc 2 §A, Doc 4 §E |
| R04 | Collect per-process network snapshot (nethogs) | Doc 2 §A, Doc 2 §D |
| R05 | Collect server-wide 24h traffic (vnstat) | Doc 2 §A, Doc 2 §D |
| R06 | Output format: CSV | Doc 2 §A (constraint) |
| R07 | Retention: 7 days data, 1 day logs | Doc 2 §A |
| R08 | Platform: Ubuntu 22.04 and 24.04 only | Doc 2 §A (constraint), Doc 4 §A |
| R09 | No external Python dependencies | Doc 2 §A (constraint) |
| R10 | Run as root/sudo | Doc 2 §A (assumption) |
| R11 | Auto-detect primary network interface | Doc 2 §A (assumption) |
| R12 | CLI with subcommands | Doc 3 §A ("server-report full/processes/hardware") |
| R13 | systemd timer daily at 01:00 | Doc 3 §A, Doc 3 §E |
| R14 | One-file bash installer | Doc 3 §A, Doc 4 §A |
| R15 | Fix vnstat -u bug (removed in 2.x) | Doc 1 (error log), Research findings |
| R16 | Fix run_cmd shell= parameter handling | Doc 1 (error log: TypeError), Doc 4 §D |
| R17 | Structured logging | Doc 5 (quality bar) |
| R18 | Error handling: no silent failures | Doc 5 (rule 6) |
| R19 | Verification plan included | Doc 5 (rule 6) |
| R20 | GitHub-ready repo structure | Doc 4 §A, Doc 5 (rule 8) |
| R21 | vnstat JSON: use date object, values in bytes | Research findings (vnstat 2.x) |
| R22 | sysstat: use systemd timers on 24.04 | Research findings (Ubuntu 24.04) |
| R23 | nethogs: parse PID from /path/PID/UID format | Research findings (nethogs man page) |
| R24 | pidstat -h: single merged header, no repeats | Research findings (pidstat man page) |

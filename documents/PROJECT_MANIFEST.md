# PROJECT_MANIFEST

## Goals

| ID | Goal | Priority |
|----|------|----------|
| G1 | Collect hardware inventory (CPU, memory, disk, DMI) | P0 |
| G2 | Collect 24h system metrics from sysstat/sadf as CSV | P0 |
| G3 | Collect per-process CPU/MEM/IO snapshot via pidstat | P0 |
| G4 | Collect per-process network bandwidth snapshot via nethogs | P0 |
| G5 | Collect server-wide 24h traffic from vnstat | P0 |
| G6 | Output all data as CSV with 7-day retention | P0 |
| G7 | Provide CLI with subcommands (full/hardware/system/processes/traffic/setup) | P1 |
| G8 | Schedule daily execution at 01:00 AM via systemd timer | P1 |
| G9 | One-command installer for Ubuntu 22.04/24.04 | P1 |
| G10 | Zero external Python dependencies (stdlib only) | P2 |

## Target Users

- Linux server administrators with basic command-line knowledge
- DevOps engineers managing Ubuntu fleets
- Users of sagernet/sing-box infrastructure needing server health monitoring

## Non-Functional Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| NFR1 | Must work on Ubuntu 22.04 and 24.04 without modification | Doc 2, Doc 3 |
| NFR2 | Must run with sudo/root only | Doc 2 |
| NFR3 | No external Python packages (stdlib + subprocess only) | Doc 2 |
| NFR4 | CSV output for all data | Doc 2 |
| NFR5 | 7-day data retention, 1-day log retention | Doc 2 |
| NFR6 | Structured logging to file | Doc 5 (quality bar) |
| NFR7 | Error handling: never crash silently, log all failures | Doc 5 |
| NFR8 | Safe for non-expert users (no destructive operations) | Doc 5 |

## Constraints

- Only apt-installable packages: `sysstat`, `vnstat`, `nethogs`, `lshw`, `dmidecode`
- Per-process historical traffic requires eBPF (out of scope); only real-time snapshot via nethogs
- sysstat needs ~10 minutes after enable to produce first data
- vnstat needs hours to accumulate meaningful traffic data

## Success Criteria

- [ ] `sudo bash install.sh` completes without errors on Ubuntu 22.04 and 24.04
- [ ] `sudo server-report full` produces 4 CSV files in `/var/log/server-audit/data/`
- [ ] `systemctl status server-audit.timer` shows active
- [ ] CSV files are valid (parseable by Python csv module and Excel)
- [ ] No `vnstat -u` usage anywhere (2.x compat)
- [ ] All subprocess calls use correct shell/list patterns
- [ ] Cleanup removes files older than 7 days

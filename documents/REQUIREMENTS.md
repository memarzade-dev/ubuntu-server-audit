# REQUIREMENTS

All requirements extracted from user documents with traceability.

## Functional Requirements

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR01 | Collect CPU info (model, cores, architecture, flags) via lscpu | Doc 2 §A | Done |
| FR02 | Collect memory info (total, available, swap) via free | Doc 2 §A | Done |
| FR03 | Collect disk info (root size/used/avail, block devices) via df/lsblk | Doc 2 §A | Done |
| FR04 | Collect DMI info (manufacturer, product) via dmidecode | Doc 2 §A | Done |
| FR05 | Collect kernel version and architecture via uname | Doc 2 §A | Done |
| FR06 | Collect system uptime via uptime | Doc 2 §A | Done |
| FR07 | Collect 24h CPU/memory/IO/network/load from sysstat sadf | Doc 2 §A, §D | Done |
| FR08 | Collect per-process CPU/MEM/IO snapshot via pidstat -u -r -d -h | Doc 2 §A | Done |
| FR09 | Collect per-process network bandwidth snapshot via nethogs -t | Doc 2 §A, §D | Done |
| FR10 | Collect server-wide 24h traffic from vnstat --json d | Doc 2 §A, §D | Done |
| FR11 | Merge pidstat + nethogs data by PID | Doc 2 §A | Done |
| FR12 | Output all data as CSV files | Doc 2 §A (constraint) | Done |
| FR13 | Auto-detect primary network interface via ip route | Doc 2 §A (assumption) | Done |
| FR14 | CLI with subcommands: full, hardware, system, processes, traffic, setup | Doc 3 §A | Done |
| FR15 | systemd timer for daily 01:00 AM execution | Doc 3 §A, §E | Done |
| FR16 | One-file bash installer (install.sh) | Doc 3 §A, Doc 4 §A | Done |
| FR17 | Auto-cleanup: 7 days data retention | Doc 2 §A | Done |
| FR18 | Auto-cleanup: 1 day log retention | Doc 2 §A | Done |
| FR19 | --setup flag installs packages and enables services | Doc 2 §F | Done |
| FR20 | --verbose flag for debug output | Doc 5 (quality bar) | Done |
| FR21 | --output-dir flag to override data directory | Enhancement | Done |

## Bug Fix Requirements (from error logs)

| ID | Bug | Root Cause | Fix | Source |
|----|-----|-----------|-----|--------|
| BF01 | `TypeError: run_cmd() got an unexpected keyword argument 'shell'` | run_cmd() did not accept `shell` parameter | run_cmd() now uses isinstance(cmd, list) to determine shell mode | Doc 1 line 14 |
| BF02 | `CalledProcessError: Command '['vnstat', '-u', '-i', 'eth0']' returned non-zero exit status 1` | `vnstat -u` removed in vnstat 2.x | Changed to `vnstat --add -i <iface>` with existence check | Doc 1 line 32 |
| BF03 | vnstat JSON parsing returned 0 traffic | Code used `id` field (1.x) instead of `date` object (2.x) | Parse `date.year/month/day` from vnstat 2.x JSON | Research |
| BF04 | vnstat traffic values 1024x too small | Code assumed KiB (1.x) but 2.x returns bytes | Division by 1024^3 for GB conversion | Research |

## Non-Functional Requirements

| ID | Requirement | Source |
|----|-------------|--------|
| NFR01 | Ubuntu 22.04 and 24.04 only | Doc 2 §A |
| NFR02 | Root/sudo required | Doc 2 §A |
| NFR03 | No external Python dependencies (stdlib only) | Doc 2 §A |
| NFR04 | Structured logging with timestamps | Doc 5 (quality bar) |
| NFR05 | Error handling: no silent failures | Doc 5 (rule 6) |
| NFR06 | Command timeouts to prevent hangs | Enhancement |
| NFR07 | GitHub-ready repo structure | Doc 4 §A, Doc 5 (rule 8) |
| NFR08 | CI pipeline (syntax check) | Doc 5 (rule 8) |
| NFR09 | Clean uninstall path | Enhancement |

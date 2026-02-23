# ASSUMPTIONS

Reasonable assumptions made during implementation. None are blocking.

| ID | Assumption | Rationale | Impact if Wrong |
|----|-----------|-----------|-----------------|
| A01 | Install directory is `/opt/server-audit` (with hyphen) | Consistent naming with systemd unit names and log directory | Low: change INSTALL_DIR in install.sh |
| A02 | Python 3.10+ is pre-installed | Ubuntu 22.04 ships Python 3.10, Ubuntu 24.04 ships Python 3.12 | High: script won't run without Python 3 |
| A03 | Primary interface is auto-detectable via `ip route get 8.8.8.8` | Works on any server with internet connectivity | Medium: falls back to first non-lo interface, then "eth0" |
| A04 | License is MIT | Default per operating_mode template | None: easily changed |
| A05 | sysstat data files are at `/var/log/sysstat/saDD` | Debian/Ubuntu default path (differs from RHEL `/var/log/sa/saDD`) | High: sadf would not find data files |
| A06 | Root/sudo is available for all operations | Required by nethogs (raw packets), pidstat (all processes), vnstat --add, apt | High: tool cannot function without root |
| A07 | Server has at least one active non-loopback interface | Required for vnstat and nethogs | Medium: graceful fallback with warning |
| A08 | UTF-8 is the system locale | Standard on Ubuntu 22.04/24.04 | Low: CSV written with explicit utf-8-sig encoding |
| A09 | /var/log partition has sufficient space for CSV files | Typical CSV files are <1MB each; 7 days max | Low: would fail with disk full error |
| A10 | vnstat daemon is capable of auto-detecting interfaces if `AlwaysAddNewInterfaces` is enabled | True for vnstat 2.8+ (both Ubuntu versions qualify) | Low: explicit `--add` as fallback |
| A11 | nethogs per-process data is a point-in-time snapshot, not 24h historical | nethogs captures live traffic; historical per-process requires eBPF | None: this is a documented limitation |
| A12 | `pidstat -h` output format is stable across sysstat 12.5.2 and 12.6.1 | Both versions produce the same merged-header format | Medium: column parsing could break on major version change |

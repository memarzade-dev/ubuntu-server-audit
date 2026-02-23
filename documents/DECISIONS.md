# DECISIONS

Key technical decisions with rationale.

## D01: vnstat --add instead of vnstat -u

| Field | Value |
|-------|-------|
| Decision | Use `vnstat --add -i <iface>` for interface initialization |
| Alternatives | `vnstat -u -i <iface>` (1.x only), rely on auto-detection |
| Rationale | `vnstat -u` was removed in vnstat 2.x. Ubuntu 22.04 ships 2.9, Ubuntu 24.04 ships 2.12. Both are 2.x. `--add` is the documented replacement. We also check if the interface already exists before adding. |
| Source | [vnstat UPGRADE.md](https://github.com/vergoh/vnstat/blob/master/UPGRADE.md), Doc 1 error log |
| Risk | None. `--add` is stable since vnstat 2.0. |

## D02: run_cmd uses isinstance(cmd, list) for shell detection

| Field | Value |
|-------|-------|
| Decision | `shell=False` when cmd is a list, `shell=True` when cmd is a string |
| Alternatives | Always shell=True with string (unsafe), auto-detect pipe characters |
| Rationale | Python subprocess docs: list with shell=False is safest (no injection). String with shell=True is required for pipes/redirects. Using isinstance() is deterministic and avoids the heuristic bugs in previous iterations (checking for 'sed'/'awk' in command strings). |
| Source | [Python subprocess docs](https://docs.python.org/3/library/subprocess.html), Doc 1 error log |
| Risk | Caller must pass list for simple commands, string for pipelines. This is explicit and clear. |

## D03: vnstat JSON parsing uses date object (2.x format)

| Field | Value |
|-------|-------|
| Decision | Parse `date.year`, `date.month`, `date.day` from vnstat JSON |
| Alternatives | Parse `id` field (1.x format) |
| Rationale | vnstat 2.x JSON uses nested `date` objects. The `id` field does not exist in 2.x output. Values are in bytes, not KiB. |
| Source | [vnstat man page](https://humdi.net/vnstat/man/vnstat.html), Research findings |
| Risk | None. All target Ubuntu versions ship vnstat 2.x. |

## D04: sysstat enablement strategy (dual-mode)

| Field | Value |
|-------|-------|
| Decision | Enable both systemd timers and set `/etc/default/sysstat` ENABLED=true |
| Alternatives | Only timers (breaks 22.04 cron path), only /etc/default (misses 24.04 timers) |
| Rationale | Ubuntu 22.04 uses cron+/etc/default, Ubuntu 24.04 uses systemd timers. Enabling both is safe and covers both versions. |
| Source | [Ubuntu bug #2066117](https://bugs.launchpad.net/ubuntu/+source/sysstat/+bug/2066117) |
| Risk | None. Redundant enable is harmless. |

## D05: nethogs PID extraction via rsplit

| Field | Value |
|-------|-------|
| Decision | Extract PID from nethogs output using `/path/binary/PID/UID` format with rsplit("/", 2) |
| Alternatives | Regex extraction, awk pre-processing |
| Rationale | nethogs -t output embeds PID as the second-to-last segment in the process identifier path. rsplit is the most reliable parser. |
| Source | [nethogs man page](https://www.mankier.com/8/nethogs), Research findings |
| Risk | Low. Format is stable across nethogs 0.8.6-0.8.7. |

## D06: pidstat -h for single merged header

| Field | Value |
|-------|-------|
| Decision | Use `pidstat -u -r -d -h 1 3` for combined CPU+MEM+IO in one header |
| Alternatives | Separate pidstat calls, parse repeated headers |
| Rationale | `-h` produces one `#`-prefixed header line with all metrics merged, no repeated headers between samples, no "Average:" summary. Simplest to parse. |
| Source | [pidstat man page](https://linux.die.net/man/1/pidstat), Research findings |
| Risk | Column count may change if sysstat adds new metrics in future major versions. |

## D07: systemd timer with Persistent + FixedRandomDelay

| Field | Value |
|-------|-------|
| Decision | Use `Persistent=true` and `FixedRandomDelay=true` with `RandomizedDelaySec=300` |
| Alternatives | Plain cron, timer without persistence |
| Rationale | Persistent ensures missed runs (server was off at 01:00) execute on next boot. FixedRandomDelay (systemd 247+, present in both Ubuntu versions) gives stable per-host jitter. |
| Source | [systemd.timer docs](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) |
| Risk | FixedRandomDelay requires systemd 247+. Ubuntu 22.04 ships 249, Ubuntu 24.04 ships 255. Both qualify. |

## D08: CSV with UTF-8 BOM

| Field | Value |
|-------|-------|
| Decision | Write CSV files with `utf-8-sig` encoding (UTF-8 with BOM) |
| Alternatives | Plain UTF-8 |
| Rationale | Excel on Windows requires BOM to auto-detect UTF-8. Unix tools ignore BOM. Best compatibility. |
| Source | Best practice for cross-platform CSV |
| Risk | None. BOM is harmless on Linux. |

## D09: Single-file Python architecture (no pip dependencies)

| Field | Value |
|-------|-------|
| Decision | Single audit.py file using only Python stdlib |
| Alternatives | Multi-module package with setup.py, external dependencies |
| Rationale | Must work on any Ubuntu 22/24 server without pip install. Single file is easiest to deploy via installer. |
| Source | Doc 2 §A constraint |
| Risk | File is large (~350 lines) but manageable. |

## Conflict Resolution

| Conflict | Resolution | Rationale |
|----------|-----------|-----------|
| Doc 2 uses `vnstat -u` but Doc 1 shows it fails | Use `vnstat --add` | Error log proves -u is broken; research confirms removal in 2.x |
| Doc 3 uses string heuristic for shell detection (checking for 'sed'/'awk') | Use isinstance(cmd, list) | Heuristic is fragile and can misfire; type check is deterministic |
| Doc 4 uses `run_cmd(["vnstat", "-u", "-i", iface])` | Use `["vnstat", "--add", "-i", iface]` with existence check | Same root cause as above |

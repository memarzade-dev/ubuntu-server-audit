# Ubuntu server audit script: verified tool reference

**Every command listed here has been verified against the Ubuntu 24.04 (Noble) and 22.04 (Jammy) package repositories and official documentation.** This reference covers vnstat 2.x interface initialization and JSON output, sysstat/sadf CSV export, nethogs text-mode parsing, pidstat column layout, Python 3.12 subprocess patterns, and systemd timer configuration — all with exact syntax, output formats, and Ubuntu-specific package versions.

| Tool | Ubuntu 22.04 (Jammy) | Ubuntu 24.04 (Noble) |
|------|---------------------|---------------------|
| vnstat | 2.9-1 | 2.12-1 |
| sysstat (sar/sadf/pidstat) | 12.5.2-2build2 | 12.6.1-2 |
| nethogs | 0.8.6-3 | 0.8.7-2build2 |
| Python 3 | 3.10.x | 3.12.3 |
| systemd | 249 | 255 |

---

## vnstat 2.x dropped `-u` entirely — use `--add` or let the daemon auto-detect

The old `vnstat -u -i eth0` command from vnstat 1.x is **not merely deprecated — it is removed**. Running it on vnstat 2.x produces an unrecognized-option error and exits with a non-zero code. The `-u`/`--update` flag does not exist in the 2.x man page or synopsis.

**The correct replacement is `vnstat --add -i <iface>`:**

```bash
vnstat --add -i eth0
```

This creates a database entry for the specified interface. The daemon picks it up automatically within `SaveInterval` minutes if `RescanDatabaseOnSave` is enabled in `/etc/vnstat.conf`, or after a restart otherwise. Note that `--add` belongs to the `vnstat` command, not `vnstatd`.

**In most cases, manual initialization is unnecessary.** On first startup with no existing database, vnstatd automatically creates entries for all available interfaces (excluding `lo`, `lo0`, `sit0`). If the database already exists and a new interface appears, auto-addition only happens if `AlwaysAddNewInterfaces 1` is set in `/etc/vnstat.conf` (available since vnstat 2.8, so present in both 2.9 and 2.12), or if vnstatd was started with the `--alwaysadd` flag.

For a production audit script, the safest initialization pattern is:

```python
# Check if interface exists in vnstat DB; add if missing
result = subprocess.run(["vnstat", "--json", "d", "-i", iface],
                        capture_output=True, text=True, timeout=10)
if result.returncode != 0:
    subprocess.run(["vnstat", "--add", "-i", iface],
                   capture_output=True, text=True, timeout=10)
```

### vnstat 2.x JSON output: structure and the critical bytes-vs-KiB change

The **most dangerous migration trap** is the unit change: vnstat 1.x reported rx/tx in **KiB**, while vnstat 2.x reports them in **bytes**. Code assuming KiB will silently under-report by 1024×.

The command `vnstat --json d` produces this structure:

```json
{
  "vnstatversion": "2.12",
  "jsonversion": "2",
  "interfaces": [
    {
      "name": "eth0",
      "alias": "",
      "created": {
        "date": { "year": 2025, "month": 1, "day": 15 }
      },
      "updated": {
        "date": { "year": 2025, "month": 2, "day": 23 },
        "time": { "hour": 14, "minute": 30 }
      },
      "traffic": {
        "total": { "rx": 2636046336, "tx": 1320157184 },
        "days": [
          {
            "date": { "year": 2025, "month": 2, "day": 22 },
            "rx": 47472640,
            "tx": 24235008
          },
          {
            "date": { "year": 2025, "month": 2, "day": 23 },
            "rx": 31457280,
            "tx": 15728640
          }
        ]
      }
    }
  ]
}
```

**Key structural details** — each day entry has exactly three fields: a `date` sub-object (with integer `year`, `month`, `day`), `rx` (received bytes as integer), and `tx` (transmitted bytes as integer). There is **no `"id"` field** in 2.x day entries (1.x had a sequential `"id": 0` where 0 meant today). The interface identifier changed from `"id"` in 1.x to `"name"` in 2.x. The `jsonversion` field reads `"2"` for the 2.x API.

Additional mode parameters for `--json`: `h` (hours), `m` (months), `y` (years), `f` (five-minute), `t` (top days), `s` (summary), `p` (95th percentile). Append a limit: `vnstat --json d 7` returns the last 7 days, `vnstat --json d 0` returns all stored days.

---

## sysstat on Ubuntu 24.04 uses systemd timers, not `/etc/default/sysstat`

On Ubuntu 24.04, sysstat **12.6.1-2** is pre-installed (seeded) and `sysstat-collect.timer` is **enabled by default via systemd preset** on fresh installs. The file `/etc/default/sysstat` with `ENABLED="true"` still exists but **only controls the legacy cron path** — it does not enable or disable the systemd timer. On Ubuntu 22.04, sysstat is not pre-installed and after installation, both the cron path and the timer are disabled; you must explicitly enable one.

The recommended enablement for both releases:

```bash
sudo systemctl enable --now sysstat-collect.timer
sudo systemctl enable --now sysstat-summary.timer
```

**Data files live at `/var/log/sysstat/saDD`** (e.g., `sa01`, `sa23`) — this is the Debian/Ubuntu-patched default, different from the upstream/RHEL default of `/var/log/sa/saDD`. When `HISTORY > 28`, files use the `saYYYYMMDD` naming convention.

### sadf CSV export: exact command and column headers

The command to export all major metrics as semicolon-delimited data:

```bash
sadf -d -s 00:00:00 -e 23:59:59 /var/log/sysstat/sa23 -- -u -r -b -n DEV -q
```

The `-d` flag produces "database format" with **semicolon delimiters**. The `--` separator is required to distinguish sadf flags from sar flags. Without `-s`/`-e`, sadf defaults to the 08:00–18:00 window, so always specify them for full-day export.

Each activity produces its own header line (prefixed with `#`) and data block. Here are the exact column headers for sysstat 12.6.1:

**CPU (`-u`):**
```
# hostname;interval;timestamp;CPU;%user;%nice;%system;%iowait;%steal;%idle
```

**Memory (`-r`):**
```
# hostname;interval;timestamp;kbmemfree;kbavail;kbmemused;%memused;kbbuffers;kbcached;kbcommit;%commit;kbactive;kbinact;kbdirty
```

**I/O transfer rates (`-b`):**
```
# hostname;interval;timestamp;tps;rtps;wtps;dtps;bread/s;bwrtn/s;bdscd/s
```

**Network devices (`-n DEV`):**
```
# hostname;interval;timestamp;IFACE;rxpck/s;txpck/s;rxkB/s;txkB/s;rxcmp/s;txcmp/s;rxmcst/s;%ifutil
```

**Load averages (`-q`):**
```
# hostname;interval;timestamp;runq-sz;plist-sz;ldavg-1;ldavg-5;ldavg-15;blocked
```

Data lines follow the pattern `hostname;600;2025-02-23 01:10:01 UTC;field_values...`. When multiple sar flags are combined, sadf outputs **separate blocks per activity** (each with its own header). To merge all metrics onto a single line per timestamp, add the `-h` flag: `sadf -d -h`.

Note the version difference for `-q`: on sysstat 12.6.1 (Noble), `-q` accepts keywords like `LOAD`, `CPU`, `IO`, `MEM`, `PSI`. On 12.5.2 (Jammy), plain `-q` covers queue/load only.

---

## nethogs text mode: `-t -c 8 -v 0` is correct, but PID parsing requires care

The command `nethogs -t -c 8 -v 0` is **valid syntax** on both Ubuntu 22.04 (nethogs 0.8.6) and 24.04 (nethogs 0.8.7). Nethogs **requires root/sudo** because it uses raw packet capture via libpcap.

```bash
sudo nethogs -t -c 8 -v 0 eth0
```

Flag breakdown: `-t` enables tracemode (text output to stdout), `-c 8` runs exactly 8 refresh cycles then exits, `-v 0` selects KB/s rate display (alternatives: `1` = total KB, `2` = total bytes, `3` = total MB), and `eth0` specifies the interface.

### nethogs output format and parsing strategy

The output looks like this:

```
Refreshing:
/usr/lib/firefox/firefox/2196/1000	0.771094	0.119922
unknown TCP/0/0	0.010547	0.011719
Refreshing:
/usr/bin/curl/8432/1000	1.234567	0.567890
/usr/lib/firefox/firefox/2196/1000	0.781641	0.232617
unknown TCP/0/0	0.010547	0.011719
```

Each refresh cycle starts with `Refreshing:`. Data lines are **tab-separated** with three fields: process identifier, sent value, received value. The critical parsing detail is that **PID is not a standalone column** — it is embedded in the process identifier string as the second-to-last `/`-delimited segment, following the format `/path/to/binary/PID/UID`. For `unknown TCP/0/0`, both PID and UID are 0.

Reliable parsing in Python:

```python
for line in output.splitlines():
    if line.startswith("Refreshing:") or not line.strip():
        continue
    parts = line.split("\t")
    if len(parts) == 3:
        proc_path, sent, received = parts
        segments = proc_path.rsplit("/", 2)
        if len(segments) == 3:
            binary_path, pid, uid = segments[0], segments[1], segments[2]
```

To run without full root, you can assign capabilities: `sudo setcap "cap_net_admin,cap_net_raw,cap_dac_read_search,cap_sys_ptrace+pe" /usr/sbin/nethogs`.

---

## pidstat `-h` produces a single `#`-prefixed header with all metrics on one line

The command `pidstat -u -r -d -h 1 3` produces three samples at 1-second intervals with **all CPU, memory, and disk I/O columns merged onto a single line per process**. The `-h` flag ensures **one header line** (prefixed with `#`) at the top, **no repeated headers** between samples, and **no "Average:" summary** at the end. Timestamps appear as Unix epoch seconds.

The exact column layout for sysstat 12.6.1 (also 12.5.2, which includes both `%wait` and `iodelay`):

```
# Time        UID       PID    %usr %system  %guest   %wait    %CPU   CPU  minflt/s  majflt/s     VSZ     RSS   %MEM   kB_rd/s   kB_wr/s kB_ccwr/s iodelay  Command
```

| Position | Column | Flag | Description |
|----------|--------|------|-------------|
| 1 | `# Time` | always | Unix timestamp (epoch seconds) |
| 2 | `UID` | always | Real user ID |
| 3 | `PID` | always | Process ID |
| 4–9 | `%usr`, `%system`, `%guest`, `%wait`, `%CPU`, `CPU` | `-u` | CPU utilization metrics |
| 10–14 | `minflt/s`, `majflt/s`, `VSZ`, `RSS`, `%MEM` | `-r` | Memory/page fault metrics |
| 15–18 | `kB_rd/s`, `kB_wr/s`, `kB_ccwr/s`, `iodelay` | `-d` | Disk I/O metrics |
| 19 | `Command` | always | Process command name |

Values of **`-1.00`** for `kB_rd/s`, `kB_wr/s`, and `kB_ccwr/s` indicate the kernel did not provide I/O accounting data for that process (common for kernel threads). Despite the "kB" naming, pidstat uses **kibibytes** (1024 bytes).

---

## Python subprocess: list+shell=False, string+shell=True, and the shell=True list trap

Ubuntu 24.04 ships **Python 3.12.3**. There are no Linux-specific subprocess changes or deprecations in Python 3.12 (the only 3.12 change is a Windows shell search order security fix).

**The correct patterns:**

```python
# List argument → shell=False (default, preferred)
result = subprocess.run(["vnstat", "--json", "d"], capture_output=True, text=True, timeout=30)

# String with pipes/redirects → shell=True (required)
result = subprocess.run("cat /proc/meminfo | grep MemTotal", shell=True,
                        capture_output=True, text=True, timeout=30)
```

**Two common mistakes to avoid.** Passing a list with `shell=True` does not work as expected — only `args[0]` becomes the shell command, while remaining elements become shell positional parameters (`$0`, `$1`), not command arguments. So `subprocess.run(["echo", "hello"], shell=True)` silently prints a blank line. Passing a string with `shell=False` raises `FileNotFoundError` because the entire string (spaces, pipes, and all) is treated as a literal executable name.

The recommended wrapper for audit scripts:

```python
import subprocess

def run_cmd(cmd, timeout=30, shell=False, check=False):
    """Run a command safely, returning CompletedProcess or None on failure."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=shell,
            check=check
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
```

Use `capture_output=True` (syntactic sugar for `stdout=PIPE, stderr=PIPE`, available since Python 3.7). Use `text=True` for string output with the system's default encoding (UTF-8 on Ubuntu). Always set a `timeout` to prevent hangs. Use `check=True` only when a non-zero exit code should halt execution — for tools like `systemctl is-active` that use exit codes semantically, leave `check=False` and inspect `returncode` manually.

---

## systemd timer: OnCalendar, Persistent, and RandomizedDelaySec on systemd 255

Ubuntu 24.04 ships **systemd 255**. Place custom unit files in `/etc/systemd/system/`.

### Complete timer unit for daily 01:00 AM execution

**`/etc/systemd/system/server-audit.timer`:**

```ini
[Unit]
Description=Daily Server Audit at 01:00 AM

[Timer]
OnCalendar=*-*-* 01:00:00
AccuracySec=1s
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
```

**`/etc/systemd/system/server-audit.service`:**

```ini
[Unit]
Description=Server Audit Script
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/audit/server_audit.py
User=root
StandardOutput=journal
StandardError=journal
Nice=10
```

**`OnCalendar=*-*-* 01:00:00`** means every day at exactly 01:00:00. You cannot use `OnCalendar=daily` for 1 AM — that normalizes to midnight. Verify with `systemd-analyze calendar "*-*-* 01:00:00"`.

**`Persistent=true`** stores the last-trigger timestamp in `/var/lib/systemd/timers/stamp-server-audit.timer`. If the system was powered off at 01:00 AM, the job triggers immediately on next boot (subject to `RandomizedDelaySec`). This only works with `OnCalendar=` timers, not monotonic timers like `OnBootSec=`.

**`RandomizedDelaySec=300`** adds a random delay between **0 and 300 seconds** to the scheduled time, spreading actual execution across a 5-minute window (01:00:00–01:05:00). This prevents thundering-herd effects on fleets of identically-configured servers. For deterministic per-host delays that are stable across reboots, add `FixedRandomDelay=true` (available since systemd 247, present in Ubuntu 24.04's systemd 255).

**`AccuracySec=1s`** overrides the default 1-minute coalescing window. Without this, systemd may delay the trigger up to 1 minute to batch timer wake-ups for power efficiency.

Enable and activate:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now server-audit.timer
sudo systemctl list-timers server-audit.timer   # verify next elapse time
```

The `.service` file intentionally has no `[Install]` section — it is activated exclusively by the timer, never enabled directly.

---

## Conclusion

The most impactful finding for audit script development is the **vnstat 1.x → 2.x migration**: the `-u` flag is gone entirely (use `--add` or rely on daemon auto-detection), and traffic values shifted from KiB to bytes — a silent 1024× discrepancy if unchecked. For sysstat on Ubuntu 24.04, ignore `/etc/default/sysstat` and manage collection exclusively through `systemctl enable sysstat-collect.timer`. When parsing nethogs output, remember that PID is not a standalone column but embedded in the process path as the second-to-last `/`-separated segment. The pidstat `-h` flag is your best friend for machine-parseable output — single header, no repeated headers, all metrics on one line. For subprocess calls, always default to `shell=False` with list arguments and reserve `shell=True` exclusively for pipe chains, and never pass a list when `shell=True` unless you understand the positional-parameter trap.
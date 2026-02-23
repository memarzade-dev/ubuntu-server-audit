# READING_LEDGER

Proof of complete reading of every input document.

## Document 1: Terminal Log (toronto-host)

| Field | Value |
|-------|-------|
| Type | Terminal session paste |
| Sections | 3 (first attempt with /opt/server_audit, second attempt with ~/ubuntu-server-audit, third retry) |
| First line | `root@toronto-host:~# cd /opt/server_audit/` |
| Last line | `root@toronto-host:~/ubuntu-server-audit#` |
| Key finding | `TypeError: run_cmd() got an unexpected keyword argument 'shell'` then `CalledProcessError: Command '['vnstat', '-u', '-i', 'eth0']' returned non-zero exit status 1` |

## Document 2: Original Design Spec (Persian)

| Field | Value |
|-------|-------|
| Type | Design document (Farsi/Persian) with sections A–G |
| Sections | 7 (A: Understanding, B: Clarifying, C: Research Plan, D: Findings, E: Design, F: Implementation, G: Runbook) |
| First line | `**A) درک درخواست**` |
| Last line | `اسکریپت کاملاً آماده کپی-پیست و اجرا است...` |
| Key finding | Original audit.py had `run_cmd(f"vnstat -u -i {iface}", shell=True)` causing TypeError, and used `shell=True` as keyword despite function signature not accepting it |

## Document 3: Second Iteration (Persian)

| Field | Value |
|-------|-------|
| Type | Revised design document (Farsi) with sections A–G |
| Sections | 7 (same structure as Doc 2) |
| First line | `**A) درک**` |
| Last line | `...اگر نیاز به اضافه کردن Prometheus exporter...` |
| Key finding | Fixed `shell=True` keyword but still used `vnstat -u -i` which is removed in vnstat 2.x; also `run_cmd` auto-detects shell via string content heuristic |

## Document 4: Third Iteration (English+Persian)

| Field | Value |
|-------|-------|
| Type | Full repo spec with operating_mode compliance |
| Sections | 7 (A–G) + repo tree + all file contents |
| First line | `**A) Understanding**` |
| Last line | `...اگر نیاز به push به GitHub...` |
| Key finding | Fixed run_cmd to use `isinstance(cmd, list)` check; BUT `vnstat -u -i` still present as `run_cmd(["vnstat", "-u", "-i", iface])` which returns exit code 1 on vnstat 2.x |

## Document 5: Operating Mode Template

| Field | Value |
|-------|-------|
| Type | SOP/prompt template for production code generation |
| Sections | 7 steps (0–7) + Input Contract + Output Format + Quality Bar |
| First line | `ROLE` |
| Last line | `* Prefer structured logs.` |
| Key finding | Defines strict output structure, non-negotiable rules (no TODOs, verification required), and multi-part batching protocol |

## Root Cause Summary

Two critical bugs persisted across all three iterations:

1. **vnstat `-u` flag removed in 2.x**: Ubuntu 22.04 ships vnstat 2.9, Ubuntu 24.04 ships 2.12. Both are 2.x. The `-u`/`--update` flag does not exist. Correct replacement: `vnstat --add -i <iface>`.
2. **vnstat JSON structure changed**: 2.x uses `date: {year, month, day}` objects (not `id` integer), and values are in bytes (not KiB).

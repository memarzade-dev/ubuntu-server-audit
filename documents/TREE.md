# TREE

```
ubuntu-server-audit/
├── README.md                          # Project documentation
├── LICENSE                            # MIT license
├── REQUIREMENTS.md                    # Extracted requirements with traceability
├── ASSUMPTIONS.md                     # Documented assumptions
├── DECISIONS.md                       # Key technical decisions
├── ACCEPTANCE.md                      # Acceptance tests
├── VERIFY.md                          # Verification commands and expected outcomes
├── TREE.md                            # This file
├── READING_LEDGER.md                  # Proof of reading all input documents
├── PROJECT_MANIFEST.md                # Goals, users, NFRs, constraints
├── TRACEABILITY_MAP.md                # Requirement-to-source mapping
├── .gitignore                         # Git ignore rules
├── .editorconfig                      # Editor configuration
├── install.sh                         # One-command installer (bash)
├── uninstall.sh                       # Clean removal script (bash)
├── audit.py                           # Main audit script (Python 3, CLI)
├── systemd/
│   ├── server-audit.service           # systemd oneshot service
│   └── server-audit.timer             # systemd daily timer (01:00 AM)
├── tests/
│   └── test_audit.py                  # Unit tests (offline, no root needed)
└── .github/
    └── workflows/
        └── ci.yml                     # GitHub Actions CI (syntax + lint)
```

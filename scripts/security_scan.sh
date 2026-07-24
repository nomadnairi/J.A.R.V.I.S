#!/usr/bin/env bash
# ==========================================================================
#  J.A.R.V.I.S. — security scan bundle
#  Dependency audit + SAST + secret detection + pattern matching.
#
#  Usage:
#     ./scripts/security_scan.sh            # run everything that is installed
#     STRICT=1 ./scripts/security_scan.sh   # exit non-zero on any finding (CI)
#
#  Install the tools:
#     pip install pip-audit bandit semgrep
#     # secret scanners (optional, native binaries):
#     #   gitleaks  — https://github.com/gitleaks/gitleaks
#     #   trufflehog — https://github.com/trufflesecurity/trufflehog
# ==========================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STRICT="${STRICT:-0}"
FAILED=0
have() { command -v "$1" >/dev/null 2>&1; }
section() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }
note() { printf '\033[0;33m%s\033[0m\n' "$1"; }

# 1) Dependency audit — known-vulnerable packages (CVEs) ---------------------
section "1/4  Dependency audit (pip-audit)"
if have pip-audit; then
    pip-audit -r requirements.txt || FAILED=1
else
    note "pip-audit not installed — skipping (pip install pip-audit)"
fi

# 2) SAST — code-level vulnerabilities (shell injection, path traversal, …) --
section "2/4  Static analysis (bandit)"
if have bandit; then
    # -ll: report medium+ severity; the repo config lists accepted findings.
    bandit -r jarvis/ -c .bandit.yaml -ll || FAILED=1
else
    note "bandit not installed — skipping (pip install bandit)"
fi

# 3) Secret detection — committed tokens / keys ------------------------------
section "3/4  Secret detection (gitleaks / trufflehog)"
if have gitleaks; then
    gitleaks detect --source . --redact --no-banner || FAILED=1
elif have trufflehog; then
    trufflehog filesystem . --only-verified --fail || FAILED=1
else
    note "no secret scanner installed — skipping"
    note "  gitleaks:  https://github.com/gitleaks/gitleaks"
    note "  trufflehog: https://github.com/trufflesecurity/trufflehog"
fi

# 4) Semgrep — vulnerability pattern matching --------------------------------
section "4/4  Pattern matching (semgrep)"
if have semgrep; then
    semgrep --config=p/python --config=p/security-audit \
        --error --quiet jarvis/ || FAILED=1
else
    note "semgrep not installed — skipping (pip install semgrep)"
fi

# Result ---------------------------------------------------------------------
section "Result"
if [ "$FAILED" -eq 0 ]; then
    echo "No blocking findings."
    exit 0
fi
echo "Findings above. Review them."
[ "$STRICT" = "1" ] && exit 1 || exit 0

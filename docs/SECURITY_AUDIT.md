# Security Audit — J.A.R.V.I.S.

Scope: Python 3.10+ async framework, LLM (Anthropic/OpenAI), SQLite + RAG,
Telegram bot, HTTP/WebSocket API, Home Assistant / weather integrations,
accounts + licensing + payments.

CVSS scores use the 3.1 base metric. This audit reflects the code as of the
security-hardening pass; the automated scan is wired into CI (`ci.yml` →
`security` job) and reproducible with `scripts/security_scan.sh`.

---

## 1. Automated scanning

| Tool | Command | Result |
|------|---------|--------|
| Dependency audit | `pip-audit -r requirements.txt` | **No known vulnerabilities** |
| SAST | `bandit -r jarvis/ -c .bandit.yaml -ll` | **0 medium+ after hardening** |
| Secret detection | `gitleaks detect --source .` | run in CI (no committed secrets) |
| Pattern matching | `semgrep --config=p/python jarvis/` | advisory in CI |

Run all four locally:

```bash
pip install pip-audit bandit semgrep
./scripts/security_scan.sh          # STRICT=1 to fail on findings (CI)
```

`.bandit.yaml` documents the accepted low-severity exclusions (asserts on
internal invariants, the `0.0.0.0` default bind, and UI-label false positives).

---

## 2. Attack-vector analysis

### 2.1 Shell injection — `jarvis/coding/runner.py`
**Verdict: mitigated by capability gating.** There is no command whitelist to
bypass; instead `ShellRunner.run()` calls
`security.require(Capability.SHELL_EXEC, ...)`, which raises `PermissionDenied`
(and audits) unless `ALLOW_SHELL=true`. With the default config the shell tool
cannot run at all. A payload like `ls; cat /etc/shadow` only executes if the
operator has explicitly enabled shell access **and** the workspace user can
read the target — i.e. it is an intended capability, not an injection. Blast
radius is limited by `cwd=workspace_root`, a timeout, and running as a
non-root user (Docker/systemd). CVSS: **N/A by default** (7.2 *if* shell is
enabled for an untrusted operator, which is out of the threat model).

### 2.2 Path traversal — `jarvis/files/manager.py`
**Verdict: mitigated.** `_safe_path()` resolves the candidate and rejects it
unless it is the root or a descendant:
`candidate.resolve()` + `self.root not in candidate.parents`. `../../../etc/passwd`
resolves outside the root and raises `SecurityError`; symlink escapes are
caught because `.resolve()` follows links before the check. CVSS: **N/A**
(control present and tested).

### 2.3 Prompt injection — skill/tool responses
**Verdict: residual risk, bounded.** Tool outputs are returned to the LLM as
tool results, not concatenated into the system prompt, so a skill cannot
overwrite the system directive. The genuine residual is *indirect* prompt
injection: a tool that fetches attacker-controlled text (a web page, a HA
attribute) could carry instructions the model then acts on. This is inherent
to agentic LLMs and is contained by the same capability gates — a hijacked
model still cannot write files / run shell / control the desktop unless those
capabilities are on. CVSS: **4.0 (medium)**, mitigated by safe-by-default
capabilities and the audit log.

### 2.4 SSRF — integrations (Home Assistant, weather)
**Verdict: no user-controlled target.** Endpoints are operator config
(`HOMEASSISTANT_URL`, fixed Open-Meteo hosts), never model/user input. The
model only supplies an `entity_id`, validated against
`^[a-z_]+\.[a-z0-9_]+$`, so it cannot inject a path or a host and cannot reach
`169.254.169.254`. The client-side URL (`JarvisApiClient`) now rejects any
scheme other than `http/https`, blocking `file:`/`gopher:` abuse. CVSS: **N/A**
(no attacker-controlled URL).

### 2.5 IDOR — Telegram bot / API sessions
**Verdict: not exploitable.** The bot derives sessions from
`message.from_user.id`, which Telegram sets server-side; a user cannot spoof
another user's id. On the API, every session is namespaced by the
authenticated principal (`user:<name>::<session_id>` in `app.py::_scoped`), so
passing someone else's `session_id` still resolves to *your* namespace — you
cannot read another account's history or memory. Login tokens and license keys
are stored only as SHA-256 hashes and compared in constant time. CVSS: **N/A**.

---

## 3. Controls already in place

- Capabilities (file-write / shell / desktop) **off by default**, gated + audited.
- Filesystem sandbox with traversal + symlink protection.
- Parameterised SQL everywhere; no `eval`/`exec`/`os.system`.
- Passwords: PBKDF2-HMAC-SHA256 (200k rounds, per-user salt).
- Tokens / license keys stored hashed; constant-time comparison.
- HMAC-signed billing webhook; idempotent by charge id.
- Secret redaction before memory storage and in logs.
- Rate limiting (token bucket) per session.

## 4. Hardening applied in this pass

- Client URL scheme validation (desktop + Android) — blocks `file:`/other schemes.
- `usedforsecurity=False` on the non-crypto embedding hash (was flagged as MD5).
- Documented `# nosec` justifications and `.bandit.yaml` policy.
- CI `security` job: pip-audit + bandit (gate) + semgrep + gitleaks.
- Always-on bot polling loop with exponential-backoff reconnect.

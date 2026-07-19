# Security

J.A.R.V.I.S. can act on your machine (files, shell, desktop) and your home
(smart devices). That power is governed so it is **safe by default** — but you
should understand the model before enabling the powerful bits.

## Safe by default

Dangerous capabilities are **off** out of the box and must be turned on
explicitly:

| Capability | Setting | Default |
|------------|---------|---------|
| Write files | `ALLOW_FILE_WRITE` | off |
| Run shell commands | `ALLOW_SHELL` | off |
| Control the desktop | `ALLOW_DESKTOP_CONTROL` | off |
| Read files | `ALLOW_FILE_READ` | on (sandboxed) |

Every attempt — allowed or denied — is checked by the **security module**
(`jarvis/security`) and written to an audit log (`AUDIT_LOG_PATH`) with secrets
redacted.

Other built-in protections:

- **Filesystem sandbox** — file tools are confined to `WORKSPACE_ROOT`; paths
  that escape it (`..`, absolute paths, symlinks) are rejected.
- **Secret redaction** — tokens, API keys and card-like numbers are stripped
  before anything is written to memory, history or the audit log.
- **Rate limiting** — per-session token bucket (`RATE_LIMIT_*`) guards against
  abuse and runaway cost.
- **Input validation** — e.g. Home Assistant entity ids are pattern-checked so
  a model-supplied value can't escape the API path.
- **Safe evaluation** — the calculator uses a restricted AST walker, never
  `eval`. All database access is parameterised (no SQL injection).

## Threat model & guidance

The main residual risk with any LLM agent is **prompt injection**: untrusted
text (a file you ask it to read, a web/API result, a message from another user)
could contain instructions trying to make the model call a dangerous tool.

Mitigations already in place: dangerous capabilities are off by default, gated,
and audited. To stay safe:

- **Never enable `ALLOW_SHELL`, `ALLOW_FILE_WRITE` or `ALLOW_DESKTOP_CONTROL`
  on a publicly reachable bot.** Combined with an open `TELEGRAM_ALLOWED_USERS`,
  that would let anyone drive those tools.
- On a shared bot, set `TELEGRAM_ALLOWED_USERS` to trusted user ids.
- Point `WORKSPACE_ROOT` at a dedicated folder, not your home directory.
- Keep secrets (API keys, bot tokens) in `.env` only — never commit them. If a
  token leaks, revoke it (e.g. `/revoke` in @BotFather) and issue a new one.
- Review the audit log when you enable powerful capabilities.

## Reporting

Found a vulnerability? Please report it privately via
[@deathgu11](https://t.me/deathgu11) rather than opening a public issue.

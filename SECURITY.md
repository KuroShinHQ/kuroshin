# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest (main) | ✅ |

Only the latest release on the `main` branch receives security fixes.

## Reporting a Vulnerability

Please **do NOT** open a public GitHub issue for security vulnerabilities.

Report privately instead:

1. **GitHub private vulnerability reporting** (preferred): Repo → Settings → Security → Report a vulnerability
2. **Email fallback**: security@kuroshin.dev

When reporting, please include:

- Affected version, tag, or commit SHA
- Description of the issue and why it is security-sensitive
- Steps to reproduce or a proof of concept
- Any relevant logs or payloads
- Potential impact and suggested mitigations (if known)

## Response

- Acknowledgment: within 3 business days
- Triage + next steps: after acknowledgment
- Confirmed issues: we will work on a fix and may publish a GitHub Security Advisory once remediation details are ready

## Out of Scope

- Do not include production secrets or personal data in reports
- Do not perform destructive testing against shared environments
- Do not publish public exploits before coordinated disclosure if the issue is unpatched
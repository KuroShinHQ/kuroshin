#!/usr/bin/env python3
"""Pre-commit secret/PII scanner for KuroShinHQ repos.

Blocks commits containing:
  - PII (owner email, 'ulucayto' handle)
  - Known API key patterns (AWS, Google, Telegram, GitHub, Slack, Stripe, JWT, private keys)
  - Sahibinden-style x-api-key/x-api-hash hex secrets
  - High-entropy hex/base64 strings near secret-context keywords

Allowlist (skip line if contains): [REDACTED], dummy, placeholder,
kuroshin-secret, <your-username>, example.com

Exit 1 on hit (commit blocked), 0 on clean.
"""
import sys
import re
import subprocess

ALLOW_SUBSTRINGS = (
    "[redacted]", "dummy", "placeholder", "kuroshin-secret",
    "<your-username>", "example.com", "your-app-password",
)
SKIP_PATHS = ("github_repos/", ".git/", "tools/gh.exe", "tools/tailwindcss.exe", "scripts/pre_commit_secret_scan.py")

PII_PATTERNS = [
    (re.compile(r"ulucayto456@gmail\.com", re.I), "PII: owner email"),
    (re.compile(r"\bulucayto\b", re.I), "PII: 'ulucayto' handle"),
]

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----"), "Private key block"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "Google API Key"),
    (re.compile(r"[0-9]{8,10}:[A-Za-z0-9_-]{35}"), "Telegram Bot Token"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{36}"), "GitHub Token"),
    (re.compile(r"xox[bp]-[0-9A-Za-z-]{10,}"), "Slack Token"),
    (re.compile(r"sk_live_[A-Za-z0-9]{20,}"), "Stripe Secret Key"),
    (re.compile(r"pk_live_[A-Za-z0-9]{20,}"), "Stripe Publishable Key"),
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "JWT Token"),
    (re.compile(r"x-api-key\s*[:=]\s*[0-9a-fA-F]{32,}", re.I), "Sahibinden-style x-api-key (hex)"),
    (re.compile(r"x-api-hash\s*[:=]\s*[0-9a-fA-F]{32,}", re.I), "Sahibinden-style x-api-hash (hex)"),
    (re.compile(r"x-devatt-token\s*[:=]\s*[0-9a-fA-F]{32,}", re.I), "Sahibinden-style x-devatt-token (hex)"),
]

CONTEXT_KEYWORDS = ("key", "secret", "token", "api", "auth", "password", "credential", "bearer")
HEX_LONG = re.compile(r"\b[0-9a-fA-F]{40,}\b")
B64_LONG = re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")


def is_allowed(text):
    low = text.lower()
    return any(s in low for s in ALLOW_SUBSTRINGS)


def should_skip_path(path):
    return any(path.startswith(s) or s in path for s in SKIP_PATHS)


def scan_line(text):
    hits = []
    if is_allowed(text):
        return hits
    for pat, label in PII_PATTERNS:
        for m in pat.finditer(text):
            hits.append((label, m.group(0)))
    for pat, label in SECRET_PATTERNS:
        for m in pat.finditer(text):
            hits.append((label, m.group(0)))
    low = text.lower()
    if any(kw in low for kw in CONTEXT_KEYWORDS):
        for m in HEX_LONG.finditer(text):
            hits.append(("High-entropy hex (secret context)", m.group(0)))
        for m in B64_LONG.finditer(text):
            hits.append(("High-entropy base64 (secret context)", m.group(0)))
    return hits


def get_staged_added_lines():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
        capture_output=True, text=True, check=True,
    )
    files = [f for f in result.stdout.splitlines() if f and not should_skip_path(f)]
    out = []
    for f in files:
        diff = subprocess.run(
            ["git", "diff", "--cached", "-U0", "--", f],
            capture_output=True, text=True,
        )
        current = 0
        for line in diff.stdout.splitlines():
            if line.startswith("@@"):
                m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
                if m:
                    current = int(m.group(1)) - 1
            elif line.startswith("+") and not line.startswith("+++"):
                current += 1
                out.append((f, current, line[1:]))
            elif not line.startswith("-"):
                current += 1
    return out


def main():
    added = get_staged_added_lines()
    if not added:
        return 0
    blocked = []
    for fpath, lineno, content in added:
        for label, match in scan_line(content):
            blocked.append((fpath, lineno, label, match, content.strip()))
    if not blocked:
        return 0
    sys.stderr.write(
        "\n\033[31m[pre-commit] BLOCKED: potential secret/PII detected\033[0m\n"
    )
    sys.stderr.write(
        "Fix: replace with [REDACTED] or move to .env (gitignored).\n\n"
    )
    for fpath, lineno, label, match, line in blocked:
        preview = match[:40] + ("..." if len(match) > 40 else "")
        sys.stderr.write(
            f"  {fpath}:{lineno}  [{label}]\n"
            f"    match: {preview}\n"
            f"    line : {line[:80]}\n\n"
        )
    sys.stderr.write(
        "If this is a false positive, commit with --no-verify "
        "(not recommended) or add to allowlist in scripts/pre_commit_secret_scan.py.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env sh
# Fails (exit 1) if staged files contain something shaped like a real API key.
# Usage: sh scripts/check-secrets.sh && git commit ...
git grep --cached -nI -E "sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|api[_-]?key\s*=\s*[A-Za-z0-9_-]{24,}"
status=$?
case "$status" in
  1) echo "Secret scan: no matches."; exit 0 ;;
  0) echo "Possible secret staged; not committing." >&2; exit 1 ;;
  *) echo "Secret scan itself failed (git grep exit $status)." >&2; exit 1 ;;
esac

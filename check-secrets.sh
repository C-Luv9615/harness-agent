#!/bin/bash
# Check for hardcoded paths, personal URLs, and API key leaks before distribution.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
FAIL=0

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
warn()  { printf '\033[33m%s\033[0m\n' "$*"; }

check() {
  local label="$1" pattern="$2"
  local hits
  hits=$(grep -rn --include='*.json' --include='*.md' --include='*.sh' \
    --include='*.yaml' --include='*.yml' --include='*.toml' --include='*.py' \
    -iE "$pattern" "$DIR" \
    --exclude-dir=.git \
    --exclude='check-secrets.sh' 2>/dev/null || true)
  if [ -n "$hits" ]; then
    red "❌ $label"
    echo "$hits" | sed 's/^/   /'
    echo
    FAIL=1
  else
    green "✅ $label — clean"
  fi
}

echo "🔍 Scanning $DIR ..."
echo

# 1. Hardcoded home paths
check "Hardcoded home directory (/home/xxx, /Users/xxx)" \
  '(/home/[a-zA-Z0-9_]+/|/Users/[a-zA-Z0-9_]+/)'

# 2. API keys / tokens
check "API keys (dataset-*, sk-*, key-*, token patterns)" \
  '(dataset-[a-zA-Z0-9]{8,}|sk-[a-zA-Z0-9]{20,}|api[_-]?key\s*[:=]\s*"[^"<]{8,}"|token\s*[:=]\s*"[^"<]{20,})'

# 3. Feishu MCP personal URLs (real ones, not placeholders)
check "Feishu MCP personal URL (non-placeholder)" \
  'mcp\.feishu\.cn/mcp/mcp_[a-zA-Z0-9]'

# 4. Email addresses (non-placeholder)
check "Personal email addresses" \
  '[a-zA-Z0-9._%+-]+@(xiaomi|mioffice|gmail|qq|163|outlook)\.(com|cn)'

# 5. Internal hostnames / IPs
check "Internal hostnames or IPs" \
  '(https?://10\.|https?://192\.168\.|https?://172\.(1[6-9]|2[0-9]|3[01])\.)'

# 6. Symlinks with absolute paths
SYMHITS=$(find "$DIR" -type l -exec readlink {} + 2>/dev/null | grep -E '^/' || true)
if [ -n "$SYMHITS" ]; then
  red "❌ Symlinks with absolute targets"
  find "$DIR" -type l -printf '   %p -> ' -exec readlink {} \; 2>/dev/null | grep -E '-> /[^$]'
  echo
  FAIL=1
else
  green "✅ Symlinks with absolute targets — clean"
fi

echo "─────────────────────────────"
if [ $FAIL -eq 0 ]; then
  green "🎉 All checks passed — safe to distribute."
else
  red "⚠️  Issues found above. Fix before distributing."
fi
exit $FAIL

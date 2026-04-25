#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_file() {
  [ -f "$1" ] || fail "expected file: $1"
}

assert_symlink() {
  [ -L "$1" ] || fail "expected symlink: $1"
  local actual
  actual="$(readlink "$1")"
  [ "$actual" = "$2" ] || fail "expected $1 -> $2, got $actual"
}

run_install() {
  local home_dir="$1"
  shift
  HOME="$home_dir" HARNESS_SKIP_PLUGIN_INSTALL=1 bash "$REPO_DIR/install.sh" "$@"
}

test_opencode_install_creates_expected_layout() {
  local tmp
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/home"

  run_install "$tmp/home" --opencode >/tmp/opencode-install.out 2>&1 || {
    cat /tmp/opencode-install.out >&2
    fail "opencode install failed"
  }

  local target="$tmp/home/.config/opencode"
  assert_symlink "$target/agents/harness.md" "$REPO_DIR/opencode/agents/harness.md"
  assert_symlink "$target/commands/fix.md" "$REPO_DIR/opencode/commands/fix.md"
  assert_symlink "$target/skills/session-handoff" "$REPO_DIR/opencode/skills/session-handoff"
  assert_file "$target/opencode.json"
  assert_file "$target/.gitignore"
  grep -q '"default_agent": "harness"' "$target/opencode.json" || fail "default_agent missing"
}

test_opencode_reinstall_preserves_existing_config() {
  local tmp
  tmp="$(mktemp -d)"
  mkdir -p "$tmp/home"

  run_install "$tmp/home" --opencode >/tmp/opencode-install-1.out 2>&1 || {
    cat /tmp/opencode-install-1.out >&2
    fail "initial opencode install failed"
  }

  local target="$tmp/home/.config/opencode"
  cat > "$target/opencode.json" <<'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "custom-agent"
}
EOF

  run_install "$tmp/home" --target opencode >/tmp/opencode-install-2.out 2>&1 || {
    cat /tmp/opencode-install-2.out >&2
    fail "second opencode install failed"
  }

  grep -q '"default_agent": "custom-agent"' "$target/opencode.json" || fail "existing opencode config was overwritten"
}

test_opencode_install_creates_expected_layout
test_opencode_reinstall_preserves_existing_config

echo "PASS: install.sh opencode tests"

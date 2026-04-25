#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$REPO_DIR/skills"
OPENCODE_SRC_DIR="$REPO_DIR/opencode"

usage() {
  echo "Usage: $0 --target <kiro-cli|claude|opencode> [--update]"
  echo "       $0 --kiro-cli|--claude|--opencode [--update]"
  echo ""
  echo "Install or update Harness Engineering Agent."
  echo ""
  echo "Options:"
  echo "  --target kiro-cli    Install to ~/.kiro/ (agents + skills)"
  echo "  --target claude      Install Claude Code plugin"
  echo "  --target opencode    Install to ~/.config/opencode/"
  echo "  --kiro-cli           Shorthand for --target kiro-cli"
  echo "  --claude             Shorthand for --target claude"
  echo "  --opencode           Shorthand for --target opencode"
  echo "  --update             Pull latest from git and re-install"
  exit 1
}

link_file() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  [ -L "$dst" ] || [ -f "$dst" ] && rm -f "$dst"
  ln -s "$src" "$dst"
}

copy_if_missing() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ ! -e "$dst" ]; then
    cp "$src" "$dst"
  fi
}

TARGET=""
UPDATE=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --target) TARGET="$2"; shift 2 ;;
    --kiro-cli|--kiro) TARGET="kiro-cli"; shift ;;
    --claude|--claude-code) TARGET="claude"; shift ;;
    --opencode) TARGET="opencode"; shift ;;
    --update) UPDATE=true; shift ;;
    *) usage ;;
  esac
done

[ -z "$TARGET" ] && usage

# ─── Update ─────────────────────────────────────────────────
if $UPDATE; then
  echo "🔄 Pulling latest changes ..."
  cd "$REPO_DIR"
  git pull --ff-only 2>&1 && echo "   ✅ Updated" || { echo "   ❌ git pull failed (merge conflict?). Resolve manually."; exit 1; }
  echo ""
fi

# ─── Kiro CLI ───────────────────────────────────────────────
install_kiro() {
  local KIRO_DIR="${HOME}/.kiro"
  echo "🔧 Installing Harness Agent for Kiro CLI ..."
  echo ""

  mkdir -p "$KIRO_DIR/agents" "$KIRO_DIR/skills"

  # Agent config
  cp "$REPO_DIR/kiro/harness.agent.md" "$KIRO_DIR/agents/"
  echo "   ✅ harness.agent.md"

  # harness.json — preserve existing feishu MCP URL if present
  local AGENT_FILE="$KIRO_DIR/agents/harness.json"
  local OLD_URL=""
  if [ -f "$AGENT_FILE" ]; then
    OLD_URL=$(python3 -c "
import json
with open('$AGENT_FILE') as f: cfg = json.load(f)
url = cfg.get('mcpServers',{}).get('feishu-mcp',{}).get('url','')
if url and '<YOUR_' not in url: print(url)
" 2>/dev/null || true)
  fi
  cp "$REPO_DIR/kiro/harness.json" "$AGENT_FILE"
  echo "   ✅ harness.json"

  # Skills — symlink
  for skill_dir in "$SKILLS_DIR"/*/; do
    local skill_name="$(basename "$skill_dir")"
    local dest="$KIRO_DIR/skills/$skill_name"
    if [ -L "$dest" ]; then unlink "$dest"; fi
    ln -s "$skill_dir" "$dest"
  done
  echo "   ✅ skills ($(ls -d "$SKILLS_DIR"/*/ | wc -l) linked)"

  # Feishu MCP — restore old URL or ask
  if [ -n "$OLD_URL" ]; then
    python3 -c "
import json
with open('$AGENT_FILE') as f: cfg = json.load(f)
cfg.setdefault('mcpServers',{})['feishu-mcp'] = {'url': '$OLD_URL'}
with open('$AGENT_FILE','w') as f: json.dump(cfg, f, indent=2, ensure_ascii=False)
"
    echo "   ✅ 飞书 MCP URL preserved"
  elif ! $UPDATE; then
    echo ""
    echo "📎 飞书 MCP 配置（可选，获取：飞书 > 设置 > MCP 服务 > 复制 URL）"
    read -p "   飞书 MCP URL（回车跳过）: " FEISHU_URL
    if [ -n "$FEISHU_URL" ]; then
      python3 -c "
import json
with open('$AGENT_FILE') as f: cfg = json.load(f)
cfg.setdefault('mcpServers',{})['feishu-mcp'] = {'url': '$FEISHU_URL'}
with open('$AGENT_FILE','w') as f: json.dump(cfg, f, indent=2, ensure_ascii=False)
print('   ✅ 飞书 MCP 已配置')
"
    else
      echo "   ⏭️  已跳过"
    fi
  fi

  echo ""
  echo "✅ Kiro CLI 安装完成"
  echo "   kiro-cli chat --agent harness"
}

# ─── Claude Code ────────────────────────────────────────────
install_claude() {
  local CLAUDE_DIR="$REPO_DIR/claude-code"
  echo "🔧 Installing Harness Agent for Claude Code ..."
  echo ""

  # Symlink shared skills (relative path so it works after clone)
  if [ -L "$CLAUDE_DIR/skills" ]; then unlink "$CLAUDE_DIR/skills"; fi
  ln -s ../skills "$CLAUDE_DIR/skills"
  echo "   ✅ skills → ../skills"

  # Register as global plugin
  if command -v claude &>/dev/null; then
    claude plugin add "$CLAUDE_DIR" 2>&1 && echo "   ✅ Plugin registered globally" || echo "   ⚠️  Registration failed, use: claude --plugin-dir $CLAUDE_DIR"
  else
    echo "   ⚠️  claude CLI not found, skipping registration"
  fi

  echo ""
  echo "✅ Claude Code 安装完成"
  echo "   直接启动 claude 即可（插件已全局注册）"
}

# ─── OpenCode ────────────────────────────────────────────────
install_opencode() {
  local OPENCODE_DIR="${HOME}/.config/opencode"
  local PLUGIN_PACKAGE="@opencode-ai/plugin@1.3.17"
  echo "🔧 Installing Harness Agent for OpenCode ..."
  echo ""

  mkdir -p "$OPENCODE_DIR/agents" "$OPENCODE_DIR/commands" "$OPENCODE_DIR/skills"

  local src_file
  for src_file in "$OPENCODE_SRC_DIR/agents"/*; do
    link_file "$src_file" "$OPENCODE_DIR/agents/$(basename "$src_file")"
  done
  echo "   ✅ agents"

  for src_file in "$OPENCODE_SRC_DIR/commands"/*; do
    link_file "$src_file" "$OPENCODE_DIR/commands/$(basename "$src_file")"
  done
  echo "   ✅ commands"

  local skill_dir skill_name
  for skill_dir in "$OPENCODE_SRC_DIR/skills"/*/; do
    skill_name="$(basename "$skill_dir")"
    skill_dir="${skill_dir%/}"
    if [ -L "$OPENCODE_DIR/skills/$skill_name" ] || [ -d "$OPENCODE_DIR/skills/$skill_name" ]; then
      rm -rf "$OPENCODE_DIR/skills/$skill_name"
    fi
    ln -s "$skill_dir" "$OPENCODE_DIR/skills/$skill_name"
  done
  echo "   ✅ skills ($(ls -d "$OPENCODE_SRC_DIR/skills"/*/ | wc -l | tr -d ' ') linked)"

  copy_if_missing "$OPENCODE_SRC_DIR/opencode.json" "$OPENCODE_DIR/opencode.json"
  copy_if_missing "$OPENCODE_SRC_DIR/.gitignore" "$OPENCODE_DIR/.gitignore"
  copy_if_missing "$OPENCODE_SRC_DIR/package.json" "$OPENCODE_DIR/package.json"
  echo "   ✅ config templates"

  if [ "${HARNESS_SKIP_PLUGIN_INSTALL:-0}" = "1" ]; then
    echo "   ⏭️  plugin install skipped (HARNESS_SKIP_PLUGIN_INSTALL=1)"
  elif command -v npm &>/dev/null; then
    (cd "$OPENCODE_DIR" && npm install "$PLUGIN_PACKAGE") >/dev/null 2>&1 \
      && echo "   ✅ OpenCode plugin installed ($PLUGIN_PACKAGE)" \
      || echo "   ⚠️  npm install failed, run manually: (cd $OPENCODE_DIR && npm install $PLUGIN_PACKAGE)"
  else
    echo "   ⚠️  npm not found, run manually: (cd $OPENCODE_DIR && npm install $PLUGIN_PACKAGE)"
  fi

  echo ""
  echo "✅ OpenCode 安装完成"
  echo "   opencode"
}

# ─── Dispatch ───────────────────────────────────────────────
echo ""
case "$TARGET" in
  kiro-cli|kiro) install_kiro ;;
  claude|claude-code) install_claude ;;
  opencode) install_opencode ;;
  *) echo "❌ Unknown target: $TARGET"; usage ;;
esac

#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$REPO_DIR/skills"

usage() {
  echo "Usage: $0 --target <kiro-cli|claude> [--update]"
  echo ""
  echo "Install or update Harness Engineering Agent."
  echo ""
  echo "Options:"
  echo "  --target kiro-cli    Install to ~/.kiro/ (agents + skills)"
  echo "  --target claude      Install to ~/.claude/ (plugin + skills)"
  echo "  --update             Pull latest from git and re-install"
  exit 1
}

TARGET=""
UPDATE=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --target) TARGET="$2"; shift 2 ;;
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

# ─── Dispatch ───────────────────────────────────────────────
echo ""
case "$TARGET" in
  kiro-cli|kiro) install_kiro ;;
  claude|claude-code) install_claude ;;
  *) echo "❌ Unknown target: $TARGET"; usage ;;
esac
